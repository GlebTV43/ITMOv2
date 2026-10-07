"""Feature B tests — validated unsubscribe."""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from registry import Registry


class TestUnsubscribePresent(unittest.TestCase):
    def test_unsubscribe_existing_name_returns_true(self):
        reg = Registry()
        reg.subscribe("alice")
        self.assertIs(reg.unsubscribe("alice"), True)

    def test_unsubscribe_removes_name_from_registry(self):
        reg = Registry()
        reg.subscribe("alice")
        reg.unsubscribe("alice")
        self.assertEqual(reg.names(), [])


class TestUnsubscribeAbsent(unittest.TestCase):
    def test_unsubscribe_absent_name_returns_false(self):
        reg = Registry()
        self.assertIs(reg.unsubscribe("alice"), False)

    def test_repeated_unsubscribe_is_idempotent(self):
        reg = Registry()
        reg.subscribe("alice")
        reg.unsubscribe("alice")
        self.assertIs(reg.unsubscribe("alice"), False)


class TestUnsubscribeWhitespaceNormalisation(unittest.TestCase):
    def test_unsubscribe_strips_whitespace_before_lookup(self):
        reg = Registry()
        reg.subscribe("alice")
        self.assertIs(reg.unsubscribe("  alice  "), True)

    def test_unsubscribe_padded_name_leaves_registry_empty(self):
        reg = Registry()
        reg.subscribe("alice")
        reg.unsubscribe("  alice  ")
        self.assertEqual(reg.names(), [])


class TestUnsubscribeDoesNotAffectOthers(unittest.TestCase):
    def test_unsubscribe_one_name_preserves_another(self):
        reg = Registry()
        reg.subscribe("alice")
        reg.subscribe("bob")
        reg.unsubscribe("alice")
        self.assertEqual(reg.names(), ["bob"])


class TestResubscribeAfterRemoval(unittest.TestCase):
    def test_resubscribe_after_removal_returns_true(self):
        reg = Registry()
        reg.subscribe("alice")
        reg.unsubscribe("alice")
        self.assertIs(reg.subscribe("alice"), True)

    def test_resubscribed_name_appears_in_names(self):
        reg = Registry()
        reg.subscribe("alice")
        reg.unsubscribe("alice")
        reg.subscribe("alice")
        self.assertEqual(reg.names(), ["alice"])


class TestUnsubscribeBoundaryLengths(unittest.TestCase):
    def test_unsubscribe_exactly_80_unicode_chars_returns_true(self):
        reg = Registry()
        name = "ä" * 80
        reg.subscribe(name)
        self.assertIs(reg.unsubscribe(name), True)

    def test_unsubscribe_81_unicode_chars_raises_value_error(self):
        reg = Registry()
        with self.assertRaises(ValueError):
            reg.unsubscribe("ä" * 81)


class TestUnsubscribeInvalidInputs(unittest.TestCase):
    def test_unsubscribe_nonstring_raises_type_error(self):
        reg = Registry()
        with self.assertRaises(TypeError):
            reg.unsubscribe(42)

    def test_unsubscribe_none_raises_type_error(self):
        reg = Registry()
        with self.assertRaises(TypeError):
            reg.unsubscribe(None)

    def test_unsubscribe_empty_string_raises_value_error(self):
        reg = Registry()
        with self.assertRaises(ValueError):
            reg.unsubscribe("")

    def test_unsubscribe_whitespace_only_raises_value_error(self):
        reg = Registry()
        with self.assertRaises(ValueError):
            reg.unsubscribe("   ")


class TestUnsubscribeInvalidInputDoesNotMutate(unittest.TestCase):
    def test_invalid_unsubscribe_does_not_change_state(self):
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
        self.assertEqual(reg.names(), before)


if __name__ == "__main__":
    unittest.main()
