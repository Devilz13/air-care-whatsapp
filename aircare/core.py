"""Deterministic commands, isolated household storage, and durable delivery queue."""
import hashlib
import hmac
import json
import math
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
METRICS = {
    "pm25": ("PM2.5", "ug/m3", 0, 5000),
    "humidity": ("Humidity", "%", 0, 100),
    "temperature": ("Temperature", "C", -40, 85),
    "filter": ("Filter remaining", "%", 0, 100),
    "tank_full": ("Water tank full", "", 0, 1),
}
HELP = ("Send a command:\nSTATUS — read your report\nDAILY 08:00 — set a daily report"
        "\nDAILY 08:00,18:00 — set two reports\nEVERY 4 HOURS — set an interval"
        "\nQUIET 22:00 08:00 — set quiet hours\nHOMES — list your homes"
        "\nHOME code — select a home\nROOM name — select a room\nALL — select all your homes"
        "\nSETTINGS — read your settings\nSTOP — stop reports\nSTART — start reports"
        "\nTimes use your configured local time. Ask your helper to change rooms or access.")


def stamp(now=None):
    return (now or datetime.now(UTC)).timestamp()


def clock(value):
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise ValueError("Use a time such as 08:00 or 18:30.")
    h, m = map(int, value.split(":"))
    return h * 60 + m


def quiet(minute, start, end):
    return start <= minute < end if start < end else minute >= start or minute < end


