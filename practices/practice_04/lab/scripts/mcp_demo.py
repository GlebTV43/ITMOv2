"""
MCP stdio client test — verifies mcp/server.py over actual subprocess.

Tests:
  1. initialize / initialized notification (no bogus response)
  2. tools/list
  3. tools/call inspect_subscriber — valid input
  4. tools/call inspect_subscriber — empty string (ValueError)
  5. tools/call inspect_subscriber — integer (TypeError)
  6. tools/call inspect_subscriber — 80-char name (valid boundary)
  7. tools/call inspect_subscriber — 81-char name (invalid boundary)
  8. ping
  9. unknown method (error response, no crash)
  10. malformed JSON (error response, no crash)

Writes results to results/mcp_stdio.json.
Exits non-zero if any test fails.
"""
import sys
import os
import json
import subprocess
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAB_DIR = os.path.dirname(SCRIPT_DIR)
RESULTS_DIR = os.path.join(LAB_DIR, "results")
SERVER_PATH = os.path.join(LAB_DIR, "mcp", "server.py")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "mcp_stdio.json")

os.makedirs(RESULTS_DIR, exist_ok=True)


def run_session(messages: list) -> list:
    """
    Send *messages* (list of dicts or raw strings) to the server over stdin,
    collect all stdout lines, parse and return them.
    """
    lines = []
    for m in messages:
        if isinstance(m, dict):
            lines.append(json.dumps(m, ensure_ascii=False))
        else:
            lines.append(str(m))  # raw string for malformed-JSON test
    stdin_text = "\n".join(lines) + "\n"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, SERVER_PATH],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"MCP exited {proc.returncode}: {proc.stderr}")
    responses = []
    for raw in proc.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            responses.append(json.loads(raw))
        except json.JSONDecodeError:
            responses.append({"_raw": raw, "_parse_error": True})
    return responses


def find_response(responses, req_id):
    for r in responses:
        if r.get("id") == req_id:
            return r
    return None


results = []


def check(name, passed, detail):
    status = "PASS" if passed else "FAIL"
    results.append({"test": name, "status": status, "detail": detail})
    print(f"  [{status}] {name}")
    if not passed:
        print(f"         {detail}")


print("Running MCP stdio tests...")
print()

# --- Session 1: initialize + initialized notification + tools/list ---
sess1 = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "test", "version": "0"}}},
    # initialized is a notification (no id) — server must NOT reply
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
]
r1 = run_session(sess1)

init_resp = find_response(r1, 1)
check(
    "initialize returns protocolVersion",
    init_resp is not None and init_resp.get("result", {}).get("protocolVersion") == "2024-11-05",
    f"got: {init_resp}",
)

# Notification must not produce a response with id=None matching a spurious entry
notification_responses = [r for r in r1 if r.get("id") is None and "result" in r]
check(
    "initialized notification produces no response",
    len(notification_responses) == 0,
    f"unexpected responses: {notification_responses}",
)

list_resp = find_response(r1, 2)
tools = list_resp.get("result", {}).get("tools", []) if list_resp else []
tool_names = [t["name"] for t in tools]
check(
    "tools/list contains inspect_subscriber",
    "inspect_subscriber" in tool_names,
    f"tools: {tool_names}",
)

# --- Session 2: valid input ---
sess2 = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
     "params": {"name": "inspect_subscriber", "arguments": {"name": "  alice  "}}},
]
r2 = run_session(sess2)
call_resp = find_response(r2, 2)
if call_resp:
    content_text = call_resp.get("result", {}).get("content", [{}])[0].get("text", "")
    try:
        payload = json.loads(content_text)
        valid_ok = (
            payload.get("valid") is True
            and payload.get("normalized") == "alice"
            and payload.get("length") == 5
            and call_resp["result"].get("isError") is False
        )
        check("inspect_subscriber valid name normalises correctly", valid_ok, f"payload: {payload}")
    except Exception as e:
        check("inspect_subscriber valid name normalises correctly", False, f"parse error: {e}, raw: {content_text}")
else:
    check("inspect_subscriber valid name normalises correctly", False, f"no response in {r2}")

