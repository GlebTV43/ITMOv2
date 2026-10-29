# AGENTS.md — Practice 04: Subscription Registry

## Before starting any feature work

**Read these files first — do not skip:**

1. `docs/requirements.md` — full behavioural contract for features A and B
2. `docs/style-guide.md` — four concrete coding rules with examples
3. `tests/test_registry.py` — the existing baseline tests show the expected
   test style; new tests must match it

**Then load the subscription-contract skill:**

```python
# Inside an OpenCode session, before writing any code:
skill("subscription-contract")
```

Loading the skill is mandatory, not optional.  It provides the reference cases,
the boundary probe script, and the step-by-step workflow.  Do not begin
implementation without it.

---

## Scope of changes

Changes in this session are **limited to this lab directory**:

```
practices/practice_04/lab/
```

Do not modify files outside this directory — in particular:

- Do not touch `practices/practice_01/`, `practice_02/`, `practice_03/`
- Do not touch the root `README.md` or any root-level files
- Do not modify `../README.md` (the practice README / presentation source)
- Do not modify `../presentation.pdf` or `../presentation.pptx`

---

## Authorisation limits

- **No git commits, pushes, or branch operations** without explicit user request.
- **No worktree creation** without explicit user instruction.
- **No secrets** (API keys, passwords, tokens) may be written to any file.
- **No reasoning traces or internal scratchpads** may be saved to the repository.

---

## Automated runner

The trusted runner is:

```
python scripts/check.py
```

- It discovers and runs all tests under `tests/`
- It syntax-checks production Python files via `compile()`
- It exits non-zero on any failure
- **Do not weaken it** — no `skipTest`, no `@unittest.skip`, no patching

The runner is invoked automatically after completed OpenCode write/edit/apply_patch
tool operations. Shell or external-editor writes require a manual runner call.
Its output is appended to your result as
`[AUTOCHECK PASS]` or `[AUTOCHECK FAIL]`.

---

## MCP tool

An `inspect_subscriber` tool is available via the `subscriber_contract` MCP server.
Use it to pre-validate a candidate name **before** implementing Feature A:

```
subscriber_contract_inspect_subscriber({"name": "  alice  "})
```

It returns the normalised name, its length, and whether it would be valid —
or an error description for invalid input.  This helps you understand the
contract before writing any code.

---

## Workflow per feature

1. Read requirements, style guide, and test example (above)
2. Load the `subscription-contract` skill via the skill tool
3. Call `inspect_subscriber` on boundary cases via MCP
4. Write **failing** behaviour test(s) following the style guide
5. Confirm the runner reports red
6. Implement the minimal code change
7. Confirm the runner reports green
8. Run `scripts/probe.py` and check `results/skill_probe.json`
