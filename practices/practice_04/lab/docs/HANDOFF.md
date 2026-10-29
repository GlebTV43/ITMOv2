# HANDOFF.md — Practice 04 Lab: Subscription Registry

_For a fresh OpenCode session picking up this worktree._

---

## State at handoff

| Feature | Status |
|---|---|
| **Feature A** — `Registry.subscribe` with validation | ✅ Complete, all tests green |
| **Feature B** — `Registry.unsubscribe` with validation | ✅ Complete, all tests green |
| Trusted runner | ✅ 56 tests, all pass |
| Boundary probe | ✅ 21/21 PASS (9 A-cases + 12 B-cases) |
| Read-only review | ✅ No confirmed problems (see `results/feature_b_review.md`) |

---

## Source files

### Production code
- **`registry.py`** — The subscription registry implementation.
  - `Registry._normalise(name)` — private static method, shared validation for both operations
  - `Registry.subscribe(name) → bool` — Feature A
  - `Registry.unsubscribe(name) → bool` — Feature B
  - `Registry.names() → list[str]` — sorted snapshot

### Tests
- `tests/test_registry.py` — Baseline tests (subscribe new, duplicate, names snapshot); 4 tests
- `tests/test_feature_a.py` — Feature A validation tests (type rejection, empty/whitespace, length boundary, normalisation, no-mutation); 17 tests
- `tests/test_mcp.py` — MCP server protocol tests; 19 tests
- `tests/test_unsubscribe.py` — Feature B tests (all B behaviours); 16 tests

### Scripts
- `scripts/check.py` — Trusted runner: syntax-checks all `.py` files, discovers and runs all `test_*.py` under `tests/`; exits non-zero on any failure. **Do not weaken it.**
- `scripts/probe.py` — Boundary probe; writes `results/skill_probe.json`. 9 Feature A cases + 12 Feature B cases.

### MCP server
- `mcp/server.py` + `mcp/contract.py` — Minimal stdio MCP server exposing `inspect_subscriber` tool (validates a candidate name per Feature A contract). Tested by `tests/test_mcp.py`.

---

## Requirements summary

From `docs/requirements.md`:

### Validation contract (identical for subscribe and unsubscribe — same order)
1. `name` must be `str` → `TypeError` if not
2. `name.strip()` — normalise
3. Normalised name must not be empty → `ValueError` if empty
4. Normalised name must be ≤ 80 Unicode characters → `ValueError` if > 80
5. No state mutation when an exception is raised

### Return values
| Operation | Name present | Name absent |
|---|---|---|
| `subscribe` | `False` (duplicate) | `True` (newly added) |
| `unsubscribe` | `True` (removed) | `False` (idempotent, not an error) |

---

## Style guide (4 rules — see `docs/style-guide.md`)

1. Tests call only public API (`subscribe`, `unsubscribe`, `names`) — no `_subscribers`, no internals
2. One behaviour per test method; name describes the expectation; multiple assertions about the *same* behaviour are fine
3. Never use `@unittest.skip`, `skipTest()`, or weaken the runner
4. stdlib only — no `pytest`, no external packages

---

## Key commands

```bash
# Run all tests (trusted runner — authoritative)
python scripts/check.py

# Run boundary probe (writes results/skill_probe.json)
python scripts/probe.py

# Load the subscription-contract skill (in an OpenCode session)
skill("subscription-contract")

# Call MCP inspect_subscriber tool (pre-validate a candidate name)
# via MCP server (stdio) or via the built-in MCP tool:
#   subscriber_contract_inspect_subscriber(name="  alice  ")
```

---

## Results files

| File | Contents |
|---|---|
| `results/skill_probe_baseline.json` | Probe at baseline (before any features) |
| `results/skill_probe_a.json` | Probe after Feature A only (9 cases, 9 PASS) |
| `results/skill_probe.json` | Current probe result (21 cases, 21 PASS) |
| `results/feature_b_checks.txt` | Full output of `python scripts/check.py` after Feature B |
| `results/feature_b_review.md` | Read-only review by separate `explore` subagent |

---

## Known limitations

- **In-memory only** — The registry is a plain Python `set`; no persistence, no database.
- **Cloud work agent** — OpenCode runs locally on Windows; its work agent uses the VseLLM cloud API. Code and review were produced by agents, with coordinator corrections.
- **Own minimal stdio MCP** — The `mcp/server.py` is a from-scratch JSON-RPC stdio server; it implements only `initialize`/`tools/list`/`tools/call`/`ping`. It is not a full MCP SDK server.
- **Autocheck hook fires only on `write`/`edit`/`apply_patch`** — The trusted runner is triggered automatically after every file write or edit. Shell and external-editor writes do not trigger the hook; run `python scripts/check.py` for those writes. Manual checks do not prove hook execution.
- **No git operations performed** — Commits, pushes, and branch operations are the coordinator's responsibility. This session made no git changes.

---

## Feature B review decision

The read-only review (by a separate `explore` subagent, session `ses_ee8c06fc3ffesTSwKzLL2l54nq`) found **no confirmed problems**. Verdict: PASS. No corrections were needed.

---

## What a fresh session should NOT do

- Do not touch files outside `practices/practice_04/lab/`
- Do not modify `docs/requirements.md`, `scripts/check.py`, or any existing passing tests
- Do not commit or push without explicit user instruction
- Do not add `@unittest.skip` or weaken any test
- Do not import third-party packages in production or test code
