# Create the Air Care Telegram bot

Updated: 12 October 2026, Singapore time.

These instructions use ASD-STE100 writing principles. Full dictionary compliance is not certified.

## Owner setup on a phone

1. Open https://t.me/BotFather in Telegram.
2. Check that the account is the official verified BotFather account.
3. Send `/newbot`.
4. Enter `Air Care` as the bot name.
5. Enter an available username that ends in `bot`.
6. Save the bot token in a secure place. Treat it as a password.
7. Give the helper the bot username. Do not put the token in this public repository or in a chat message.

BotFather creates the bot identity. It does not host the Air Care software. The bot cannot answer until the helper connects the cloud service and enrolls the user.

## Optional command menu

Send `/setcommands` to BotFather. Select the new bot. Send this text:

```text
start - Start reports
status - Read the latest report
settings - Read report settings
homes - List your homes
all - Select all your homes and rooms
stop - Stop scheduled reports
help - Read the instructions
```

Use a private chat with the bot. Keep group access disabled for this pilot.

## Helper handoff

- The tested serverless prototype is in `cloudflare/`.
- Keep the account on Workers Free. No paid service is authorized.
- Cloudflare account access and deployment are pending.
- Store the token as the `TELEGRAM_BOT_TOKEN` Worker secret when the Worker exists.
- Follow [the deployment procedure](../cloudflare/README.md) to create storage, set the webhook secret, register the webhook, and enroll authorized users.
- Keep sending disabled until setup and enrollment are complete.
- Test `/start`, `/status`, schedule changes, and `/stop` with the owner.
- Verify each device connection before you show real readings. No device connection is verified yet.

## User operation after activation

1. Open the bot link from your helper.
2. Send `/start`.
3. Send `/status` to read the report.
4. Send `DAILY 08:00,18:00` to get two reports each day.
5. Send `EVERY 4 HOURS` to use an interval instead.
6. Send `/stop` to stop scheduled reports.

All report times use Singapore time. Default quiet hours are 22:00 to 08:00.

## Current status

The bot is not online. No bot token is configured. No cloud deployment or live device connection has been completed. Creating a bot with BotFather alone does not change this status.

Source: https://core.telegram.org/bots/tutorial#obtain-your-bot-token (checked 12 October 2026, Singapore time).
