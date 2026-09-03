#!/usr/bin/env python3
"""Fail-closed contraction audit for the narrow full-outer constant result.

This checker reconstructs the particular vector and projective 2x2 solve but
does not repeat the 24-minute exact marginal traversal.  Independent literal
low-k geometry is covered by ``test_two_band_full_outer_constant.py``.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
ARTIFACT = HERE / "results/full_bv_two_band_full_outer_constant_2x2_exact_v2.json"
ARTIFACT_SHA256 = "4a4d94f20ca5ae21a0fc83e874531299586db75e01ee357a16d1c1c9bdae0006"
PRODUCER = HERE / "two_band_full_outer_constant.py"
PRODUCER_SHA256 = "75637298284a40be523621ebe1fcdc85bda59dcac42514fb8b50ffd8b460259d"
TEST = HERE / "test_two_band_full_outer_constant.py"
TEST_SHA256 = "0865416ba5dd116de50c9c2110ae3c1bb6790a443a4dad6af0ba1ff2a0612d33"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    for path, expected in ((ARTIFACT, ARTIFACT_SHA256),
                           (PRODUCER, PRODUCER_SHA256), (TEST, TEST_SHA256)):
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"SHA mismatch: {path}: {actual}")
    data = json.loads(ARTIFACT.read_bytes())
    if (data.get("format") !=
            "full-bv-two-band-full-capped-shell-constant-exact-v1" or
            data.get("script_sha256") != PRODUCER_SHA256 or
            data.get("k") != 48 or data.get("theorem_ready") is not False):
        raise ValueError("artifact identity/status mismatch")
    expected_parameters = {
        "delta": "7/250", "alpha1": "103/400", "eta1": "97/400",
        "alpha2": "521/2000", "eta2": "491/2000",
        "outer_schedule": ["43/500", "43/500", "57/500",
                           "71/500", "71/500", "71/500"]}
    if data.get("parameters") != expected_parameters:
        raise ValueError("support parameters changed")
    if data.get("branch_integral_counts") != {
            "rr": 600, "rl": 600, "vr": 600, "vl": 600,
            "hh": 624, "hl": 624, "ll": 624}:
        raise ValueError("branch traversal inventory changed")
    A, B = data["I_matrix"], data["kJ_matrix"]
    if A[0][1] != "0" or A[1][0] != "0" or B[0][1] != B[1][0]:
        raise ArithmeticError("2x2 symmetry/disjoint-I identity failed")
    x, y = map(Q, data["rational_vector"])
    denominator = x * x * Q(A[0][0]) + y * y * Q(A[1][1])
    numerator = (x * x * Q(B[0][0]) + 2 * x * y * Q(B[0][1]) +
                 y * y * Q(B[1][1]))
    if (denominator != Q(data["exact_denominator"]) or
            numerator != Q(data["exact_numerator"]) or
            numerator / denominator != Q(data["exact_quotient"]) or
            numerator - denominator != Q(data["exact_margin"])):
        raise ArithmeticError("exact particular-vector contraction failed")
    base = Q(B[0][0]) / Q(A[0][0])
    if numerator / denominator - base != Q(data["exact_gain"]):
        raise ArithmeticError("exact gain identity failed")
    cross = tuple(map(Q, data["by_common_large_count"]["cross_kJ"]))
    shell = tuple(map(Q, data["by_common_large_count"]["shell_kJ"]))
    if len(cross) != 6 or len(shell) != 6 or sum(cross) != Q(B[0][1]) or \
            sum(shell) != Q(B[1][1]):
        raise ArithmeticError("per-count reconstruction failed")
    with localcontext() as context:
        context.prec = 260
        dec = lambda value: Decimal(value.numerator) / Decimal(value.denominator)
        aa = dec(Q(B[0][0])) / dec(Q(A[0][0]))
        dd = dec(Q(B[1][1])) / dec(Q(A[1][1]))
        bb = dec(Q(B[0][1])) ** 2 / (dec(Q(A[0][0])) * dec(Q(A[1][1])))
        eigenvalue = (aa + dd + ((aa - dd) ** 2 + 4 * bb).sqrt()) / 2
        recorded = Decimal(data["cross_precision_solves"][-1]["eigenvalue"])
        if abs(eigenvalue - recorded) > Decimal("1e-235"):
            raise ArithmeticError("independent 2x2 root mismatch")
    if not denominator > 0 or not numerator < denominator:
        raise ArithmeticError("denominator/margin sign changed")
    print("FULL OUTER CONSTANT ARTIFACT SCOPED AUDIT PASS")


if __name__ == "__main__":
    main()
