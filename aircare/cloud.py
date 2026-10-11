"""Pull from operator-hosted cloud integrations; nothing runs in the user's home.

This is an adapter for a cloud-hosted Home Assistant instance, not a direct
Dyson or Xiaomi login implementation. Those integrations must be commissioned.
"""
import json
import os
import re
from urllib.parse import urlsplit
from .collector import snapshot
from .transport import request_json


def load_sources(raw, environ):
    sources = json.loads(raw)
    if not isinstance(sources, list) or len(sources) > 20:
        raise ValueError("Configure at most 20 cloud sources")
    homes = set()
    validated = []
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("Invalid cloud source")
        home = item.get("home", "")
        if not re.fullmatch(r"[a-z0-9-]{1,30}", home) or home in homes:
            raise ValueError("Each source must have a unique home code")
        homes.add(home)
        url = urlsplit(item.get("ha_url", ""))
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("Use an HTTPS cloud integration URL without credentials or query parameters")
        key = item.get("token_env", "")
        if not re.fullmatch(r"CLOUD_HA_TOKEN_[A-Z0-9_]+", key) or not environ.get(key):
            raise ValueError("Set the cloud integration token in its separate secret environment variable")
        devices = item.get("devices")
        if not isinstance(devices, list) or not 1 <= len(devices) <= 50:
            raise ValueError("Configure 1 to 50 devices for each home")
        # Check labels and metric shape early using the same ingest validation later.
        snapshot(item, [], 1)
        validated.append({**item, "ha_url": item["ha_url"].rstrip("/"), "token": environ[key]})
    return validated


class CloudPoller:
    def __init__(self, store, sources, fetch=request_json):
        self.store, self.sources, self.fetch = store, sources, fetch

    def poll(self, now):
        results = []
        for source in self.sources:
            try:
                with self.store.lock:
                    exists = self.store.db.execute("SELECT 1 FROM homes WHERE id=?", (source["home"],)).fetchone()
                if not exists:
                    raise ValueError("Home has not been enrolled")
                states = self.fetch(source["ha_url"] + "/api/states", token=source["token"])
                if not isinstance(states, list):
                    raise ValueError("Invalid cloud states")
                self.store.ingest(source["home"], snapshot(source, states, now), now)
                results.append(True)
            except Exception:
                # Leave prior timestamps unchanged. Never fabricate fresh data on failure.
                # Return only success flags; no tokens, URLs, or household names in logs.
                results.append(False)
        return results


def from_environment(store):
    return CloudPoller(store, load_sources(os.environ.get("AIRCARE_CLOUD_SOURCES_JSON", "[]"), os.environ))
