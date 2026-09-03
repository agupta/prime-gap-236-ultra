#!/usr/bin/env python3
"""Calibrated D18 H^2 bridge for the verified truncated one-band support.

The frozen v1 bridge engine samples the old d=1/60 full outer shell from a
known, exactly normalized natural-D18 ``h^2`` density.  This wrapper uses that
same proposal and exact cross calibration, but evaluates ``G_F`` with the
verified one-band cutoff and retains only the truncated radial band and its
sorted-removal count cap.  The proposal polynomial is merely an importance
sampling device; the reported capped quantity is ``I(G_F 1_V)/I(F)``.

This is a bounded numerical discovery screen.  It has no exact producer,
resume action, or launch authorization.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
ENGINE = FILE.with_name("active25_d18_h2_bridge_v1.py")
ENGINE_SHA256 = (
    "2d262e1ea4a1ea20f42ea03cb8c8bc6405ae75b8f94cc1db668dfeb0797dfe1b")
CHECKER = REPO / "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py"
CHECKER_SHA256 = (
    "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5")
RESULT = REPO / "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json"
RESULT_SHA256 = (
    "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f")
ANALYTIC_TEST = REPO / "agents/analytic-new-lever/test_truncated_lower_energy_v3.py"
ANALYTIC_TEST_SHA256 = (
    "9b0e1409ef4ea2dda1292a69881c344a35d52f4886f0568c0e8a71f806d0b1fa")

GEOMETRY = "d1over60_truncated_one_band_verified_v3"
ALPHA1 = Q(103, 400)
ALPHA2 = Q(9500917, 36000000)
ETA = Q(8960917, 36000000)
DELTA = Q(1, 60)
SCHEDULE_HEAD = tuple(Q(x, 1_000_000) for x in (
    140375, 157041, 168544, 174338, 185488, 190375,
    193097, 197146, 202047, 207090, 211668, 211668))
SCHEDULE = SCHEDULE_HEAD + (SCHEDULE_HEAD[-1],) * (48 - len(SCHEDULE_HEAD))
MAX_WALL_SECONDS = 180
MAX_RSS_BYTES = 512 * 1024 * 1024


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


def load(name, path, expected):
    if sha256(path) != expected:
        raise RuntimeError(f"pinned one-band bridge dependency changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_support():
    for path, expected in ((CHECKER, CHECKER_SHA256),
                           (RESULT, RESULT_SHA256),
                           (ANALYTIC_TEST, ANALYTIC_TEST_SHA256)):
        if sha256(path) != expected:
            raise RuntimeError(f"pinned analytic one-band input changed: {path}")
    data = strict_json(RESULT)
    parameters = data.get("parameters", {})
    definition5 = data.get("definition5_single_outer_band", {})
    schedule = tuple(Q(x) for x in parameters.get(
        "outer_schedule_through_first_empty", ()))
    if (data.get("status") !=
            "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS" or
            data.get("checker_sha256") != CHECKER_SHA256 or
            parameters.get("k") != 48 or
            parameters.get("delta") != str(DELTA) or
            parameters.get("A") != [
                "-3/400", "1/4", "9230917/36000000"] or
            parameters.get("alpha") != [str(ALPHA1), str(ALPHA2)] or
            parameters.get("outer_width_fraction_of_old_outer") != "37/40" or
            parameters.get("outer_active_counts") != list(range(13)) or
            schedule != SCHEDULE_HEAD or
            definition5.get("eta_inner_inner") != "97/400" or
            definition5.get("eta_inner_outer") != str(ETA) or
            definition5.get("eta_outer_outer") != str(ETA)):
        raise ValueError("verified truncated one-band geometry mismatch")
    if not (all(SCHEDULE[r - 1] > r * DELTA for r in range(1, 13)) and
            SCHEDULE[12] <= 13 * DELTA):
        raise ArithmeticError("one-band active-count boundary changed")
    return data


def one_band_geometry(_module):
    validate_support()
    return {
        # The engine calls this the lower radial band.  There is deliberately
        # no accepted upper band in this wrapper.
        "boundary": ALPHA2,
        "lower_eta_sensitivity": ETA,
        "lower_schedule": SCHEDULE,
        "upper_schedule": (Q(0),) * 48,
        "result_sha256": RESULT_SHA256,
        "checker_sha256": CHECKER_SHA256,
    }


def one_band_cap_membership(module, counts, large_sums, *, geometry,
                            totals=None, band_geometry=None):
    if geometry != GEOMETRY or totals is None or band_geometry is None:
        raise ValueError("one-band membership geometry mismatch")
    radial = totals <= module.ld(ALPHA2)
    count_cap = engine.schedule_membership(
        module, counts, large_sums, SCHEDULE)
    return radial & count_cap


def configure_engine():
    global engine
    engine = load("active25_d18_h2_bridge_engine", ENGINE, ENGINE_SHA256)
    # Reuse the audited old-full-shell proposal and its exact contraction,
    # while replacing only the band/cap observer with the pinned one-band
    # geometry.  The engine's internal closure check now also binds the new
    # checker and result paths through these constants.
    engine.TWO_BAND_GEOMETRY = GEOMETRY
    engine.TWO_BAND_CHECKER = CHECKER
    engine.TWO_BAND_CHECKER_SHA256 = CHECKER_SHA256
    engine.TWO_BAND_RESULT = RESULT
    engine.TWO_BAND_RESULT_SHA256 = RESULT_SHA256
    engine.two_band_geometry = one_band_geometry
    engine.cap_membership = one_band_cap_membership
    return engine


engine = None


def run(*, seed, chains, burn, draws):
    start = {path: path.read_bytes() for path in
             (FILE, ENGINE, CHECKER, RESULT, ANALYTIC_TEST)}
    validate_support()
    bridge = configure_engine()
    row = bridge.run(geometry=GEOMETRY, seed=seed, chains=chains,
                     burn=burn, draws=draws, cap_result=None)
    if any(path.read_bytes() != payload for path, payload in start.items()):
        raise RuntimeError("one-band bridge source closure changed during run")
    lower = row["screen"]["by_radial_band"]["lower_outer"]
    if abs(row["screen"]["capped_G_norm_over_inner_I"] -
           lower["capped_G_norm_over_inner_I"]) > 1e-18:
        raise ArithmeticError("radially truncated cap energy mismatch")
    row["format"] = "active25-d18-truncated-one-band-h2-bridge-v1"
    row["source_sha256"] = sha256(start[FILE])
    row["engine_source_sha256"] = ENGINE_SHA256
    row["parameters"]["proposal_full_shell"] = {
        "alpha1": str(ALPHA1),
        "alpha2": "237991/900000",
        "eta_for_exact_cross_calibration": "224491/900000",
        "purpose": "exactly normalized old natural-D18 h^2 importance density",
    }
    row["parameters"]["one_band"] = {
        "low": str(ALPHA1), "high": str(ALPHA2), "eta_UV": str(ETA),
        "schedule": [str(x) for x in SCHEDULE],
        "active_counts": list(range(13)), "first_empty_count": 13,
        "analytic_result_sha256": RESULT_SHA256,
        "analytic_checker_sha256": CHECKER_SHA256,
        "analytic_test_sha256": ANALYTIC_TEST_SHA256,
    }
    row["parameters"].pop("two_band", None)
    row["screen"]["one_band_uncapped_by_count_cap_G_norm_over_inner_I"] = \
        lower["G_norm_over_inner_I"]
    row["screen"]["one_band_uncapped_by_count_cap_standard_error"] = \
        lower["G_norm_standard_error"]
    row["screen"]["one_band_capped_G_norm_over_inner_I"] = \
        lower["capped_G_norm_over_inner_I"]
    row["screen"]["one_band_capped_G_norm_standard_error"] = \
        lower["capped_G_norm_standard_error"]
    row["screen"]["exact_single_band_sufficient_criterion"] = (
        "I(G_F*1_V)/I(F) > 1-48J(F,F)/I(F)")
    row["screen"]["screen_is_directly_comparable_to_single_band_threshold"] = True
    row["source_hashes"][str(ENGINE.relative_to(REPO))] = ENGINE_SHA256
    row["source_hashes"][str(CHECKER.relative_to(REPO))] = CHECKER_SHA256
    row["source_hashes"][str(RESULT.relative_to(REPO))] = RESULT_SHA256
    row["source_hashes"][str(ANALYTIC_TEST.relative_to(REPO))] = \
        ANALYTIC_TEST_SHA256
    row["launch_authorized"] = False
    row["exact_target_started"] = False
    row["resume_supported"] = False
    return row


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


def apply_limits():
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    new_hard = hard if hard != resource.RLIM_INFINITY else MAX_RSS_BYTES
    resource.setrlimit(resource.RLIMIT_AS,
                       (min(MAX_RSS_BYTES, new_hard), new_hard))
    signal.alarm(MAX_WALL_SECONDS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--chains", type=int, default=8)
    parser.add_argument("--burn", type=int, default=4000)
    parser.add_argument("--draws", type=int, default=6000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    apply_limits()
    row = run(seed=args.seed, chains=args.chains,
              burn=args.burn, draws=args.draws)
    payload = canonical_json(row)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload), "status": row["status"],
        "one_band_s_over_I": row["screen"][
            "one_band_capped_G_norm_over_inner_I"],
        "one_band_standard_error": row["screen"][
            "one_band_capped_G_norm_standard_error"],
        "threshold": row["screen"]["sufficient_threshold"],
        "wall_seconds": row["wall_seconds"],
        "peak_rss_kib": row["peak_rss_kib"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
