#!/usr/bin/env python3
"""Independent fail-closed checker for the frozen one-band D18 H^2 screen."""

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
                 "active25_d18_truncated_one_band_h2_bridge_v1.py")
BRIDGE_TEST = REPO / ("agents/structural-basis/tests/"
                      "test_active25_d18_truncated_one_band_h2_bridge_v1.py")
ENGINE = REPO / "agents/structural-basis/code/active25_d18_h2_bridge_v1.py"
CERT = REPO / ("agents/exact-integrator/results/"
               "aquarter_fullsimplex_k48_B18_refined_exact.json")
ANALYTIC_CHECKER = REPO / (
    "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py")
ANALYTIC_RESULT = REPO / (
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json")
ANALYTIC_TEST = REPO / (
    "agents/analytic-new-lever/test_truncated_lower_energy_v3.py")
RUNS = (
    REPO / ("agents/structural-basis/results/"
            "active25_d18_truncated_one_band_h2_bridge_seed2361817_v1.json"),
    REPO / ("agents/structural-basis/results/"
            "active25_d18_truncated_one_band_h2_bridge_seed2361818_v1.json"),
)
PINS = {
    BRIDGE: "1e15d2a568c497586389ec7b3dd7e336f05e9a2d0b3583345194a13221ee55e0",
    BRIDGE_TEST: "117005d3c60a78c995b5b580e75b698608e926d07fac7b851e20148541108db9",
    ENGINE: "2d262e1ea4a1ea20f42ea03cb8c8bc6405ae75b8f94cc1db668dfeb0797dfe1b",
    CERT: "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58",
    ANALYTIC_CHECKER:
        "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5",
    ANALYTIC_RESULT:
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    ANALYTIC_TEST:
        "9b0e1409ef4ea2dda1292a69881c344a35d52f4886f0568c0e8a71f806d0b1fa",
    RUNS[0]: "d3936a661c4320268a4b61e75b6a039ba7af13ee7ac0dfd45c7a8f248adffbd3",
    RUNS[1]: "9692feb0a4ae92e8eb52fb2ad6a3e4db7e9ec7a230a3997ce043798859a9696d",
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


def check():
    starts = {}
    for path, expected in PINS.items():
        payload = path.read_bytes()
        if sha256(payload) != expected:
            raise RuntimeError(f"frozen one-band bridge input changed: {path}")
        starts[path] = payload
    cert = strict_json(CERT)
    if (cert.get("format") != "bv-even-exact-vector-v1" or
            (cert.get("k"), cert.get("degree")) != (48, 18)):
        raise ValueError("inner D18 certificate identity changed")
    inner_i = Q(cert["exact_denominator"])
    inner_48j = Q(cert["exact_numerator"])
    deficit = inner_i - inner_48j
    if deficit <= 0:
        raise ArithmeticError("inner deficit must be positive")
    rows = [strict_json(path) for path in RUNS]
    estimates = []
    errors = []
    for row, seed in zip(rows, (2361817, 2361818)):
        screen = row.get("screen", {})
        calibration = row.get("mcmc_calibration", {})
        one_band = row.get("parameters", {}).get("one_band", {})
        if (row.get("format") !=
                "active25-d18-truncated-one-band-h2-bridge-v1" or
                row.get("status") != "H2-BRIDGE HEURISTIC CALIBRATED" or
                row.get("source_sha256") != PINS[BRIDGE] or
                row.get("engine_source_sha256") != PINS[ENGINE] or
                row.get("schedule", {}).get("seed") != seed or
                row.get("schedule", {}).get("workers") != 1 or
                one_band.get("low") != "103/400" or
                one_band.get("high") != "9500917/36000000" or
                one_band.get("eta_UV") != "8960917/36000000" or
                one_band.get("active_counts") != list(range(13)) or
                one_band.get("first_empty_count") != 13 or
                calibration.get("mixing_pass") is not True or
                calibration.get("cross_pass") is not True or
                calibration.get("radial_band_calibration", {}).get(
                    "every_chain_visits_both_bands") is not True or
                screen.get(
                    "screen_is_directly_comparable_to_single_band_threshold")
                    is not True or
                row.get("launch_authorized") is not False or
                row.get("exact_target_started") is not False or
                row.get("resume_supported") is not False):
            raise ValueError("one-band bridge result failed closure checks")
        estimate = screen["one_band_capped_G_norm_over_inner_I"]
        error = screen["one_band_capped_G_norm_standard_error"]
        if (type(estimate) is not float or type(error) is not float or
                not math.isfinite(estimate) or not math.isfinite(error) or
                estimate <= 0 or error <= 0):
            raise ValueError("invalid one-band finite-chain estimate")
        estimates.append(estimate)
        errors.append(error)
    weights = [1 / (error * error) for error in errors]
    combined = sum(value * weight for value, weight in zip(
        estimates, weights)) / sum(weights)
    combined_se = math.sqrt(1 / sum(weights))
    exact_threshold = deficit / inner_i
    if any(path.read_bytes() != payload for path, payload in starts.items()):
        raise RuntimeError("frozen one-band bridge inputs changed during check")
    return {
        "format": "active25-d18-truncated-one-band-h2-bridge-check-v1",
        "status": "INDEPENDENT HEURISTIC SCREEN CHECK PASS",
        "rigorous": False,
        "source_sha256": sha256(FILE),
        "input_sha256": {str(path.relative_to(REPO)): digest
                          for path, digest in PINS.items()},
        "exact_single_band_criterion": {
            "definitions": "A=I(H), b=48J(F,H), D=I(F)-48J(F,F)",
            "absolute": "b^2/A > D",
            "normalized": "(b/I(F))^2/(A/I(F)) > D/I(F)",
            "inner_I": str(inner_i),
            "inner_48J": str(inner_48j),
            "inner_deficit": str(deficit),
            "inner_deficit_over_I": str(exact_threshold),
            "inner_deficit_over_I_decimal": float(exact_threshold),
            "exact_riesz_specialization": (
                "for H=G_F*1_V, b=A, hence I(G_F*1_V)/I(F)>D/I(F)"),
            "factor_48_note": "b already contains 48; apply no further factor",
        },
        "finite_chain_screen": {
            "seed_estimates": estimates,
            "seed_standard_errors": errors,
            "inverse_variance_combined": combined,
            "naive_combined_standard_error": combined_se,
            "combined_minus_exact_threshold": combined - float(exact_threshold),
            "combined_minus_threshold_in_naive_SE": (
                combined - float(exact_threshold)) / combined_se,
            "decision": "STRONG HEURISTIC NEGATIVE; DO NOT LAUNCH D18 EXACT TARGET",
            "not_a_rigorous_upper_bound": True,
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
