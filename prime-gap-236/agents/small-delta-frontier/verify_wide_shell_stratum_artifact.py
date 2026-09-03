#!/usr/bin/env python3
"""Read-only exact checker for the wide-shell tagged-constant pencil."""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FULL = HERE / "results/wide_volume_ramp_shell_stratum_pencil_v3.json"
FULL_OPT = HERE / "results/wide_volume_ramp_shell_stratum_pencil_v3_opt.json"
IONLY = HERE / "results/wide_volume_ramp_shell_I_by_R_v3.json"
IONLY_OPT = HERE / "results/wide_volume_ramp_shell_I_by_R_v3_opt.json"

EXPECTED = {
    FULL: "5ad7b42edfcae72b27a0e6221a1f5c1296695749c56d69309e01f0d505abdaf9",
    FULL_OPT: "5ad7b42edfcae72b27a0e6221a1f5c1296695749c56d69309e01f0d505abdaf9",
    IONLY: "3bc1f4cc49a5abfe054635d846935dae94d0dcea17a494ebcb0d4a53631fef70",
    IONLY_OPT: "3bc1f4cc49a5abfe054635d846935dae94d0dcea17a494ebcb0d4a53631fef70",
    HERE / "wide_shell_stratum_diagnostic.py":
        "dbbf990caf2c1e6bc418d525d4becdaedc82af54eec457e8eb5578da29555cc5",
    HERE / "test_wide_shell_stratum_diagnostic.py":
        "05e27874bc9238f503b1554b712e47d66482da4216bb715839e748f07e4f2d31",
    REPO / "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    REPO / "agents/exact-integrator/src/stratum_integrator.py":
        "0566f77860b0b61ce0ed342b5bb3a4743990725099d8b0cd6e685efad3c7394f",
    REPO / "agents/exact-integrator/grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    REPO / "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json":
        "88b6e1aeb04bd2e7d8600e5f4a7bcca8726b5307b95e5a4e9337a20c8f7afa96",
}


def sha256(data_or_path):
    data = (data_or_path if isinstance(data_or_path, bytes)
            else Path(data_or_path).read_bytes())
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def frac(value, name):
    require(type(value) is str and value and value.strip() == value,
            f"{name}: not a canonical string")
    parsed = Q(value)
    require(str(parsed) == value, f"{name}: noncanonical Fraction")
    return parsed


def canonical_load(path):
    raw = path.read_bytes()
    data = json.loads(raw)
    expected = (json.dumps(data, sort_keys=True, separators=(",", ":")) +
                "\n").encode("ascii")
    require(raw == expected, f"{path.name}: noncanonical JSON")
    return raw, data


def exact_ldl(a, diagonal, superdiagonal, bound):
    pivots = []
    for i in range(len(a)):
        value = bound * a[i] - diagonal[i]
        if i:
            require(pivots[-1] != 0, "zero preceding LDL pivot")
            value -= superdiagonal[i - 1] ** 2 / pivots[-1]
        pivots.append(value)
    return pivots


