#!/usr/bin/env python3
"""Freeze the two-seed D12/D14/D16 one-band projection screen."""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
SCREEN = FILE.with_name("active25_d19_lower_degree_projection_bridge_v1.py")
SCREEN_SHA256 = "82a9a357d6605faa349c830d56b410cb7bd5c45f2b2ab05d81754ed55b8a84a7"
SCREEN_TEST = REPO / (
    "agents/structural-basis/tests/"
    "test_active25_d19_lower_degree_projection_bridge_v1.py")
SCREEN_TEST_SHA256 = "8207f7d2c5066b7720e8126fff43e1a24f2628bd4a73d25118170772d79ec41a"
RESULTS = (
    (REPO / "agents/structural-basis/results/active25_d19_lower_degree_projection_seed2361817_v1.json",
     "9104c3dddd40a4b508d7dc49340dd2c2fff0d12bec84a6b5837dd9fb887d3199",
     2361817, 67.94, 337024),
    (REPO / "agents/structural-basis/results/active25_d19_lower_degree_projection_seed2361818_v1.json",
     "0c020286f2abb92c73c9c209ae46095cd0e862231c5b40215b12c2c5ec1423de",
     2361818, 63.09, 337060),
)
LOWER_EXACT = REPO / (
    "agents/structural-basis/results/bv_D12_D14_D16_vectors_direct_exact_v1.json")
