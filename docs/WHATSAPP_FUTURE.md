# Future WhatsApp pathway — research, not enabled

Checked: 11 October 2026.

## Finding

Meta's official FAQ now states that, from 1 October 2026, the first **1,000 service messages per business phone number each month** are free, with charges from message 1,001. It separately lists marketing, utility, and authentication messages as charged categories. This is more specific than older text on the public pricing page that still describes service responses as uncharged.

This creates a candidate for **bounded user-requested reports**, not a guarantee of permanently free unattended scheduled WhatsApp delivery. The normal customer-service window still matters. Sending a command each day to reopen that window may be workable for some users, but must not be disguised as the original hands-off experience.

## Options to investigate

| Option | Potential use | Limitation |
|---|---|---|
| Direct Cloud API service replies | User sends STATUS; bot responds within the permitted window and free account allowance | Account eligibility, billing behavior, and a hard quota guard must be verified |
| Scheduled responses during a valid service window | Possibly send requested reports while a window is open, subject to Meta rules and allowance | Needs recent user interaction; cannot cover unattended operation indefinitely |
| Manual WhatsApp sharing | A helper manually shares a Telegram report | Free app use is possible, but this is not automated delivery |
| Meta test number | Developer testing only | Not a production route for elderly household users |
| Ad/free-entry-point window | Temporary pricing exception | Advertising can cost money and the window is temporary; not a permanent zero-cost architecture |
| Unofficial WhatsApp Web libraries | Not selected | Session maintenance, platform restrictions, and account risk conflict with minimal setup and dependable operation |

## Conditions before implementing free WhatsApp

1. Read the account's current Meta pricing and applicable terms.
2. Verify that the free allowance applies to the actual business phone number and intended service messages.
3. Use the direct API if it avoids third-party platform fees.
4. Account for **all** applications that send from the same business number, not just Air Care.
5. Implement a durable, atomic monthly reservation counter and a conservative margin below the allowance.
6. Refuse template messages and refuse sends outside the permitted window in the free-only mode.
7. Refuse sends if the usage counter, account data, or pricing policy cannot be verified.
8. Test the limit without sending enough real messages to incur charges.
9. Explain to users that reports can pause until they send another message or the allowance resets.

No such quota guard is implemented in the original Python WhatsApp adapter. Do not enable that adapter under the current free-only constraint. The Telegram Worker contains no WhatsApp sender.

Sources:

- https://whatsappbusiness.com/resources/faq/ — see the current pricing bullets with the 1 October 2026 effective date; the page also contains older conversation-pricing text.
- https://whatsappbusiness.com/products/platform-pricing/ — broader pricing description, partially inconsistent with the dated FAQ change.
- https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages — service-window restrictions.

This document records a future pathway, not a claim that the owner has an eligible configured account or that all requested messages will be free.
