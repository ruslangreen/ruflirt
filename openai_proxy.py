#!/usr/bin/env python3
"""RuFlirt private OpenAI proxy. Standard-library only; bind to loopback."""
import hmac
import json
import os
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = int(os.getenv("RUFLIRT_PORT", "18765"))
API_KEY = os.environ["OPENAI_API_KEY"]
ACCESS_TOKEN = os.environ["RUFLIRT_ACCESS_TOKEN"]
ALLOWED_ORIGIN = os.getenv("RUFLIRT_ALLOWED_ORIGIN", "https://ruslangreen.github.io")
MODEL = os.getenv("RUFLIRT_MODEL", "gpt-4.1-mini")
MAX_REQUESTS = int(os.getenv("RUFLIRT_REQUESTS_PER_HOUR", "120"))
MAX_BODY = 8192
calls = defaultdict(deque)
lock = threading.Lock()
INSTRUCTIONS = (
    "Ты суфлёр живого флирта для взрослого мужчины. Учитывай историю диалога, "
    "тон, границы и взаимность. Дай одну естественную, слегка игривую реплику "
    "от первого лица, до 15 слов. Без пояснений, пафоса и давления. "
    "Если девушка отказывает или ей некомфортно, предложи вежливо закончить разговор."
)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Do not log conversation text, credentials, or response bodies.
        print("%s %s" % (self.address_string(), fmt % args), flush=True)

    def headers_common(self):
        origin = self.headers.get("Origin")
        if origin == ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")

    def reply(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.headers_common()
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        if self.headers.get("Origin") != ALLOWED_ORIGIN:
            return self.reply(403, {"error": "origin_not_allowed"})
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.headers_common()
        self.end_headers()

    def do_POST(self):
        if self.path != "/suggest":
            return self.reply(404, {"error": "not_found"})
        origin = self.headers.get("Origin")
        if origin and origin != ALLOWED_ORIGIN:
            return self.reply(403, {"error": "origin_not_allowed"})
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, ACCESS_TOKEN):
            return self.reply(401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                return self.reply(413, {"error": "invalid_size"})
            body = json.loads(self.rfile.read(length))
            text = body.get("text", "")
            history = body.get("history", [])
            if not isinstance(text, str) or not 0 < len(text) <= 1500:
                return self.reply(400, {"error": "invalid_text"})
            if not isinstance(history, list):
                history = []
            history = [(str(item.get("speaker", "other")) + ": " + str(item.get("text", "")))[:300] if isinstance(item, dict) else str(item)[:300] for item in history[-8:]]
        except (ValueError, UnicodeError, TypeError, json.JSONDecodeError):
            return self.reply(400, {"error": "invalid_json"})
        now = time.monotonic()
        with lock:
            q = calls["single_private_user"]
            while q and now - q[0] > 3600:
                q.popleft()
            if len(q) >= MAX_REQUESTS:
                return self.reply(429, {"error": "hourly_limit"})
            q.append(now)
        prompt = "\n".join(history + [text])
        payload = json.dumps({
            "model": MODEL,
            "instructions": INSTRUCTIONS,
            "input": prompt,
            "max_output_tokens": 80,
            "store": False
        }, ensure_ascii=False).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=payload,
            headers={
                "Authorization": "Bearer " + API_KEY,
                "Content-Type": "application/json"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.load(resp)
            answer = " ".join(
                item.get("text", "")
                for output in data.get("output", [])
                for item in output.get("content", [])
                if item.get("type") == "output_text"
            ).strip()
            if not answer:
                return self.reply(502, {"error": "empty_model_response"})
            return self.reply(200, {"reply": answer, "suggestion": answer})
        except (urllib.error.URLError, TimeoutError, ValueError):
            return self.reply(502, {"error": "upstream_failed"})

if __name__ == "__main__":
    if len(ACCESS_TOKEN) < 24:
        raise SystemExit("RUFLIRT_ACCESS_TOKEN must be at least 24 characters")
    print("RuFlirt proxy listening on %s:%s" % (HOST, PORT), flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
