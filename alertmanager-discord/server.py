"""Minimal Alertmanager → Discord webhook bridge."""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

import urllib.request

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "9094"))


class AlertHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        alerts = data.get("alerts", [])
        for alert in alerts:
            status = alert.get("status", "unknown").upper()
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})

            alertname = labels.get("alertname", "Unknown")
            severity = labels.get("severity", "info")
            summary = annotations.get("summary", "")
            description = annotations.get("description", "")

            color = {"critical": 0xFF0000, "warning": 0xFFA500}.get(severity, 0x00FF00)
            if status == "RESOLVED":
                color = 0x00FF00

            embed = {
                "title": f"[{status}] {alertname}",
                "description": f"**{summary}**\n{description}",
                "color": color,
                "fields": [
                    {"name": "Severity", "value": severity, "inline": True},
                    {"name": "Status", "value": status, "inline": True},
                ],
            }

            payload = json.dumps(
                {"username": "Alertmanager", "embeds": [embed]}
            ).encode("utf-8")

            req = urllib.request.Request(
                DISCORD_WEBHOOK,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "AlertmanagerDiscord/1.0",
                },
                method="POST",
            )
            try:
                urllib.request.urlopen(req)
                print(f"Sent alert {alertname} ({status}) to Discord")
            except Exception as e:
                print(f"Failed to send to Discord: {e}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        print(f"[webhook] {args[0]}")


if __name__ == "__main__":
    if not DISCORD_WEBHOOK:
        print("WARNING: DISCORD_WEBHOOK not set!")
    print(f"Listening on 0.0.0.0:{LISTEN_PORT}")
    server = HTTPServer(("0.0.0.0", LISTEN_PORT), AlertHandler)
    server.serve_forever()
