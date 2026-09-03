#!/usr/bin/env python3
"""One-command fail-closed analytic and cap-schedule audit for C722."""

from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent


def checked(command: list[str], marker: str, required: tuple[str, ...]) -> str:
    run = subprocess.run(command, text=True, capture_output=True)
    if run.returncode != 0:
        sys.stdout.write(run.stdout)
        sys.stderr.write(run.stderr)
        raise SystemExit(run.returncode or 1)
    if marker not in run.stdout:
        raise SystemExit(f"missing success marker: {marker}")
    for token in required:
        if token not in run.stdout:
            raise SystemExit(f"missing required exact audit line: {token}")
    return run.stdout


def main() -> None:
    analytic = checked(
        [sys.executable, str(HERE / "audit_c70.py"), "361/50000", "C722", "1/250"],
        "C722 DIRECT-HB ANALYTIC AUDIT PASS",
        (
            "active_counts\t0..20 (21 including zero)",
            "Definition1 epsilon\t1/250",
            "Definition1 upper reserve\t2831/12000",
            "scalar II face 2b\t149999/5000000000",
            "IIc literal C1\t4573399986563/15000000000000",
            "IIc all-first master margin C1-2B\t167599986563/15000000000000",
            "IIb near shrunken width over support delta\t3/350000000000",
            "Proposition1 roughness beta-B1\t17657/50000",
        ),
    )
    schedule = checked(
        [sys.executable, str(HERE / "verify_c722_schedule.py")],
        "C722 COUNT-SCHEDULE EXACT PREFIX AUDIT PASS",
        (
            "active_counts=0..24 first_empty=25 checked_pairs_per_branch=625",
            "IIc_worst_margin=56499669613/285000000000000",
            "schedule_sha256=8c67d65544a8f6036bae6f868eb937cabe963eaec12ec59e3a9fb537a9695f17",
        ),
    )
    # These are printed only after both subprocesses and all exact-string
    # guards have succeeded.
    print("C722 FAIL-CLOSED COMBINED AUDIT PASS")
    for line in analytic.splitlines():
        if line.startswith(("scalar II face 2b", "IIc literal C1", "IIc all-first master")):
            print(line)
    for line in schedule.splitlines():
        if line.startswith(("active_counts=", "IIc_worst_margin=", "schedule_sha256=")):
            print(line)


if __name__ == "__main__":
    main()
