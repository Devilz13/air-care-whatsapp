# Cloud hosting — no computer or hub in the home

## Status

The report service has a Render deployment definition and an in-process cloud-source poller. **It has not been deployed.** The Render account is not connected yet. Cloud device integrations and account authorization still require commissioning. The Render file provisions the report service only; it does not provision Home Assistant or implement direct vendor login.

This distinction matters: hosting the WhatsApp bot alone does not give it access to Dyson or Xiaomi readings.

## Intended user experience

1. Connect the appliances to the home's existing Wi-Fi with their normal phone apps.
2. Ask the helper to connect the device accounts to the cloud service once.
3. Open the Air Care contact in WhatsApp.
4. Send `START`.
5. Send `DAILY 08:00,18:00` or `EVERY 4 HOURS`.

The phone does not run a background collector. It can be off when the service collects data. No home Raspberry Pi, PC, hub, router port forwarding, or VPN is required **when the cloud integrations pass their device tests**. Home internet and appliance power are still required.

An elderly user does not configure hosting or tokens. A helper must handle account connections and reauthentication. A fully self-service WhatsApp account-linking flow is not implemented.

## Proposed components

| Component | Location | Purpose |
|---|---|---|
| Existing appliances | Home Wi-Fi | Send readings to vendor cloud services. |
| Vendor integrations | Operator-managed cloud Home Assistant | Connect to Xiaomi cloud and Dyson Cloud Only. |
| Air Care report service | Render Singapore | Read selected cloud entities and send scheduled WhatsApp reports. |
| User interface | WhatsApp on the phone | Read reports and change the schedule. |

The remotely hosted Home Assistant instance is a backend service, not home hardware. It must have a secure HTTPS endpoint. Do not place an unclaimed Home Assistant onboarding page on a public URL. Provision the owner account behind an access restriction before enabling public access. Use a supported managed host or commission a protected container after the hosting account is connected. The original home-local installation procedure is now an optional legacy route.

## Integration checks before paying for a permanent service

### Xiaomi

Use the official Xiaomi Home integration in cloud mode. Do not enable LAN control or require a physical Xiaomi gateway. Select the same region as the appliance account.

The upstream login currently has a fixed `homeassistant.local:8123` callback. Its documented remote-host workaround requires the helper to replace that origin with the trusted cloud Home Assistant origin while preserving the callback path and parameters. Follow the upstream instructions linked below. Do not send the callback URL, authorization code, or account password through WhatsApp or GitHub. Do not claim that this is a one-tap login for an elderly user.

### Dyson

The `cmgrayb/hass-dyson` integration documents a **Cloud Only** connection through Dyson's MQTT proxy. This is a different integration path from the local `libdyson-wg/ha-dyson` route initially assessed. Choose Cloud Only, not local or fallback mode. Confirm login, device discovery, and real HJ10 sensor messages. Cloud Only availability for the integration does not prove compatibility with these exact HJ10 units.

For both brands, disconnect each physical unit and confirm that the service marks readings unavailable or old. If either brand cannot provide working cloud readings for the actual model, the no-home-hardware requirement remains blocked for that device. Do not substitute invented values or add a hidden home gateway.

## Deploy the report service

These are helper instructions, written using ASD-STE100 principles. Full dictionary compliance is not certified.

1. Connect the Render account to ChatGPT.
2. Review the cost for the report service, persistent disk, cloud integration host, and Meta messages.
3. Approve the selected hosting resources before they are created.
4. Use `render.yaml` in this repository to create the report service.
5. Set the required Meta values in Render's secret environment settings.
6. Use the generated `onrender.com` HTTPS address.
7. Set the Meta webhook to `https://YOUR-SERVICE.onrender.com/webhook`.
8. Use the generated `META_VERIFY_TOKEN` for webhook verification.

No domain purchase, DNS edit, TLS certificate installation, Docker command, or router port change is needed for the report service. Render provides the public HTTPS address and routing. The app reads Render's assigned `PORT` automatically.

The proposed report service uses 0.5 CPU, 512 MB memory, and a 1 GB persistent disk. This is paid compute. The exact bill must be checked in the account before deployment; it excludes the cloud integration host and Meta usage. The free service is unsuitable for reliable schedules and persistent SQLite state. Automatic deployments are off so repository edits do not unexpectedly restart the running pilot.

## Connect cloud data to reports

1. Create the home and allowed recipient with the existing admin commands in the Render service shell.
2. Create a dedicated Home Assistant token in the protected cloud integration host.
3. Put it in a Render secret named `CLOUD_HA_TOKEN_HOME_A`.
4. Copy `examples/cloud-sources.example.json` into `AIRCARE_CLOUD_SOURCES_JSON` in Render.
5. Replace the cloud host URL and entity IDs with verified values.
6. Use the same home code that was enrolled in step 1.
7. Save the settings and restart the service.
8. Send `STATUS` from the enrolled WhatsApp number.

The source JSON stores the **name** of a secret variable, not the token itself. Use one source entry per home. A single cloud Home Assistant host may serve several homes, but the operator must map the correct entities to each home. Automatic cross-account isolation inside Home Assistant is not supplied by this adapter. For unrelated customers, use separate integration instances or a reviewed multi-tenant integration layer.

The poller runs inside the report process every minute. It uses HTTPS to fetch the cloud integration's states and preserves their timestamps. Failed requests do not refresh the stored readings. Scheduled delivery uses a separate thread, so a slow cloud request does not block the scheduler. `AIRCARE_CLOUD_SOURCES_JSON=[]` leaves cloud collection disabled while the report service is being commissioned.

## What is tested

28 local tests pass: the original 22 and six additional cloud-source tests. New tests cover HTTPS requirements, separated secrets, duplicate home rejection, correct-home ingestion, failed-source isolation, and preservation of old data after a network failure.

Render deployment, cloud Home Assistant hosting, vendor login, HJ10 cloud readings, and real WhatsApp delivery have not been tested. Do not give the elderly user the service as ready until those checks pass.

## Primary references

- Render web services: https://render.com/docs/web-services
- Render Blueprint reference: https://render.com/docs/blueprint-spec
- Persistent disk limitations: https://render.com/docs/disks
- Render free service limits: https://render.com/docs/free
- Xiaomi integration: https://github.com/XiaoMi/ha_xiaomi_home
- Xiaomi remote-host login: https://github.com/XiaoMi/ha_xiaomi_home/wiki/OAuth-2.0-login-when-Home-Assistant-URL-is-not-homeassistant.local:8123
- Dyson Cloud Only configuration: https://github.com/cmgrayb/hass-dyson#configuration

References checked on 11 October 2026. The recorded upstream main commits were `75b3acb6325a3a8d295688b13904737d6738a6a5` (Xiaomi) and `da351525e1650a40abd25bd9cc3d857fb5abdd7c` (Dyson); this repository does not bundle or install those integrations.
