# Free-only deployment constraint

**Update:** Telegram is now approved as the primary channel. A Cloudflare Worker/D1 prototype is in `cloudflare/`. No resources have been provisioned. See `PROJECT_STATUS.md` for the current plan and `WHATSAPP_FUTURE.md` for the newly identified bounded WhatsApp service-message allowance.

Confirmed by the owner on 11 October 2026: the service must remain free.

No paid compute, disks, databases, messaging, or automatic upgrades are authorized. Render workspace `My Workspace` is approved for use, subject to this limit. No Render services have been created by this project.

The paid `render.yaml` has been withdrawn. Earlier cloud instructions describing a paid report instance and disk are historical design notes, not deployment instructions under this requirement.

## Why the current build must not be deployed to Render Free

- The app schedules messages inside a continuously running process. Render Free sleeps after 15 minutes without inbound traffic.
- The app stores schedules, consent, permissions, and delivery records in SQLite. Render Free loses local files on restart, redeploy, or sleep, and cannot attach a persistent disk.
- Render Free Postgres expires after 30 days; it is not a permanent free replacement.
- Free Render compute does not by itself guarantee zero bills. Bandwidth and build overages may be billed when a payment method is present. Account billing controls have not been inspected or changed.
- WhatsApp proactive template delivery cannot be assumed free. Provider pricing and account-specific allowances must be verified before enabling real delivery. Do not imply that keeping a service window open guarantees a permanently free automated service.
- The cloud-hosted device integration service has not been provisioned or verified. A free report endpoint alone does not solve appliance connectivity.

Do not use synthetic keep-alive traffic as a substitute for a supported reliable scheduler. Do not store household credentials or live readings in the public GitHub repository to avoid database costs. Do not substitute an unapproved messaging platform or a demo for the requested service without explaining the difference.

## Remaining design choices

A zero-cost design needs a verified free durable store, event-driven scheduling within enforceable free quotas, and a free delivery method. Even if hosting is solved on another provider, WhatsApp proactive delivery remains a separate pricing constraint. The current requirements cannot be promised together on the verified Render/WhatsApp route.

An on-demand report or a different notification channel may reduce costs, but neither has been selected by the owner. Research those alternatives before claiming they meet the requirements. Keep the existing source and tests available; do not enable live messaging until the zero-cost constraint is satisfied or explicitly changed.

Primary references checked on 11 October 2026:

- https://render.com/docs/free
- https://whatsappbusiness.com/products/platform-pricing/

Meta's public pricing page and secondary reports of October changes were not fully consistent during checking. No account-specific free allowance was verified. No exact WhatsApp rate or permanent free guarantee is asserted here.
