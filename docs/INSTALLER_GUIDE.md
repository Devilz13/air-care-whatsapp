# Air Care — installer instructions

Audience: the family helper or service operator. The elderly user uses only WhatsApp after setup.
These procedures use ASD-STE100 writing principles. Full controlled-dictionary compliance is not certified.

## 1. Prepare the equipment

1. Prepare one always-on computer for each home.
2. Install Home Assistant on that computer or another computer in the same home.
3. Prepare a central Linux host with Python 3.12 or Docker Compose.
4. Prepare a domain name for the central host.
5. Point the domain name to the host.
6. Permit inbound HTTPS on port 443. Permit port 80 for certificate setup.
7. Keep port 8080 private.

The central host and a home gateway can use the same computer if the network permits this.
Each separate home needs a collector that can reach its Home Assistant instance.
The service needs internet access. Check hosting and WhatsApp charges before activation.

## 2. Connect Xiaomi devices

1. Add each device to the owner's Xiaomi Home app.
2. Confirm that each device shows live data in the app.
3. Install the official Xiaomi Home integration in Home Assistant.
4. Sign in with the owner's permission.
5. Select the account region that contains the devices.
6. Import the required devices.
7. Check the available entities in Home Assistant.

Use the upstream installation instructions in `SOURCES.md`.
Do not assume that every device exposes all report fields.
Confirm whether “4 Lite 2” means two 4 Lite devices.

## 3. Check the Dyson HJ10 connection

1. Confirm the model on the device label.
2. Confirm that MyDyson shows live data.
3. Check the current HJ10 support status in the Dyson integration.
4. Install a supported release only after you verify the exact model.
5. Confirm that Home Assistant shows live readings.
6. Disconnect the device from the network.
7. Confirm that the integration marks the data unavailable or stops refreshing it.
8. Reconnect the device.

HJ10 support was not verified for this build. The reviewed upstream support change was open.
If HJ10 is unsupported, stop this connection procedure. Keep its report fields unavailable.
The Xiaomi devices can still be commissioned separately. Do not label the whole installation complete until the required HJ10 units pass.

## 4. Map homes, rooms, and entities

1. Copy `examples/collector.example.json` to `collector.json` on the home gateway.
2. Set `ha_url` to the local Home Assistant address.
3. Set `server_url` to the central HTTPS address.
4. Set a unique `id` for each device in that home.
5. Set each device name and room name.
6. Replace every example `entity_id` with a real entity ID.
7. Remove metric mappings that the device does not support.
8. Keep at least one device in the list.

The example IDs are placeholders. They do not prove device support.
Use PM2.5 concentration in `µg/m³`, humidity in `%`, and temperature in `°C`.
Map filter percentage only if the value means remaining filter life.
Do not map filter hours or percentage used to filter remaining.
Map `tank_full` only to a binary entity where `on` means full and `off` means not full.

For a value stored in an entity attribute, use this form:

```json
{"entity_id":"humidifier.example","attribute":"current_humidity","unit":"%"}
```

Only the installer can change the device or room mapping in this version.

## 5. Prepare WhatsApp

1. Open the official Meta WhatsApp Cloud API setup page in `SOURCES.md`.
2. Create or select the WhatsApp Business account.
3. Register a service phone number.
4. Get the business phone number ID.
5. Create an access token with the required WhatsApp messaging permissions.
6. Record the Meta app secret securely.
7. Select a currently supported Graph API version.
8. Create the template from `examples/whatsapp-template.json`.
9. Wait for Meta to approve the template.
10. Record its exact name and language code.

The template contains one body parameter. The service puts the report in that parameter.
Meta decides approval and category. Do not assume that the suggested utility category will be accepted.
The service needs the approved template when the user has not recently sent a message.
Temporary development tokens and Meta test numbers are not a production installation.

## 6. Set the server configuration

1. Copy `examples/server.env.example` to `.env` in the project folder.
2. Replace every `REPLACE_` value.
3. Set `AIRCARE_DOMAIN` to your domain name.
4. Set the approved template name and language.
5. Generate a random verification token of at least 32 characters.
6. Put the verification token in `META_VERIFY_TOKEN`.
7. Restrict access to `.env`.

