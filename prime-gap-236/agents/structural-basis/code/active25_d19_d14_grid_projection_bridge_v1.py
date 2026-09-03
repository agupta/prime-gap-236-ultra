#!/usr/bin/env python3
"""CRN capped-projection comparison for exact D14 common-grid vectors."""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
LOWER_SCREEN = FILE.with_name("active25_d19_lower_degree_projection_bridge_v1.py")
LOWER_SCREEN_SHA256 = "82a9a357d6605faa349c830d56b410cb7bd5c45f2b2ab05d81754ed55b8a84a7"
LOWER_TEST = REPO / (
    "agents/structural-basis/tests/"
    "test_active25_d19_lower_degree_projection_bridge_v1.py")
LOWER_TEST_SHA256 = "8207f7d2c5066b7720e8126fff43e1a24f2628bd4a73d25118170772d79ec41a"
GRID_SOURCE = FILE.with_name("prepare_bv_D14_common_grid_candidates_v1.py")
GRID_SOURCE_SHA256 = "55eece4f4fc15ae2112a55bb78eafd6d3e10f4e2a21d6a5981a165e853692787"
GRID_RESULT = REPO / (
    "agents/structural-basis/results/bv_D14_common_grid_candidates_exact_v1.json")
GRID_RESULT_SHA256 = "761bc005f666d57ac459d54d53a18f7b7c771c15c3af26e807bdac03d8810309"
GRID_TEST = REPO / (
    "agents/structural-basis/tests/test_prepare_bv_D14_common_grid_candidates_v1.py")
