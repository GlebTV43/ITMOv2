"""
Pure contract normalizer for the MCP module.

This is an independent implementation of the Feature A contract — it does NOT
call registry.py.  It exists so the MCP server can inspect candidate names
before Feature A is implemented in the registry itself.
"""


def normalize_name(name) -> dict:
    """
    Apply the Feature A contract to *name*.

    Returns a dict with:
        valid (bool)        — True if name passes all checks
        normalized (str)    — the stripped name (only present when input is str)
        length (int)        — Unicode character count of normalized name
        error_type (str)    — 'TypeError' or 'ValueError' when not valid
        error_message (str) — human-readable reason when not valid

    Never raises; all outcomes are returned as data.
    """
    if not isinstance(name, str):
        return {
            "valid": False,
            "error_type": "TypeError",
            "error_message": (
                f"name must be str, got {type(name).__name__!r}"
            ),
        }

    normalized = name.strip()

    if normalized == "":
        return {
            "valid": False,
            "normalized": normalized,
            "length": 0,
            "error_type": "ValueError",
            "error_message": "name is empty after stripping whitespace",
        }

    length = len(normalized)

    if length > 80:
        return {
            "valid": False,
            "normalized": normalized,
            "length": length,
            "error_type": "ValueError",
            "error_message": (
                f"name has {length} Unicode characters after normalisation; "
                f"maximum is 80"
            ),
        }

    return {
        "valid": True,
        "normalized": normalized,
        "length": length,
    }
