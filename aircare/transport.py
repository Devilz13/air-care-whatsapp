"""Official Meta Cloud API transport. No WhatsApp Web automation."""
import json
import os
import re
import urllib.request


def request_json(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=None if data is None else json.dumps(data, allow_nan=False).encode(), headers=headers, method=method)
    # Reject redirects so bearer credentials cannot travel to a different host.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None
    with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Response too large")
        return json.loads(raw)


def message_payload(phone, body, template, callback, template_name, language):
    payload = {"messaging_product": "whatsapp", "to": phone, "biz_opaque_callback_data": callback}
    if template:
        # Template text parameters cannot contain newlines. Stay below the
        # template body limit after the fixed text is added.
        summary = " | ".join(body.splitlines())
        summary = " ".join(summary.split())
        if len(summary) > 800:
            summary = summary[:730] + "... Report shortened. Reply STATUS for more."
        payload.update(type="template", template={"name": template_name,
            "language": {"code": language}, "components": [{"type": "body", "parameters": [{"type": "text", "text": summary}]}]})
    else:
        if len(body) > 3500:
            body = body[:3380] + "\nReport shortened. Send HOME code, then ROOM name, then STATUS for a smaller report."
        payload.update(type="text", text={"preview_url": False, "body": body})
    return payload


class MetaSender:
    def __init__(self):
        self.version = os.environ["META_GRAPH_VERSION"]
        self.phone_id = os.environ["META_PHONE_NUMBER_ID"]
        self.token = os.environ["META_ACCESS_TOKEN"]
        self.template = os.environ["META_TEMPLATE_NAME"]
        self.language = os.environ.get("META_TEMPLATE_LANGUAGE", "en_US")
        if not re.fullmatch(r"v\d+\.\d+", self.version) or not self.phone_id.isdigit():
            raise ValueError("Invalid Meta version or phone number ID")

    def __call__(self, phone, body, template, callback):
        payload = message_payload(phone, body, template, callback, self.template, self.language)
        response = request_json(f"https://graph.facebook.com/{self.version}/{self.phone_id}/messages", "POST", payload, self.token)
        return response["messages"][0]["id"]