LOWER_EXACT_SHA256 = "77884ae1197beace517fd758323e53b92d4cc8ef055ddf873ae4cd858625dbe4"
NAMES = ("D12", "D14", "D16")
IDEAL_CONSERVATIVE_FLOOR = 0.020


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json(path):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key {key!r} in {path}")
            answer[key] = value
        return answer
    return json.loads(
        Path(path).read_bytes(), object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token {token!r} in {path}")))


def ivw(rows, value_key, error_key):
    values = [(float(row[value_key]), float(row[error_key])) for row in rows]
    if any(not (math.isfinite(value) and math.isfinite(error) and error > 0)
           for value, error in values):
        raise ValueError("invalid IVW input")
    weights = [1 / (error * error) for _, error in values]
    return (sum(value * weight for (value, _), weight in zip(values, weights)) /
            sum(weights), 1 / math.sqrt(sum(weights)))


def validate_row(data, seed):
    schedule = data.get("schedule", {})
    calibrations = (
        data.get("point_evaluator_calibration", {}),
        data.get("marginal_antiderivative_calibration", {}),
        data.get("target_point_evaluator_calibration", {}),
        data.get("target_marginal_antiderivative_calibration", {}),
    )
    mcmc = data.get("mcmc_calibration", {})
    if (data.get("format") !=
            "active25-d19-lower-degree-projection-bridge-v1" or
            data.get("status") !=
            "H2-BRIDGE HEURISTIC CALIBRATED; CACHE-FREE EXACT INNER FORMS" or
            data.get("source_sha256") != SCREEN_SHA256 or
            data.get("launch_authorized") is not False or
            data.get("exact_target_started") is not False or
            data.get("resume_supported") is not False or
            schedule != {"burn": 4000, "chains": 8,
                         "draws_per_chain": 6000, "seed": seed,
                         "workers": 1} or
            not all(item.get("pass") is True for item in calibrations) or
            mcmc.get("mixing_pass") is not True or
            mcmc.get("cross_pass") is not True or
            data.get("lower_degree_exact_reconstruction", {}).get("sha256") !=
                LOWER_EXACT_SHA256 or
            set(data.get("lower_degree_natural_projections", {})) != set(NAMES)):
        raise ValueError(f"projection result identity/calibration mismatch: {seed}")
    return data


def build():
    snapshots = {path: path.read_bytes() for path in
                 (FILE, SCREEN, SCREEN_TEST, LOWER_EXACT)}
    if sha256(snapshots[SCREEN]) != SCREEN_SHA256:
        raise RuntimeError("pinned screen source changed")
    if sha256(snapshots[SCREEN_TEST]) != SCREEN_TEST_SHA256:
        raise RuntimeError("pinned screen tests changed")
    if sha256(snapshots[LOWER_EXACT]) != LOWER_EXACT_SHA256:
        raise RuntimeError("pinned lower-degree exact reconstruction changed")
    data = []
    result_snapshots = {}
    external = []
    for path, expected, seed, wall, rss in RESULTS:
        raw = path.read_bytes()
        result_snapshots[path] = raw
        if sha256(raw) != expected:
            raise RuntimeError(f"projection result changed: {path}")
        data.append(validate_row(strict_json(path), seed))
        external.append({
            "seed": seed, "elapsed_wall_seconds_usr_bin_time": wall,
            "maximum_resident_set_kib_usr_bin_time": rss,
        })
    exact_threshold = Q(data[0]["screen"]["exact_sufficient_threshold"])
    if (any(Q(row["screen"]["exact_sufficient_threshold"]) != exact_threshold
            for row in data) or
            any(abs(row["screen"]["sufficient_threshold"] -
                    float(exact_threshold)) > 1e-18 for row in data)):
        raise ArithmeticError("D19 threshold changed between seeds")

    candidates = {}
    for name in NAMES:
        rows = [row["lower_degree_natural_projections"][name] for row in data]
        projection, projection_se = ivw(
            rows, "projected_energy_over_inner_I",
            "projected_energy_over_inner_I_delta_standard_error")
        a_mean, a_se = ivw(rows, "A_over_inner_I",
                           "A_over_inner_I_standard_error")
        b_mean, b_se = ivw(rows, "b_over_inner_I",
                           "b_over_inner_I_standard_error")
        difference, difference_se = ivw(
            rows, "CRN_difference_from_natural_D19_projection",
            "CRN_difference_standard_error")
        lower3 = projection - 3 * projection_se
        inventory = rows[0]["exact_b_global_collection_inventory"]
        if (any(row["candidate_sha256"] != rows[0]["candidate_sha256"] or
                row["exact_A_square_product_groups"] !=
                    rows[0]["exact_A_square_product_groups"] or
                row["exact_b_global_collection_inventory"] != inventory
                for row in rows[1:])):
            raise ArithmeticError(f"{name} provenance/cost changed between seeds")
        candidates[name] = {
            "candidate_degree": rows[0]["candidate_degree"],
            "candidate_basis_dimension": rows[0]["candidate_basis_dimension"],
            "candidate_path": rows[0]["candidate_path"],
            "candidate_sha256": rows[0]["candidate_sha256"],
            "cache_free_direct_result_sha256": LOWER_EXACT_SHA256,
            "legacy_integrator_source_present_in_current_tree":
                rows[0]["legacy_integrator_source_present_in_current_tree"],
            "provenance_note": rows[0]["provenance_note"],
            "A_over_inner_I_IVW": a_mean,
            "A_over_inner_I_IVW_standard_error": a_se,
            "b_over_inner_I_IVW": b_mean,
            "b_over_inner_I_IVW_standard_error": b_se,
            "projected_energy_over_inner_I_IVW": projection,
            "projected_energy_over_inner_I_IVW_standard_error": projection_se,
            "three_SE_lower_projected_energy": lower3,
            "projected_minus_exact_threshold": projection - float(exact_threshold),
            "three_SE_lower_margin_over_exact_threshold":
                lower3 - float(exact_threshold),
            "CRN_difference_from_natural_D19_IVW": difference,
            "CRN_difference_from_natural_D19_IVW_standard_error": difference_se,
            "per_seed_projected_energy": [
                row["projected_energy_over_inner_I"] for row in rows],
            "per_seed_projection_standard_error": [
                row["projected_energy_over_inner_I_delta_standard_error"]
                for row in rows],
            "exact_A_square_product_groups":
                rows[0]["exact_A_square_product_groups"],
            "exact_b_global_collection_inventory": inventory,
            "passes_exact_threshold_at_three_SE": lower3 > float(exact_threshold),
            "passes_ideal_0p020_floor_at_three_SE":
                lower3 > IDEAL_CONSERVATIVE_FLOOR,
        }

    baselines = {}
    for name in ("natural_D19_projection", "natural_D18_proposal_projection"):
        rows = [row[name] for row in data]
        value, error = ivw(
            rows, "projected_energy_over_inner_I",
            "projected_energy_over_inner_I_delta_standard_error")
        baselines[name] = {
            "projected_energy_over_inner_I_IVW": value,
            "projected_energy_over_inner_I_IVW_standard_error": error,
            "three_SE_lower_projected_energy": value - 3 * error,
        }

    eligible = [name for name in NAMES
                if candidates[name]["passes_ideal_0p020_floor_at_three_SE"]]
    chosen = min(
        eligible,
        key=lambda name: candidates[name]["exact_b_global_collection_inventory"]
            ["global_canonical_b_keys_before_coefficient_cancellation"],
        default=None)
    if chosen != "D14":
        raise ArithmeticError("prespecified conservative selection changed")
    selection = {
        "chosen_candidate": chosen,
        "rule": (
            "require the independent-seed IVW projection minus three naive "
            "chain-SE to exceed both the exact D19 deficit and 0.020; then "
            "minimize global canonical b-key inventory"),
        "chosen_projected_energy_over_inner_I": candidates[chosen]
            ["projected_energy_over_inner_I_IVW"],
        "chosen_projection_standard_error": candidates[chosen]
            ["projected_energy_over_inner_I_IVW_standard_error"],
        "chosen_three_SE_lower_projected_energy": candidates[chosen]
            ["three_SE_lower_projected_energy"],
        "chosen_three_SE_lower_margin_over_threshold": candidates[chosen]
            ["three_SE_lower_margin_over_exact_threshold"],
        "chosen_A_square_product_groups": candidates[chosen]
            ["exact_A_square_product_groups"],
        "chosen_global_b_keys": candidates[chosen]
            ["exact_b_global_collection_inventory"]
            ["global_canonical_b_keys_before_coefficient_cancellation"],
        "screen_is_heuristic_not_a_bound": True,
        "exact_launch_authorized": False,
    }
    if (any(path.read_bytes() != payload for path, payload in snapshots.items()) or
            any(path.read_bytes() != payload
                for path, payload in result_snapshots.items())):
        raise RuntimeError("aggregate source closure changed")
    return {
        "format": "active25-d19-lower-degree-projection-aggregate-v1",
        "status": "CALIBRATED LOWER-DEGREE PROJECTION SCREEN PASS; D14 EXACT STAGE GATED",
        "rigorous": False,
        "calibrated": True,
        "independent_seeds": [item[2] for item in RESULTS],
        "common_random_numbers_within_each_seed": True,
        "schedule_per_seed": {"chains": 8, "burn": 4000,
                              "draws_per_chain": 6000, "workers": 1},
        "exact_single_band_criterion": {
            "A": "I(H)", "b": "48J(F,H)",
            "deficit": "I(F)-48J(F,F)",
            "sufficient_inequality": "b^2/A > I(F)-48J(F,F)",
            "normalized_inequality":
                "(b/I(F))^2/(A/I(F)) > 1-48J(F,F)/I(F)",
            "factor_48_note": "b already includes 48; no extra factor",
            "exact_D19_normalized_deficit": str(exact_threshold),
            "exact_D19_normalized_deficit_decimal": float(exact_threshold),
        },
        "candidates": candidates,
        "baselines": baselines,
        "selection": selection,
        "calibration_maxima": {
            "cross_relative_error": max(
                row["mcmc_calibration"]["cross_relative_error"] for row in data),
            "split_Rhat_ratio": max(
                row["mcmc_calibration"]["split_Rhat_ratio"] for row in data),
            "split_Rhat_ratio_squared": max(
                row["mcmc_calibration"]["split_Rhat_ratio_squared"]
                for row in data),
            "split_Rhat_radial_total": max(
                row["mcmc_calibration"]["split_Rhat_radial_total"]
                for row in data),
            "target_point_relative_error": max(float(
                row["target_point_evaluator_calibration"]
                    ["maximum_relative_error"]) for row in data),
            "target_marginal_relative_error": max(
                row["target_marginal_antiderivative_calibration"]
                    ["maximum_relative_error"] for row in data),
        },
        "external_resource_measurements": external,
        "provenance_note": (
            "D12/D14 legacy producer source hashes are not present as the "
            "current integrator; their explicit rational vectors were therefore "
            "reconstructed cache-free under the pinned current recurrence. D16 "
            "was cache-discovered but its particular forms were likewise rebuilt "
            "without cache or serialized matrix entries."),
        "source_sha256": sha256(snapshots[FILE]),
        "source_hashes": {
            str(SCREEN.relative_to(REPO)): SCREEN_SHA256,
            str(SCREEN_TEST.relative_to(REPO)): SCREEN_TEST_SHA256,
            str(LOWER_EXACT.relative_to(REPO)): LOWER_EXACT_SHA256,
            **{str(path.relative_to(REPO)): expected
               for path, expected, _, _, _ in RESULTS},
        },
        "launch_authorized": False,
        "exact_target_started": False,
        "resume_supported": False,
        "theorem_ready": False,
    }


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build()
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"],
        "output_sha256": sha256(payload),
        "selection": result["selection"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