# --- Session 3: empty string (ValueError) ---
sess3 = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
     "params": {"name": "inspect_subscriber", "arguments": {"name": ""}}},
]
r3 = run_session(sess3)
err_resp = find_response(r3, 2)
if err_resp:
    is_error = err_resp.get("result", {}).get("isError") is True
    text = err_resp.get("result", {}).get("content", [{}])[0].get("text", "")
    check(
        "inspect_subscriber empty string returns isError with ValueError",
        is_error and "ValueError" in text,
        f"isError={is_error}, text={text!r}",
    )
else:
    check("inspect_subscriber empty string returns isError with ValueError", False, f"no response in {r3}")

# --- Session 4: integer (TypeError) ---
sess4 = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
     "params": {"name": "inspect_subscriber", "arguments": {"name": 42}}},
]
r4 = run_session(sess4)
err_resp4 = find_response(r4, 2)
if err_resp4:
    is_error4 = err_resp4.get("result", {}).get("isError") is True
    text4 = err_resp4.get("result", {}).get("content", [{}])[0].get("text", "")
    check(
        "inspect_subscriber integer returns isError with TypeError",
        is_error4 and "TypeError" in text4,
        f"isError={is_error4}, text={text4!r}",
    )
else:
    check("inspect_subscriber integer returns isError with TypeError", False, f"no response in {r4}")

# --- Session 5: 80-char name (valid boundary) ---
sess5 = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
     "params": {"name": "inspect_subscriber", "arguments": {"name": "a" * 80}}},
]
r5 = run_session(sess5)
resp5 = find_response(r5, 2)
if resp5:
    text5 = resp5.get("result", {}).get("content", [{}])[0].get("text", "")
    try:
        p5 = json.loads(text5)
        check(
            "inspect_subscriber 80-char name is valid",
            p5.get("valid") is True and p5.get("length") == 80,
            f"payload: {p5}",
        )
    except Exception as e:
        check("inspect_subscriber 80-char name is valid", False, f"{e}, raw: {text5}")
else:
    check("inspect_subscriber 80-char name is valid", False, f"no response in {r5}")

# --- Session 6: 81-char name (invalid boundary) ---
sess6 = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
     "params": {"name": "inspect_subscriber", "arguments": {"name": "a" * 81}}},
]
r6 = run_session(sess6)
resp6 = find_response(r6, 2)
if resp6:
    is_error6 = resp6.get("result", {}).get("isError") is True
    text6 = resp6.get("result", {}).get("content", [{}])[0].get("text", "")
    check(
        "inspect_subscriber 81-char name returns isError with ValueError",
        is_error6 and "ValueError" in text6,
        f"isError={is_error6}, text={text6!r}",
    )
else:
    check("inspect_subscriber 81-char name returns isError with ValueError", False, f"no response in {r6}")

# --- Session 7: ping ---
sess7 = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
    {"jsonrpc": "2.0", "id": 2, "method": "ping"},
]
r7 = run_session(sess7)
ping_resp = find_response(r7, 2)
check(
    "ping returns empty result",
    ping_resp is not None and ping_resp.get("result") == {},
    f"got: {ping_resp}",
)

# --- Session 8: unknown method ---
sess8 = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
    {"jsonrpc": "2.0", "id": 2, "method": "no_such_method"},
]
r8 = run_session(sess8)
unknown_resp = find_response(r8, 2)
check(
    "unknown method returns error without crashing",
    unknown_resp is not None and "error" in unknown_resp,
    f"got: {unknown_resp}",
)

# --- Session 9: malformed JSON ---
sess9_raw = [
    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}),
    "{this is not json",
    json.dumps({"jsonrpc": "2.0", "id": 3, "method": "ping"}),
]
r9 = run_session(sess9_raw)
# Should have an error response for the bad line AND a ping response
has_error = any("error" in r and r.get("id") is None for r in r9)
has_ping = find_response(r9, 3) is not None
check(
    "malformed JSON returns error response without crashing",
    has_error,
    f"responses: {r9}",
)
check(
    "server continues processing after malformed JSON",
    has_ping,
    f"no ping response in: {r9}",
)

# --- Summary ---
total = len(results)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = total - passed

output = {
    "runner": "scripts/mcp_demo.py",
    "note": "Evidence of real subprocess MCP calls. Not an OpenCode invocation.",
    "summary": {"total": total, "passed": passed, "failed": failed},
    "tests": results,
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print()
print(f"Results written to: {OUTPUT_FILE}")
print(f"Summary: {passed}/{total} passed")

if failed > 0:
    sys.exit(1)
