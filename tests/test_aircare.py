import hashlib
import hmac
import json
import tempfile
import threading
import unittest
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from aircare.core import Store, default_prefs, next_due
from aircare.collector import snapshot
from aircare.server import Application, handler
from aircare.transport import message_payload, request_json

NOW = datetime(2026, 10, 11, 0, 0, tzinfo=timezone.utc).timestamp()
PHONE = "6590000001"


class SystemTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "db")
        self.store = Store(self.path)
        self.store.add_home("home-a", "Home A", "a" * 32)
        self.store.add_home("home-b", "Private Home B", "b" * 32)
        self.store.add_user(PHONE, ["home-a"])
        self.app = Application(self.store, "s" * 32, "v" * 32, "123")
        self.seq = 0

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def command(self, text, now=NOW):
        self.seq += 1
        self.store.receive(str(self.seq), PHONE, text, now)

    def payload(self, value=12, observed=NOW):
        return {"devices": [{"id": "purifier", "room": "Living room", "name": "Xiaomi 4 Lite", "metrics": {"pm25": {"value": value, "observed_at": observed}}}]}

    def webhook(self, text="START", msg_id="wa-1", phone=PHONE, at=NOW, phone_id="123"):
        return json.dumps({"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {"metadata": {"phone_number_id": phone_id}, "messages": [{"id": msg_id, "from": phone, "timestamp": str(int(at)), "type": "text", "text": {"body": text}}]}}]}]}).encode()

    def signed(self, body):
        return {"X-Hub-Signature-256": "sha256=" + hmac.new(b"s" * 32, body, hashlib.sha256).hexdigest()}

    def test_household_isolation_and_unknown_phone(self):
        self.store.ingest("home-a", self.payload(), NOW)
        self.store.ingest("home-b", self.payload(999), NOW)
        report = self.store.report(PHONE, NOW)
        self.assertIn("12 ug/m3", report)
        self.assertNotIn("Private Home B", report)
        self.command("HOME home-b")
        self.assertIn("not available", self.store.db.execute("SELECT body FROM outbox").fetchone()[0])
        self.store.receive("unknown", "6590000099", "STATUS", NOW)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 1)

    def test_consent_required_and_stop_cancels(self):
        self.store.schedule(NOW)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 0)
        self.command("START", NOW - 60)
        self.store.schedule(NOW)
        self.command("STOP")
        self.assertEqual(self.store.db.execute("SELECT active FROM users").fetchone()[0], 0)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM outbox WHERE kind='scheduled' AND state='pending'").fetchone()[0], 0)

    def test_invalid_schedule_does_not_replace_settings(self):
        original = self.store.db.execute("SELECT prefs FROM users").fetchone()[0]
        for i, text in enumerate(["DAILY 25:00", "EVERY 0 HOURS", "EVERY 1 HOURS", "QUIET 08:00 08:00", "DAILY 23:00"]):
            self.command(text, NOW + i * 61)
            self.assertEqual(self.store.db.execute("SELECT prefs FROM users").fetchone()[0], original)

    def test_daily_interval_and_quiet(self):
        prefs = default_prefs("Asia/Singapore")
        self.assertEqual(next_due(prefs, NOW - 60), NOW)
        prefs.update(mode="interval", hours=4)
        self.assertEqual(next_due(prefs, NOW + 12 * 3600), NOW + 24 * 3600)
        self.command("DAILY 08:00,18:00")
        self.command("START", NOW + 61)
        self.assertEqual(self.store.db.execute("SELECT due FROM users").fetchone()[0], NOW + 10 * 3600)

    def test_dst_repeated_hour_is_not_sent_twice(self):
        prefs = default_prefs("America/New_York")
        prefs.update(times=["01:30"], quiet=["03:00", "04:00"])
        first = datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc).timestamp()
        self.assertEqual(next_due(prefs, first), datetime(2026, 11, 2, 6, 30, tzinfo=timezone.utc).timestamp())

    def test_scheduler_deduplicates_and_skips_backlog(self):
        self.command("START", NOW - 60)
        self.store.schedule(NOW)
        self.store.schedule(NOW)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM outbox WHERE kind='scheduled'").fetchone()[0], 1)
        self.store.schedule(NOW + 3 * 86400 + 600)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM outbox WHERE kind='scheduled'").fetchone()[0], 1)

    def test_signature_webhook_dedup_and_wrong_business(self):
        body = self.webhook()
        self.assertEqual(self.app.handle("POST", "/webhook", {}, body, NOW)[0], 403)
        for _ in range(2):
            self.assertEqual(self.app.handle("POST", "/webhook", self.signed(body), body, NOW)[0], 200)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 1)
        for body in (self.webhook(msg_id="other", phone_id="456"), self.webhook(msg_id="old", at=NOW-86400)):
            self.app.handle("POST", "/webhook", self.signed(body), body, NOW)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 1)

    def test_verification_and_payload_limits(self):
        self.assertEqual(self.app.handle("GET", "/webhook?hub.mode=subscribe&hub.verify_token=" + "v"*32 + "&hub.challenge=42", {})[:], (200, "42"))
        self.assertEqual(self.app.handle("POST", "/webhook", {}, b"x"*256001)[0], 413)

    def test_ingestion_auth_scopes_home(self):
        data = self.payload()
        data["home"] = "home-b"
        body = json.dumps(data).encode()
        self.assertEqual(self.app.handle("POST", "/v1/readings", {"Authorization": "Bearer wrong"}, body, NOW)[0], 403)
        self.assertEqual(self.app.handle("POST", "/v1/readings", {"Authorization": "Bearer " + "a"*32}, body, NOW)[0], 200)
        self.assertEqual(self.store.db.execute("SELECT home FROM readings").fetchone()[0], "home-a")

    def test_bad_metrics_and_times_rejected(self):
        for value, observed in [(float("nan"), NOW), (-1, NOW), (True, NOW), (12, NOW+61), (12, float("nan"))]:
            with self.assertRaises(ValueError):
                self.store.ingest("home-a", self.payload(value, observed), NOW)

    def test_old_or_missing_data_not_shown_as_current(self):
        self.store.ingest("home-a", self.payload(12, NOW-901), NOW)
        report = self.store.report(PHONE, NOW)
        self.assertIn("Old data", report)
        self.assertNotIn("12 ug/m3", report)
        self.store.ingest("home-a", self.payload(None), NOW)
        self.assertIn("No data", self.store.report(PHONE, NOW))

    def test_old_ingest_cannot_overwrite_new_metric(self):
        self.store.ingest("home-a", self.payload(12), NOW)
        self.store.ingest("home-a", self.payload(50, NOW-60), NOW)
        self.assertIn("12 ug/m3", self.store.report(PHONE, NOW))

    def test_delivery_failure_not_retried(self):
        self.command("STATUS")
        calls = []
        def fail(*args):
            calls.append(args)
            raise TimeoutError()
        self.store.deliver_one(fail, NOW)
        self.store.deliver_one(fail, NOW)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.store.db.execute("SELECT state FROM outbox").fetchone()[0], "unknown")

    def test_queued_report_cannot_cross_into_quiet_hours(self):
        self.command("START")
        quiet_start = NOW + 14 * 3600
        with self.store.db:
            self.store.db.execute("DELETE FROM outbox")
            self.store.queue(PHONE, "scheduled", "", quiet_start-60)
        calls = []
        self.store.deliver_one(lambda *args: calls.append(args), quiet_start)
        self.assertEqual(calls, [])
        self.assertEqual(self.store.db.execute("SELECT state FROM outbox").fetchone()[0], "cancelled")

    def test_delivery_window_and_status(self):
        self.command("START", NOW-86400)
        with self.store.db:
            self.store.db.execute("DELETE FROM outbox")
            self.store.queue(PHONE, "scheduled", "", NOW)
        calls = []
        def sender(*args):
            calls.append(args)
            return "meta-1"
        self.store.deliver_one(sender, NOW)
        self.assertTrue(calls[0][2])
        self.store.delivery_status("meta-1", "read")
        self.store.delivery_status("meta-1", "sent")
        self.assertEqual(self.store.db.execute("SELECT state FROM outbox").fetchone()[0], "read")

    def test_template_is_single_line_bounded_and_no_spam_split(self):
        payload = message_payload(PHONE, "home\n" * 1000, True, "1", "air_care_report", "en_US")
        text = payload["template"]["components"][0]["parameters"][0]["text"]
        self.assertNotIn("\n", text)
        self.assertLess(len(text), 801)
        self.assertIn("shortened", text)
        self.assertEqual(payload["biz_opaque_callback_data"], "1")

    def test_restart_preserves_preferences_and_suppresses_uncertain_send(self):
        self.command("EVERY 6 HOURS")
        with self.store.db:
            self.store.db.execute("UPDATE outbox SET state='sending'")
        self.store.db.close()
        self.store = Store(self.path, recover=True)
        self.assertEqual(json.loads(self.store.db.execute("SELECT prefs FROM users").fetchone()[0])["hours"], 6)
        self.assertEqual(self.store.db.execute("SELECT state FROM outbox").fetchone()[0], "unknown")

    def test_rate_limit_preserves_stop(self):
        for _ in range(10):
            self.command("STATUS")
        self.command("STOP")
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 6)
        self.assertEqual(self.store.db.execute("SELECT active FROM users").fetchone()[0], 0)

    def test_room_filter_and_all(self):
        data = self.payload()
        data["devices"].append({"id":"bed", "room":"Bedroom", "name":"Bedroom device", "metrics":{}})
        self.store.ingest("home-a", data, NOW)
        self.command("ROOM Living room")
        self.assertNotIn("Bedroom device", self.store.report(PHONE, NOW))
        self.command("ALL")
        self.assertIn("Bedroom device", self.store.report(PHONE, NOW))

    def test_collector_preserves_timestamp_and_checks_units(self):
        config = {"devices": [{"id":"x", "name":"Device", "room":"Room", "metrics":{"pm25":{"entity_id":"sensor.pm"}}}]}
        states = [{"entity_id":"sensor.pm", "state":"12", "last_updated":"2026-10-10T23:00:00+00:00", "attributes":{"unit_of_measurement":"µg/m³"}}]
        reading = snapshot(config, states, NOW)["devices"][0]["metrics"]["pm25"]
        self.assertEqual(reading, {"value":12, "observed_at":NOW-3600})
        states[0]["attributes"]["unit_of_measurement"] = "AQI"
        self.assertIsNone(snapshot(config, states, NOW)["devices"][0]["metrics"]["pm25"]["value"])

    def test_collector_unavailable_and_missing_entity(self):
        config = {"devices": [{"id":"x", "name":"Device", "room":"Room", "metrics":{"humidity":{"entity_id":"sensor.rh"}}}]}
        self.assertIsNone(snapshot(config, [], NOW)["devices"][0]["metrics"]["humidity"]["value"])
        states = [{"entity_id":"sensor.rh", "state":"unavailable", "last_updated":"2026-10-11T00:00:00+00:00", "attributes":{"unit_of_measurement":"%"}}]
        self.assertIsNone(snapshot(config, states, NOW)["devices"][0]["metrics"]["humidity"]["value"])

    def test_real_local_http_ingestion_and_webhook_to_fake_sender(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.app))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            import time
            now = time.time()
            self.assertTrue(request_json(url+"/v1/readings", "POST", self.payload(observed=now), "a"*32)["ok"])
            body = self.webhook("STATUS", at=now)
            req = urllib.request.Request(url+"/webhook", data=body, headers=self.signed(body))
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.status, 200)
            sent = []
            self.store.deliver_one(lambda *args: sent.append(args) or "fake-meta-id", now)
            self.assertIn("12 ug/m3", sent[0][1])
            self.assertFalse(sent[0][2])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
