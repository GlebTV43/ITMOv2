"""Security regressions fail against the supplied vulnerable service."""

import unittest
from attacks import exercise, running_shop


class SecurityRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with running_shop() as client:
            cls.report = exercise(client)


def security_test(case_id):
    def run(self):
        case = next(c for c in self.report["cases"] if c["id"] == case_id)
        self.assertTrue(case["safe"], f"{case['title']}: {case['exchange']['status']}; expected {case['expected']}")
    return run


for index in range(1, 25):
    case_id = f"A{index:02d}"
    setattr(SecurityRegression, "test_" + case_id, security_test(case_id))


if __name__ == "__main__":
    unittest.main(verbosity=2)
