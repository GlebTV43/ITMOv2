# Style Guide — Practice 04

Four concrete rules for all code in this lab.

---

## Rule 1 — Test public behaviour, not implementation details

Tests must call only the **public API** (`subscribe`, `unsubscribe`, `names`).
They must never inspect `_subscribers`, reach into private attributes, or
monkey-patch internals.

**Good example:**

```python
reg = Registry()
reg.subscribe("alice")
assert reg.names() == ["alice"]
```

**Bad example:**

```python
reg = Registry()
reg._subscribers.add("alice")   # touching internals — forbidden
assert "alice" in reg._subscribers
```

---

## Rule 2 — One behaviour per test method; name the test for what it checks

Each `unittest.TestCase` method tests exactly one behaviour.
The method name must read as a plain-English sentence describing the expectation.
Multiple assertions about the *same* behaviour (e.g. return value and resulting
state for a single action) are fine; mixing *different* behaviours in one method
is not.

**Good example:**

```python
def test_subscribe_new_name_returns_true(self):
    assert Registry().subscribe("alice") is True

def test_subscribe_strips_whitespace_and_stores_normalised_name(self):
    reg = Registry()
    reg.subscribe("  alice  ")
    assert reg.names() == ["alice"]  # return value + state for same action
```

**Bad example:**

```python
def test_stuff(self):
    reg = Registry()
    assert reg.subscribe("alice")          # behaviour: new name
    assert reg.subscribe("alice") is False # behaviour: duplicate (different!)
    assert reg.names() == ["alice"]        # behaviour: snapshot
```

---

## Rule 3 — Never weaken the runner or skip tests conditionally

Do not use `@unittest.skip`, `@pytest.mark.skip`, `skipTest()`, or any other
mechanism that silences a test to make the suite pass.
The runner (`scripts/check.py`) must always exit non-zero if any test fails.

**Good example:** keep failing behaviour tests in the file and fix production
code until they turn green — never delete or weaken a test to conceal a
regression.

**Bad example:**

```python
@unittest.skip("not implemented yet")
def test_empty_name_raises(self):
    ...
```

---

## Rule 4 — stdlib only; no external packages

All production code and all test helpers must use Python's standard library
exclusively.  Do not `import pytest`, `import requests`, `import pydantic`, or
any other third-party package.  The canonical runner is:

```
python scripts/check.py
```

Running `pytest` directly is optional for local convenience but is **not**
the authoritative check.  The suite must pass under `python scripts/check.py`.
