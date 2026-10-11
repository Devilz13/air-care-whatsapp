# Design and operating limits

## Deployment boundary

This is a small, single-process pilot. Use one central server with persistent local SQLite storage, plus one collector per home. The collector makes outbound HTTPS requests. The home router needs no inbound port. Home Assistant must reach the appliances and any required vendor cloud. Internet access is required for WhatsApp.

The standard-library HTTP service must bind to loopback or a private container network behind the supplied TLS proxy. It is not intended to be exposed directly on port 8080 or scaled to multiple workers. Add provider-level rate limits, traffic monitoring, capacity testing, managed backups, and a production web server before a public multi-customer launch.

## Data contract

`POST /v1/readings` accepts a home-scoped bearer token and JSON with a `devices` array. Each device has an ID, name, room, and named metrics. Each metric has a numeric or null value and a UTC epoch `observed_at`. The token determines the home; a payload cannot choose a different home. Maximum 50 devices and 256 KB per request.

The central database stores only the latest device snapshot, not long-term air history. The schema accepts only PM2.5, humidity, temperature, filter remaining, and tank-full state. Device control is excluded. Unknown or unsupported metrics are rejected. No medical categories are inferred from instantaneous PM2.5 values.

The collector verifies units. It does not silently convert Fahrenheit, AQI, filter hours, or fractional percentages. Attribute-based readings require an explicit unit in the mapping. Adjustments must be verified against the actual appliance display before activation.

## Freshness

The collector uses Home Assistant `last_reported`, falling back to `last_updated`. It does not use `last_changed`, which can remain old when a valid reading stays constant. If no trustworthy timestamp is available, the reading is unavailable. The server also checks gateway receipt age.

Home Assistant timestamps show integration reporting time; they are not proof that hardware made a new measurement. An integration that repeatedly republishes a cached value can still appear fresh. The physical-device acceptance test must disconnect each device and confirm unavailable/old status. This limitation is especially relevant to community integrations. The 15-minute threshold is fixed in this pilot.

## User access and consent

An operator enrolls a phone number and assigns allowed homes locally. There is no public registration or administrative endpoint. A WhatsApp sender cannot gain access by knowing a home code. An unknown phone receives no reply. `START` turns scheduled delivery on; `STOP` or `PAUSE` turns it off. On-demand `STATUS` remains available to enrolled users. The authenticated webhook timestamp must be recent, and duplicate message IDs are ignored for seven days.

Only the local administrator can add or remove access. Remove the user and re-add them with the correct homes to change permissions; this resets consent. Phone reassignment must be handled by the operator. A recycled phone number is not automatically detected.

## Scheduling

Each recipient has one schedule and one home/room selection. Default: 08:00 daily, Asia/Singapore, quiet 22:00–08:00. Daily mode allows 1–4 times. Interval mode allows 2–24 hours. A selected room applies to scheduled and on-demand reports. `ALL` resets both filters.

All scheduling uses UTC instants plus IANA zones. Skipped local times are skipped. The repeated autumn hour sends only on the first fold. A slot more than five minutes late is skipped. No catch-up queue is created. An interval may shift after downtime. Commands may get replies during quiet hours because the user requested them.

## WhatsApp delivery

The user sees a structured text report in an active service window. Outside it, the same report is flattened into one approved template parameter. A 23-hour cutoff leaves margin before the documented 24-hour limit. The template must be approved for the actual business and content; approval and category cannot be guaranteed by code. A scheduled sensor report may incur Meta fees. The service cannot enforce a currency budget; the minimum interval and four-times-daily cap constrain frequency.

Large reports are visibly shortened, never silently split into a message burst. Users can select a home and room for a smaller report. The template summary is limited to 800 characters; the full text is limited to 3,500. A very large room can still require a smaller configured device set.

Queue states distinguish accepted, sent, delivered, read, failed, unknown, and cancelled. HTTP API acceptance does not mean delivery. Meta delivery-status callbacks update the record. Calls that time out or fail are marked unknown, because acceptance may be ambiguous. They are not retried automatically. This deliberately prefers a missed report over duplicate messages. Inspect Meta logs before a manual recovery. A restart changes in-flight sends to unknown. Exactly-once delivery across the remote network is not promised.

## Security and retention

Webhook POSTs require HMAC-SHA256 verification of exact request bytes and the expected business phone ID. Verification GETs require a separate secret. Tokens are environment values; home bearer tokens are hashed in the server database. The transport rejects redirects. Logs omit request URLs, message bodies, phone numbers, and secrets.

Only six command replies per minute per enrolled phone are queued. STOP is processed even at that limit. The TLS proxy limits request size, and the handler rejects oversized bodies and transfer-encoding. Additional edge rate limits are needed for hostile public traffic. A valid compromised home token can submit false readings for that home; it must be protected and rotated by the operator.

Inbound IDs and completed delivery records are pruned after seven days. STOP stops delivery but does not delete enrollment or readings. `remove-user` deletes the recipient, access links, and their queue. Latest readings remain until an administrator removes the home database records. Backups require a separate retention and deletion policy. Use encrypted host storage and restrict `.env`, collector configuration, and database access.

## Scope not implemented

- Automatic pairing of vendor appliances through WhatsApp.
- Verified HJ10 protocol support or bundled Dyson forks.
- Voice notes, translation, caregiver escalation, health alarms, or device control.
- Subscription billing, automatic account recovery, public self-registration, or automatic retries.
- Sensor trends and historical analytics.

English text commands form the first usable interface. Additional languages and WhatsApp list/button menus can be added after testing the core with the intended elderly users.