GRID_TEST_SHA256 = "f9f584630bb56c0e95491cafa447f58ea53ec2ed2a960336d2d7a891ad53c325"
MAX_WALL_SECONDS = 180
MAX_RSS_BYTES = 512 * 1024 * 1024


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path, expected):
    if sha256(path) != expected:
        raise RuntimeError(f"pinned D14 grid screen input changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result
    return json.loads(
        Path(path).read_bytes(), object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token {token!r} in {path}")))


def load_grid_candidates(original_basis):
    for path, expected in ((GRID_SOURCE, GRID_SOURCE_SHA256),
                           (GRID_RESULT, GRID_RESULT_SHA256),
                           (GRID_TEST, GRID_TEST_SHA256)):
        if sha256(path) != expected:
            raise RuntimeError(f"D14 grid provenance changed: {path}")
    data = strict_json(GRID_RESULT)
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in data.get("basis", ()))
    if (data.get("status") !=
            "EXACT D14 COMMON-GRID PARTICULAR VECTORS PASS" or
            data.get("rigorous") is not True or
            data.get("cache_read") is not False or
            data.get("serialized_matrix_entries_read") is not False or
            (data.get("degree"), data.get("basis_dimension")) != (14, 195) or
            basis != original_basis):
        raise ValueError("D14 grid candidate identity mismatch")
    rows = {}
    for item in data.get("candidates", ()):
        digits = item.get("grid_digits")
        vector = tuple(Q(x) for x in item.get("rational_vector", ()))
        if (digits not in (16, 14, 12) or digits in rows or
                item.get("name") != f"D14_grid_1e-{digits}" or
                len(vector) != 195 or max(abs(x) for x in vector) != 1 or
                Q(item["exact_denominator"]) <= 0 or
                not 0 < Q(item["exact_quotient"]) < Q(1, 4)):
            raise ValueError("D14 grid row mismatch")
        rows[digits] = (item, vector)
    if set(rows) != {12, 14, 16}:
        raise ValueError("D14 grid inventory mismatch")
    return data, rows


def crn_difference(left, right):
    x = np.asarray(left["per_chain_projected_energy_over_inner_I"],
                   dtype=np.longdouble)
    y = np.asarray(right["per_chain_projected_energy_over_inner_I"],
                   dtype=np.longdouble)
    if x.shape != y.shape or len(x) < 4:
        raise ValueError("CRN chain inventory mismatch")
    delta = x - y
    return (float(np.mean(delta, dtype=np.longdouble)),
            float(np.std(delta, ddof=1) / np.sqrt(len(delta))),
            [float(value) for value in delta])


def run(*, seed, chains, burn, draws):
    snapshots = {path: path.read_bytes() for path in
                 (FILE, LOWER_SCREEN, LOWER_TEST, GRID_SOURCE,
                  GRID_RESULT, GRID_TEST)}
    lower = load("active25_d14_grid_lower_screen", LOWER_SCREEN,
                 LOWER_SCREEN_SHA256)
    _lower_data, candidates = lower.load_candidates()
    original_row, basis, original_vector = candidates["D14"]
    grid_data, grid_rows = load_grid_candidates(basis)
    projection = lower.load(
        "active25_d14_grid_projection_base", lower.BASE, lower.BASE_SHA256)
    d19 = projection.load(
        "active25_d14_grid_h2_base", projection.D19_BRIDGE,
        projection.D19_BRIDGE_SHA256)
    state = projection.instrument(d19)
    row = d19.run(seed=seed, chains=chains, burn=burn, draws=draws)
    natural19, natural18, count_projection = projection.projection_from_capture(
        row, state, chains, draws)
    arrays = lower.captured_common_arrays(state, row, chains, draws)
    original = lower.candidate_projection(
        projection, arrays, basis, original_vector, chains, draws)
    threshold = row["screen"]["sufficient_threshold"]
    original["candidate_path"] = original_row["candidate_path"]
    original["candidate_sha256"] = original_row["candidate_sha256"]
    original["projected_minus_threshold"] = (
        original["projected_energy_over_inner_I"] - threshold)
    screens = {}
    for digits in (16, 14, 12):
        exact, vector = grid_rows[digits]
        screen = lower.candidate_projection(
            projection, arrays, basis, vector, chains, draws)
        difference, difference_se, differences = crn_difference(
            screen, original)
        value = screen["projected_energy_over_inner_I"]
        error = screen["projected_energy_over_inner_I_delta_standard_error"]
        screen.update({
            "grid_digits": digits,
            "maximum_absolute_coefficient_error":
                exact["maximum_absolute_coefficient_error"],
            "maximum_reduced_denominator_bits":
                exact["maximum_reduced_denominator_bits"],
            "cache_free_exact_full_simplex_quotient": exact["exact_quotient"],
            "projected_minus_threshold": value - threshold,
            "three_SE_lower_projected_energy": value - 3 * error,
            "CRN_difference_from_original_D14": difference,
            "CRN_difference_standard_error": difference_se,
            "CRN_difference_by_chain": differences,
            "indistinguishable_from_original_at_three_SE":
                abs(difference) <= 3 * difference_se,
            "conditional_decision": (
                "GRID CANDIDATE RETAINED FOR TWO-SEED AGGREGATION"
                if (value - 3 * error > threshold and
                    abs(difference) <= 3 * difference_se) else
                "GRID CANDIDATE HEURISTICALLY REJECTED"),
        })
        screens[str(digits)] = screen
    if any(path.read_bytes() != payload for path, payload in snapshots.items()):
        raise RuntimeError("D14 grid screen source closure changed")
    row["format"] = "active25-d19-d14-grid-projection-bridge-v1"
    row["source_sha256"] = sha256(snapshots[FILE])
    row["lower_screen_source_sha256"] = LOWER_SCREEN_SHA256
    row["natural_D19_projection"] = natural19
    row["natural_D18_proposal_projection"] = natural18
    row["count_radial_low_degree_projection"] = count_projection
    row["original_D14_projection"] = original
    row["D14_common_grid_projections"] = screens
    row["D14_grid_exact_result"] = {
        "path": str(GRID_RESULT.relative_to(REPO)),
        "sha256": GRID_RESULT_SHA256,
        "status": grid_data["status"],
    }
    for path, expected in ((LOWER_SCREEN, LOWER_SCREEN_SHA256),
                           (LOWER_TEST, LOWER_TEST_SHA256),
                           (GRID_SOURCE, GRID_SOURCE_SHA256),
                           (GRID_RESULT, GRID_RESULT_SHA256),
                           (GRID_TEST, GRID_TEST_SHA256)):
        row["source_hashes"][str(path.relative_to(REPO))] = expected
    row["launch_authorized"] = False
    row["exact_target_started"] = False
    row["resume_supported"] = False
    row["theorem_ready"] = False
    return row


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


def apply_limits():
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    new_hard = hard if hard != resource.RLIM_INFINITY else MAX_RSS_BYTES
    resource.setrlimit(resource.RLIMIT_AS,
                       (min(MAX_RSS_BYTES, new_hard), new_hard))
    signal.alarm(180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--chains", type=int, default=8)
    parser.add_argument("--burn", type=int, default=4000)
    parser.add_argument("--draws", type=int, default=6000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    apply_limits()
    result = run(seed=args.seed, chains=args.chains,
                 burn=args.burn, draws=args.draws)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"], "output_sha256": sha256(payload),
        "original": result["original_D14_projection"]
            ["projected_energy_over_inner_I"],
        "grids": {digits: {
            "projection": row["projected_energy_over_inner_I"],
            "standard_error": row[
                "projected_energy_over_inner_I_delta_standard_error"],
            "CRN_difference": row["CRN_difference_from_original_D14"],
            "CRN_difference_standard_error": row[
                "CRN_difference_standard_error"],
            "decision": row["conditional_decision"],
        } for digits, row in result["D14_common_grid_projections"].items()},
    }, sort_keys=True))


if __name__ == "__main__":
    main()
