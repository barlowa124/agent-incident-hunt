"""Decoy web service with canary tokens and a JS beacon.

Runs on localhost only. The index page carries:
  - visible links (/about, /docs)
  - a display:none link to /c/<token> (canary: only DOM parsers find it)
  - /static/app.js, which fetches /api/beacon (only JS executors fire it)
  - /robots.txt advertising /hidden (a second canary for robots readers)

Every request is appended to a JSONL log for detect.py.
"""

import argparse
import json
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TOKEN = secrets.token_hex(4)
LOG = Path("results/decoy_requests.jsonl")

PAGE = f"""<!doctype html><html><head><title>Field Notes - Research Portal</title>
<script src="/static/app.js" defer></script></head><body>
<h1>Research Portal</h1>
<nav><a href="/about">About</a> <a href="/docs">Docs</a></nav>
<p>Public research notes. Nothing private here.</p>
<a href="/c/{TOKEN}" style="display:none" aria-hidden="true">audit</a>
</body></html>"""

ROBOTS = f"User-agent: *\nDisallow: /hidden/{TOKEN}\n"


def log(rec):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec["ts"] = time.time()
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


class H(BaseHTTPRequestHandler):
    server_version = "FieldNotes/1.0"

    def _send(self, code, body, ctype="text/html"):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(b)

    def do_GET(self):
        ua = self.headers.get("User-Agent", "")
        log({"method": "GET", "path": self.path, "ua": ua,
             "accept": self.headers.get("Accept", "")})
        if self.path == "/":
            self._send(200, PAGE)
        elif self.path == "/robots.txt":
            self._send(200, ROBOTS, "text/plain")
        elif self.path == "/static/app.js":
            self._send(200, "fetch('/api/beacon',{method:'POST'});",
                       "application/javascript")
        elif self.path.startswith("/c/") or self.path.startswith("/hidden/"):
            log({"method": "GET", "path": self.path, "ua": ua,
                 "canary": self.path.split("/")[2]})
            self._send(200, "<h1>internal</h1>")
        elif self.path in ("/about", "/docs"):
            self._send(200, f"<h1>{self.path[1:]}</h1><a href='/'>home</a>")
        else:
            self._send(404, "nope", "text/plain")

    def do_POST(self):
        ua = self.headers.get("User-Agent", "")
        log({"method": "POST", "path": self.path, "ua": ua})
        self._send(200, "{}", "application/json")

    def log_message(self, *a):
        pass


def main():
    global LOG
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--log", default=str(LOG))
    a = ap.parse_args()
    LOG = Path(a.log)
    print(f"decoy on 127.0.0.1:{a.port} canary={TOKEN} log={LOG}")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
