"""
MCP stdio regression tests — exercises mcp/server.py as a real subprocess
over the JSON-RPC 2.0 stdio protocol.

Each test sends one or more newline-delimited JSON messages via stdin and
asserts on the parsed JSON-RPC response. The subprocess is launched fresh
per test class (shared via setUpClass) and communicated with a timeout.

Covered scenarios:
  - null / array / scalar (non-object) JSON envelope → -32600 Invalid Request
  - malformed JSON → -32700 Parse error
  - invalid params type (non-dict) → -32602 Invalid params
  - invalid arguments type (non-dict) → -32602 Invalid params
  - missing 'name' key in arguments → isError result (tool-level error)
  - unknown method → -32601 Method not found
  - unknown tool name → -32601 Unknown tool
  - numeric 42 as name value (raw stdio, bypassing JSON schema) →
      isError result reporting TypeError (not an internal server error)
  - valid Unicode name → success result with normalized/length/valid
  - process continues to handle ping after prior invalid input
"""
import sys
import os
import json
import subprocess
import unittest

_LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVER = os.path.join(_LAB, "mcp", "server.py")


def _run_server(lines: list[str]) -> list[dict]:
    """
    Start mcp/server.py, write *lines* to its stdin, collect stdout until EOF,
    return parsed JSON objects.  Raises on timeout or non-decodable output.
    """
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        [sys.executable, _SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=_LAB,
        env=env,
    )
    payload = "\n".join(lines) + "\n"
    stdout, stderr = proc.communicate(input=payload.encode("utf-8"), timeout=5)
    if proc.returncode != 0:
        raise AssertionError(f"MCP exited {proc.returncode}: {stderr.decode('utf-8')}")

    results = []
    for raw in stdout.decode("utf-8").splitlines():
        raw = raw.strip()
        if raw:
            results.append(json.loads(raw))
    return results


def _ping_msg(req_id=99):
    return json.dumps({"jsonrpc": "2.0", "id": req_id, "method": "ping"})


class TestMcpNullEnvelope(unittest.TestCase):
    """JSON null at top level must return -32600, not AttributeError."""

    def test_null_envelope_returns_invalid_request_error(self):
        responses = _run_server(["null"])
        self.assertEqual(len(responses), 1)
        err = responses[0].get("error", {})
        self.assertEqual(err.get("code"), -32600)

    def test_null_envelope_error_message_is_string(self):
        responses = _run_server(["null"])
        self.assertEqual(len(responses), 1)
        err = responses[0].get("error", {})
        self.assertIsInstance(err.get("message"), str)


class TestMcpArrayEnvelope(unittest.TestCase):
    """JSON array at top level must return -32600, not AttributeError."""

    def test_array_envelope_returns_invalid_request_error(self):
        responses = _run_server(['[{"jsonrpc":"2.0","id":1,"method":"ping"}]'])
        self.assertEqual(len(responses), 1)
        err = responses[0].get("error", {})
        self.assertEqual(err.get("code"), -32600)


class TestMcpScalarEnvelope(unittest.TestCase):
    """JSON scalar (number) at top level must return -32600."""

    def test_scalar_number_envelope_returns_invalid_request_error(self):
        responses = _run_server(["42"])
        self.assertEqual(len(responses), 1)
        err = responses[0].get("error", {})
        self.assertEqual(err.get("code"), -32600)


class TestMcpMalformedJson(unittest.TestCase):
    """Malformed JSON must return -32700 Parse error."""

    def test_malformed_json_returns_parse_error(self):
        responses = _run_server(["{not valid json"])
        self.assertEqual(len(responses), 1)
        err = responses[0].get("error", {})
        self.assertEqual(err.get("code"), -32700)


class TestMcpInvalidParamsType(unittest.TestCase):
    """Non-object params must produce a recoverable -32602 error."""

    def test_array_params_returns_invalid_request_error(self):
        msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": [1, 2]})
        responses = _run_server([msg])
        self.assertEqual(len(responses), 1)
        err = responses[0].get("error", {})
        self.assertEqual(err.get("code"), -32602)

    def test_null_params_are_rejected_and_ping_still_works(self):
        msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": None})
        responses = _run_server([msg, _ping_msg(req_id=2)])
        self.assertEqual(responses[0]["error"]["code"], -32602)
        self.assertEqual(responses[1], {"jsonrpc": "2.0", "id": 2, "result": {}})


class TestMcpInvalidArgumentsType(unittest.TestCase):
    """arguments that is a JSON array (not object) must return -32602."""

    def test_array_arguments_returns_invalid_params_error(self):
        msg = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "inspect_subscriber", "arguments": ["alice"]},
        })
        responses = _run_server([msg])
        self.assertEqual(len(responses), 1)
        err = responses[0].get("error", {})
        self.assertEqual(err.get("code"), -32602)


