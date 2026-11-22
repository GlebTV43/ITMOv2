"""Run the catalog regression against the pinned practice demo source."""

import argparse
import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[3]
PROJECT = Path("practices/practice_07.1")
BASE_COMMIT = "ffd4eed"
BEFORE = "        When(search_text=book.search_text, then=Value(0)),"
AFTER = '        When(search_text__startswith=book.title.casefold() + "\\n", then=Value(0)),'
REGRESSION = "books.test_practice72_alternatives.EquivalentEditionTest.test_same_title_precedes_same_author"
FAILURE_MARKER = "same-title edition should appear before another book by the same author"
TEST_TIMEOUT = 45


def run_tests(project, python, *labels):
    return subprocess.run(
        [str(python), "manage.py", "test", *labels],
        cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=TEST_TIMEOUT, check=False,
    )


def pinned_commit():
    return subprocess.check_output(
        ["git", "rev-parse", f"{BASE_COMMIT}^{{commit}}"], cwd=REPO, text=True, timeout=8,
    ).strip()


def verify(commit, replacement, python):
    if commit != pinned_commit() or replacement != AFTER:
        raise ValueError("Candidate is outside the pinned catalog change.")
    archive = subprocess.check_output(
        ["git", "archive", "--format=zip", commit, "--",
         str(PROJECT / "books"), str(PROJECT / "bookshare"), str(PROJECT / "manage.py")],
        cwd=REPO, timeout=15,
    )
    with TemporaryDirectory(prefix="bookshare-72-") as scratch:
        with ZipFile(io.BytesIO(archive)) as files:
            files.extractall(scratch)
        project = Path(scratch) / PROJECT
        regression = Path(__file__).with_name("test_practice72_alternatives.py")
        (project / "books" / regression.name).write_bytes(regression.read_bytes())
        initial = run_tests(project, python, REGRESSION)
        if initial.returncode != 1 or FAILURE_MARKER not in initial.stderr:
            raise ValueError("Regression did not reproduce against the baseline.")
        source = project / "books/views.py"
        text = source.read_text(encoding="utf-8")
        if text.count(BEFORE) != 1:
            raise ValueError("Expected catalog line is missing or ambiguous.")
        source.write_text(text.replace(BEFORE, replacement, 1), encoding="utf-8", newline="\n")
        corrected = run_tests(project, python, "books")
        if corrected.returncode:
            raise ValueError("Django tests did not pass with the proposed change.")
    return {"ok": True, "commit": commit, "replacement": replacement,
            "regression": "failed on baseline, passed after patch", "suite": "passed"}


def handler(python):
    class RegressionHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/test":
                self.send_error(404)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2048:
                    self.send_error(413)
                    return
                candidate = json.loads(self.rfile.read(size))
                data = verify(candidate["commit"], candidate["replacement"], python)
                status = 200
            except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
                data = {"ok": False, "error": "The pinned regression check did not pass."}
                status = 422
            payload = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return RegressionHandler


def main():
    parser = argparse.ArgumentParser()
    default = REPO / PROJECT / ".venv/Scripts/python.exe"
    parser.add_argument("--python", type=Path, default=default)
    parser.add_argument("--check", action="store_true", help="Run the red/green checks once and exit.")
    options = parser.parse_args()
    python = options.python.resolve(strict=True)
    if options.check:
        print(json.dumps(verify(pinned_commit(), AFTER, python)))
        return
    with HTTPServer(("127.0.0.1", 5782), handler(python)) as server:
        print("Catalog regression runner on 127.0.0.1:5782", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
