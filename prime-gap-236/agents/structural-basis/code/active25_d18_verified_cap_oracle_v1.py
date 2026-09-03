#!/usr/bin/env python3
"""Fail-closed wrapper for the exactly verified delta=1/60 cap schedule.

The bounded numerical core remains byte-frozen.  This wrapper adds only the
analytically verified support geometry, binds its independent exact natural
D18 contraction, and corrects a core metadata field that otherwise always
describes the older audited geometry.  No exact target or theorem computation
is launched.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
CORE = REPO / (
    "agents/structural-basis/code/active25_d18_cap_adapted_oracle_v1.py")
CORE_SHA256 = (
    "7258643c15d5ca26a1025ead96f8a6d2a6a9170e639913d2d272007b51e19840")
SUPPORT = REPO / "agents/analytic-new-lever/adaptive_support_v1_exact.json"
SUPPORT_SHA256 = (
    "b7070c2677815b22a86b5a55ce41b3a2477d593495062256356a5df2a37befa7")
CONTRACTION = REPO / (
    "agents/structural-basis/results/"
    "d1over60_d18_uncapped_pencil_exact_v1.json")
CONTRACTION_SHA256 = (
    "3bfaafb532da80a17bb40e4a2cfb94090beda8ca6df43acb07c4f531ce5be02f")
GEOMETRY = "d1over60_verified"


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_core():
    if sha256(CORE) != CORE_SHA256:
        raise RuntimeError("pinned bounded-oracle core changed")
    spec = importlib.util.spec_from_file_location(
        "active25_d18_cap_adapted_oracle_v1_verified_core", CORE)
    if spec is None or spec.loader is None:
        raise ImportError(CORE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verified_geometry(module):
    if sha256(SUPPORT) != SUPPORT_SHA256:
        raise RuntimeError("pinned analytic support certificate changed")
    data = module.strict_json(SUPPORT)
    if (data.get("status") != "EXACT ADAPTIVE ANALYTIC SUPPORT PASS" or
            data.get("checker_sha256") !=
            "b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d"):
        raise ValueError("analytic support certificate did not pass")
    parameters = data["candidate"]["parameters"]
    schedule_prefix = tuple(
        Q(value) for value in parameters["outer_schedule_through_first_empty"])
    expected = tuple(Q(value, 1_000_000) for value in (
        138360, 155020, 158662, 171688, 177684, 180588,
        183402, 185486, 187011, 188221, 189137, 189137))
    if (schedule_prefix != expected or parameters["alpha"] !=
            ["103/400", "237991/900000"] or
            parameters["delta"] != "1/60" or
            parameters["A2_minus_A1"] != "6241/900000"):
        raise ValueError("verified support geometry mismatch")
    schedule = schedule_prefix + (schedule_prefix[-1],) * (
        26 - len(schedule_prefix))
    return {
        "approved": True,
        "delta": Q(1, 60),
        "alpha2": Q(237991, 900000),
        "eta2": Q(224491, 900000),
        "schedule": schedule,
        "source": "exact adaptive analytic support pass b7070c26",
    }


def exact_contraction(module):
    if sha256(CONTRACTION) != CONTRACTION_SHA256:
        raise RuntimeError("pinned exact natural contraction changed")
    data = module.strict_json(CONTRACTION)
    expected_parameters = {
        "k": 48, "alpha1": "103/400", "alpha2": "237991/900000",
        "eta1": "97/400", "eta2": "224491/900000",
        "delta": "1/60", "outer_c": "231750/237991",
    }
    if (data.get("format") !=
            "parameterized-d18-uncapped-pencil-exact-v1" or
            data.get("rigorous_values") is not True or
            data.get("parameters") != expected_parameters):
        raise ValueError("exact contraction geometry mismatch")
    a00 = Q(data["I_matrix"][0][0])
    a11 = Q(data["I_matrix"][1][1])
    b01 = Q(data["kJ_matrix"][0][1])
    projection = Q(data["natural_projection_over_inner_I"])
    if projection != b01 ** 2 / (a11 * a00):
        raise ArithmeticError("exact natural projection formula mismatch")
    return data, projection, a11 / a00, b01 / a00


def run(*, seed, batches, base_samples, focus_samples):
    module = load_core()
    module.GEOMETRIES[GEOMETRY] = verified_geometry(module)
    module.configure_geometry(GEOMETRY)
    _exact, projection, a11_ratio, b01_ratio = exact_contraction(module)
    starts = {path: path.read_bytes()
              for path in (FILE, CORE, SUPPORT, CONTRACTION)}
    result = module.run_oracle(
        seed=seed, batches=batches, base_samples=base_samples,
        focus_samples=focus_samples)
    screen = result["rayleigh_screen"]
    mislabeled = {
        "value": screen.pop(
            "uncapped_exact_natural_D18_projection_over_inner_I"),
        "decimal": screen.pop(
            "uncapped_exact_natural_D18_projection_decimal"),
        "reason": (
            "bounded core always reads the older audited alpha2=3211/12000, "
            "eta2=3031/12000 contraction; it is not this geometry"),
    }
    cap_s = screen["cap_riesz_norm_over_inner_I_estimate"]
    screen["geometry_exact_natural_D18_projection_over_inner_I"] = str(
        projection)
    screen["geometry_exact_natural_D18_projection_decimal"] = float(
        projection)
    screen["cap_riesz_over_geometry_natural_projection_ratio"] = (
        cap_s / float(projection))
    screen["superseded_core_metadata"] = mislabeled
    result["format"] = "active25-d18-verified-cap-bounded-oracle-v1"
    result["status"] = result["status"].replace(
        "HEURISTIC", "VERIFIED-GEOMETRY HEURISTIC", 1)
    result["verified_geometry_binding"] = {
        "support_path": str(SUPPORT.relative_to(REPO)),
        "support_sha256": SUPPORT_SHA256,
        "support_checker_sha256":
            "b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d",
        "schedule": [str(value) for value in module.SCHEDULE],
        "active_counts": list(range(module.MAX_ACTIVE_COUNT + 1)),
    }
    result["exact_natural_contraction_binding"] = {
        "path": str(CONTRACTION.relative_to(REPO)),
        "sha256": CONTRACTION_SHA256,
        "formula": "B01^2/(A11*A00)",
        "projection_over_inner_I": str(projection),
        "A11_over_A00": str(a11_ratio),
        "B01_over_A00": str(b01_ratio),
    }
    result["core_source_sha256"] = CORE_SHA256
    result["source_sha256"] = sha256(starts[FILE])
    if any(path.read_bytes() != payload for path, payload in starts.items()):
        raise RuntimeError("verified wrapper closure changed during run")
    return result


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
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--batches", type=int, default=4)
    parser.add_argument("--base-samples", type=int, default=128)
    parser.add_argument("--focus-samples", type=int, default=2048)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    module = load_core()
    module.apply_limits()
    result = run(seed=args.seed, batches=args.batches,
                 base_samples=args.base_samples,
                 focus_samples=args.focus_samples)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload), "status": result["status"],
        "s_over_I": result["rayleigh_screen"][
            "cap_riesz_norm_over_inner_I_estimate"],
        "wall_seconds": result["wall_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
