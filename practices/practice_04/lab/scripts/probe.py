"""
Boundary probe for the subscription-contract skill.

Calls the public Registry API against reference boundary cases and writes
results to results/skill_probe.json.

Expected to report FAIL cases until Feature A is implemented — this is
honest; do not modify to suppress failures.

Usage:
    python scripts/probe.py
"""
import sys
import os
import json

# Locate lab root relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAB_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, LAB_DIR)

from registry import Registry  # noqa: E402

RESULTS_DIR = os.path.join(LAB_DIR, "results")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "skill_probe.json")

os.makedirs(RESULTS_DIR, exist_ok=True)


def run_case(case_id, description, fn):
    """Run fn(), return a result dict with status PASS/FAIL."""
    try:
        passed, detail = fn()
        return {
            "id": case_id,
            "description": description,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    except Exception as exc:
        return {
            "id": case_id,
            "description": description,
            "status": "FAIL",
            "detail": f"Unexpected exception: {type(exc).__name__}: {exc}",
        }


cases = []

# Case 1: empty string → ValueError
def case_empty_string():
    reg = Registry()
    try:
        reg.subscribe("")
        return False, "Expected ValueError, got no exception"
    except ValueError:
        return True, "Correctly raised ValueError for empty string"
    except Exception as e:
        return False, f"Expected ValueError, got {type(e).__name__}: {e}"

cases.append(run_case("empty_string", "Empty string raises ValueError", case_empty_string))

# Case 2: whitespace-only → ValueError (strips to empty)
def case_whitespace_only():
    reg = Registry()
    try:
        reg.subscribe("   ")
        return False, "Expected ValueError, got no exception"
    except ValueError:
        return True, "Correctly raised ValueError for whitespace-only string"
    except Exception as e:
        return False, f"Expected ValueError, got {type(e).__name__}: {e}"

cases.append(run_case("whitespace_only", "Whitespace-only string raises ValueError", case_whitespace_only))

# Case 3: non-string (int) → TypeError
def case_nonstring_int():
    reg = Registry()
    try:
        reg.subscribe(42)
        return False, "Expected TypeError, got no exception"
    except TypeError:
        return True, "Correctly raised TypeError for integer input"
    except Exception as e:
        return False, f"Expected TypeError, got {type(e).__name__}: {e}"

cases.append(run_case("nonstring_int", "Integer input raises TypeError", case_nonstring_int))

# Case 4: None → TypeError
def case_nonstring_none():
    reg = Registry()
    try:
        reg.subscribe(None)
        return False, "Expected TypeError, got no exception"
    except TypeError:
        return True, "Correctly raised TypeError for None input"
    except Exception as e:
        return False, f"Expected TypeError, got {type(e).__name__}: {e}"

cases.append(run_case("nonstring_none", "None input raises TypeError", case_nonstring_none))

# Case 5: exactly 80 chars → valid
def case_exactly_80_chars():
    reg = Registry()
    name = "a" * 80
    result = reg.subscribe(name)
    if result is True:
        return True, f"Correctly accepted 80-char name, returned True"
    return False, f"Expected True, got {result!r}"

cases.append(run_case("exactly_80_chars", "80-character name is valid", case_exactly_80_chars))

# Case 6: exactly 81 chars → ValueError
def case_exactly_81_chars():
    reg = Registry()
    name = "a" * 81
    try:
        reg.subscribe(name)
        return False, "Expected ValueError for 81-char name, got no exception"
    except ValueError:
        return True, "Correctly raised ValueError for 81-char name"
    except Exception as e:
        return False, f"Expected ValueError, got {type(e).__name__}: {e}"

cases.append(run_case("exactly_81_chars", "81-character name raises ValueError", case_exactly_81_chars))

# Case 7: leading/trailing whitespace normalisation
def case_whitespace_normalisation():
    reg = Registry()
    result = reg.subscribe("  alice  ")
    if result is not True:
        return False, f"subscribe('  alice  ') expected True (new), got {result!r}"
    snapshot = reg.names()
    if snapshot != ["alice"]:
        return False, f"names() expected ['alice'] after normalisation, got {snapshot!r}"
    return True, "Normalised '  alice  ' → 'alice', stored correctly"

cases.append(run_case("whitespace_normalisation", "Whitespace stripped before storage", case_whitespace_normalisation))

# Case 8: Ann normalisation + deduplication
def case_ann_normalisation_dedup():
    reg = Registry()
    r1 = reg.subscribe("  Ann  ")
    r2 = reg.subscribe("Ann")
    if r1 is not True:
        return False, f"First subscribe('  Ann  ') expected True, got {r1!r}"
    if r2 is not False:
        return False, f"Second subscribe('Ann') expected False (duplicate), got {r2!r}"
    return True, "Ann normalisation and deduplication correct"

cases.append(run_case("ann_normalisation_dedup", "Normalised duplicates detected correctly", case_ann_normalisation_dedup))

# Case 9: no state mutation on rejected input
def case_no_mutation_on_rejection():
    reg = Registry()
    reg.subscribe("existing")
    before = reg.names()
    try:
        reg.subscribe("")
    except (TypeError, ValueError):
        pass
    try:
        reg.subscribe("   ")
    except (TypeError, ValueError):
        pass
    try:
        reg.subscribe(42)
    except (TypeError, ValueError):
        pass
    after = reg.names()
    if before == after:
        return True, f"State unchanged after rejected inputs: {after!r}"
    return False, f"State mutated! before={before!r}, after={after!r}"

cases.append(run_case("no_mutation_on_rejection", "Rejected inputs do not mutate state", case_no_mutation_on_rejection))

# ── Feature B: unsubscribe ──────────────────────────────────────────────────

# B-1: unsubscribe a present name → True; name gone from registry
def case_b_unsubscribe_present():
    reg = Registry()
    reg.subscribe("alice")
    result = reg.unsubscribe("alice")
    if result is not True:
        return False, f"Expected True for existing name, got {result!r}"
    if reg.names() != []:
        return False, f"Expected empty registry after removal, got {reg.names()!r}"
    return True, "Unsubscribed present name, returned True, registry is empty"

cases.append(run_case("b_unsubscribe_present", "Unsubscribe existing name returns True", case_b_unsubscribe_present))

# B-2: unsubscribe absent name → False; no mutation
def case_b_unsubscribe_absent():
    reg = Registry()
    result = reg.unsubscribe("alice")
    if result is not False:
        return False, f"Expected False for absent name, got {result!r}"
    return True, "Unsubscribing absent name correctly returned False"

cases.append(run_case("b_unsubscribe_absent", "Unsubscribe absent name returns False", case_b_unsubscribe_absent))

# B-3: repeated unsubscribe is idempotent
def case_b_repeated_unsubscribe():
    reg = Registry()
    reg.subscribe("alice")
    reg.unsubscribe("alice")
    result = reg.unsubscribe("alice")
    if result is not False:
        return False, f"Second unsubscribe expected False, got {result!r}"
    return True, "Repeated unsubscribe is idempotent, returned False"

cases.append(run_case("b_repeated_unsubscribe", "Repeated unsubscribe is idempotent", case_b_repeated_unsubscribe))

# B-4: padded name normalises before lookup
def case_b_padded_name():
    reg = Registry()
    reg.subscribe("alice")
    result = reg.unsubscribe("  alice  ")
    if result is not True:
        return False, f"Expected True for padded name, got {result!r}"
    if reg.names() != []:
        return False, f"Expected empty registry, got {reg.names()!r}"
    return True, "Padded '  alice  ' correctly removes 'alice'"

cases.append(run_case("b_padded_name", "Unsubscribe with surrounding whitespace normalises correctly", case_b_padded_name))

# B-5: resubscribe after removal is accepted as new
def case_b_resubscribe_after_removal():
    reg = Registry()
    reg.subscribe("alice")
    reg.unsubscribe("alice")
    result = reg.subscribe("alice")
    if result is not True:
        return False, f"Resubscribe after removal expected True, got {result!r}"
    return True, "Resubscribe after removal correctly returns True"

cases.append(run_case("b_resubscribe_after_removal", "Resubscribe after removal is treated as new", case_b_resubscribe_after_removal))

# B-6: unsubscribe one name does not affect another
def case_b_preserves_other_subscribers():
    reg = Registry()
    reg.subscribe("alice")
    reg.subscribe("bob")
    reg.unsubscribe("alice")
    remaining = reg.names()
    if remaining != ["bob"]:
        return False, f"Expected ['bob'] after removing 'alice', got {remaining!r}"
    return True, "Removing 'alice' preserved 'bob'"

cases.append(run_case("b_preserves_other_subscribers", "Unsubscribe does not affect other subscribers", case_b_preserves_other_subscribers))

# B-7: 80 Unicode chars accepted by unsubscribe
def case_b_exactly_80_unicode():
    reg = Registry()
    name = "ä" * 80
    reg.subscribe(name)
    result = reg.unsubscribe(name)
    if result is not True:
        return False, f"Expected True for 80-char Unicode name, got {result!r}"
    return True, "80-char Unicode name correctly accepted by unsubscribe"

cases.append(run_case("b_exactly_80_unicode", "80 Unicode characters accepted by unsubscribe", case_b_exactly_80_unicode))

# B-8: 81 Unicode chars rejected by unsubscribe
def case_b_exactly_81_unicode():
    reg = Registry()
    try:
        reg.unsubscribe("ä" * 81)
        return False, "Expected ValueError for 81-char Unicode name, got no exception"
    except ValueError:
        return True, "Correctly raised ValueError for 81-char Unicode name"
    except Exception as e:
        return False, f"Expected ValueError, got {type(e).__name__}: {e}"

cases.append(run_case("b_exactly_81_unicode", "81 Unicode characters rejected by unsubscribe", case_b_exactly_81_unicode))

# B-9: non-string raises TypeError
def case_b_nonstring_raises_type_error():
    reg = Registry()
    try:
        reg.unsubscribe(42)
        return False, "Expected TypeError for int input, got no exception"
    except TypeError:
        return True, "Correctly raised TypeError for integer input"
    except Exception as e:
        return False, f"Expected TypeError, got {type(e).__name__}: {e}"

cases.append(run_case("b_nonstring_raises_type_error", "Non-string input raises TypeError", case_b_nonstring_raises_type_error))

# B-10: empty string raises ValueError
def case_b_empty_string():
    reg = Registry()
    try:
        reg.unsubscribe("")
        return False, "Expected ValueError for empty string, got no exception"
    except ValueError:
        return True, "Correctly raised ValueError for empty string"
    except Exception as e:
        return False, f"Expected ValueError, got {type(e).__name__}: {e}"

cases.append(run_case("b_empty_string", "Empty string raises ValueError in unsubscribe", case_b_empty_string))

# B-11: whitespace-only raises ValueError
def case_b_whitespace_only():
    reg = Registry()
    try:
        reg.unsubscribe("   ")
        return False, "Expected ValueError for whitespace-only, got no exception"
    except ValueError:
        return True, "Correctly raised ValueError for whitespace-only input"
    except Exception as e:
        return False, f"Expected ValueError, got {type(e).__name__}: {e}"

cases.append(run_case("b_whitespace_only", "Whitespace-only raises ValueError in unsubscribe", case_b_whitespace_only))

# B-12: invalid input does not mutate state
def case_b_no_mutation_on_invalid():
    reg = Registry()
    reg.subscribe("alice")
    before = reg.names()
    try:
        reg.unsubscribe(42)
    except (TypeError, ValueError):
        pass
    try:
        reg.unsubscribe("")
    except (TypeError, ValueError):
        pass
    try:
        reg.unsubscribe("   ")
    except (TypeError, ValueError):
        pass
    after = reg.names()
    if before == after:
        return True, f"State unchanged after invalid unsubscribe calls: {after!r}"
    return False, f"State mutated! before={before!r}, after={after!r}"

cases.append(run_case("b_no_mutation_on_invalid", "Invalid unsubscribe inputs do not mutate state", case_b_no_mutation_on_invalid))

# Summary
total = len(cases)
passed = sum(1 for c in cases if c["status"] == "PASS")
failed = total - passed

output = {
    "summary": {
        "total": total,
        "passed": passed,
        "failed": failed,
        "note": (
            "FAIL cases are expected at baseline — Feature A not yet implemented. "
            "Do not modify probe to suppress failures."
        ) if failed > 0 else "All cases passed.",
    },
    "cases": cases,
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(json.dumps(output, indent=2, ensure_ascii=False))

if failed > 0:
    print(f"\nProbe result: {passed}/{total} passed — FAIL (expected at baseline)")
    sys.exit(1)
else:
    print(f"\nProbe result: {passed}/{total} passed — PASS")
    sys.exit(0)
