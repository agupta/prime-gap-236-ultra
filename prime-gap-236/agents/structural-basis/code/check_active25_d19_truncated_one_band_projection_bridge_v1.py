#!/usr/bin/env python3
"""Independent fail-closed checker for the frozen D19 projection screens."""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
BRIDGE = REPO / ("agents/structural-basis/code/"
                 "active25_d19_truncated_one_band_projection_bridge_v1.py")
BRIDGE_TEST = REPO / ("agents/structural-basis/tests/"
                      "test_active25_d19_truncated_one_band_projection_bridge_v1.py")
G2_BRIDGE = REPO / ("agents/structural-basis/code/"
                    "active25_d19_truncated_one_band_h2_bridge_v1.py")
G2_BRIDGE_TEST = REPO / ("agents/structural-basis/tests/"
                         "test_active25_d19_truncated_one_band_h2_bridge_v1.py")
DIRECT_INNER = REPO / "verify/results/bv_D19_krylov20_direct_exact_v1.json"
ANALYTIC_SUPPORT = REPO / (
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json")
RUNS = (
    REPO / ("agents/structural-basis/results/"
            "active25_d19_truncated_one_band_projection_bridge_"
            "seed2361817_v1.json"),
    REPO / ("agents/structural-basis/results/"
            "active25_d19_truncated_one_band_projection_bridge_"
            "seed2361818_v1.json"),
)
PINS = {
    BRIDGE: "132992f8c25ec52228a9bab407d4464cb614917dad43eb3eff6fb9eda7d82ef5",
    BRIDGE_TEST:
        "2150bd54dcb7c129ca5955022b07ca7594874ff8f6ff323e248b7aa414b4ed1d",
    G2_BRIDGE:
        "e1e06fbbc5c79d4708e9adf6911873798bf04368449609a407b41f05cb80bd68",
    G2_BRIDGE_TEST:
        "2669517674b1b080420e94099784948a48abd8e13ebd592102045fe6390423f3",
    DIRECT_INNER:
        "a71b9bacf9fbe9ce21d6d0f3c23eec69baa917c46157c402d2d60e6565517d0b",
    ANALYTIC_SUPPORT:
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    RUNS[0]:
        "bdf356b70ed1dde418cc3d1f16135738bd873a351b7eeb7e221dc98e2d6424b1",
    RUNS[1]:
        "69fb8bb1211f6f584a81f2354d97092199c759e21f5d7d575e7499b67bf225d1",
}


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json(path):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            answer[key] = value
        return answer
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite JSON token: {token}")))


def combine(rows, field, error):
    values = [row[field] for row in rows]
    errors = [row[error] for row in rows]
    weights = [1 / (value * value) for value in errors]
    return {
        "seed_values": values,
        "seed_standard_errors": errors,
        "inverse_variance_combined": sum(
            value * weight for value, weight in zip(values, weights)) /
            sum(weights),
        "naive_combined_standard_error": math.sqrt(1 / sum(weights)),
    }


def check():
    starts = {}
    for path, expected in PINS.items():
        payload = path.read_bytes()
        if sha256(payload) != expected:
            raise RuntimeError(f"frozen D19 screen input changed: {path}")
        starts[path] = payload
    inner = strict_json(DIRECT_INNER)
    support = strict_json(ANALYTIC_SUPPORT)
    if (inner.get("format") !=
            "bv-rational-vector-cache-free-direct-check-v1" or
            inner.get("status") !=
                "INDEPENDENT EXACT PARTICULAR INNER VECTOR PASS" or
            inner.get("rigorous") is not True or
            inner.get("cache_read") is not False or
            inner.get("serialized_matrix_entries_read") is not False or
            support.get("status") !=
                "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS"):
        raise ValueError("D19 inner/support authority changed")
    inner_i = Q(inner["exact_denominator"])
    inner_48j = Q(inner["exact_numerator"])
    threshold = (inner_i - inner_48j) / inner_i
    if Q(inner["exact_normalized_deficit"]) != threshold:
        raise ArithmeticError("D19 exact threshold mismatch")
    raw_rows = [strict_json(path) for path in RUNS]
    natural19 = []
    natural18 = []
    g2 = []
    count_rows = []
    for row, seed in zip(raw_rows, (2361817, 2361818)):
        calibration = row.get("mcmc_calibration", {})
        target = row.get("target_inner", {})
        if (row.get("format") !=
                "active25-d19-truncated-one-band-projection-bridge-v1" or
                row.get("status") !=
                "H2-BRIDGE HEURISTIC CALIBRATED; CACHE-FREE EXACT INNER FORMS" or
                row.get("source_sha256") != PINS[BRIDGE] or
                row.get("G2_bridge_source_sha256") != PINS[G2_BRIDGE] or
                row.get("schedule", {}).get("seed") != seed or
                row.get("schedule", {}).get("workers") != 1 or
                target.get("cache_free_direct_result_sha256") !=
                    PINS[DIRECT_INNER] or
                target.get("cache_free_direct_result_rigorous") is not True or
                target.get("cache_read_by_direct_checker") is not False or
                target.get("serialized_matrix_entries_read_by_direct_checker")
                    is not False or
                calibration.get("mixing_pass") is not True or
                calibration.get("cross_pass") is not True or
                calibration.get("radial_band_calibration", {}).get(
                    "every_chain_visits_both_bands") is not True or
                row.get("launch_authorized") is not False or
                row.get("exact_target_started") is not False or
                row.get("resume_supported") is not False):
            raise ValueError("D19 projection result failed closure")
        if Q(row["screen"]["exact_sufficient_threshold"]) != threshold:
            raise ArithmeticError("screen used a different D19 threshold")
        for key, destination in (
                ("natural_D19_projection", natural19),
                ("natural_D18_proposal_projection", natural18)):
            projection = row[key]
            a = projection["A_over_inner_I"]
            b = projection["b_over_inner_I"]
            energy = projection["projected_energy_over_inner_I"]
            if (min(a, energy) <= 0 or
                    abs(energy - b * b / a) > 2e-15 or
                    projection["conditional_decision"].startswith("GATED")
                        is not True):
                raise ArithmeticError(f"invalid {key} moment algebra")
            destination.append(projection)
        screen = row["screen"]
        g2.append({
            "value": screen["one_band_capped_G_norm_over_inner_I"],
            "error": screen["one_band_capped_G_norm_standard_error"]})
        count = row["count_radial_low_degree_projection"]
        if (count.get("candidate_coordinate_count") != 130 or
                count.get("retained_coordinate_count") != 60 or
                count.get("pooled_projected_energy_over_inner_I") >=
                    float(threshold)):
            raise ValueError("count/radial supplementary screen changed")
        count_rows.append(count)
    combined_g2 = combine(g2, "value", "error")
    combined19 = combine(natural19, "projected_energy_over_inner_I",
                         "projected_energy_over_inner_I_delta_standard_error")
    combined18 = combine(natural18, "projected_energy_over_inner_I",
                         "projected_energy_over_inner_I_delta_standard_error")
    if (combined19["inverse_variance_combined"] -
            2 * combined19["naive_combined_standard_error"] <=
            float(threshold)):
        raise ArithmeticError("D19 projection no longer clears screen gate")
    if any(path.read_bytes() != payload for path, payload in starts.items()):
        raise RuntimeError("frozen D19 screen inputs changed during check")
    return {
        "format": "active25-d19-truncated-one-band-projection-check-v1",
        "status": "INDEPENDENT D19 PROJECTION SCREEN CHECK PASS",
        "source_sha256": sha256(FILE),
        "input_sha256": {str(path.relative_to(REPO)): digest
                          for path, digest in PINS.items()},
        "exact_inner": {
            "cache_free_direct_verification": True,
            "I": str(inner_i), "48J": str(inner_48j),
            "deficit_over_I": str(threshold),
            "deficit_over_I_decimal": float(threshold),
        },
        "finite_chain_screen": {
            "G2": combined_g2,
            "natural_D19_projection": combined19,
            "natural_D18_proposal_projection": combined18,
            "natural_D19_projection_minus_threshold":
                combined19["inverse_variance_combined"] - float(threshold),
            "natural_D19_projection_margin_in_naive_SE": (
                combined19["inverse_variance_combined"] - float(threshold)) /
                combined19["naive_combined_standard_error"],
            "count_radial_pooled_seed_values": [row[
                "pooled_projected_energy_over_inner_I"] for row in count_rows],
            "decision": "GATED MINIMAL NATURAL-D19 EXACT A,b PLAN WARRANTED",
            "not_a_rigorous_error_bound": True,
        },
        "production_target_started": False,
        "launch_authorized": False,
        "resume_supported": False,
        "theorem_ready": False,
    }


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = canonical_json(check())
    if args.output is not None:
        publish_exclusive(args.output, payload)
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
