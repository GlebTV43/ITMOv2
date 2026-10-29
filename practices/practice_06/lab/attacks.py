"""Reproduce attacks only against a private local Mini Shop process and fixtures."""

import argparse
from contextlib import contextmanager
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import subprocess
import signal
import shutil
import tempfile
import sys
from urllib.parse import quote, urlencode, urlsplit

LAB = Path(__file__).resolve().parent
PRACTICE = LAB.parent


class Client:
    def __init__(self, base):
        target = urlsplit(base)
        if target.hostname != "127.0.0.1":
            raise ValueError("exercise accepts only loopback")
        self.port = target.port
        self.exchange = None

    def call(self, method, path, body=None, auth=None, headers=None, raw=None):
        values = {"Content-Type": "application/json", **(auth or {}), **(headers or {})}
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        connection = HTTPConnection("127.0.0.1", self.port, timeout=8)
        try:
            connection.request(method, path, data, values)
            response = connection.getresponse()
            text = response.read().decode("utf-8")
            try:
                result = json.loads(text)
            except ValueError:
                result = text
            self.exchange = {"method": method, "path": path, "body": body,
                             "raw_body_hex": raw.hex() if raw is not None else None,
                             "headers": {k: ("<session>" if k.lower() == "x-token" else v)
                                         for k, v in values.items()},
                             "status": response.status, "response": result}
            return response.status, result
        finally:
            connection.close()

    def login(self, username):
        status, result = self.call("POST", "/login", {"username": username, "password": "learn-" + username})
        if status != 200:
            raise RuntimeError(f"fixture login failed: {status}")
        return {"X-Token": result["token"]}