class TestMcpMissingName(unittest.TestCase):
    """Calling inspect_subscriber with no 'name' key returns isError result."""

    def test_missing_name_returns_is_error_result(self):
        msg = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "inspect_subscriber", "arguments": {}},
        })
        responses = _run_server([msg])
        self.assertEqual(len(responses), 1)
        result = responses[0].get("result", {})
        self.assertTrue(result.get("isError"))

    def test_missing_name_does_not_crash_server(self):
        # After a missing-name call the server should still handle ping
        missing_msg = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "inspect_subscriber", "arguments": {}},
        })
        responses = _run_server([missing_msg, _ping_msg(req_id=2)])
        ids = [r.get("id") for r in responses]
        self.assertIn(2, ids)


class TestMcpUnknownMethod(unittest.TestCase):
    """Unknown method must return -32601."""

    def test_unknown_method_returns_method_not_found(self):
        msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "no/such/method"})
        responses = _run_server([msg])
        self.assertEqual(len(responses), 1)
        err = responses[0].get("error", {})
        self.assertEqual(err.get("code"), -32601)


class TestMcpUnknownTool(unittest.TestCase):
    """Unknown tool name must return -32601."""

    def test_unknown_tool_returns_error(self):
        msg = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "no_such_tool", "arguments": {}},
        })
        responses = _run_server([msg])
        self.assertEqual(len(responses), 1)
        err = responses[0].get("error", {})
        self.assertEqual(err.get("code"), -32601)


class TestMcpNumericName(unittest.TestCase):
    """
    Sending numeric 42 as the value of 'name' via raw stdio (bypassing any
    JSON schema layer) must produce an isError tool result reporting TypeError,
    NOT an internal -32603 server error.  This distinguishes the raw stdio
    path from the recorded OpenCode invocation which supplied the string "42".
    """

    def test_numeric_name_returns_is_error_not_internal_error(self):
        msg = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "inspect_subscriber", "arguments": {"name": 42}},
        })
        responses = _run_server([msg])
        self.assertEqual(len(responses), 1)
        # Must be a result (tool-level isError), not a JSON-RPC error
        self.assertIn("result", responses[0], "Expected tool result, not JSON-RPC error")
        result = responses[0]["result"]
        self.assertTrue(result.get("isError"), "Expected isError=True for numeric name")

    def test_numeric_name_error_text_mentions_type(self):
        msg = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "inspect_subscriber", "arguments": {"name": 42}},
        })
        responses = _run_server([msg])
        self.assertEqual(len(responses), 1)
        result = responses[0].get("result", {})
        content = result.get("content", [])
        text = content[0].get("text", "") if content else ""
        self.assertIn("TypeError", text)


class TestMcpValidUnicodeName(unittest.TestCase):
    """Valid Unicode name must return success with normalized/length/valid fields."""

    def test_unicode_name_returns_valid_true(self):
        msg = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "inspect_subscriber", "arguments": {"name": "Анна"}},
        })
        responses = _run_server([msg])
        self.assertEqual(len(responses), 1)
        result = responses[0].get("result", {})
        self.assertFalse(result.get("isError"), "Expected isError=False for valid Unicode name")

    def test_unicode_name_normalized_field_correct(self):
        msg = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "inspect_subscriber", "arguments": {"name": "  Анна  "}},
        })
        responses = _run_server([msg])
        self.assertEqual(len(responses), 1)
        result = responses[0].get("result", {})
        content = result.get("content", [])
        payload = json.loads(content[0]["text"]) if content else {}
        self.assertEqual(payload.get("normalized"), "Анна")
        self.assertEqual(payload.get("length"), 4)


class TestMcpServerSurvivesInvalidThenPing(unittest.TestCase):
    """Process must remain alive and process a valid ping after invalid input."""

    def test_ping_succeeds_after_null_envelope(self):
        responses = _run_server(["null", _ping_msg(req_id=5)])
        ids = [r.get("id") for r in responses]
        self.assertIn(5, ids)

    def test_ping_succeeds_after_malformed_json(self):
        responses = _run_server(["{bad json", _ping_msg(req_id=6)])
        ids = [r.get("id") for r in responses]
        self.assertIn(6, ids)

    def test_ping_result_is_empty_object(self):
        responses = _run_server([_ping_msg(req_id=7)])
        ping_resp = next((r for r in responses if r.get("id") == 7), None)
        self.assertIsNotNone(ping_resp)
        self.assertEqual(ping_resp.get("result"), {})


if __name__ == "__main__":
    unittest.main()
