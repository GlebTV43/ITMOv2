"""
windows_ollama_bridge.py — WSL-side HTTP proxy to Windows Ollama.

Architecture (local IPC only, no cloud):
  WSL process (this server) listens on 127.0.0.1:11434
  For each request, it spawns Windows Python via subprocess,
  passes method/path/body as base64-encoded JSON on stdin,
  Windows Python calls http://127.0.0.1:11434 on the Windows side,
  returns status/content-type/body (base64) on stdout.

Limitations:
  - Streaming SSE responses are fully buffered before returning.
    TTFT is not meaningful; suitable for correctness checks, not latency benchmarks.
  - One connection per request (subprocess overhead ~200-500 ms per call).
  - Designed for WSL2 NAT where WSL cannot reach Windows localhost directly.

Usage:
  python3 windows_ollama_bridge.py [--port 11434] [--win-python /path/to/python.exe]

Stop: Ctrl-C or send SIGTERM.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

WIN_PYTHON = "/mnt/c/Users/HanSolo/AppData/Local/Programs/Python/Python314/python.exe"
WIN_OLLAMA_URL = "http://127.0.0.1:11434"

# Compact Windows-side urllib client — sent as a single string to Win Python via stdin.
# Receives: JSON {method, path, body_b64, headers} on stdin (base64-encoded wrapper)
# Returns: JSON {status, content_type, body_b64} on stdout
WIN_CLIENT_CODE = r"""
import sys, json, base64, urllib.request, urllib.error

raw = sys.stdin.buffer.read()
req_obj = json.loads(base64.b64decode(raw.split(b"||PAYLOAD||",1)[1]))
method = req_obj["method"]
path = req_obj["path"]
body_b64 = req_obj.get("body_b64", "")
headers = req_obj.get("headers", {})

body_bytes = base64.b64decode(body_b64) if body_b64 else None

# Inject reasoning suppression for Ollama /api/chat and /v1/chat/completions
if body_bytes and method == "POST":
    ct = headers.get("content-type","")
    if "json" in ct or ct == "":
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
            if path == "/api/chat":
                payload.setdefault("think", False)
                payload.setdefault("stream", False)
                opts = payload.setdefault("options", {})
                opts.setdefault("num_predict", 1024)
            elif path in ("/v1/chat/completions", "/v1/chat/completions/"):
                payload.setdefault("stream", False)
                payload.setdefault("reasoning_effort", "none")
                payload.setdefault("max_tokens", 1024)
            body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["content-length"] = str(len(body_bytes))
        except Exception:
            pass

url = "http://127.0.0.1:11434" + path
req = urllib.request.Request(url, data=body_bytes, method=method)
for k, v in headers.items():
    lk = k.lower()
    if lk in ("host", "content-length", "transfer-encoding", "connection"):
        continue
    req.add_header(k, v)

try:
    with urllib.request.urlopen(req, timeout=600) as resp:
        body_out = resp.read()
        ct = resp.headers.get("Content-Type", "application/octet-stream")
        status = resp.status
except urllib.error.HTTPError as e:
    body_out = e.read()
    ct = e.headers.get("Content-Type", "application/json")
    status = e.code
except Exception as ex:
    body_out = json.dumps({"error": str(ex)}).encode()
    ct = "application/json"
    status = 502

result = {"status": status, "content_type": ct,
          "body_b64": base64.b64encode(body_out).decode()}
sys.stdout.buffer.write(json.dumps(result).encode("utf-8"))
sys.stdout.buffer.flush()
"""

_server_instance = None


class BridgeHandler(BaseHTTPRequestHandler):
    log_lock = threading.Lock()

    def log_message(self, fmt, *args):  # suppress default per-request stderr spam
        with self.log_lock:
            sys.stderr.write(f"[bridge] {self.address_string()} {fmt % args}\n")

    def _forward(self, method):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        headers_dict = {k: v for k, v in self.headers.items()}

        req_obj = {
            "method": method,
            "path": self.path,
            "body_b64": base64.b64encode(body).decode(),
            "headers": headers_dict,
        }
        payload_b64 = base64.b64encode(json.dumps(req_obj).encode("utf-8"))
        stdin_data = b"||PAYLOAD||" + payload_b64

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        try:
            result = subprocess.run(
                [WIN_PYTHON, "-c", WIN_CLIENT_CODE],
                input=stdin_data,
                capture_output=True,
                timeout=620,
                env=env,
            )
            if result.returncode != 0:
                err = result.stderr.decode("utf-8", errors="replace")
                self._error(502, f"Windows subprocess error: {err[:500]}")
                return
            out = result.stdout
            resp = json.loads(out.decode("utf-8"))
        except subprocess.TimeoutExpired:
            self._error(504, "Windows subprocess timed out")
            return
        except Exception as exc:
            self._error(502, f"Bridge internal error: {exc}")
            return

        status = resp.get("status", 502)
        ct = resp.get("content_type", "application/octet-stream")
        body_out = base64.b64decode(resp.get("body_b64", ""))

        self.send_response(status)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body_out)))
        self.end_headers()
        self.wfile.write(body_out)

    def _error(self, code, msg):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._forward("GET")

    def do_POST(self):
        self._forward("POST")

    def do_HEAD(self):
        self._forward("HEAD")

    def do_DELETE(self):
        self._forward("DELETE")


def run(port: int, win_python: str):
    global WIN_PYTHON
    WIN_PYTHON = win_python
    server = HTTPServer(("127.0.0.1", port), BridgeHandler)
    sys.stderr.write(
        f"[bridge] Listening on 127.0.0.1:{port} → Windows Ollama {WIN_OLLAMA_URL}\n"
        f"[bridge] Windows Python: {win_python}\n"
        f"[bridge] Buffering streaming responses fully (TTFT not measured). Ctrl-C to stop.\n"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("[bridge] Stopped.\n")
    finally:
        server.server_close()


def main():
    ap = argparse.ArgumentParser(description="WSL→Windows Ollama HTTP bridge")
    ap.add_argument("--port", type=int, default=11434)
    ap.add_argument("--win-python", default=WIN_PYTHON)
    args = ap.parse_args()
    run(args.port, args.win_python)


if __name__ == "__main__":
    main()
