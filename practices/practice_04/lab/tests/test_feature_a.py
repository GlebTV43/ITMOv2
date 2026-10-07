"""Feature A behaviour tests — validated subscribe.

Each method tests exactly one behaviour (Rule 2).
All assertions use only the public API (Rule 1).
No @unittest.skip or similar weakening (Rule 3).
stdlib only (Rule 4).
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from registry import Registry


# ── Type rejection ──────────────────────────────────────────────────────────

class TestSubscribeTypeRejection(unittest.TestCase):
    def test_subscribe_integer_raises_type_error(self):
        with self.assertRaises(TypeError):
            Registry().subscribe(42)

    def test_subscribe_none_raises_type_error(self):
        with self.assertRaises(TypeError):
            Registry().subscribe(None)

    def test_subscribe_list_raises_type_error(self):
        with self.assertRaises(TypeError):
            Registry().subscribe(["alice"])


# ── Empty / whitespace rejection ────────────────────────────────────────────

class TestSubscribeEmptyRejection(unittest.TestCase):
    def test_subscribe_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            Registry().subscribe("")

    def test_subscribe_whitespace_only_raises_value_error(self):
        with self.assertRaises(ValueError):
            Registry().subscribe("   ")


# ── 80 / 81 Unicode character boundary ─────────────────────────────────────

class TestSubscribeLengthBoundary(unittest.TestCase):
    def test_subscribe_80_char_name_returns_true(self):
        self.assertIs(Registry().subscribe("a" * 80), True)

    def test_subscribe_81_char_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            Registry().subscribe("a" * 81)

    def test_subscribe_80_unicode_chars_returns_true(self):
        self.assertIs(Registry().subscribe("я" * 80), True)

    def test_subscribe_81_unicode_chars_raises_value_error(self):
        with self.assertRaises(ValueError):
            Registry().subscribe("я" * 81)


# ── No state mutation on invalid input ──────────────────────────────────────

class TestSubscribeNoMutationOnTypeError(unittest.TestCase):
    def test_type_error_does_not_mutate_state(self):
        reg = Registry()
        reg.subscribe("existing")
        with self.assertRaises(TypeError):
            reg.subscribe(42)
        self.assertEqual(reg.names(), ["existing"])


class TestSubscribeNoMutationOnValueErrorEmpty(unittest.TestCase):
    def test_empty_string_does_not_mutate_state(self):
        reg = Registry()
        reg.subscribe("existing")
        with self.assertRaises(ValueError):
            reg.subscribe("")
        self.assertEqual(reg.names(), ["existing"])


class TestSubscribeNoMutationOnValueErrorWhitespace(unittest.TestCase):
    def test_whitespace_only_does_not_mutate_state(self):
        reg = Registry()
        reg.subscribe("existing")
        with self.assertRaises(ValueError):
            reg.subscribe("   ")
        self.assertEqual(reg.names(), ["existing"])


class TestSubscribeNoMutationOnValueErrorTooLong(unittest.TestCase):
    def test_too_long_name_does_not_mutate_state(self):
        reg = Registry()
        reg.subscribe("existing")
        with self.assertRaises(ValueError):
            reg.subscribe("a" * 81)
        self.assertEqual(reg.names(), ["existing"])


# ── Whitespace stripping + storage ──────────────────────────────────────────

class TestSubscribeStripsWhitespace(unittest.TestCase):
    def test_subscribe_strips_leading_trailing_whitespace(self):
        reg = Registry()
        reg.subscribe("  alice  ")
        self.assertEqual(reg.names(), ["alice"])

    def test_subscribe_with_whitespace_returns_true_when_new(self):
        self.assertIs(Registry().subscribe("  alice  "), True)


# ── Normalised duplicate detection (Ann case from cases.json) ────────────────

class TestSubscribeNormalisedDuplicate(unittest.TestCase):
    def test_subscribe_padded_then_plain_ann_is_duplicate(self):
        reg = Registry()
        reg.subscribe("  Ann  ")
        self.assertIs(reg.subscribe("Ann"), False)

    def test_subscribe_padded_ann_first_call_returns_true(self):
        self.assertIs(Registry().subscribe("  Ann  "), True)


if __name__ == "__main__":
    unittest.main()
