# Air Care — user instructions

These instructions use ASD-STE100 writing principles. Full dictionary compliance is not certified.

## Before you start

Ask your helper to connect your home devices.
Ask your helper to add your phone number.
Get the Air Care WhatsApp contact from your helper.
The default time zone is Singapore time.

## Start reports

1. Open WhatsApp.
2. Open the Air Care chat.
3. Send `START`.
4. Read the reply.
5. Send `STATUS`.
6. Check the home and room names.

The default report time is 08:00 each day.
The default quiet hours are 22:00 to 08:00.
Scheduled reports do not arrive during quiet hours.
You can request a report during quiet hours.

## Set a report time

1. Send `DAILY 08:00`.
2. Read the reply.

For two reports each day, send `DAILY 08:00,18:00`.
You can set a maximum of four times each day.
Use the 24-hour clock. For example, 18:00 means 6 pm.
Choose times outside your quiet hours.

## Set an interval

1. Send `EVERY 4 HOURS`.
2. Read the reply.

You can set an interval from 2 to 24 hours.
This setting replaces the daily times.
The first report follows the interval from your command time.
If that time is inside quiet hours, the report waits until quiet hours end.
Each later interval starts from the previous report slot.

## Set quiet hours

1. Send `QUIET 22:00 08:00`.
2. Read the reply.

The first time is the start time.
The second time is the end time.
For this example, scheduled reports can start at 08:00.

## Read one home

1. Send `HOMES`.
2. Find the home code in the reply.
3. Send `HOME home-a`. Replace `home-a` with your home code.
4. Send `STATUS`.

This selection also applies to scheduled reports.
You can see only homes that your helper assigned to you.

## Read one room

1. Find the room name in your report.
2. Send `ROOM Living room`. Replace `Living room` with the room name.
3. Send `STATUS`.

To show all your homes and rooms again, send `ALL`.

## Read the data

| Report item | Meaning |
|---|---|
| PM2.5 | The measured amount of small particles in the air. The unit is micrograms per cubic metre. |
| Humidity | The relative humidity, as a percentage. |
| Temperature | The temperature, in degrees Celsius. |
| Filter remaining | The device estimate of remaining filter life. |
| Water tank full: Yes | Empty the water tank as specified in the device manual. |
| No data | A reading is not available. |
| Old data | The reading or gateway update is more than 15 minutes old. |

The report does not measure all air pollutants.
PM2.5 is not a PSI or AQI score.
Do not use this service as an emergency alarm.

## Stop reports

1. Send `STOP`.
2. Read the reply.

Scheduled reports stop. A message already sent can still arrive.
You can still send `STATUS` for one report.
To start scheduled reports again, send `START`.

## Check the settings

1. Send `SETTINGS`.
2. Check the times and home selection.

For command help, send `HELP`.

## If a report does not arrive

1. Send `SETTINGS`.
2. Check that reports are on.
3. Check the report time.
4. Check the quiet hours.
5. Send `STATUS`.
6. Ask your helper for assistance if there is no reply.

## If the report shows old data

1. Check that the device has power.
2. Check that the home internet connection works.
3. Ask your helper to check the home gateway.

Do not send passwords or access tokens in WhatsApp.
