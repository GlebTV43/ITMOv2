# Feature B Code Review

**Reviewer:** Separate read-only `explore` subagent (session `ses_ee8c06fc3ffesTSwKzLL2l54nq`)
**Date:** 2026-10-07
**Instruction given:** Read-only inspection of Feature B diff and public behaviour; identify only confirmed problems; do not edit any files.

---

# Code Review: Feature B — `Registry.unsubscribe`

---

## Summary

Three files were reviewed:
- `registry.py` — production implementation
- `tests/test_unsubscribe.py` — Feature B unit tests
- `scripts/probe.py` — extended boundary probe (cases B-1 through B-12)

All files were cross-checked against `docs/requirements.md`, `docs/style-guide.md`, the baseline `tests/test_registry.py`, and each other.

---

## Implementation Review (`registry.py`)

### Validation order in `_normalise`
The shared `_normalise` static method applies checks in exactly the order the requirements specify:
1. `isinstance(name, str)` check → `TypeError` ✓
2. `name.strip()` → ✓
3. Empty-after-strip check → `ValueError` ✓
4. `len(normalised) > 80` check → `ValueError` ✓

Both `subscribe` and `unsubscribe` delegate to `_normalise` before any state access, so validation order is identical for both methods.

### `subscribe` correctness
- Returns `True` on new name, `False` on duplicate. ✓
- Mutates state only after successful normalisation. ✓

### `unsubscribe` correctness
- Returns `True` if present and removed, `False` if absent. ✓
- Uses `discard` (safe, no `KeyError`), preceded by a membership check; the check-then-discard pattern is correct here. ✓
- Returns `False` (not an error) for absent name. ✓
- Normalisation happens before any state inspection, so invalid inputs never reach the membership check. ✓
- No other subscriber is touched. ✓

### `names()`
Returns `sorted(self._subscribers)` — a fresh list each call. Unchanged from baseline. ✓

### stdlib-only
`registry.py` has zero imports. ✓

**No implementation problems found.**

---

## Test Review (`tests/test_unsubscribe.py`)

### Style Rule 1 — Public API only
Every test uses only `subscribe`, `unsubscribe`, and `names`. No `_subscribers`, no private attributes. ✓

### Style Rule 2 — One behaviour per test, descriptive names
Each method tests a single, clearly named behaviour. Where a method has two assertions (`test_unsubscribe_strips_whitespace_before_lookup` checks both return value and resulting state for the *same single action*), both assertions concern the same behaviour — this is explicitly permitted by the style guide. ✓

The class groupings are logical and mirror the structure of `test_registry.py`. ✓

### Style Rule 3 — No skips or weakening
No `@unittest.skip`, `skipTest()`, or conditional skips anywhere in the file. ✓

### Style Rule 4 — stdlib only
Imports are `sys`, `os`, `unittest`, and `registry` — all stdlib or local. ✓

### Coverage assessment against requirements
| Requirement | Test present |
|---|---|
| TypeError for non-str (int) | `test_unsubscribe_nonstring_raises_type_error` ✓ |
| TypeError for None | `test_unsubscribe_none_raises_type_error` ✓ |
| ValueError for empty string | `test_unsubscribe_empty_string_raises_value_error` ✓ |
| ValueError for whitespace-only | `test_unsubscribe_whitespace_only_raises_value_error` ✓ |
| Whitespace stripped before lookup | `test_unsubscribe_strips_whitespace_before_lookup` ✓ |
| Exactly 80 chars accepted | `test_unsubscribe_exactly_80_unicode_chars_returns_true` ✓ |
| 81 chars raises ValueError | `test_unsubscribe_81_unicode_chars_raises_value_error` ✓ |
| Returns True when name present | `test_unsubscribe_existing_name_returns_true` ✓ |
| Removes name from registry | `test_unsubscribe_removes_name_from_registry` ✓ |
| Returns False when absent | `test_unsubscribe_absent_name_returns_false` ✓ |
| Idempotent (repeated removal) | `test_repeated_unsubscribe_is_idempotent` ✓ |
| Does not affect other names | `test_unsubscribe_one_name_preserves_another` ✓ |
| No mutation on invalid input | `test_invalid_unsubscribe_does_not_change_state` ✓ |
| Resubscribe after removal works | `test_resubscribe_after_removal_returns_true` + `test_resubscribed_name_appears_in_names` ✓ |

All requirements-mandated behaviours are covered. ✓

**No test problems found.**

---

## Probe Review (`scripts/probe.py`)

### Feature A cases preserved
Cases 1–9 (empty string, whitespace-only, non-str int, None, 80 chars, 81 chars, whitespace normalisation, Ann dedup, no-mutation-on-rejection) are unchanged from what would have existed pre-Feature-B. ✓

### Feature B cases (B-1 through B-12)
| Case ID | Description | Correct |
|---|---|---|
| `b_unsubscribe_present` (B-1) | Returns True; registry empty | ✓ |
| `b_unsubscribe_absent` (B-2) | Returns False; no error | ✓ |
| `b_repeated_unsubscribe` (B-3) | Second removal returns False | ✓ |
| `b_padded_name` (B-4) | Padded name normalises before lookup | ✓ |
| `b_resubscribe_after_removal` (B-5) | Resubscribe returns True | ✓ |
| `b_preserves_other_subscribers` (B-6) | Removes only target name | ✓ |
| `b_exactly_80_unicode` (B-7) | 80 Unicode chars accepted | ✓ |
| `b_exactly_81_unicode` (B-8) | 81 Unicode chars → ValueError | ✓ |
| `b_nonstring_raises_type_error` (B-9) | int → TypeError | ✓ |
| `b_empty_string` (B-10) | `""` → ValueError | ✓ |
| `b_whitespace_only` (B-11) | `"   "` → ValueError | ✓ |
| `b_no_mutation_on_invalid` (B-12) | State unchanged after invalid calls | ✓ |

All 12 Feature B cases are substantive, correctly specified, and the assertions accurately reflect the requirements. Each case creates a fresh `Registry` instance, so there is no cross-case state contamination. ✓

The probe's summary block and exit-code logic are unchanged from the baseline structure. ✓

**No probe problems found.**

---

## Confirmed Problems

**None.** No confirmed problems were found in any of the three reviewed files.

---

## Verdict

**PASS — the Feature B implementation is correct and complete.**

Every requirement is implemented exactly as specified. The tests conform fully to the style guide (public API only, one behaviour per method, no skips, stdlib only) and cover every required behaviour. The probe extension is substantive and preserves all original Feature A cases. There are no issues to report.

---

## Decision by implementing agent

The reviewer found no confirmed problems. No corrections were required. The implementation is accepted as-is.
