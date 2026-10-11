"""Read explicitly mapped Home Assistant entities and push one household snapshot."""
import json
import math
import os
import sys
import time
from datetime import datetime
from urllib.parse import urlparse
from .core import METRICS
from .transport import request_json

UNITS = {"pm25": {"µg/m³", "μg/m³", "ug/m3"}, "humidity": {"%"},
         "temperature": {"°C", "C"}, "filter": {"%"}}


def snapshot(config, states, now):
    indexed = {state["entity_id"]: state for state in states}
    result = []
    for device in config["devices"]:
        readings = {}
        for metric, mapping in device["metrics"].items():
            if metric not in METRICS:
                raise ValueError("Unsupported metric")
            entity = indexed.get(mapping["entity_id"])
            value, observed = None, now
            if entity:
                attrs = entity.get("attributes", {})
                raw = attrs.get(mapping["attribute"]) if mapping.get("attribute") else entity.get("state")
                # Never turn HA retrieval time into a fresh sensor measurement time.
                timestamp = entity.get("last_reported") or entity.get("last_updated")
                try:
                    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        raise ValueError("Missing timezone")
                    observed = parsed.timestamp()
                    if not 0 < observed <= now + 60:
                        raise ValueError("Future timestamp")
                    if entity.get("state") not in ("unavailable", "unknown"):
                        if metric == "tank_full":
                            value = {"on": 1, "off": 0}.get(str(raw).lower())
                        else:
                            # Attribute units must be explicitly declared by the installer.
                            unit = mapping.get("unit") if mapping.get("attribute") else attrs.get("unit_of_measurement")
                            if unit in UNITS[metric] and not isinstance(raw, bool):
                                candidate = float(raw)
                                if math.isfinite(candidate) and METRICS[metric][2] <= candidate <= METRICS[metric][3]:
                                    value = candidate
                except (ValueError, TypeError, AttributeError):
                    value, observed = None, now
            readings[metric] = {"value": value, "observed_at": observed}
        result.append({"id": device["id"], "room": device["room"], "name": device["name"], "metrics": readings})
    return {"devices": result}


def main():
    with open(sys.argv[1], encoding="utf-8") as file:
        config = json.load(file)
    server = config["server_url"].rstrip("/")
    if urlparse(server).scheme != "https":
        raise ValueError("Use HTTPS for the reporting server")
    ha = config["ha_url"].rstrip("/")
    if urlparse(ha).scheme not in ("http", "https"):
        raise ValueError("Invalid Home Assistant URL")
    once = "--once" in sys.argv
    while True:
        try:
            states = request_json(ha + "/api/states", token=os.environ["HA_TOKEN"])
            payload = snapshot(config, states, time.time())
            request_json(server + "/v1/readings", "POST", payload, os.environ["AIRCARE_HOME_TOKEN"])
        except Exception:
            print("Collection failed. Check the connection, credentials, and entity mapping.", flush=True)
            if once:
                raise SystemExit(1)
        if once:
            return
        time.sleep(60)


if __name__ == "__main__":
    main()
