"""Compile new sources and run HTTP tests plus the unchanged lab4 runner."""

from pathlib import Path
import os
import subprocess
import sys
import unittest

PRACTICE = Path(__file__).resolve().parents[2]
LAB = PRACTICE / "lab"


def main():
    results = PRACTICE / "results"
    results.mkdir(exist_ok=True)
    for required in [LAB / "web.py", LAB / "view.py", LAB / "tests" / "test_http.py"]:
        if not required.is_file():
            raise SystemExit(f"Missing required file: {required}")
    for source in LAB.rglob("*.py"):
        compile(source.read_bytes(), str(source), "exec")
    suite = unittest.TestLoader().discover(str(LAB / "tests"))
    if suite.countTestCases() == 0:
        raise SystemExit("No HTTP tests discovered")
    commands = [
        ("Practice 05 HTTP tests", [sys.executable, "-m", "unittest", "discover", "-s", str(LAB / "tests"), "-v"]),
        ("Practice 04 regression", [sys.executable, str(PRACTICE.parent / "practice_04" / "lab" / "scripts" / "check.py")]),
    ]
    outputs = ["Syntax: PASS\n"]
    failed = False
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    for label, command in commands:
        completed = subprocess.run(command, capture_output=True, text=True,
                                   encoding="utf-8", env=environment, cwd=LAB)
        output = f"\n=== {label} ===\n{completed.stdout}{completed.stderr}\nExit: {completed.returncode}\n"
        outputs.append(output)
        print(output, end="")
        failed = failed or completed.returncode != 0
    (results / "checks.txt").write_text("".join(outputs), encoding="utf-8")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
