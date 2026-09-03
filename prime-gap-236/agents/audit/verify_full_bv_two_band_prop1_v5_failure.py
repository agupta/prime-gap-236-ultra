#!/usr/bin/env python3
"""Independent exact counterexample to the frozen narrow Proposition-1 v5 audit.

The producer's Type-IIb packing succeeds, but its maximal auxiliary width
d_b(gamma) violates a stated endpoint hypothesis of Stadlmann's three-factor
partition lemma in an interior outer/outer above-square parameter slice.
No producer module or serialized arithmetic is imported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
PINNED = {
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "agents/small-delta-frontier/verify_full_bv_two_band_prop1_v5.py":
        "03cc767fb8c95156afffdcc0c30c5b8811934a6a495827ff9478bb3c1323ecae",
    "agents/small-delta-frontier/results/full_bv_two_band_prop1_audit_v5.json":
        "358b5bf1528265b75afd8085da656582a58ce3e62205b9d7eb53638969686b76",
    "agents/small-delta-frontier/test_full_bv_two_band_prop1_v5.py":
        "2715fb18f037d02fcafce8f1e0a2c7c6bf70bb85aad2ab8f0e2f757116adb329",
    "agents/small-delta-frontier/verify_wide_c722_two_band_prop1.py":
        "3ec590c95376432a75fb55c7810fbff10e87b67964d6cc4f761576c23aa414ca",
}

H = Q(1, 10**10)
ZETA = H / 1000
R0 = H / 10
DELTA = Q(7, 250)
OMEGA = Q(3, 1000)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def g_a() -> Q:
    return Q(2, 5) + Q(24, 5) * OMEGA + Q(7, 5) * DELTA + 2 * H


def g_b() -> Q:
    return Q(1, 3) + 8 * OMEGA + Q(7, 3) * DELTA + 3 * H


def d_b(gamma: Q) -> Q:
    return Q(3, 7) * gamma - Q(1, 7) - Q(24, 7) * OMEGA - H


def build() -> dict[str, object]:
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"pinned input changed: {relative}")

    # This is strictly inside the IIb interval G_b < gamma < G_a, avoiding
    # every possible open/closed-boundary interpretation.
    gamma = g_a() - H
    require(g_b() < gamma < g_a(), "chosen gamma is not interior IIb")
    width = d_b(gamma)

    # Source TeX 1290--1298 requires a_1,a_2,b_1,b_2 in (0,1/2).
    # With both open IIb factor intervals moved inward by r0, the lower
    # exponent of the u interval is the following exact value.
    a2 = (Q(1, 2) - gamma - 2 * OMEGA - 6 * ZETA - width + R0)
    b2 = Q(1, 2) - gamma - 2 * OMEGA - 6 * ZETA - R0
    require(a2 == -Q(4285714453, 5000000000000),
            "counterexample value changed")
    require(a2 < 0 < b2 < Q(1, 2), "counterexample signs changed")

    # Independently preserve the near-square IIb(1,4) regression.  All five
    # coordinates in bin 1 fail, but moving the smallest of the four sorted
    # outer coordinates to bin 2 succeeds with bin 3 empty.  Thus this is not
    # evidence that a third bin is necessary.
    c1 = Q(1, 3) + Q(7, 3) * DELTA - 4 * H
    c2 = Q(1, 10) - Q(7, 5) * DELTA - 4 * H
    c3 = DELTA
    inner = Q(103, 400)
    outer = Q(71, 500)
    all_first = c1 - inner - outer
    smallest_outer = outer / 4
    remaining_outer = outer - DELTA
    literal_slacks = (c1 - inner - remaining_outer,
                      c2 - smallest_outer, c3)
    require(all_first == -Q(6250003, 7500000000),
            "near IIb all-first regression changed")
    require(literal_slacks == (
        Q(203749997, 7500000000),
        Q(63249999, 2500000000),
        Q(7, 250)), "near IIb literal redistribution changed")
    require(min(literal_slacks) > 0, "near IIb literal witness failed")

    # A prospective repair exists but is intentionally not promoted to a
    # verdict on the frozen package: choosing a smaller auxiliary width can
    # restore a2>0 while retaining strict theorem faces.
    repair_width = DELTA + H / 4
    repair_a2 = (Q(1, 2) - gamma - 2 * OMEGA - 6 * ZETA -
                 repair_width + R0)
    repair_face1 = -1 - (24 * OMEGA + 7 * repair_width - 3 * g_b())
    repair_face2 = -(8 * OMEGA + 3 * repair_width - g_a())
    repair_shrunk_width = repair_width - 2 * R0 - DELTA
    require(min(repair_a2, repair_face1, repair_face2,
                repair_shrunk_width) > 0, "prospective repair diagnostic")

    return {
        "status": "AUDIT FAIL",
        "scope": "frozen narrow full-BV two-band Proposition-1 v5 analytic claim",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "failure": {
            "source": "Bounded_Gaps_2.0.tex lines 1290-1298 (Partition Lemma 12)",
            "required": "a1,a2,b1,b2 all lie in (0,1/2)",
            "band_pair": "outer/outer",
            "modulus_range": "above square root",
            "omega": str(OMEGA),
            "gamma": str(gamma),
            "gamma_minus_Gb": str(gamma - g_b()),
            "Ga_minus_gamma": str(g_a() - gamma),
            "db_gamma": str(width),
            "inward_a2": str(a2),
            "inward_b2": str(b2),
            "conclusion": "a2<0, so the frozen proof cannot invoke Partition Lemma 12 on this interior IIb slice",
        },
        "near_iib_1_4_regression": {
            "all_first_margin": str(all_first),
            "literal_assignment": "smallest sorted outer coordinate to bin 2; all others to bin 1; bin 3 empty",
            "literal_slacks": [str(value) for value in literal_slacks],
            "third_bin_used": False,
        },
        "prospective_unfrozen_repair_only": {
            "auxiliary_width": str(repair_width),
            "inward_a2": str(repair_a2),
            "IIb_face1_margin": str(repair_face1),
            "IIb_face2_margin": str(repair_face2),
            "shrunk_width_minus_delta": str(repair_shrunk_width),
            "warning": "requires a new frozen proof/checker and fresh hostile audit",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
