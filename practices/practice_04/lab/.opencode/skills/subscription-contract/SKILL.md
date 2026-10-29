---
name: subscription-contract
description: >
  Guides an agent through implementing and verifying the validated subscribe
  (Feature A) and unsubscribe (Feature B) contract for the Subscription
  Registry.  Provides reference boundary cases, a boundary probe script, and
  a step-by-step red/green workflow.  Load this skill before any feature work.
---

# Subscription-Contract Skill

Run the commands below from the lab root. `docs/`, `scripts/`, and `results/`
refer to that root; `references/cases.json` is relative to this skill directory.
The executable helper is [scripts/probe.py](../../../scripts/probe.py).

## Purpose

This skill operationalises the requirements in `docs/requirements.md` into
concrete steps an agent can follow without re-reading the spec from scratch
each time.

---

## Step-by-step procedure

### 1 — Read the contract and reference cases

Read `docs/requirements.md` fully.
Then read `references/cases.json` in this skill directory.
These are the authoritative boundary cases; your tests and implementation must
agree with them exactly.

### 2 — Pre-validate boundary inputs with the MCP tool

Before writing any code call `inspect_subscriber` from the `subscriber_contract`
MCP server on at least these inputs:

| Input | Expected outcome |
|---|---|
| `""` | invalid — empty after normalisation |
| `"  "` | invalid — empty after normalisation |
| `"alice"` | valid, length 5 |
| `"  alice  "` | valid, normalises to `"alice"`, length 5 |
| `"a" * 80` | valid, length 80 |
| `"a" * 81` | invalid — exceeds 80 chars |
| `42` (integer) | invalid — not a str |

### 3 — Write a **failing** behaviour test

Add a new test method to `tests/test_registry.py` (or a new file under
`tests/`) that calls the public API and asserts the expected behaviour.
Do **not** peek at `registry._subscribers`.

Run the trusted runner and confirm it reports red:

```
python scripts/check.py
```

### 4 — Implement the minimal fix

Edit `registry.py` to make exactly the failing test pass.
Do not add any code beyond what is needed.

### 5 — Confirm green

Run `python scripts/check.py` again.  All tests must pass.

### 6 — Run the probe and save results

```
python scripts/probe.py
```

The probe writes `results/skill_probe.json`.
Inspect it.  Until Feature A is fully implemented, several cases will show
`"status": "FAIL"` — this is expected and honest.

---

## Notes

- The probe is **expected to fail** at baseline.  Do not modify the probe to
  make it appear to pass.
- All Feature A validation tests must wait for the A implementation turn.
  Do not add them during baseline setup.
- Feature B tests must wait for the B implementation turn.
- Follow `docs/style-guide.md` — one behaviour per test (multiple assertions
  about the *same* behaviour are fine), public API only, no `@unittest.skip`,
  stdlib only.
- Never delete or weaken a failing test to conceal a regression; fix production
  code instead.