Generate a token with:

```sh
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Do not put actual tokens, device credentials, or recipient numbers in GitHub.
Do not send them in this chat or in WhatsApp.

## 7. Create a home and enroll a user

1. Build the container.

```sh
docker compose build
```

2. Generate a separate random token for the home.
3. Create the home. Replace the example code and name.

```sh
docker compose run --rm app python -m aircare.admin add-home home-a 'Home A'
```

4. Enter the home token at the hidden prompt.
5. Add the user's number with the international country code. Omit `+` and spaces.

```sh
docker compose run --rm app python -m aircare.admin add-user 6590000001 home-a
```

The number above is an example. Replace it before you run the command.
Adding a user does not start scheduled reports.
For a caregiver with access to two homes, append the second home code after the first.
Use `--timezone` to set an IANA time zone other than `Asia/Singapore`.

## 8. Start the server and webhook

1. Start the server and HTTPS proxy.

```sh
docker compose up -d
```

2. Set the Meta webhook URL to `https://YOUR-DOMAIN/webhook`.
3. Enter the same verification token used in `.env`.
4. Subscribe to WhatsApp message events for the correct account.
5. Confirm that Meta verifies the webhook.

The server verifies message signatures and the business phone number ID.
Use one app container only. Do not increase the worker count.

## 9. Start the home collector

1. Create a dedicated Home Assistant user for this connection.
2. Get a long-lived access token for that user.
3. Copy the project to `/opt/air-care-whatsapp` on the home gateway.
4. Create `/etc/aircare-collector.env` with the two entries below.

```text
HA_TOKEN=REPLACE_WITH_HOME_ASSISTANT_TOKEN
AIRCARE_HOME_TOKEN=REPLACE_WITH_THIS_HOME_TOKEN
```

5. Restrict the environment file to the service administrator.
6. Put the completed mapping at `/opt/air-care-whatsapp/collector.json`.
7. Create a local service user named `aircare`.
8. Give that user read access to the project and mapping.
9. Copy `deploy/aircare-collector.service` to `/etc/systemd/system/`.
10. Load the service configuration.

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now aircare-collector
```

For a manual connection check, load the two environment variables securely and run:

```sh
python -m aircare.collector collector.json --once
```

The collector reads data once each minute. Use HTTPS between the gateway and central host.
Use HTTP for Home Assistant only on a trusted local network. Otherwise, use HTTPS.

## 10. Perform the acceptance test

1. Ask the enrolled user to send `START`.
2. Ask the user to send `STATUS`.
3. Compare the device values with Home Assistant and the appliance app.
4. Confirm that home and room names are correct.
5. Check each physical device with the acceptance checklist in `TEST_REPORT.md`.
6. Set one report time a few minutes ahead and outside quiet hours.
7. Confirm that only one report arrives.
8. Send `STOP` before another scheduled report.
9. Confirm that no scheduled report arrives.
10. Confirm approved-template delivery after the service window closes.
11. Give the user `USER_GUIDE.md`.

## 11. Maintain the service

1. Check delivery results regularly.

```sh
docker compose exec app python -m aircare.admin delivery-summary
```

2. Investigate `failed` or `unknown` results in Meta logs.
3. Do not resend an unknown result until you confirm whether Meta accepted it.
4. Back up the SQLite database with the SQLite backup API or while the service is stopped.
5. Encrypt backups and set a retention period.
6. Check token expiry and template status before they interrupt service.

`/healthz` confirms HTTP availability only. It does not prove device freshness or message delivery.

To remove a user and their queued messages, run:

```sh
docker compose exec app python -m aircare.admin remove-user 6590000001
```

Replace the example number. To change home access, remove the user and add them again.
Ask the user to send `START` again after re-enrollment.

## 12. Save this project to the new GitHub repository

This step is needed only if the connected assistant cannot yet access the new repository.

1. Open GitHub.
2. Create a private repository named `air-care-whatsapp`.
3. Add a README file when you create the repository.
4. Give the ChatGPT GitHub connection access to that repository.
5. Tell the assistant that the repository is ready.

The assistant can then save the tested source without changing your other repositories.
