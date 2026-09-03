#!/usr/bin/env python3
"""Exact analytic parameter audit for the one-band B=.16/.177 support.

This program reconstructs every parameter-dependent inequality in the
existing direct-Heath--Brown proof and reruns the exact continuum partition
cover.  The pinned analytic notes contain the source-level proofs of the
uniform distribution lemmas; this program does not replace those lemmas.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import argparse
import os
import sys
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
GEOMETRY_PATH = FILE.with_name("two_band_mixed_audit.py")
GEOMETRY_SHA256 = "7323ab20b12e550799646684720e23487ec379886a24f325546d5cef7bb03116"
GEOMETRY_RESULT = FILE.parent / "results/one_band_177_and_two_band_geometry.json"
GEOMETRY_RESULT_SHA256 = "0190e729eb2a4bc547aea0a057c0cb631c480f0a3fd596702340cfc452ccfbeb"

PINNED_ANALYTIC = {
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "agents/hostile-analytic-audit/direct-hb-prime-equidistribution.md":
        "47cd11457c44aa2348e7b3d22c5615261c5af04d999414dae3d58eba16f9e80c",
    "agents/hostile-analytic-audit/c10-analytic-repair-addendum.md":
        "2fc564f6e7e87661a7769980db85889720a19d09d4e65026fa23458fb6d583d7",
    "agents/structural-basis/C10-DEEP-DISTRIBUTION-AUDIT.md":
        "f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd",
    "agents/structural-basis/PROP1-C2ZERO-AUDIT.md":
        "050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb",
}

H = Q(1, 10**10)
S = H / 10
K = 10
EPSILON = Q(3, 400)
DELTA = Q(7, 250)
A = Q(253, 1000)
OMEGA = A - Q(1, 4)
XI1, XI2, XI3 = Q(19, 50), Q(2, 5), Q(2, 5)
SCHEDULE_HEAD = (
    Q(159999999, 10**9), Q(159999999, 10**9), Q(177, 1000),
    Q(177, 1000), Q(177, 1000), Q(177, 1000), Q(177, 1000),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_sha(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"SHA mismatch for {path}: {actual} != {expected}")


def positive(margins: dict[str, Q], name: str, value: Q) -> None:
    if value <= 0:
        raise AssertionError(f"{name} is not positive: {value}")
    margins[name] = value


def load_geometry():
    require_sha(GEOMETRY_PATH, GEOMETRY_SHA256)
    spec = importlib.util.spec_from_file_location("one_band_geometry", GEOMETRY_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load geometry verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_sha(GEOMETRY_RESULT, GEOMETRY_RESULT_SHA256)
    for relative, expected in PINNED_ANALYTIC.items():
        require_sha(REPO / relative, expected)

    artifact = json.loads(GEOMETRY_RESULT.read_bytes())
    expected_schedule = [str(x) for x in SCHEDULE_HEAD]
    one = artifact["one_band_improvement"]
    if (artifact["status"] != "one-band-and-two-band-exact-geometric-cover-pass" or
            artifact["theorem_ready"] is not False or one["A"] != str(A) or
            one["schedule"] != expected_schedule or
            one["cover"]["pair_count"] != 27 or
            one["cover"]["node_totals"] !=
            {"IIa": 27, "IIb": 27, "III": 27, "IIc": 1179}):
        raise ValueError("geometry artifact schema or exact counts changed")

    geometry = load_geometry()
    geometry.iv.DELTA = DELTA
    geometry.iv.H = H
    fresh = geometry.cover_schedule_pair(
        SCHEDULE_HEAD, SCHEDULE_HEAD, OMEGA, unordered=True)
    if fresh != one["cover"]:
        raise ArithmeticError("fresh continuum cover differs from pinned artifact")

    margins: dict[str, Q] = {}
    positive(margins, "Definition1 epsilon", EPSILON)
    positive(margins, "Definition1 A1-A0", A + EPSILON)
    positive(margins, "Definition1 upper", Q(1, 2) - EPSILON - A)
    full_schedule = SCHEDULE_HEAD[:6] + (SCHEDULE_HEAD[5],) * 29
    if len(full_schedule) != 35:
        raise AssertionError("full schedule length is not floor(1/delta)=35")
    for index, value in enumerate(full_schedule):
        positive(margins, f"Definition1 B{index + 1}-delta", value - DELTA)
        if index and not full_schedule[index - 1] <= value <= \
                full_schedule[index - 1] + DELTA:
            raise AssertionError(f"Definition 1 cap transition {index}->{index + 1}")
    if not 6 * DELTA <= full_schedule[5] < 7 * DELTA:
        raise AssertionError("first empty count is not seven")

    sigma = Q(1, 10) + S
    positive(margins, "HB sigma endpoint", sigma - Q(1, 10))
    positive(margins, "HB K=10", 2 * sigma - Q(1, K))
    positive(margins, "HB TypeII lower containment",
             (Q(1, 2) - sigma) - (XI2 - H))
    positive(margins, "HB TypeII upper containment",
             (1 - XI2 + H) - (Q(1, 2) + sigma))
    positive(margins, "HB TypeIII lower containment",
             2 * sigma - (1 - 2 * XI3 - H))
    positive(margins, "HB TypeIII upper containment",
             (XI3 + H) - (Q(1, 2) - sigma))
    positive(margins, "HB TypeIII pair containment",
             (Q(1, 2) + sigma) - (1 - XI3 - H))

    # Definition 2's epsilon enlargement cancels exactly for one band.
    qexp = (A - EPSILON) + (A + EPSILON)
    if qexp != 2 * A:
        raise AssertionError("epsilon did not cancel in Q-star exponent")
    positive(margins, "Type0 sharp-interval power saving",
             1 - ((Q(1, 2) - sigma) + qexp))
    positive(margins, "Type0 full-Poisson power saving",
             1 - (1 - 2 * sigma + 4 * OMEGA))
    positive(margins, "prime-square modulus saving", 1 - qexp)
    positive(margins, "higher-prime-power saving", 1 - (qexp + Q(1, 3)))
    positive(margins, "near-square-root IIc empty gap",
             (Q(1, 2) - sigma) -
             (Q(1, 3) + Q(7, 3) * DELTA + 3 * H))

    positive(margins, "TypeII scalar 19/2",
             Q(19, 2) - 36 * A - 13 * DELTA + 100 * H)
    positive(margins, "TypeII scalar first min",
             Q(21, 25) - Q(16, 5) * A - 2 * H - DELTA)
    positive(margins, "TypeII scalar second min",
             Q(63, 80) - 3 * A - 2 * H - DELTA)
    gamma3 = Q(1, 2) - sigma
    delta3 = Q(1, 2) - Q(7, 2) * OMEGA - Q(9, 8) * gamma3 - H
    positive(margins, "TypeIII inward width", delta3 - DELTA)
    positive(margins, "TypeIII distribution",
             4 - (28 * OMEGA + 9 * gamma3 + 8 * delta3))

    # Proposition 2 is not needed by the direct-HB proof, but its exact
    # prime-indicator branch independently gives c1=c2=0 at this parameter.
    positive(margins, "Prop2 2-(2xi1+3xi2)",
             2 - (2 * XI1 + 3 * XI2))
    if XI2 != XI3:
        raise AssertionError("Prop2 xi2=xi3 failed")
    positive(margins, "Prop2 4-(xi1+9xi2)", 4 - (XI1 + 9 * XI2))
    positive(margins, "Prop2 2xi1+xi2-1", 2 * XI1 + XI2 - 1)
    positive(margins, "Prop2 7-17xi2", 7 - 17 * XI2)
    beta = 1 - 2 * XI2
    positive(margins, "Prop1 beta-B11", beta - full_schedule[0])
    positive(margins, "Prop1 beta-B12", beta - full_schedule[1])
    c1 = c2 = Q(0)
    if (1 - c1, c2) != (Q(1), Q(0)):
        raise AssertionError("prime-indicator constants changed")

    result = {
        "status": "one-band-177-analytic-parameter-pass",
        "scope": (
            "exact parameter substitution and fresh continuum cover; "
            "source-level distribution lemmas are the pinned audited dependencies"
        ),
        "script_sha256": sha256(FILE),
        "geometry_script_sha256": GEOMETRY_SHA256,
        "geometry_artifact_sha256": GEOMETRY_RESULT_SHA256,
        "parameters": {
            "k": 48, "epsilon": str(EPSILON), "delta": str(DELTA),
            "A0": str(-EPSILON), "A1": str(A), "omega": str(OMEGA),
            "xi": [str(XI1), str(XI2), str(XI3)],
            "schedule_head_through_first_empty": expected_schedule,
            "first_empty_count": 7, "qstar_exponent_bound": str(qexp),
            "rho": "prime indicator (or weighted theta/log(3x) in direct-HB transfer)",
            "c1": "0", "c2": "0", "beta": str(beta),
        },
        "margins": {name: str(value) for name, value in margins.items()},
        "fresh_cover_counts": {
            "pairs": fresh["pair_count"], "nodes": fresh["node_totals"]},
        "pinned_analytic_dependencies": PINNED_ANALYTIC,
        "theorem_ready": False,
        "remaining": "finite-dimensional k=48 quotient and final independent audit",
    }
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode()
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode(), end="")


if __name__ == "__main__":
    main()