def main():
    for path, expected in EXPECTED.items():
        require(path.is_file(), f"missing pinned file: {path}")
        require(sha256(path) == expected, f"SHA mismatch: {path}")
    full_raw, data = canonical_load(FULL)
    opt_raw, opt = canonical_load(FULL_OPT)
    i_raw, ionly = canonical_load(IONLY)
    io_raw, ioopt = canonical_load(IONLY_OPT)
    require(full_raw == opt_raw and i_raw == io_raw,
            "normal/-O artifacts differ")
    require(data == opt and ionly == ioopt, "parsed artifacts differ")

    require(data.get("status") ==
            "wide-volume-ramp-shell-stratum-exact-diagnostic", "status")
    require(data.get("script_sha256") == EXPECTED[
        HERE / "wide_shell_stratum_diagnostic.py"], "producer SHA")
    require(data.get("active_strata") == list(range(23)), "active strata")
    require(data.get("domain_counts") ==
            {"hh": 8832, "hl": 8832, "ll": 8832}, "domain counts")
    gate = data.get("resource_gate")
    require(type(gate) is dict and gate.get("total_domain_count") == 26496 and
            gate.get("gate_passed_at_launch") is True, "resource gate")
    require(data.get("parameters") == ionly.get("parameters"),
            "I/full parameters")
    require(data.get("analytic_artifact_sha256") == EXPECTED[
        REPO / "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json"],
        "analytic artifact binding")

    a = [frac(x, f"I[{i}]") for i, x in enumerate(data["I_diagonal"])]
    bd = [frac(x, f"Bdiag[{i}]")
          for i, x in enumerate(data["kJ_diagonal"])]
    bs = [frac(x, f"Bsuper[{i}]")
          for i, x in enumerate(data["kJ_superdiagonal"])]
    vector = [frac(x, f"vector[{i}]")
              for i, x in enumerate(data["rational_vector"])]
    require(len(a) == len(bd) == len(vector) == 23 and len(bs) == 22,
            "matrix dimensions")
    require(all(x > 0 for x in a), "nonpositive I diagonal")

    denominator = sum((a[i] * vector[i] ** 2 for i in range(23)), Q(0))
    numerator = sum((bd[i] * vector[i] ** 2 for i in range(23)), Q(0))
    numerator += 2 * sum((bs[i] * vector[i] * vector[i + 1]
                          for i in range(22)), Q(0))
    require(denominator == frac(data["exact_particular_denominator"],
                                "particular denominator"), "denominator")
    require(numerator == frac(data["exact_particular_numerator"],
                              "particular numerator"), "numerator")
    require(numerator / denominator == frac(data["exact_particular_quotient"],
                                             "particular quotient"), "quotient")
    require(numerator - denominator == frac(data["exact_particular_margin"],
                                             "particular margin"), "margin")
    require(numerator < denominator, "particular vector unexpectedly crosses 1")

    bound = frac(data["rigorous_all_vector_quotient_upper_bound"], "bound")
    require(bound == Q(1, 16), "unexpected finite-space bound")
    pivots = exact_ldl(a, bd, bs, bound)
    serialized_pivots = [frac(x, f"pivot[{i}]")
                         for i, x in enumerate(data["upper_bound_LDL_pivots"])]
    require(pivots == serialized_pivots and all(x > 0 for x in pivots),
            "exact upper-bound LDL failed")
    require(data.get("upper_bound_LDL_all_positive") is True and
            data.get("finite_tagged_constant_space_no_crossing_rigorous") is True,
            "finite-space theorem flags")

    rows = data.get("stratum_rows")
    require(type(rows) is list and len(rows) == 23, "stratum rows")
    total = sum(a, Q(0))
    require(total == frac(data["I_total_shell"], "I total"), "I total")
    require(total == frac(ionly["I_total_shell"], "I-only total"),
            "I-only total mismatch")
    irows = ionly.get("stratum_I_rows")
    require(type(irows) is list and len(irows) == 23, "I-only rows")
    for r, row in enumerate(rows):
        require(row.get("R") == r and irows[r].get("R") == r, f"row R={r}")
        require(frac(row["I_mass"], f"row mass {r}") == a[r] ==
                frac(irows[r]["I_mass"], f"I-only mass {r}"), f"mass R={r}")
        require(frac(row["I_mass_fraction"], f"mass share {r}") == a[r] / total,
                f"mass share R={r}")
        require(frac(row["kJ_diagonal"], f"row Bdiag {r}") == bd[r],
                f"B diagonal R={r}")
        require(frac(row["single_stratum_quotient"], f"local q {r}") ==
                bd[r] / a[r], f"local quotient R={r}")
        require(frac(row["particular_vector_coefficient"], f"row vector {r}") ==
                vector[r], f"vector R={r}")
        require(frac(row["particular_I_fraction"], f"row I share {r}") ==
                a[r] * vector[r] ** 2 / denominator,
                f"particular I share R={r}")
        expected_super = bs[r] if r < 22 else Q(0)
        require(frac(row["kJ_super"], f"row Bsuper {r}") == expected_super,
                f"B super R={r}")

    mass_rank = sorted(range(23), key=lambda r: a[r], reverse=True)
    pweights = [a[r] * vector[r] ** 2 for r in range(23)]
    priority = sorted(range(23), key=lambda r: pweights[r], reverse=True)
    require(data.get("mass_rank_descending") == mass_rank and
            data.get("top_mass_strata") == mass_rank[:8], "mass ranking")
    require(data.get("particular_I_rank_descending") == priority and
            data.get("suggested_first_cross_strata") == priority[:6],
            "cross priority ranking")

    solves = data.get("cross_precision_discovery")
    require(type(solves) is list and [x.get("precision") for x in solves] ==
            [100, 160], "discovery precision list")
    with localcontext() as context:
        context.prec = 80
        q0, q1 = (Decimal(x["rayleigh_quotient"]) for x in solves)
        require(abs(q0 - q1) < Decimal("1e-90"), "precision instability")
        require(q1 < Decimal(1) / Decimal(16), "discovery exceeds exact bound")

    print("AUDIT PASS")
    print("artifact_sha256=", sha256(full_raw), sep="")
    print("I_artifact_sha256=", sha256(i_raw), sep="")
    print("rigorous_all_vector_quotient_upper_bound=1/16")
    with localcontext() as context:
        context.prec = 55
        print("exact_particular_quotient_decimal=",
              Decimal(numerator.numerator) / Decimal(numerator.denominator) /
              (Decimal(denominator.numerator) /
               Decimal(denominator.denominator)), sep="")
    print("suggested_first_cross_strata=", priority[:6], sep="")


if __name__ == "__main__":
    main()
