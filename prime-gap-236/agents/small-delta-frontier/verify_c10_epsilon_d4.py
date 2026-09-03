#!/usr/bin/env python3
"""Fail-closed audit of the C10 epsilon_s=7/2000, no-ones D4 run.

This checker performs no integration.  It pins and cross-compares the exact
pair-matrix contraction and the independently grouped fixed-vector
contraction, verifies the Definition-1 parameter arithmetic, and compares the
particular-vector quotient exactly with the earlier epsilon_s=1/200 D4
particular-vector certificate.  Generalized-eigenvalue optimality is
deliberately not certified.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, getcontext
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PATHS = {
    "new": HERE / "c10_eps0035_noones_D4_robust.json",
    "grouped": HERE / "c10_eps0035_noones_D4_grouped_exact.json",
    "basis": ROOT / "agents/exact-integrator/results/c10_fullsimplex_k48_noones_D4.json",
    "schedule": ROOT / "agents/exact-integrator/results/c10_beta_schedule.json",
    "old": ROOT / "agents/exact-integrator/results/c10_stratum_amplitude_cappedopt_D4_exact.json",
    "old_input": ROOT / "agents/exact-integrator/results/c10_capped_D4_decimal55_vector_input.json",
    "old_discovery": ROOT / "experiments/results/decimal_hb_c10_noones_D4.json",
    "robust_script": ROOT / "agents/exact-integrator/robust_generalized_solve.py",
    "grouped_script": ROOT / "agents/exact-integrator/scheduled_fixed_vector.py",
    "grouped_evaluator": ROOT / "agents/exact-integrator/grouped_fixed_vector.py",
}

EXPECTED_SHA = {
    "new": "7a5e9fd38a3bc46263b9bed3d20b4d69653a30bc36cc6b372e8a9d59bf474938",
    "grouped": "65fc03c97818b867b5d9ba4e3cc2afcb5061d2858d2fe248e6fd759a7caf189b",
    "basis": "ac48820277b68dd5232fd2678a7980d60318b69e60d15d44d9c6eb006fa1ea0d",
    "schedule": "2bf65835289d122d258027e3167be823266824c3575895f58634eb822e45a018",
    "old": "362b2b58938e3fdfdf0afd6916ddabce17cce71aa856795866f5d51f26dcb043",
    "old_input": "2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b",
    "old_discovery": "e879d914f2c183c744476dc59244370898ac5c1f375bcb2529fe20bca2db73c6",
    "robust_script": "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e",
    "grouped_script": "a2127b5edb1fd4287f2e105884dee9db7fcd13a5fc36b7016f01680cbb381928",
    "grouped_evaluator": "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    path = PATHS[name]
    got = sha(path)
    if got != EXPECTED_SHA[name]:
        raise SystemExit(f"{name} SHA mismatch: {got}")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise SystemExit(f"{name} is not a JSON object")
    return value


def main() -> None:
    for name, path in PATHS.items():
        if sha(path) != EXPECTED_SHA[name]:
            raise SystemExit(f"{name} SHA mismatch: {sha(path)}")

    new = load("new")
    grouped = load("grouped")
    basis = load("basis")
    schedule_doc = load("schedule")
    old = load("old")
    old_input = load("old_input")
    load("old_discovery")

    eps = Q(7, 2000)
    A0 = -eps
    A1 = Q(77747, 300000)
    delta = Q(1, 100)
    alpha = A1 + eps
    eta = A1 - eps
    schedule = (Q(3, 20), Q(3, 20), Q(97, 625))
    if (A0, alpha, eta) != (Q(-7, 2000), Q(78797, 300000), Q(76697, 300000)):
        raise SystemExit("endpoint arithmetic failed")
    if alpha + eta != 2 * A1:
        raise SystemExit("epsilon does not cancel in relevant-modulus exponent")

    # Every Definition-1 requirement through k=48, including weak transition
    # equalities and the strict endpoint conditions.
    margins = {
        "epsilon": eps,
        "A1_minus_A0": A1 - A0,
        "half_minus_epsilon_minus_A1": Q(1, 2) - eps - A1,
        "delta": delta,
        "B1_minus_delta": schedule[0] - delta,
        "B3_minus_delta": schedule[2] - delta,
        "B2_minus_B1": schedule[1] - schedule[0],
        "B1_plus_delta_minus_B2": schedule[0] + delta - schedule[1],
        "B3_minus_B2": schedule[2] - schedule[1],
        "B2_plus_delta_minus_B3": schedule[1] + delta - schedule[2],
        "B4_minus_B3": Q(0),
        "B3_plus_delta_minus_B4": delta,
        "m15_delta_reserve": schedule[2] - 15 * delta,
        "m16_empty_reserve": 16 * delta - schedule[2],
        "one_minus_2A1": 1 - 2 * A1,
    }
    strict = (
        "epsilon", "A1_minus_A0", "half_minus_epsilon_minus_A1",
        "delta", "B1_minus_delta", "B3_minus_delta",
        "B1_plus_delta_minus_B2", "B3_minus_B2",
        "B2_plus_delta_minus_B3", "B3_plus_delta_minus_B4",
        "m15_delta_reserve", "m16_empty_reserve", "one_minus_2A1",
    )
    if any(margins[key] <= 0 for key in strict):
        raise SystemExit("a strict Definition-1/support margin is nonpositive")
    if margins["B2_minus_B1"] != 0 or margins["B4_minus_B3"] != 0:
        raise SystemExit("expected permitted weak transition equalities failed")
    B = lambda m: schedule[min(m, 3) - 1]
    for m in range(1, 48):
        if not (delta < B(m) <= B(m + 1) <= B(m) + delta):
            raise SystemExit(f"Definition-1 B transition failed at {m}")
    active = [m for m in range(1, 49) if m * delta <= B(m)]
    if active != list(range(1, 16)):
        raise SystemExit(f"unexpected active counts: {active}")

    expected_parameters = {
        "alpha": str(alpha), "delta": str(delta), "eta": str(eta)
    }
    if new.get("status") != "robust-decimal-discovery-exact-rational-vector":
        raise SystemExit("wrong robust result status")
    if new.get("k") != 48 or new.get("basis_dimension") != 12:
        raise SystemExit("wrong k or dimension")
    if new.get("parameters") != expected_parameters:
        raise SystemExit("wrong new geometry")
    if new.get("beta_schedule") != [str(x) for x in schedule]:
        raise SystemExit("wrong new cap schedule")
    if new.get("source_basis_sha256") != EXPECTED_SHA["basis"]:
        raise SystemExit("basis provenance mismatch")
    if new.get("schedule_file_sha256") != EXPECTED_SHA["schedule"]:
        raise SystemExit("schedule provenance mismatch")
    if new.get("script_sha256") != EXPECTED_SHA["robust_script"]:
        raise SystemExit("robust producer provenance mismatch")
    if new.get("integrator_sha256") != "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52":
        raise SystemExit("integrator provenance mismatch")
    if new.get("matrix_sha256") != "868307f366effe807c70532463b923b94a80193903b885ab36bd311607f33fc4":
        raise SystemExit("matrix SHA mismatch")
    if new.get("cache_hits") != 0 or new.get("cache_misses") != 78:
        raise SystemExit("matrix traversal count mismatch")
    if new.get("eigenvalue_claim_rigorous") is not False or new.get("particular_vector_forms_rigorous") is not True:
        raise SystemExit("rigor flags are misstated")
    if new.get("basis") != basis.get("basis") or len(new.get("rational_vector", [])) != 12:
        raise SystemExit("basis/vector mismatch")
    solves = new.get("cross_precision_solves")
    if not isinstance(solves, list) or [x.get("precision") for x in solves] != [160, 240]:
        raise SystemExit("cross-precision solve record mismatch")

    if grouped.get("status") != "exact-scheduled-grouped-fixed-vector" or grouped.get("rigorous") is not True:
        raise SystemExit("grouped evaluation is not marked exact")
    if grouped.get("input_sha256") != EXPECTED_SHA["new"]:
        raise SystemExit("grouped input provenance mismatch")
    if grouped.get("script_sha256") != EXPECTED_SHA["grouped_script"] or grouped.get("grouped_evaluator_sha256") != EXPECTED_SHA["grouped_evaluator"]:
        raise SystemExit("grouped producer provenance mismatch")
    if grouped.get("integrator_sha256") != new.get("integrator_sha256"):
        raise SystemExit("integrator mismatch between contractions")
    if grouped.get("parameters") != expected_parameters or grouped.get("beta_schedule") != [str(x) for x in schedule]:
        raise SystemExit("grouped support mismatch")
    if grouped.get("i_orbit_groups") != 20 or grouped.get("i_faces") != 312 or grouped.get("marginal_components") != 19 or grouped.get("j_branch_integrals") != 1496:
        raise SystemExit("grouped traversal count mismatch")

    pair_I = Q(new["exact_denominator"])
    pair_N = Q(new["exact_numerator"])
    group_I = Q(grouped["denominator"])
    group_N = Q(grouped["numerator"])
    if (pair_I, pair_N) != (group_I, group_N):
        raise SystemExit("independent exact contractions disagree")
    if pair_I <= 0 or pair_N - pair_I >= 0:
        raise SystemExit("unexpected sign of exact D4 forms")
    if Q(new["exact_quotient"]) != pair_N / pair_I or Q(new["exact_margin"]) != pair_N - pair_I:
        raise SystemExit("new serialized quotient/margin mismatch")

    # Earlier epsilon_s=1/200 particular-vector certificate.  Its baseline
    # forms were reconstructed by the stratum-block and direct evaluators.
    if old.get("input_sha256") != EXPECTED_SHA["old_input"] or old.get("block_direct_bitwise_equal") is not True:
        raise SystemExit("old exact baseline provenance/equality failed")
    if old_input.get("basis") != basis.get("basis") or old_input.get("k") != 48:
        raise SystemExit("old basis does not match")
    if old.get("parameters") != {
        "alpha": "79247/300000", "delta": "1/100", "eta": "76247/300000",
        "beta1": "3/20", "beta2": "3/20", "beta3plus": "97/625",
    }:
        raise SystemExit("old geometry mismatch")
    old_q = Q(old["baseline_quotient"])
    if old_q != Q(old["baseline_numerator"]) / Q(old["baseline_denominator"]):
        raise SystemExit("old exact baseline quotient mismatch")
    new_q = pair_N / pair_I
    gain = new_q - old_q
    if gain <= 0:
        raise SystemExit("epsilon variation did not give the expected exact D4 gain")

    getcontext().prec = 60
    dec = lambda x: str(Decimal(x.numerator) / Decimal(x.denominator))
    print("C10 EPSILON D4 AUDIT PASS")
    print("claim_scope=exact particular-vector forms; eigenvalue optimality non-rigorous; no D12 inference")
    print(f"new_artifact_sha256={EXPECTED_SHA['new']}")
    print(f"grouped_artifact_sha256={EXPECTED_SHA['grouped']}")
    print("matrix_sha256=868307f366effe807c70532463b923b94a80193903b885ab36bd311607f33fc4")
    print(f"new_quotient_decimal={dec(new_q)}")
    print(f"new_shortfall_decimal={dec(1-new_q)}")
    print(f"old_quotient_decimal={dec(old_q)}")
    print(f"exact_gain_decimal={dec(gain)}")
    print(f"exact_gain={gain}")
    for key, value in margins.items():
        print(f"margin_{key}={value}")


if __name__ == "__main__":
    main()
