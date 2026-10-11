# Air Care — aim, progress, and remaining work

Last updated: 11 October 2026, Singapore time.

## Aim

Give elderly users one clear air-condition report through a phone messaging app. Group readings by household, room, and device. Let each user choose daily report times or an interval. Avoid a stream of separate sensor notifications.

The user's requirements are:

- No extra home computer, Raspberry Pi, hub, or other hardware.
- No router port management or technical setup for elderly users.
- Devices use their existing Wi-Fi and vendor accounts.
- A helper can perform initial account setup; ordinary use is through messaging.
- The service must remain free. No paid hosting, storage, broadcast, or automatic upgrades are authorized.
- Telegram is approved as the first delivery channel.
- Continue researching a supported free WhatsApp pathway for possible future use.
- Keep code, progress, and instructions in this public GitHub repository.
- Write user procedures using ASD-STE100 principles. Full controlled-dictionary certification has not been performed.

## Overall status

**Tested prototypes and documentation. Not deployed. Not connected to real appliances.**

The messaging/storage/scheduling problem has a proposed free-tier solution. The end-to-end project does **not** yet have a verified free device-data connection. Do not present the current prototype as a working household installation.

## Completed work

| Work | Result | Evidence |
|---|---|---|
| Original Python reporting service | Implemented household permissions, home/room grouping, daily and interval schedules, quiet hours, opt-in/out, stale-data handling, duplicate suppression, and durable local queue. | `aircare/`, `tests/test_aircare.py` |
| Original WhatsApp adapter | Official Meta API request and webhook handling implemented. No live sends or credentials configured. | `aircare/transport.py`, `aircare/server.py` |
| Cloud-source adapter | Can read mapped entities from a separately hosted Home Assistant service over HTTPS. Does not implement direct Dyson/Xiaomi login. | `aircare/cloud.py`, `tests/test_cloud.py` |
| GitHub publication | Project saved in `Devilz13/air-care-whatsapp`; public visibility explicitly approved by owner. | Repository history |
| Render review | Connected account; owner approved `My Workspace`. No services created. | `docs/FREE_ONLY.md` |
| Free-only constraint | Removed the proposed paid Render manifest. Render Free is unsuitable for the current always-running SQLite service. | `docs/FREE_ONLY.md` |
| Telegram/serverless prototype | Implemented a separate Cloudflare Worker with D1 schema, Cron handler, Telegram webhook, authenticated readings intake, opt-in/out, access checks, and bounded reports. | `cloudflare/` |
| Cost controls in Telegram prototype | Sending disabled by default. `allow_paid_broadcast` explicitly false. No WhatsApp network calls in the Worker. | `cloudflare/worker.mjs` |
| Local tests | 28 Python tests passed previously; 15 new Node/SQLite tests pass for the serverless prototype. | `tests/`, `cloudflare/tests/` |
| WhatsApp research | Identified Meta's stated 1,000 free service-message monthly allowance as a possible bounded, user-initiated path. It is not a free unattended-template solution. | `docs/WHATSAPP_FUTURE.md` |

## Proposed free architecture

| Part | Proposed implementation | Current state |
|---|---|---|
| Messaging | Telegram Bot API, without paid broadcasts | Code and mocked tests complete; bot not configured |
| Webhook and scheduler | Cloudflare Workers Free plus Cron Trigger | Code/config prepared; account and deployment pending |
| Durable settings | Cloudflare D1 Free | Schema prepared; database not created |
| Device readings | Authenticated, home-scoped input from a verified vendor-cloud connector | **Main unresolved technical dependency** |
| User access | Helper enrolls Telegram chat IDs and allowed homes | Schema implemented; production enrollment pending |

The Worker is a separate JavaScript implementation, not a deployed rewrite of the Python process. It supports Singapore time only in this first version. It does not carry out direct vendor OAuth, MQTT subscriptions, or background Home Assistant hosting. An API endpoint that accepts readings is not itself a device connector.

## Tests and limits

New tests use Node's built-in test runner and real local SQLite with a D1-shaped adapter. They cover schedule parsing, quiet hours, access isolation, signed-secret webhook checks, duplicate handling, missing data, concurrent schedule claims, STOP, disabled paid broadcasts, and uncertain delivery. They are **not** tests of Cloudflare's actual runtime, CPU quota, network behavior, or real Telegram delivery.

The Worker processes at most five due recipients per minute. Small deployments may fit the published free quotas, but load and CPU usage must be measured on the real platform. Free-tier limits can stop service. No automatic paid upgrade is authorized. A crash after a claim can skip a report; uncertain sends are not retried automatically. A message already being sent can still arrive after STOP.

## Remaining work, in order

1. **Verify a no-home-hardware device-data path.** Confirm exact model identifiers and account regions. Test Xiaomi cloud readings and Dyson HJ10 cloud readings. Record which metrics each unit actually exposes.
2. **Find or implement a free way to run that connector.** Cloud-hosted Home Assistant was a candidate, but no permanently free, reliable hosting has been validated for it. Workers' short executions are not a drop-in replacement for an always-connected vendor MQTT client. A bounded on-demand vendor API may be an alternative if supported and authorized.
3. **Confirm the Cloudflare account is on Workers Free.** No connected Cloudflare tool was found in the available plugin search. Account access and deployment are still pending. Do not ask users to paste account secrets into chat.
4. **Create the Telegram bot.** The owner uses BotFather once. Store the bot token as a secret. Do not enable paid broadcasts.
5. **Create D1 and deploy the Worker.** Apply the schema, set secret values, configure the HTTPS webhook and Cron Trigger, and verify the actual runtime and quota usage.
6. **Enroll homes and users.** Use private administrator input. Keep phone/chat IDs, tokens, vendor credentials, and real readings out of the public repository.
7. **Perform live acceptance tests.** Check every reading against the appliance app; test unplugged devices, stale data, scheduled sends, quiet hours, STOP, restart behavior, and household isolation.
8. **Test elderly-user usability.** Validate setup and commands with the intended users. Add buttons or language support if needed. Buttons and voice messages are not implemented.
9. **Evaluate WhatsApp separately.** Validate account-specific free allowance, service-window rules, quota accounting, and a hard stop before any possible charge. Keep the channel disabled until verified.

Steps 1–2 are essential. Completing steps 3–5 alone would create a bot with no verified live appliance data.

## Acceptance conditions

- An enrolled user can start reports, set a schedule, read a report, and stop reports from their phone.
- Each recipient sees only authorized homes and rooms.
- No extra home hardware or router changes are needed.
- Values and timestamps match the actual devices; disconnected devices do not appear fresh.
- Settings survive infrastructure restarts.
- No paid resource or paid messaging feature is enabled.
- Provider limits cause controlled service interruption, not an automatic paid upgrade.
- The final setup and ongoing costs are documented accurately.

## Next decision

Continue with Telegram. Validate the free cloud device connector before claiming the system can run end-to-end. Keep WhatsApp as a separately researched future channel.
