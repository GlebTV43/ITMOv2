"""
Local stdio MCP server — Practice 04: Subscription Registry.

Implements JSON-RPC 2.0 over stdin/stdout (newline-delimited).
Supports protocol versions: 2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25.

Tools exposed:
  inspect_subscriber(name) — validate and normalise a candidate subscriber name
                             using the Feature A contract, before the registry
                             itself implements validation.

Protocol messages go to stdout only.
All debug/error output goes to stderr.
No external packages; stdlib only.
"""

import sys
import json
import os

# Allow importing mcp.contract when run as a script
_DIR = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.dirname(_DIR)
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from mcp.contract import normalize_name  # noqa: E402

SUPPORTED_VERSIONS = {
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
}
SERVER_VERSION = "2024-11-05"

INSPECT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "description": (
                "Candidate subscriber name to validate and normalise. "
                "May be any JSON value; non-strings return a TypeError result."
            ),
            # No type constraint here — we intentionally accept any value
            # so the tool can demonstrate TypeError behaviour.
        }
    },
    "required": ["name"],
}

TOOLS = [
    {
        "name": "inspect_subscriber",
        "description": (
            "Validate and normalise a candidate subscriber name using the "
            "Feature A contract: must be str, stripped, non-empty, ≤80 chars. "
            "Returns normalised name, length, and valid=true on success. "
            "Returns isError=true with a helpful message on invalid input."
        ),
        "inputSchema": INSPECT_SCHEMA,
    }
]


def send(obj: dict) -> None:
    """Write a JSON object to stdout followed by a newline."""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def error_response(req_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def handle_initialize(req_id, params: dict) -> dict:
    client_version = params.get("protocolVersion", SERVER_VERSION)
    # Negotiate: use requested version if supported, else fall back
    negotiated = client_version if client_version in SUPPORTED_VERSIONS else SERVER_VERSION
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": negotiated,
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "subscriber_contract",
                "version": "1.0.0",
            },
        },
    }


def handle_tools_list(req_id) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"tools": TOOLS},
    }


def handle_tools_call(req_id, params: dict) -> dict:
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if tool_name != "inspect_subscriber":
        return error_response(req_id, -32601, f"Unknown tool: {tool_name!r}")

    name = arguments.get("name")
    result = normalize_name(name)

    if result.get("valid"):
        content_text = json.dumps(
            {
                "normalized": result["normalized"],
                "length": result["length"],
                "valid": True,
            },
            ensure_ascii=False,
        )
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": content_text}],
                "isError": False,
            },
        }
    else:
        error_text = (
            f"{result['error_type']}: {result['error_message']}"
        )
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": error_text}],
                "isError": True,
            },
        }


def handle_ping(req_id) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": {}}


def dispatch(msg: dict):
    """Dispatch one parsed JSON-RPC message. Returns response dict or None."""
    method = msg.get("method", "")
    req_id = msg.get("id")  # None for notifications

    if msg.get("jsonrpc") != "2.0" or not isinstance(method, str) or not method:
        return error_response(req_id, -32600, "Invalid JSON-RPC request")

    # notifications (no id) — do not send a response
    if "id" not in msg:
        # Handle 'notifications/initialized' silently
        return None

    # params must be a dict (object) when present
    raw_params = msg.get("params")
    if "params" in msg and not isinstance(raw_params, dict):
        return error_response(
            req_id, -32602,
            "Invalid params: 'params' must be a JSON object when present"
        )

    if method == "initialize":
        return handle_initialize(req_id, msg.get("params", {}))
    elif method == "tools/list":
        return handle_tools_list(req_id)
    elif method == "tools/call":
        params = msg.get("params", {})
        # arguments must be a dict when present
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return error_response(
                req_id, -32602,
                "Invalid params: 'arguments' must be a JSON object"
            )
        return handle_tools_call(req_id, params)
    elif method == "ping":
        return handle_ping(req_id)
    else:
        return error_response(req_id, -32601, f"Method not found: {method!r}")


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError as e:
            send({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            })
            continue

        # Structural validation: msg must be a dict (JSON object)
        if not isinstance(msg, dict):
            send({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: message must be a JSON object",
                },
            })
            continue

        try:
            response = dispatch(msg)
        except Exception as e:
            print(f"[mcp/server.py] internal error: {e}", file=sys.stderr)
            req_id = msg.get("id")
            if req_id is not None:
                send(error_response(req_id, -32603, f"Internal error: {e}"))
            continue

        if response is not None:
            send(response)


if __name__ == "__main__":
    main()
