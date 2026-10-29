# RuFlirt AI backend
Static PWA runs on GitHub Pages. AI needs a **separate HTTPS server**; GitHub Pages cannot keep an API key secret or execute Python.

## Setup (on a server you control)
```bash
export OPENAI_API_KEY='YOUR_KEY'
export RUFLIRT_ORIGIN='https://ruslangreen.github.io'
python3 server.py
```
Bind is 127.0.0.1:8765. Put nginx with HTTPS in front, proxy `/suggest` to this port. Do not expose the port directly.

In RuFlirt's **Test and settings**, enter your backend HTTPS endpoint ending in `/suggest`. No API keys in the browser.

Caution: origin checks are not authentication. Before making the backend publicly reachable, add access control and rate limiting at nginx or application level. Do not deploy this sample publicly without protection. Audio is recognized by the browser; only transcript text and recent context are sent to the AI endpoint. Inform and obtain consent from participants.

AI response time is not guaranteed. The frontend falls back to local replies if backend times out.