@contextmanager
def running_shop(port=0):
    fixture_root = None
    process = subprocess.Popen([sys.executable, "-u", str(LAB / "service.py"), "--port", str(port)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    try:
        line = process.stdout.readline().strip()
        if not line.startswith("Local exercise: "):
            raise RuntimeError("shop failed to start: " + line)
        base = line.split("Local exercise: ", 1)[1]
        fixture_line = process.stdout.readline().strip()
        prefix = "Disposable fixture files: "
        if fixture_line.startswith(prefix):
            candidate = Path(fixture_line[len(prefix):]).resolve()
            if (candidate.parent == Path(tempfile.gettempdir()).resolve()
                    and candidate.name.startswith("itmo-practice-06-")):
                fixture_root = candidate
        yield Client(base)
    finally:
        # Dedicated graceful shutdown channel, not exposed as an HTTP route.
        if os.name == "nt":
            process.terminate()
        else:
            process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
        # Windows terminate bypasses Python finally. Only remove the exact newly
        # created fixture root reported by our own process after verifying its boundary.
        if fixture_root is not None and fixture_root.exists():
            shutil.rmtree(fixture_root)


def exercise(client):
    alice, bob, staff = (client.login(name) for name in ("alice", "bob", "staff"))
    cases = []

    def check(case_id, title, method, path, body=None, auth=None, headers=None,
              predicate=None, expected="denied", raw=None):
        status, result = client.call(method, path, body, auth, headers, raw)
        safe = predicate(status, result) if predicate else status in (400, 401, 403, 404, 413, 415, 429)
        cases.append({"id": case_id, "title": title, "expected": expected,
                      "safe": bool(safe), "exchange": client.exchange})

    check("A01", "Unauthenticated profile access", "GET", "/profile?id=1")
    check("A02", "Cross-customer profile IDOR", "GET", "/profile?id=2", auth=alice)
    check("A03", "Numeric SQL injection", "GET", "/profile?" + urlencode({"id": "1 OR 1=1"}), auth=alice)
    check("A04", "String SQL injection and unrestricted search", "GET",
          "/search?" + urlencode({"q": "' OR 1=1 --"}), auth=alice,
          predicate=lambda s, r: s == 200 and isinstance(r, list) and not any(x.get("id") == 2 for x in r),
          expected="200, no Bob or SQL expansion")
    check("A05", "All-customer order disclosure", "GET", "/orders", auth=alice,
          predicate=lambda s, r: s == 200 and all(x.get("owner") == 1 for x in r),
          expected="200, only Alice orders")
    check("A06", "Client controls purchase price", "POST", "/orders",
          {"product": "chair", "price": 0.01}, alice,
          predicate=lambda s, r: s == 201 and r.get("price") == 5000,
          expected="201, server catalogue price 5000")
    check("A07", "Forged staff role without session", "GET", "/admin/export", headers={"X-Role": "staff"})
    check("A08", "Forged staff role with customer session", "GET", "/admin/export", auth=alice,
          headers={"X-Role": "staff"})
    check("A09", "Cross-customer receipt access", "GET", "/files?user=bob&path=receipt.txt", auth=alice)
    check("A10", "Traversal within physical sandbox", "GET",
          "/files?" + urlencode({"user": "alice", "path": "../../private/operator-note.txt"}), auth=alice)
    marker = '<script>document.body.dataset.compromised="yes"</script>'
    client.call("POST", "/reviews", {"product": "chair", "text": marker}, alice)
    check("A11", "Stored HTML/script injection", "GET", "/reviews/view", auth=alice,
          predicate=lambda s, r: s == 200 and "<script>" not in r and "&lt;script&gt;" in r,
          expected="200, escaped review text")
    check("A12", "Password and token exposure in debug logs", "GET", "/debug/logs", auth=alice)
    check("A13", "Cross-customer AI context", "GET", "/assistant/context?order_id=2", auth=alice)
    check("A14", "SQL injection in AI order lookup", "GET",
          "/assistant/context?" + urlencode({"order_id": "1 OR 1=1"}), auth=alice)
    check("A15", "AI executor reads another receipt", "POST", "/assistant/execute",
          {"decision": {"tool": "read_file", "arguments": {"path": "files/bob/receipt.txt"}}}, alice)
    check("A16", "AI executor reads private note", "POST", "/assistant/execute",
          {"decision": {"tool": "read_file", "arguments": {"path": "private/operator-note.txt"}}}, alice)
    check("A17", "AI executor exports profiles", "POST", "/assistant/execute",
          {"decision": {"tool": "export_profiles", "arguments": {}}}, alice)
    check("A18", "Unauthenticated AI tool execution", "POST", "/assistant/execute",
          {"decision": {"tool": "export_profiles", "arguments": {}}})
    check("A19", "Malformed JSON leaks exception details", "POST", "/login", raw=b'{"username":',
          predicate=lambda s, r: s == 400 and isinstance(r, dict) and "type" not in r,
          expected="400, no internal exception")
    check("A20", "Unexpected JSON type causes internal error", "POST", "/orders", raw=b"[]", auth=alice,
          predicate=lambda s, r: s == 400 and isinstance(r, dict) and "type" not in r,
          expected="400, no traceback/type")
    check("A21", "Unbounded review length", "POST", "/reviews",
          {"product": "chair", "text": "x" * 2001}, alice)
    check("A22", "Anonymous review creation", "POST", "/reviews",
          {"product": "chair", "text": "anonymous"})
    check("A23", "AI deletion of fixture files", "POST", "/assistant/execute",
          {"decision": {"tool": "delete_tree", "arguments": {"path": "files"}}}, alice)
    status, result = client.call("GET", "/files?user=alice&path=receipt.txt", auth=alice)
    cases.append({"id": "A24", "title": "Receipt survives dangerous decision", "expected": "200, own receipt intact",
                  "safe": status == 200 and "TEST_ALICE" in str(result), "exchange": client.exchange})
    # Successful scenarios are retained alongside exploit evidence.
    good = []
    for title, method, path, body, auth, expected in [
        ("own profile", "GET", "/profile?id=1", None, alice, 200),
        ("staff export using server session", "GET", "/admin/export", None, staff, 200),
        ("catalogue purchase", "POST", "/orders", {"product": "lamp"}, alice, 201),
    ]:
        status, _ = client.call(method, path, body, auth)
        good.append({"scenario": title, "status": status, "expected": expected, "pass": status == expected})
    return {"cases": cases, "good_scenarios": good,
            "safe": sum(c["safe"] for c in cases), "total": len(cases)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["before", "after"], required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if args.phase == "before" and (PRACTICE / "evidence/before/attacks.json").exists():
        parser.error("original before evidence already exists; refusing to overwrite it with the fixed service")
    with running_shop(args.port) as client:
        report = exercise(client)
    report["source_sha256"] = hashlib.sha256((LAB / "service.py").read_bytes()).hexdigest()
    report["phase"] = args.phase
    directory = PRACTICE / "evidence" / args.phase
    directory.mkdir(parents=True, exist_ok=True)
    # Sessions and passwords are synthetic fixture values; no external credentials are present.
    output = directory / "attacks.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.phase}: {report['safe']}/{report['total']} safe outcomes; evidence: {output}")
    if args.phase == "after" and (report["safe"] != report["total"] or
                                  not all(g["pass"] for g in report["good_scenarios"])):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
