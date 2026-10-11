# Telegram on Cloudflare — uncommissioned prototype

This is the preferred messaging/scheduling prototype under the owner's free-only constraint. It uses a Worker, one D1 database, and one Cron Trigger. **It is not deployed and does not yet have a vendor-cloud device connector.** See `../docs/PROJECT_STATUS.md`.

## Local test

Use Node 24, which includes `node:sqlite`:

```sh
node --test cloudflare/tests/worker.test.mjs
```

Run this from the repository root. Fifteen tests passed locally. The SQL adapter is a local stand-in for D1; Cloudflare deployment, free CPU quota, and live Telegram behavior remain untested.

## Helper setup sequence

These steps use ASD-STE100 writing principles. Full dictionary compliance is not certified. Do not hand these technical steps to the elderly user.

1. Confirm the Cloudflare account uses **Workers Free**.
2. Do not enable a paid Workers plan or paid add-on.
3. Create a Telegram bot with the verified `@BotFather` account.
4. Keep the bot token private.
5. Create one D1 database named `air-care-telegram`.
6. Put its database ID in `wrangler.jsonc`.
7. Apply `schema.sql` to that database.
8. Store `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET` as Worker secrets.
9. Enroll each home, Telegram chat ID, and access assignment in D1.
10. Deploy the Worker with Wrangler or the Cloudflare account workflow.
11. Register `https://YOUR-WORKER.workers.dev/telegram` with Telegram's `setWebhook` method.
12. Set `secret_token` to the same value as `TELEGRAM_WEBHOOK_SECRET`.
13. Set `max_connections` to `1`. Set `allowed_updates` to `["message"]`.
14. Connect the verified reading source to `/v1/readings`.
15. Set `TELEGRAM_ENABLED` to `true` only when you are ready for the acceptance test.

The Worker requires HTTPS, supplied by Cloudflare. No router, domain purchase, or home hardware is required for the Worker itself. A free device-cloud connector is still required for the complete system.

Cloudflare access is not connected in this ChatGPT session. No database ID or endpoint has been created. The placeholder database ID must not be treated as a real resource.

## Enrollment and secrets

Enrollment is administrator-only in this pilot. The user first opens the bot and sends `/start`; the helper then obtains the verified private chat ID through the owner's Telegram bot setup process. The user record must be created before the Worker will answer. Do not use public third-party ID bots as an identity trust mechanism.

Create a `users` record with `chat` as the decimal Telegram ID and `prefs` equal to:

```json
{"mode":"daily","times":["08:00"],"hours":4,"quiet":["22:00","08:00"],"home":null,"room":null}
```

`active` defaults to zero. Add the intended rows in `access`. Send START again after enrollment to give consent. Production SQL must be prepared privately; never commit real chat IDs or credentials.

The optional `AIRCARE_INGEST_TOKENS_JSON` secret maps each home code to a separate random token of at least 32 characters. POST readings with `Authorization: Bearer TOKEN`. The token determines the home; the payload cannot override it. The payload is the same `devices`/`metrics` format used by the Python collector, with numeric UTC epoch observation times. The Worker accepts a maximum of 20 devices and a 16 KB body.

The intake is designed for an authorized **cloud** connector. Do not require the user to run the Python home collector to satisfy the no-extra-hardware design.

## User instructions

1. Open the bot link supplied by your helper.
2. Send `START`.
3. Send `STATUS` to read a report.
4. Send `DAILY 08:00,18:00` for two daily reports.
5. Send `EVERY 4 HOURS` to use an interval instead.
6. Send `STOP` to stop scheduled reports.

All times in this prototype use **Singapore time**. Quiet hours are 22:00–08:00 by default. Use `QUIET 22:00 08:00` to set them. Send `HOMES`, `HOME code`, `ROOM name`, `ALL`, `SETTINGS`, or `HELP` as needed. Rooms must already be mapped by the helper.

## Free-plan and reliability limits

- Telegram paid broadcasts are explicitly disabled on every send.
- No WhatsApp sender, paid cloud resource, R2 bucket, or paid queue is configured.
- Cloudflare Free quota exhaustion can interrupt the service. Remain on Free; do not upgrade automatically.
- One Cron invocation runs each minute. Only five due recipients are processed per invocation; late slots beyond five minutes are skipped.
- Data is stored in D1, not ephemeral Worker memory. Events are retained for seven days.
- Send claims prevent routine duplicates. A crash after a claim can lose a response/report. Uncertain sends are not automatically retried.
- STOP prevents future scheduled reports; an already in-flight message can arrive.
- Never publish bot tokens or real readings in this public repository.
- Enrollment, source authentication, free quota usage, and runtime performance require live acceptance tests.

Primary references, checked 11 October 2026:

- https://core.telegram.org/bots — free bot platform.
- https://core.telegram.org/bots/api — webhook secret, sendMessage, paid-broadcast flag.
- https://developers.cloudflare.com/workers/platform/pricing/ — Workers Free request/CPU limits.
- https://developers.cloudflare.com/d1/platform/pricing/ — durable storage and row-operation free limits.
- https://developers.cloudflare.com/workers/configuration/cron-triggers/ — scheduled invocation support.
