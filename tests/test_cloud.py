import json
import tempfile
import unittest
from pathlib import Path
from aircare.cloud import CloudPoller, load_sources
from aircare.core import Store

NOW = 1791676800


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(str(Path(self.temp.name) / "state.db"))
        self.store.add_home("home-a", "Home A", "a"*32)
        self.store.add_home("home-b", "Home B", "b"*32)
        self.store.add_user("6590000001", ["home-a"])
        self.item = {"home":"home-a", "ha_url":"https://cloud.example", "token_env":"CLOUD_HA_TOKEN_A", "devices":[{"id":"d1", "name":"Purifier", "room":"Living room", "metrics":{"pm25":{"entity_id":"sensor.pm"}}}]}

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def load(self, items=None):
        return load_sources(json.dumps(items or [self.item]), {"CLOUD_HA_TOKEN_A":"secret"})

    def test_https_required_and_credentials_not_in_url(self):
        for url in ["http://example.com", "https://user:pass@example.com", "https://example.com?token=secret", "https://example.com#secret"]:
            self.item["ha_url"] = url
            with self.assertRaises(ValueError):
                self.load()

    def test_duplicate_home_and_missing_secret_rejected(self):
        with self.assertRaises(ValueError):
            self.load([self.item, self.item])
        with self.assertRaises(ValueError):
            load_sources(json.dumps([self.item]), {})

    def test_cloud_readings_enter_only_assigned_home(self):
        def fetch(url, token):
            self.assertEqual(url, "https://cloud.example/api/states")
            self.assertEqual(token, "secret")
            return [{"entity_id":"sensor.pm", "state":"12", "attributes":{"unit_of_measurement":"ug/m3"}, "last_reported":"2026-10-11T00:00:00Z"}]
        self.assertEqual(CloudPoller(self.store, self.load(), fetch).poll(NOW), [True])
        self.assertEqual(self.store.db.execute("SELECT home FROM readings").fetchone()[0], "home-a")
        self.assertIn("12 ug/m3", self.store.report("6590000001", NOW))

    def test_network_failure_does_not_refresh_old_data(self):
        self.store.ingest("home-a", {"devices":[{"id":"d1","room":"Living room","name":"Purifier","metrics":{"pm25":{"value":12,"observed_at":NOW-1000}}}]}, NOW-1000)
        def fail(*args, **kwargs):
            raise TimeoutError("secret should not be logged")
        self.assertEqual(CloudPoller(self.store, self.load(), fail).poll(NOW), [False])
        self.assertEqual(self.store.db.execute("SELECT received FROM readings").fetchone()[0], NOW-1000)
        self.assertIn("Old data", self.store.report("6590000001", NOW))

    def test_one_failed_home_does_not_block_another(self):
        second = {**self.item, "home":"home-b", "ha_url":"https://other.example"}
        def fetch(url, token):
            if "cloud.example" in url:
                raise TimeoutError()
            return []
        self.assertEqual(CloudPoller(self.store, self.load([self.item, second]), fetch).poll(NOW), [False, True])

    def test_empty_cloud_configuration_preserves_legacy_mode(self):
        self.assertEqual(load_sources("[]", {}), [])


if __name__ == "__main__":
    unittest.main()
