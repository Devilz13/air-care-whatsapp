# Test report — 11 October 2026

## Result

**22 automated tests passed** on Python 3.12.14. Command:

```sh
python -m unittest discover -s tests -v
```

All tests ran locally. The HTTP integration test used a real loopback HTTP server, synthetic sensor readings, a signed synthetic Meta webhook, SQLite, and a fake outbound sender. No real recipient was messaged.

## Verified behavior

| Area | Evidence |
|---|---|
| Access | A recipient cannot see or select an unassigned home. Unknown numbers get no reply. |
| Collector authorization | A home token determines the destination home, even if a payload supplies another home ID. |
| Consent | Enrollment alone does not schedule reports. START subscribes. STOP cancels queued reports. |
| Commands | Invalid times and intervals preserve the previous settings. Home and room filters work. |
| Schedules | Daily times, intervals, quiet hours, and a repeated daylight-saving hour behave as specified. |
| Restart/outage | Preferences persist. Repeated scheduler runs do not duplicate a slot. Missed slots do not flood the user. |
| Quiet boundary | A report queued before quiet hours cannot be sent after quiet hours start. |
| Webhooks | Invalid signatures, duplicate IDs, old timestamps, wrong business phone IDs, and oversized requests are handled. |
| Data validity | Invalid numbers, booleans, future timestamps, and invalid units are rejected or unavailable. |
| Freshness | Old and missing readings are not presented as current values. Older metric updates cannot replace newer readings. |
| Anti-spam | Command replies are limited. STOP remains effective at the limit. Reports are not split into many messages. |
| Delivery | Old service windows use templates. Uncertain sends are not automatically retried. Delivery status does not regress. |
| HTTP integration | JSON ingestion and signed STATUS request produce the expected isolated report through a fake sender. |

## Not tested in this environment

- Your physical HJ10, Xiaomi 4 Lite, or Xiaomi Dehumidifier Lite units.
- Vendor account login, exact regional model IDs, or integration behavior with disconnected hardware.
- Meta template approval, real API permissions, message delivery, billing, or recipient usability.
- Docker build, Caddy configuration execution, systemd execution, DNS, or TLS certificates. Docker and Caddy were unavailable here.
- Large-scale load, adversarial public traffic, host security, or disaster recovery.

The deployment files are supplied as configuration examples. They require commissioning. This is a tested software pilot, not a commissioned appliance service.

## Physical acceptance checklist

Record the outcome, actual model ID, Home Assistant version, and integration version for each unit.

1. Confirm the exact device model and region.
2. Confirm the room assignment.
3. Compare each mapped value and unit with the device app.
4. Confirm filter percentage means remaining life.
5. Confirm the dehumidifier tank-full binary state.
6. Disconnect one device.
7. Confirm that unavailable or old data appears within 15 minutes of the last valid update.
8. Reconnect the device and confirm fresh readings return.
9. Stop the collector and confirm the report marks the gateway data old.
10. Send duplicate webhook test events and confirm only one response.
11. Test an unassigned phone number and confirm no household data is disclosed.
12. Test daily and interval reports.
13. Test quiet hours and STOP.
14. Test approved-template delivery outside the service window.
15. Restart the server and confirm no message burst occurs.
16. Ask an elderly user to set a schedule and request a report without assistance.

Activation remains pending until the required physical and WhatsApp checks pass.
