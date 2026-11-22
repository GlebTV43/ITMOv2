import os
import sys
from pathlib import Path
from tempfile import mkdtemp

import django
from django.core.management import call_command


def main():
    local = Path(".local").resolve()
    local.mkdir(exist_ok=True)
    os.environ.update(
        DJANGO_SETTINGS_MODULE="browser_tests.settings",
        BOOKSHARE_BROWSER_RUNTIME=mkdtemp(prefix="browser-", dir=local),
        BOOKSHARE_DEBUG="1",
    )
    django.setup()
    call_command("migrate", interactive=False, verbosity=0)
    call_command("seed_demo", verbosity=0)
    address = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:8764"
    call_command("runserver", address, use_reloader=False)


if __name__ == "__main__":
    main()
