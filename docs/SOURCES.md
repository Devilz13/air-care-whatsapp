# Sources checked on 11 October 2026

These are primary product, integration-maintainer, and platform references. No exact appliance compatibility is inferred solely from a product marketing page.

- Xiaomi official Home Assistant integration: https://github.com/XiaoMi/ha_xiaomi_home — regional account login and MIoT integration. Confirm exact device entities after login.
- Xiaomi Dehumidifier Lite upstream temperature correction: https://github.com/XiaoMi/ha_xiaomi_home/actions/runs/19374503020 — evidence of `xiaomi.derh.lite` upstream work; not a physical test of this installation.
- Xiaomi Air Purifier 4 Lite: https://www.mi.com/global/product/xiaomi-smart-air-purifier-4-lite/ — product identity.
- Dyson HJ10 product: https://www.dyson.com/air-treatment/air-purifiers/hushjet/black-teal — HJ10 and MyDyson product reference.
- Dyson integration: https://github.com/libdyson-wg/ha-dyson
- HJ10 support change: https://github.com/libdyson-wg/ha-dyson/pull/321 — listed open when checked; treat as an integration blocker until verified.
- Home Assistant REST API: https://developers.home-assistant.io/docs/api/rest/ — bearer-token access and state endpoints.
- Meta Cloud API setup: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started
- Meta service messages: https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages — service-window restrictions.
- Meta template fundamentals: https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview — templates outside the customer service window.
- Meta Messages API: https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/whatsapp-business-phone-number/message-api
- Meta webhook signature behavior: https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/ — HMAC validation reference. The SDK itself is not used.

Select a supported Graph API version from the Meta account at deployment. The code deliberately requires an explicit value instead of assuming that an old hard-coded version remains supported.
