#!/usr/bin/env python3
"""
claude_proxy.py — Zero-cost Anthropic API proxy

Runs a local HTTP proxy on port 4080 (configurable).
Point your tools at http://localhost:4080 instead of https://api.anthropic.com.
Every real response updates ~/.cache/claude_ratelimit.json with the latest
rate-limit headers — no extra API calls, no wasted tokens.

Usage:
    python3 claude_proxy.py &

Then in your shell profile:
    export ANTHROPIC_BASE_URL=http://localhost:4080
"""

import http.server
import http.client
import json
import os
import ssl
import threading
import urllib.parse
from datetime import datetime, timezone

PROXY_PORT    = 4080
UPSTREAM_HOST = "api.anthropic.com"
UPSTREAM_PORT = 443
STATE_FILE    = os.path.expanduser("~/.cache/claude_ratelimit.json")

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

RATELIMIT_HEADERS = [
    # unified (Claude Max / claude.ai plans)
    "anthropic-ratelimit-unified-tokens-limit",
    "anthropic-ratelimit-unified-tokens-remaining",
    "anthropic-ratelimit-unified-tokens-reset",
    # standard API
    "anthropic-ratelimit-tokens-limit",
    "anthropic-ratelimit-tokens-remaining",
    "anthropic-ratelimit-tokens-reset",
    "anthropic-ratelimit-requests-limit",
    "anthropic-ratelimit-requests-remaining",
    "anthropic-ratelimit-requests-reset",
    "anthropic-ratelimit-input-tokens-limit",
    "anthropic-ratelimit-input-tokens-remaining",
    "anthropic-ratelimit-input-tokens-reset",
    "anthropic-ratelimit-output-tokens-limit",
    "anthropic-ratelimit-output-tokens-remaining",
    "anthropic-ratelimit-output-tokens-reset",
    # retry
    "retry-after",
]

_write_lock = threading.Lock()


def save_state(headers: dict[str, str]) -> None:
    captured = {k: v for k, v in headers.items() if k in RATELIMIT_HEADERS}
    if not captured:
        return
    captured["_updated_at"] = datetime.now(timezone.utc).isoformat()
    with _write_lock:
        with open(STATE_FILE, "w") as f:
            json.dump(captured, f, indent=2)


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    # Silence access log — iTerm2 script reads the file, not stdout
    def log_message(self, fmt, *args):
        pass

    def _forward(self):
        # ── Build upstream request ────────────────────────────────────────────
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length else b""

        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(UPSTREAM_HOST, UPSTREAM_PORT, context=ctx)

        # Forward all headers except Host
        fwd_headers = {
            k: v for k, v in self.headers.items()
            if k.lower() != "host"
        }

        conn.request(self.command, self.path, body=body, headers=fwd_headers)
        resp = conn.getresponse()

        # ── Capture rate-limit headers ────────────────────────────────────────
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        save_state(resp_headers)

        # ── Stream response back to client ────────────────────────────────────
        self.send_response(resp.status, resp.reason)
        for k, v in resp.getheaders():
            # Don't forward transfer-encoding; we'll send raw body
            if k.lower() in ("transfer-encoding",):
                continue
            self.send_header(k, v)
        self.end_headers()

        while chunk := resp.read(8192):
            self.wfile.write(chunk)

        conn.close()

    def do_GET(self):    self._forward()
    def do_POST(self):   self._forward()
    def do_PUT(self):    self._forward()
    def do_DELETE(self): self._forward()
    def do_PATCH(self):  self._forward()


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PROXY_PORT), ProxyHandler)
    print(f"Claude proxy running on http://127.0.0.1:{PROXY_PORT}")
    print(f"Rate-limit state → {STATE_FILE}")
    print(f"Set: export ANTHROPIC_BASE_URL=http://localhost:{PROXY_PORT}")
    server.serve_forever()
