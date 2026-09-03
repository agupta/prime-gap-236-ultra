#!/usr/bin/env python3
"""Cross-result withdrawal audit for the local pair-MCMC search runs.

This checker imports no Monte Carlo producer.  It pins every frozen result,
reconstructs the count-15 calibration comparison from the exact rational
uncapped normalizer and the independently computed Decimal80 capped stage,
and records why none of the realized MCMC quotient signs is usable.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]

UNCAPPED = "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json"
EXACT_I15 = (
    "agents/small-delta-frontier/results/"
    "piecewise_D16_capped_R15_I_decimal80.json")
FIXED_I = "results/heuristic_piecewise_capped_mcmc_I_v1.json"
FIXED_J1 = "results/heuristic_piecewise_capped_mcmc_J_v1.json"
FIXED_J2 = "results/heuristic_piecewise_capped_mcmc_J_v2.json"
COUNT = "results/heuristic_capped_count_pencil_mcmc_v1.json"
BINARY = "results/heuristic_capped_single_count_R15_umbrella_v1.json"
SMOOTH = (
    "results/heuristic_capped_single_count_R15_smooth_count15_166_v1.json")
COUNT_FORMULA = (
    "agents/audit/results/heuristic_capped_count_pencil_mcmc_audit.json")
BINARY_FORMULA = (
    "agents/audit/results/"
    "heuristic_capped_single_count_umbrella_mcmc_audit.json")
EXACT_I15_SOURCE = (
    "agents/small-delta-frontier/piecewise_d16_capped_target.py")
FIXED_SOURCE = "scripts/heuristic_piecewise_capped_mcmc.py"
COUNT_SOURCE = "scripts/heuristic_capped_count_pencil_mcmc.py"
BINARY_SOURCE = "scripts/heuristic_capped_single_count_umbrella_mcmc.py"
SMOOTH_SOURCE = (
    "scripts/heuristic_capped_single_count_smooth_umbrella_mcmc.py")

PINNED = {
    UNCAPPED:
        "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7",
    EXACT_I15:
        "4f493d645c25354ba9218c923ae8bff06d56a5b79cd45dc608c0aa3a4b051abd",
    FIXED_I:
        "194d91210c3f14bfc07f2ec4a73ebf41371880e5594872dbf10a5f3703d9f959",
    FIXED_J1:
        "76430979d1ec81cf1245a064191e70d3645d9b6cbfa5890ac49668dc11de62bc",
    FIXED_J2:
        "7c5371c0ce9b5dacb3c3f2184e9153c05391319bdef6085976cc4af241549b53",
    COUNT:
        "e8a93753ceb5b5cf10af0cae61937ed05647aad40863da67b3385d84ef12f29c",
    BINARY:
        "bdc64a3523a4e00846caa143372b164153181386e7f0b56fb4a55b6e073bdabc",
    SMOOTH:
        "a2abc28102b96912a6b2b2b6dae19c2fadb79491b029ce864c2586bf0d796f37",
    COUNT_FORMULA:
        "fe62c0865e93b9b14fab3227c4677094863b74de73c0abb84dd9d474b3846976",
    BINARY_FORMULA:
        "01ee2c600058d4ad592a3c2ce0b242fb43edb39109fe521400b890a7f2d6018a",
    EXACT_I15_SOURCE:
        "cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c",
    FIXED_SOURCE:
        "7d456f0616c382858c946ada3f6ea8d7bc72c22b04eb62a1b566f3077acd7213",
    COUNT_SOURCE:
        "5accfe97f9561ce08f3fb403d9d0579847caf289a9cbd2ca8ad6229f6bc11c7b",
    BINARY_SOURCE:
        "fcef0eefc2a0503d2d1f27c568c64897dab01f8ed4c84dc33afb47a3551200a5",
    SMOOTH_SOURCE:
        "f5d20923b9b3c6e38abce316accb42f46f0e39c9726b4f221aa5141ea008a687",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def strict_json(relative: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {relative}: {key}")
            result[key] = value
        return result

    return json.loads(
        (REPO / relative).read_bytes(), object_pairs_hook=pairs,
        parse_float=Decimal,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {relative}: {token}")))


def dec(value) -> Decimal:
    require(isinstance(value, (str, int, Decimal)),
            "expected serialized decimal scalar")
    answer = Decimal(value)
    require(answer.is_finite(), "nonfinite serialized decimal scalar")
    return answer


def ratio(values) -> Decimal:
    parsed = [dec(x) for x in values]
    require(parsed and min(parsed) > 0, "ratio input is not strictly positive")
    return max(parsed) / min(parsed)


def build():
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"frozen withdrawal input changed: {relative}")

    uncapped = strict_json(UNCAPPED)
    exact_i = strict_json(EXACT_I15)
    fixed_i = strict_json(FIXED_I)
    fixed_j1 = strict_json(FIXED_J1)
    fixed_j2 = strict_json(FIXED_J2)
    count = strict_json(COUNT)
    binary = strict_json(BINARY)
    smooth = strict_json(SMOOTH)
    count_formula = strict_json(COUNT_FORMULA)
    binary_formula = strict_json(BINARY_FORMULA)

    for raw in (fixed_i, fixed_j1, fixed_j2, count, binary, smooth):
        require(raw.get("status") == "HEURISTIC ONLY" and
                raw.get("rigorous") is False and
                raw.get("theorem_ready") is False,
                "a withdrawn result changed its negative scope")
    require(count_formula.get("status") == "SEARCH-INSTRUMENT PASS" and
            binary_formula.get("status") == "SEARCH-INSTRUMENT PASS",
            "a pinned formula-level audit changed status")
    require(exact_i.get("script_sha256") == PINNED[EXACT_I15_SOURCE] and
            count.get("script_sha256_before_output") ==
            PINNED[COUNT_SOURCE] and
            binary.get("script_sha256_before_output") ==
            PINNED[BINARY_SOURCE] and
            smooth.get("script_sha256_before_output") ==
            PINNED[SMOOTH_SOURCE] and
            fixed_j2.get("script_sha256_before_output") ==
            PINNED[FIXED_SOURCE],
            "result-to-source provenance changed")
    require(fixed_i.get("script_sha256_before_output") !=
            PINNED[FIXED_SOURCE] and
            fixed_j1.get("script_sha256_before_output") !=
            PINNED[FIXED_SOURCE],
            "expected fixed v1 source-replay loss changed")

    stage = exact_i.get("i_stage", {})
    require(exact_i.get("complete_stage") is True and
            stage.get("total_count") == 15 and
            stage.get("faces") == {"high": 23, "low": 21},
            "count-15 calibration stage is incomplete or changed")

    with localcontext() as context:
        context.prec = 90
        high = dec(stage["high"])
        low = dec(stage["scheduled_low"])
        shell = dec(stage["shell_difference"])
        require(high - low == shell and shell > 0,
                "serialized Decimal80 shell subtraction does not replay")

        a11_q = Fraction(uncapped["I_matrix"][1][1])
        a11 = Decimal(a11_q.numerator) / Decimal(a11_q.denominator)
        exact_cap_fraction = shell / a11

        counts = count.get("parameters", {}).get("counts")
        require(counts == list(range(6, 16)),
                "count-pencil coordinate ordering changed")
        sampled_cap_fraction = dec(count["I_capped_frequency_by_count"][15])
        sampled_i15 = dec(count["I_diagonal"][-1])
        reconstructed_sampled_i15 = a11 * sampled_cap_fraction
        require(abs(sampled_i15 - reconstructed_sampled_i15) /
                reconstructed_sampled_i15 < Decimal("1e-19"),
                "count-pencil I15 entry is not its sampled frequency times a11")

        frequency_factor = sampled_cap_fraction / exact_cap_fraction
        integral_factor = sampled_i15 / shell
        require(frequency_factor > 700 and integral_factor > 700 and
                abs(frequency_factor - integral_factor) < Decimal("1e-12"),
                "the decisive factor-711 calibration failure disappeared")

    require(count["estimated_top_quotient"] == "1.0324314258639082365" and
            count["group_quotient_standard_error"] == "nan" and
            sum(x == "nan" for x in count["group_top_quotients"]) == 2,
            "count-pencil pathology changed")
    require(binary["estimated_top_quotient"] == "0.9814546588482798605" and
            smooth["estimated_top_quotient"] == "0.98128064191930841533",
            "single-count reported roots changed")

    binary_i_ratio = ratio(binary["group_I_capped_probability"])
    smooth_i_ratio = ratio(smooth["group_I_capped_probability"])
    fixed_i_ratio = ratio(fixed_i["I"]["group_means"])
    smooth_transition_min = min(
        dec(x) for x in smooth["group_J_count_transition_fraction"])
    smooth_transition_max = max(
        dec(x) for x in smooth["group_J_count_transition_fraction"])
    require(binary_i_ratio > 38 and smooth_i_ratio > 20 and
            fixed_i_ratio > Decimal("2.8") and
            Decimal("0.08") < smooth_transition_min <
            smooth_transition_max < Decimal("0.13"),
            "frozen cross-run mixing diagnostics changed")

    return {
        "status": "AUDIT FAIL / ALL LOCAL PAIR-MCMC SIGNS WITHDRAWN",
        "scope": (
            "realized fixed-amplitude, count-pencil, binary-umbrella, and "
            "smooth-umbrella MCMC results as evidence for a capped quotient"),
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "calibration": {
            "uncapped_outer_I_a11": str(a11),
            "decimal80_capped_volume_R15_I": str(shell),
            "decimal80_capped_volume_R15_fraction": str(exact_cap_fraction),
            "count_mcmc_sampled_R15_fraction": str(sampled_cap_fraction),
            "count_mcmc_predicted_R15_I": str(sampled_i15),
            "sampled_over_decimal80_fraction_factor": str(frequency_factor),
            "sampled_over_decimal80_integral_factor": str(integral_factor),
            "reference_scope": (
                "deterministic Decimal80 high-minus-low calculation, "
                "source-bound and independently branch-audited; not an "
                "interval certificate"),
        },
        "cross_run_pathologies": {
            "fixed_I_group_max_over_min": str(fixed_i_ratio),
            "fixed_I_reported_q":
                fixed_i["fixed_amplitude_estimate"]["capped_quotient"],
            "fixed_J1_reported_q":
                fixed_j1["fixed_amplitude_estimate"]["capped_quotient"],
            "fixed_J2_reported_q":
                fixed_j2["fixed_amplitude_estimate"]["capped_quotient"],
            "fixed_I_and_J1_original_source_bytes_preserved": False,
            "count_reported_q": count["estimated_top_quotient"],
            "count_nonfinite_group_roots": 2,
            "binary_reported_q": binary["estimated_top_quotient"],
            "binary_I_group_max_over_min": str(binary_i_ratio),
            "smooth_reported_q": smooth["estimated_top_quotient"],
            "smooth_I_group_max_over_min": str(smooth_i_ratio),
            "smooth_J_last_proposal_count_change_range": [
                str(smooth_transition_min), str(smooth_transition_max)],
        },
        "formula_level_status": {
            "count_pencil": "SEARCH-INSTRUMENT PASS retained",
            "binary_umbrella": "SEARCH-INSTRUMENT PASS retained",
            "meaning": (
                "algebraic expectation identities do not validate a "
                "non-equilibrated realized sample"),
        },
        "withdrawn_inferences": [
            "fixed-amplitude capped quotient signs from I-v1/J-v1/J-v2",
            "the count-pencil aggregate q=1.032431 positive sign",
            "the binary-umbrella q=0.981454 negative sign",
            "the smooth-umbrella q=0.981281 negative sign/search veto",
            "all rankings that use these local-chain frequencies as calibrated",
        ],
        "decision": (
            "the count sampler overestimates a directly reconstructed R15 "
            "capped mass by a factor above 711; group dispersion and the "
            "shared short local-chain design leave no convergence evidence. "
            "No realized MCMC quotient sign may guide a theorem claim, exact "
            "launch veto, or support retirement"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
