"""Small pilot server; bind behind a TLS reverse proxy. Run one process only."""
import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from .core import Store
from .transport import MetaSender
from .cloud import from_environment


class Application:
    def __init__(self, store, secret, verify_token, phone_id):
        if min(len(secret), len(verify_token)) < 16:
            raise ValueError("Webhook secrets must have at least 16 characters")
        self.store, self.secret, self.verify_token, self.phone_id = store, secret, verify_token, phone_id

    def handle(self, method, path, headers, body=b"", now=None):
        now = now if now is not None else time.time()
        url = urlparse(path)
        if method == "GET" and url.path == "/healthz":
            return 200, "ok"
        if method == "GET" and url.path == "/webhook":
            query = parse_qs(url.query)
            if query.get("hub.mode") == ["subscribe"] and hmac.compare_digest(query.get("hub.verify_token", [""])[0], self.verify_token):
                return 200, query.get("hub.challenge", [""])[0]
            return 403, "forbidden"
        if method != "POST" or url.path not in ("/webhook", "/v1/readings"):
            return 404, "not found"
        if len(body) > 256_000:
            return 413, "too large"
        if url.path == "/webhook":
            expected = "sha256=" + hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(headers.get("X-Hub-Signature-256", ""), expected):
                return 403, "forbidden"
        else:
            auth = headers.get("Authorization", "")
            home = self.store.authenticate(auth[7:]) if auth.startswith("Bearer ") else None
            if home is None:
                return 403, "forbidden"
        try:
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError()
            if url.path == "/v1/readings":
                self.store.ingest(home, data, now)
            else:
                if data.get("object") != "whatsapp_business_account":
                    return 200, "ignored"
                for entry in data.get("entry", []):
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        if value.get("metadata", {}).get("phone_number_id") != self.phone_id:
                            continue
                        for message in value.get("messages", []):
                            # Reject old replayed messages even after ID retention expires.
                            observed = float(message["timestamp"])
                            if not now - 300 <= observed <= now + 60:
                                continue
                            text = message.get("text", {}).get("body", "HELP")
                            if message.get("type") == "interactive":
                                text = message.get("interactive", {}).get("button_reply", {}).get("id", "HELP")
                            if len(text) <= 256:
                                self.store.receive(str(message["id"]), str(message["from"]), text, now)
                        for status in value.get("statuses", []):
                            self.store.delivery_status(status["id"], status["status"], status.get("biz_opaque_callback_data"))
        except (ValueError, TypeError, KeyError, AttributeError):
            return 400, "invalid payload"
        return 200, '{"ok":true}'


def handler(app):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(20)

        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 256_000 or self.headers.get("Transfer-Encoding"):
                    code, text = 413, "too large"
                else:
                    code, text = app.handle(self.command, self.path, self.headers, self.rfile.read(length))
            except (ValueError, TimeoutError):
                code, text = 400, "invalid request"
            except Exception:
                # Do not expose payloads, tokens, numbers, or stack traces.
                code, text = 500, "internal error"
            encoded = text.encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format, *args):
            pass  # URLs can contain verification secrets.
    return Handler


def main():
    os.umask(0o077)
    database = os.environ.get("AIRCARE_DB", "data/aircare.db")
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    store = Store(database, recover=True)
    sender = MetaSender()
    app = Application(store, os.environ["META_APP_SECRET"], os.environ["META_VERIFY_TOKEN"], sender.phone_id)
    stop = threading.Event()
    cloud = from_environment(store)

    def cloud_worker():
        while not stop.is_set():
            results = cloud.poll(time.time())
            if not all(results):
                print("Cloud collection failed. Check integration connection and source configuration.", flush=True)
            stop.wait(60)

    if cloud.sources:
        threading.Thread(target=cloud_worker, daemon=True).start()

    def worker():
        while not stop.is_set():
            try:
                store.schedule(time.time())
                for _ in range(20):
                    if not store.deliver_one(sender, time.time()):
                        break
            except Exception:
                print("Worker error. Check service and database availability.", flush=True)
            stop.wait(5)
    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer((os.environ.get("AIRCARE_BIND", "127.0.0.1"), int(os.environ.get("PORT", "8080"))), handler(app))
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
