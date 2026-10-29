# Subscription Registry — Requirements

## Overview

A pure in-memory subscription registry implemented with Python stdlib only.
No HTTP, no database, no external dependencies.

## Baseline (no validation)

- `Registry.subscribe(name)` adds `name` to an internal `set` and returns
  `True` if newly added, `False` if it was already present.
- `Registry.names()` returns a **sorted list** snapshot of all current subscribers.
  The snapshot is read-only (a plain `list`); mutating it does not affect the registry.

## Feature A — Validated subscribe

### Input contract (applied in this order, reject before mutating state)

1. `name` must be an instance of `str`; otherwise raise `TypeError`.
2. Strip surrounding whitespace from the normalised name (`str.strip()`).
3. Reject a normalised name that is empty (`""`); raise `ValueError`.
4. Reject a normalised name longer than **80 Unicode characters**; raise `ValueError`.
   - A name of exactly 80 characters is **valid**.
   - A name of 81 characters is **invalid**.

### Return values (after normalisation)

- `True`  — normalised name was **not** previously in the registry (newly added).
- `False` — normalised name was **already** present (duplicate, idempotent).

### Guarantees

- State is never mutated when an exception is raised.
- Normalisation is deterministic: leading/trailing whitespace is stripped before
  storage and before duplicate checking.

## Feature B — Validated unsubscribe

### Input contract

Identical to Feature A's contract — same `TypeError` / `ValueError` rules,
same normalisation, same rejection-before-mutation guarantee.

### Return values

- `True`  — normalised name was present and has been removed.
- `False` — normalised name was **absent** (idempotent; not an error).

### Guarantees

- Removing a name never affects any other name.
- All Feature A cases (subscribe behaviour, validation, snapshot) are preserved.
- Calling `unsubscribe` with an absent name is safe and returns `False`.