def next_due(prefs, after):
    """Find next real UTC minute; handles skipped/repeated local times safely."""
    zone = ZoneInfo(prefs["timezone"])
    start, end = map(clock, prefs["quiet"])
    base = int(after // 60) * 60 + 60
    if prefs["mode"] == "interval":
        base = int((after + prefs["hours"] * 3600 + 59) // 60) * 60
    times = {clock(x) for x in prefs["times"]}
    for offset in range(3 * 24 * 60):
        candidate = base + offset * 60
        local = datetime.fromtimestamp(candidate, zone)
        minute = local.hour * 60 + local.minute
        if quiet(minute, start, end):
            continue
        if prefs["mode"] == "interval" or (minute in times and local.fold == 0):
            return candidate
    raise ValueError("All report times are inside quiet hours. Change the report times or quiet hours.")


def default_prefs(zone):
    ZoneInfo(zone)
    return {"timezone": zone, "mode": "daily", "times": ["08:00"], "hours": 4,
            "quiet": ["22:00", "08:00"], "home": None, "room": None}


class Store:
    def __init__(self, path, recover=False):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS homes(id TEXT PRIMARY KEY,name TEXT NOT NULL,token TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS users(phone TEXT PRIMARY KEY,active INTEGER NOT NULL DEFAULT 0,
          prefs TEXT NOT NULL,last_inbound REAL NOT NULL DEFAULT 0,due REAL);
        CREATE TABLE IF NOT EXISTS access(phone TEXT REFERENCES users ON DELETE CASCADE,
          home TEXT REFERENCES homes ON DELETE CASCADE,PRIMARY KEY(phone,home));
        CREATE TABLE IF NOT EXISTS readings(home TEXT REFERENCES homes ON DELETE CASCADE,
          device TEXT,room TEXT,name TEXT,metrics TEXT,received REAL,PRIMARY KEY(home,device));
        CREATE TABLE IF NOT EXISTS inbound(id TEXT PRIMARY KEY,received REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY,phone TEXT REFERENCES users ON DELETE CASCADE,
          kind TEXT,body TEXT,created REAL,state TEXT DEFAULT 'pending',provider_id TEXT,error TEXT);
        """)
        # A process restart must not replay a possibly accepted remote send.
        if recover:
            with self.db:
                self.db.execute("UPDATE outbox SET state='unknown',error='restart during send' WHERE state='sending'")

    def add_home(self, home, name, token):
        if not re.fullmatch(r"[a-z0-9-]{1,30}", home) or not 1 <= len(name) <= 50 or len(token) < 32:
            raise ValueError("Use a short home code, a name, and a token of at least 32 characters.")
        with self.lock, self.db:
            self.db.execute("INSERT INTO homes VALUES(?,?,?)", (home, name, hashlib.sha256(token.encode()).hexdigest()))

    def add_user(self, phone, homes, zone="Asia/Singapore"):
        if not re.fullmatch(r"[1-9]\d{7,14}", phone) or not homes:
            raise ValueError("Use country code and digits, without +; supply at least one home.")
        with self.lock, self.db:
            self.db.execute("INSERT INTO users(phone,prefs) VALUES(?,?)", (phone, json.dumps(default_prefs(zone))))
            for home in homes:
                self.db.execute("INSERT INTO access VALUES(?,?)", (phone, home))

    def authenticate(self, token):
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            for row in self.db.execute("SELECT id,token FROM homes"):
                if hmac.compare_digest(row["token"], digest):
                    return row["id"]
        return None

    def ingest(self, home, payload, now):
        devices = payload.get("devices")
        if not isinstance(devices, list) or not 1 <= len(devices) <= 50:
            raise ValueError("Supply 1 to 50 devices.")
        cleaned = []
        seen = set()
        for device in devices:
            for key in ("id", "room", "name"):
                if not isinstance(device.get(key), str) or not 1 <= len(device[key]) <= 60 or any(ord(c) < 32 for c in device[key]):
                    raise ValueError("Invalid device label.")
            if device["id"] in seen:
                raise ValueError("Duplicate device.")
            seen.add(device["id"])
            metrics = device.get("metrics")
            if not isinstance(metrics, dict) or not set(metrics) <= METRICS.keys():
                raise ValueError("Invalid metrics.")
            checked = {}
            for key, reading in metrics.items():
                if not isinstance(reading, dict):
                    raise ValueError("Invalid reading.")
                value, observed = reading.get("value"), reading.get("observed_at")
                if value is not None:
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                        raise ValueError("Invalid numeric value.")
                    if not METRICS[key][2] <= value <= METRICS[key][3] or (key == "tank_full" and value not in (0, 1)):
                        raise ValueError("Reading outside supported range.")
                if isinstance(observed, bool) or not isinstance(observed, (int, float)) or not math.isfinite(observed) or not 0 < observed <= now + 60:
                    raise ValueError("Invalid observation time.")
                checked[key] = {"value": value, "observed_at": observed}
            cleaned.append((device, checked))
        with self.lock, self.db:
            for device, metrics in cleaned:
                old = self.db.execute("SELECT metrics FROM readings WHERE home=? AND device=?", (home, device["id"])).fetchone()
                if old:
                    previous = json.loads(old[0])
                    for key, reading in metrics.items():
                        if key in previous and reading["observed_at"] < previous[key]["observed_at"]:
                            metrics[key] = previous[key]
                self.db.execute("INSERT OR REPLACE INTO readings VALUES(?,?,?,?,?,?)",
                                (home, device["id"], device["room"], device["name"], json.dumps(metrics), now))

    def report(self, phone, now):
        user = self.db.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        prefs = json.loads(user["prefs"])
        local = datetime.fromtimestamp(now, ZoneInfo(prefs["timezone"]))
        lines = [f"AIR CARE | {local:%d %b %H:%M} ({prefs['timezone']})"]
        homes = self.db.execute("SELECT h.* FROM homes h JOIN access a ON h.id=a.home WHERE a.phone=? ORDER BY h.name", (phone,)).fetchall()
        for home in homes:
            if prefs["home"] and prefs["home"] != home["id"]:
                continue
            lines.append(f"\nHOME: {home['name']}")
            rows = self.db.execute("SELECT * FROM readings WHERE home=? ORDER BY room,name", (home["id"],)).fetchall()
            if not rows:
                lines.append("No device data. Ask your helper to check the gateway.")
            room = None
            for row in rows:
                if prefs.get("room") and row["room"].casefold() != prefs["room"]:
                    continue
                if row["room"] != room:
                    room = row["room"]
                    lines.append(f"ROOM: {room}")
                lines.append(row["name"])
                metrics = json.loads(row["metrics"])
                if not metrics:
                    lines.append("No supported readings.")
                for key, reading in metrics.items():
                    label, unit, _, _ = METRICS[key]
                    age = now - reading["observed_at"]
                    if reading["value"] is None:
                        result = "No data"
                    elif age > 900 or now - row["received"] > 900:
                        result = f"Old data ({max(0, int(age // 60))} min). Check device."
                    elif key == "tank_full":
                        result = "Yes. Empty the tank." if reading["value"] else "No"
                    else:
                        result = f"{reading['value']:g} {unit} (updated {max(0,int(age//60))} min ago)"
                    lines.append(f"{label}: {result}")
        lines.append("\nPM2.5 is a particle reading, not PSI or AQI. Send HELP for options.")
        return "\n".join(lines)

    def queue(self, phone, kind, body, now):
        self.db.execute("INSERT INTO outbox(phone,kind,body,created) VALUES(?,?,?,?)", (phone, kind, body, now))

    def receive(self, message_id, phone, text, now):
        with self.lock, self.db:
            user = self.db.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
            # Unknown numbers get no household information and no outbound message.
            if not user or self.db.execute("SELECT 1 FROM inbound WHERE id=?", (message_id,)).fetchone():
                return
            self.db.execute("INSERT INTO inbound VALUES(?,?)", (message_id, now))
            command = " ".join(text.strip().upper().split())
            # Bound inbound-triggered outbound volume. STOP always takes effect.
            count = self.db.execute("SELECT count(*) FROM outbox WHERE phone=? AND kind='reply' AND created>?", (phone, now - 60)).fetchone()[0]
            prefs = json.loads(user["prefs"])
            active, due = user["active"], user["due"]
            response = HELP
            if command in ("STOP", "PAUSE"):
                active, due = 0, None
                self.db.execute("UPDATE outbox SET state='cancelled' WHERE phone=? AND state='pending'", (phone,))
                response = "Reports stopped. Send START to start reports again."
            elif count >= 6:
                return
            elif command == "START":
                active = 1
                due = next_due(prefs, now)
                response = "Reports started. " + self.settings(prefs) + " Send STOP at any time."
            elif command in ("STATUS", "NOW", "1"):
                response = self.report(phone, now)
            elif command == "SETTINGS":
                response = ("Reports on. " if active else "Reports off. ") + self.settings(prefs)
            elif command == "HOMES":
                response = "Your homes:\n" + "\n".join(f"{r[0]}: {r[1]}" for r in self.db.execute("SELECT h.id,h.name FROM homes h JOIN access a ON h.id=a.home WHERE a.phone=?", (phone,)))
            elif command.startswith("HOME ") or command == "ALL":
                target = command[5:].lower() if command != "ALL" else None
                if target and not self.db.execute("SELECT 1 FROM access WHERE phone=? AND home=?", (phone, target)).fetchone():
                    response = "Home not available. Send HOMES to see your homes."
                else:
                    prefs["home"] = target
                    prefs["room"] = None
                    response = "Report selection changed. Send STATUS to read your report."
                    self.db.execute("UPDATE outbox SET state='cancelled' WHERE phone=? AND kind='scheduled' AND state='pending'", (phone,))
            elif command.startswith("ROOM "):
                target = command[5:].casefold()
                rows = self.db.execute("SELECT r.room,r.home FROM readings r JOIN access a ON r.home=a.home WHERE a.phone=?", (phone,)).fetchall()
                if any(r["room"].casefold() == target and (not prefs["home"] or r["home"] == prefs["home"]) for r in rows):
                    prefs["room"] = target
                    response = "Room selected. Send STATUS for your report. Send ALL to show all rooms and homes."
                    self.db.execute("UPDATE outbox SET state='cancelled' WHERE phone=? AND kind='scheduled' AND state='pending'", (phone,))
                else:
                    response = "Room not available. Use the room name from your report."
            elif command.startswith(("DAILY ", "EVERY ", "QUIET ")):
                proposed = dict(prefs)
                try:
                    if command.startswith("DAILY "):
                        times = sorted(set(command[6:].replace(" ", "").split(",")))
                        if not 1 <= len(times) <= 4:
                            raise ValueError("Set one to four report times.")
                        for value in times:
                            clock(value)
                        proposed.update(mode="daily", times=times)
                    elif command.startswith("EVERY "):
                        match = re.fullmatch(r"EVERY (\d{1,2}) HOURS?", command)
                        if not match or not 2 <= int(match[1]) <= 24:
                            raise ValueError("Use EVERY 4 HOURS. Set 2 to 24 hours.")
                        proposed.update(mode="interval", hours=int(match[1]))
                    else:
                        parts = command.split()
                        if len(parts) != 3:
                            raise ValueError("Use QUIET 22:00 08:00.")
                        if clock(parts[1]) == clock(parts[2]):
                            raise ValueError("Use different quiet start and end times.")
                        proposed["quiet"] = parts[1:]
                    new_due = next_due(proposed, now)
                    prefs, due = proposed, new_due if active else None
                    self.db.execute("UPDATE outbox SET state='cancelled' WHERE phone=? AND kind='scheduled' AND state='pending'", (phone,))
                    response = "Settings saved. " + self.settings(prefs)
                    if not active:
                        response += " Send START to allow scheduled reports."
                except ValueError as exc:
                    response = str(exc)
            self.db.execute("UPDATE users SET active=?,prefs=?,due=?,last_inbound=? WHERE phone=?", (active, json.dumps(prefs), due, now, phone))
            if count < 6:
                self.queue(phone, "reply", response, now)

    @staticmethod
    def settings(prefs):
        schedule = "Daily at " + ", ".join(prefs["times"]) if prefs["mode"] == "daily" else f"Every {prefs['hours']} hours"
        return f"{schedule}. Quiet hours: {' to '.join(prefs['quiet'])}. Time zone: {prefs['timezone']}. Home: {prefs['home'] or 'all'}. Room: {prefs.get('room') or 'all'}."

    def schedule(self, now):
        with self.lock, self.db:
            for user in self.db.execute("SELECT * FROM users WHERE active=1 AND due<=?", (now,)).fetchall():
                prefs = json.loads(user["prefs"])
                local = datetime.fromtimestamp(now, ZoneInfo(prefs["timezone"]))
                # Skip missed slots after an outage; never flood a backlog.
                if now - user["due"] <= 300 and not quiet(local.hour * 60 + local.minute, *map(clock, prefs["quiet"])):
                    self.queue(user["phone"], "scheduled", "", now)
                self.db.execute("UPDATE users SET due=? WHERE phone=?", (next_due(prefs, now), user["phone"]))
            self.db.execute("DELETE FROM inbound WHERE received<?", (now - 7 * 86400,))
            self.db.execute("DELETE FROM outbox WHERE created<? AND state!='sending'", (now - 7 * 86400,))

    def deliver_one(self, sender, now):
        # Serialize command changes and delivery, so STOP cannot race a queued send.
        with self.lock:
            job = self.db.execute("SELECT * FROM outbox WHERE state='pending' ORDER BY id LIMIT 1").fetchone()
            if not job:
                return False
            user = self.db.execute("SELECT * FROM users WHERE phone=?", (job["phone"],)).fetchone()
            prefs = json.loads(user["prefs"])
            local = datetime.fromtimestamp(now, ZoneInfo(prefs["timezone"]))
            is_quiet = quiet(local.hour * 60 + local.minute, *map(clock, prefs["quiet"]))
            if now - job["created"] > 300 or (job["kind"] == "scheduled" and (not user["active"] or is_quiet)):
                with self.db:
                    self.db.execute("UPDATE outbox SET state='cancelled' WHERE id=?", (job["id"],))
                return True
            body = self.report(job["phone"], now) if job["kind"] == "scheduled" else job["body"]
            with self.db:
                self.db.execute("UPDATE outbox SET state='sending' WHERE id=?", (job["id"],))
            try:
                provider_id = sender(job["phone"], body, now - user["last_inbound"] >= 23 * 3600, str(job["id"]))
                with self.db:
                    # A fast callback may have already marked it delivered.
                    self.db.execute("UPDATE outbox SET state=CASE WHEN state='sending' THEN 'accepted' ELSE state END,provider_id=? WHERE id=?", (provider_id, job["id"]))
            except Exception:
                # A timeout could occur after Meta accepts a send. Do not retry blindly.
                with self.db:
                    self.db.execute("UPDATE outbox SET state='unknown',error='send failed or acceptance unknown; inspect provider' WHERE id=?", (job["id"],))
            return True

    def delivery_status(self, provider_id, status, callback=None):
        if status not in ("sent", "delivered", "read", "failed"):
            return
        with self.lock, self.db:
            row = self.db.execute("SELECT id,state FROM outbox WHERE provider_id=?", (provider_id,)).fetchone()
            if not row and callback and str(callback).isdigit():
                row = self.db.execute("SELECT id,state FROM outbox WHERE id=? AND state IN ('sending','unknown','accepted')", (int(callback),)).fetchone()
            if row:
                rank = {"sending": 0,"unknown": 0,"accepted": 0,"sent": 1,"failed": 2,"delivered": 3,"read": 4}
                if rank.get(status, 0) >= rank.get(row["state"], 0):
                    self.db.execute("UPDATE outbox SET state=?,provider_id=? WHERE id=?", (status, provider_id, row["id"]))
