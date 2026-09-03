#!/usr/bin/env python3
"""Independent exact box-cover spots for the nonconstant C10 schedule.

This deliberately imports the independent attack's interval-box engine and
does not use the prefix lemma or its checker.  The two cases are only
adversarial spot reconstructions; the universal proof is the closed-form
all-pairs loop in verify_c10_nonconstant_schedule.py.
"""

from fractions import Fraction as Q
from pathlib import Path
import sys


INDEPENDENT = Path(__file__).resolve().parents[2] / "independent-attack" / "code"
sys.path.insert(0, str(INDEPENDENT))
import interval_partition_verify as iv  # noqa: E402


DELTA = Q(1, 100)
BOUNDS = {
    3: Q(97, 625),
    13: Q(17241, 100000),
    14: Q(17293, 100000),
}
CASES = (
    (
        "IIc pair 3,3",
        3,
        3,
        (Q(4601199986563, 15000000000000),
         Q(776499995341, 15000000000000)),
    ),
    (
        "III-omega pair 13,14",
        13,
        14,
        (Q(207035999869, 600000000000),
         Q(138313333277, 800000000000)),
    ),
)


def main() -> None:
    iv.DELTA = DELTA
    for tag, m, mp, caps in CASES:
        groups = (iv.initial_group(m, BOUNDS[m]),
                  iv.initial_group(mp, BOUNDS[mp]))
        if None in groups:
            raise AssertionError(f"unexpected empty group in {tag}")
        state = {
            "nodes": 0,
            "leaves": 0,
            "max_depth": 0,
            "node_limit": 100000,
            "min_width": Q(1, 10**12),
            "witness_box": None,
        }
        if not iv.cover(groups, caps, state):
            raise AssertionError(f"unresolved exact box in {tag}: {state}")
        print(f"{tag} EXACT BOX PASS nodes={state['nodes']} "
              f"leaves={state['leaves']} depth={state['max_depth']}")


if __name__ == "__main__":
    main()
