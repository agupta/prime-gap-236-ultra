#!/usr/bin/env python3
"""Exact-form discovery probe for constants on the clean rising-tail strata.

This reuses the independently tested stratum recurrence but deliberately does
not claim an analytic or finite-space audit.  Its purpose is to rank the new
support before the much more expensive BV-D16 cross contraction.
"""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
MODULE_DIR = REPO / "agents/small-delta-frontier"
sys.path.insert(0, str(MODULE_DIR))
import wide_shell_stratum_diagnostic as w  # noqa: E402


FIRST_NINE = (
    Q(597, 5000), Q(633, 5000), Q(669, 5000), Q(141, 1000),
    Q(737, 5000), Q(773, 5000), Q(1553, 10000), Q(809, 5000),
    Q(81, 500),
)
TAIL = (Q(3329, 20000),) + tuple(
    Q(x, 10000) for x in
    (1690, 1695, 1718, 1737, 1752, 1762, 1764, 1774, 1782, 1790,
     1796, 1801, 1806, 1811, 1815)
)
SCHEDULE = FIRST_NINE + TAIL + (Q(1815, 10000),) * 23


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    started = time.monotonic()
    w.SCHEDULE = SCHEDULE
    hi, lo, masses = w.exact_i_masses()
    tables = {}
    domains = {}
    for name, left, right in (("hh", hi, hi), ("hl", hi, lo),
                              ("ll", lo, lo)):
        tables[name], domains[name] = w.cross_constant_stratum_table(
            left, right, w.ETA2)
    hlt = [list(row) for row in zip(*tables["hl"])]
    j = w.matrix_add((Q(1), tables["hh"]), (Q(-1), tables["hl"]),
                     (Q(-1), hlt), (Q(1), tables["ll"]))
    b = [[w.K * x for x in row] for row in j]
    active = [r for r, x in enumerate(masses) if x > 0]
    if active != list(range(26)):
        raise ArithmeticError(f"unexpected active strata: {active}")
    a_active = [masses[r] for r in active]
    b_active = [[b[r][s] for s in active] for r in active]
    solve = w.decimal_jacobi_diagonal_gram(a_active, b_active, 100)
    result = {
        "format": "clean-rising-tail-shell-constants-probe-v1",
        "claim_scope": "exact matrix forms; Decimal eigensolve discovery only",
        "script_sha256": sha(FILE),
        "reused_module_sha256": sha(Path(w.__file__)),
        "schedule": [str(x) for x in SCHEDULE[:26]],
        "active": active,
        "I_total": str(sum(a_active, Q(0))),
        "domains": domains,
        "solve": solve,
        "wall_seconds": time.monotonic() - started,
        "theorem_ready": False,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
