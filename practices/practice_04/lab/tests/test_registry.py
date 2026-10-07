"""Baseline tests — valid subscribe, duplicate, and snapshot."""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from registry import Registry


class TestSubscribeNew(unittest.TestCase):
    def test_subscribe_new_name_returns_true(self):
        self.assertIs(Registry().subscribe("alice"), True)


class TestSubscribeDuplicate(unittest.TestCase):
    def test_subscribe_duplicate_returns_false(self):
        reg = Registry()
        reg.subscribe("alice")
        self.assertIs(reg.subscribe("alice"), False)


class TestNamesSnapshot(unittest.TestCase):
    def test_names_returns_sorted_list(self):
        reg = Registry()
        reg.subscribe("charlie")
        reg.subscribe("alice")
        reg.subscribe("bob")
        self.assertEqual(reg.names(), ["alice", "bob", "charlie"])

    def test_names_snapshot_is_independent_of_registry(self):
        reg = Registry()
        reg.subscribe("alice")
        snapshot = reg.names()
        snapshot.append("injected")
        self.assertEqual(reg.names(), ["alice"])


if __name__ == "__main__":
    unittest.main()
