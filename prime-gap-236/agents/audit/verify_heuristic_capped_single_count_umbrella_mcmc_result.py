#!/usr/bin/env python3
"""Hostile post-run audit of the frozen single-count umbrella MCMC result.

This checker does not import either Monte Carlo implementation.  It pins the
frozen run and the earlier formula-level audit, reconstructs all reported 2x2
roots from exact uncapped normalizers, and diagnoses whether the run supplies
usable evidence.  A formula-level PASS and a result-level FAIL are compatible:
the latter concerns mixing and uncertainty, not the change-of-measure identity.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
RESULT = "results/heuristic_capped_single_count_R15_umbrella_v1.json"
SOURCE = "scripts/heuristic_capped_single_count_umbrella_mcmc.py"
FORMULA_AUDIT = (
    "agents/audit/results/"
    "heuristic_capped_single_count_umbrella_mcmc_audit.json")
UNCAPPED = "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json"
INNER_ETA2 = "results/wide_c722_D16_inner_eta2_exact.json"
BASE = "scripts/heuristic_capped_count_pencil_mcmc.py"

PINNED = {
    RESULT:
        "bdc64a3523a4e00846caa143372b164153181386e7f0b56fb4a55b6e073bdabc",
    SOURCE:
        "fcef0eefc2a0503d2d1f27c568c64897dab01f8ed4c84dc33afb47a3551200a5",
    FORMULA_AUDIT:
        "01ee2c600058d4ad592a3c2ce0b242fb43edb39109fe521400b890a7f2d6018a",
    UNCAPPED:
        "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7",
    INNER_ETA2:
        "78ae10ff34a195779077222f7a845a948a78e11ff905c7e5cbdb590c6d6f256e",
    BASE:
        "5accfe97f9561ce08f3fb403d9d0579847caf289a9cbd2ca8ad6229f6bc11c7b",
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


def dfrac(value: Q) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def decimal_string(value) -> Decimal:
    require(isinstance(value, str), "Monte Carlo scalar is not a string")
    parsed = Decimal(value)
    require(parsed.is_finite(), "nonfinite Monte Carlo scalar")
    return parsed


def top_2d(a00, arr, b00, b0r, brr):
    require(a00 > 0 and arr > 0, "nonpositive 2x2 denominator")
    w00 = b00 / a00
    w11 = brr / arr
    w01 = b0r / (a00 * arr).sqrt()
    return ((w00 + w11) / 2 +
            ((((w00 - w11) / 2) ** 2 + w01 * w01).sqrt()))


def build():
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"frozen umbrella input changed: {relative}")

    raw = strict_json(RESULT)
    formula = strict_json(FORMULA_AUDIT)
    uncapped = strict_json(UNCAPPED)
    inner_eta2 = strict_json(INNER_ETA2)
    require(formula.get("status") == "SEARCH-INSTRUMENT PASS",
            "formula-level audit no longer passes")
    require(raw.get("status") == "HEURISTIC ONLY" and
            raw.get("rigorous") is False and
            raw.get("theorem_ready") is False and
            raw.get("script_sha256_before_output") == PINNED[SOURCE],
            "run identity or negative scope changed")
    require(raw.get("parameters") == {
        "burnin": 300, "chains": 128, "groups": 8,
        "i_factor": 32, "j_factor": 16, "output": None,
        "seed": 2360486, "steps": 300, "target": 15, "thin": 2,
    }, "frozen run schedule changed")
    require(raw.get("source_hashes") == {
        INNER_ETA2: PINNED[INNER_ETA2],
        UNCAPPED: PINNED[UNCAPPED],
        BASE: PINNED[BASE],
    }, "run dependency provenance changed")

    groups = 8
    keys = (
        "group_I_capped_probability", "group_J_cross_normalized",
        "group_J_diagonal_normalized", "group_top_quotient",
        "group_I_umbrella_visit_fraction",
        "group_J_umbrella_visit_fraction")
    values = {}
    for key in keys:
        tokens = raw.get(key)
        require(isinstance(tokens, list) and len(tokens) == groups,
                f"wrong group inventory for {key}")
        values[key] = [decimal_string(token) for token in tokens]

    with localcontext() as context:
        context.prec = 90
        a00 = dfrac(Q(uncapped["I_matrix"][0][0]))
        a11 = dfrac(Q(uncapped["I_matrix"][1][1]))
        b00 = dfrac(Q(uncapped["kJ_matrix"][0][0]))
        envelope = dfrac(
            Q(uncapped["kJ_matrix"][1][1]) +
            Q(inner_eta2["numerator_48J"]))

        recomputed_groups = []
        for ip, cross, diagonal in zip(
                values["group_I_capped_probability"],
                values["group_J_cross_normalized"],
                values["group_J_diagonal_normalized"]):
            recomputed_groups.append(top_2d(
                a00, a11 * ip, b00, envelope * cross,
                envelope * diagonal))
        for ours, theirs in zip(
                recomputed_groups, values["group_top_quotient"]):
            require(abs(ours - theirs) < Decimal("5e-18"),
                    "reported group root does not replay")

        pooled_q = top_2d(
            a00,
            a11 * decimal_string(raw["pooled_I_capped_probability"]),
            b00,
            envelope * decimal_string(raw["pooled_J_cross_normalized"]),
            envelope * decimal_string(raw["pooled_J_diagonal_normalized"]))
        reported_q = decimal_string(raw["estimated_top_quotient"])
        require(abs(pooled_q - reported_q) < Decimal("5e-18"),
                "reported pooled root does not replay")

    ip = values["group_I_capped_probability"]
    cross = values["group_J_cross_normalized"]
    diagonal = values["group_J_diagonal_normalized"]
    qgroup = values["group_top_quotient"]
    jvisit = values["group_J_umbrella_visit_fraction"]
    se = decimal_string(raw["group_quotient_standard_error"])
    require(min(ip) > 0 and min(diagonal) > 0,
            "expected finite positive frozen group estimates changed")
    require(sum(x > 0 for x in cross) == 2 and
            sum(x < 0 for x in cross) == 6,
            "frozen cross-sign disagreement changed")

    # There are 16 chains per group and 150 retained records per chain.  Every
    # J visit fraction is exactly an integer multiple of 1/16, hence every
    # group visit total is an integer multiple of a complete chain history.
    # Aggregate totals alone cannot logically identify each chain's path, but
    # this complete chain-granularity, across all groups, supplies no evidence
    # of within-chain movement between the umbrella strata and is a trapping
    # diagnostic.  The run serialized no transition counts or ESS to rebut it.
    chains_per_group = 16
    retained_per_chain = 150
    j_chain_equivalents = [x * chains_per_group for x in jvisit]
    require(all(x == x.to_integral_value() for x in j_chain_equivalents),
            "J visits are no longer chain-granular")
    require(j_chain_equivalents == [
        Decimal(4), Decimal(3), Decimal(1), Decimal(2),
        Decimal(4), Decimal(4), Decimal(1), Decimal(4)],
        "frozen J chain-equivalent visit inventory changed")

    i_ratio = max(ip) / min(ip)
    diagonal_ratio = max(diagonal) / min(diagonal)
    q_range = max(qgroup) - min(qgroup)
    require(i_ratio > 38 and diagonal_ratio > 2900 and q_range > 1.34 and
            se > Decimal("0.16"),
            "expected frozen instability no longer present")

    never = raw.get("never_implies")
    require(isinstance(never, list) and set(never) >= {
        "an exact quotient", "Proposition 1", "H1<=236"},
        "negative theorem scope is incomplete")

    return {
        "status": "AUDIT FAIL",
        "scope": "umbrella MCMC artifact as evidence for a capped sign",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "formula_level_status": "SEARCH-INSTRUMENT PASS",
        "replay": {
            "all_group_2x2_roots_recomputed": True,
            "pooled_2x2_root_recomputed": True,
            "reported_pooled_q": raw["estimated_top_quotient"],
            "reported_group_standard_error":
                raw["group_quotient_standard_error"],
        },
        "pathologies": {
            "group_I_max_over_min": str(i_ratio),
            "group_J_diagonal_max_over_min": str(diagonal_ratio),
            "group_cross_signs_positive_negative": [2, 6],
            "group_q_min": str(min(qgroup)),
            "group_q_max": str(max(qgroup)),
            "group_q_range": str(q_range),
            "J_visit_chain_equivalents": [
                str(x) for x in j_chain_equivalents],
            "chains_per_group": chains_per_group,
            "retained_records_per_chain": retained_per_chain,
            "serialized_transition_counts": False,
            "serialized_effective_sample_sizes": False,
            "serialized_raw_group_numerators_denominators": False,
        },
        "statistically_unusable": [
            "the pooled quotient sign (reported below one)",
            "all individual group quotient signs",
            "the unweighted group-root standard error as an uncertainty bound",
            "the J common-count occupancy estimates without mixing evidence",
            "any exact-stage go/no-go decision based on this run",
        ],
        "decision": (
            "the code's change-of-measure and pooling formulas passed the "
            "separate source audit, but this frozen run is trapped/unstable "
            "and supplies no reliable sign evidence; it cannot authorize or "
            "veto an exact capped calculation"),
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
