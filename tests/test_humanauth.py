"""Selftest for the humanauth module. Exit code 0 only if every red-team attack is refused and the control passes."""
import os
import sys

from support_humanauth_checks import run_all  # noqa: E402

results = run_all()
bad = [r for r in results if not r[1]]
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + " | " + detail)
print(f"{len(results) - len(bad)}/{len(results)} passed")
sys.exit(1 if bad else 0)
