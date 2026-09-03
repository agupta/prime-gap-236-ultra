#!/usr/bin/env python3
"""One-seed CRN/point gate for 10^-38/10^-40/10^-42 D14 grids."""

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
FINE_SOURCE = FILE.with_name("prepare_bv_D14_common_grid_candidates_v2.py")
FINE_SOURCE_SHA256 = "83dfdd7d88ee7f2f2a4dfbf492af693b9ae99c2bfaf983816c0fdcdec3229a57"
FINE_RESULT = REPO / (
    "agents/structural-basis/results/bv_D14_fine_common_grid_candidates_exact_v2.json")
FINE_RESULT_SHA256 = "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0"
FINE_TEST = REPO / (
    "agents/structural-basis/tests/test_prepare_bv_D14_common_grid_candidates_v2.py")
FINE_TEST_SHA256 = "d7f0f8856f677080495a59dcb04f93c732e7a7103546da9f65311916796e49c3"
MAX_RSS_BYTES = 512 * 1024 * 1024


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path, expected):
    if sha256(path) != expected:
        raise RuntimeError(f"pinned fine-grid screen input changed: {path}")
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


def load_fine_candidates(original_basis):
    for path, expected in ((FINE_SOURCE, FINE_SOURCE_SHA256),
                           (FINE_RESULT, FINE_RESULT_SHA256),
                           (FINE_TEST, FINE_TEST_SHA256)):
        if sha256(path) != expected:
            raise RuntimeError(f"fine-grid provenance changed: {path}")
    data = strict_json(FINE_RESULT)
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in data.get("basis", ()))
    original_q = Q(data.get("source_D14", {}).get("exact_quotient", "0"))
    if (data.get("status") !=
            "EXACT D14 FINE COMMON-GRID PARTICULAR VECTORS PASS" or
            data.get("rigorous") is not True or
            data.get("cache_read") is not False or
            data.get("serialized_matrix_entries_read") is not False or
            basis != original_basis or not Q(97, 100) < original_q < 1):
        raise ValueError("fine-grid exact result identity mismatch")
    rows = {}
    for item in data.get("candidates", ()):
        digits = item.get("grid_digits")
        vector = tuple(Q(x) for x in item.get("rational_vector", ()))
        quotient = Q(item.get("exact_quotient", "0"))
        if (digits not in (38, 40, 42) or digits in rows or
                item.get("name") != f"D14_grid_1e-{digits}" or
                len(vector) != 195 or max(abs(x) for x in vector) != 1 or
                abs(quotient - original_q) >= Q(1, 10**20)):
            raise ValueError("fine-grid row mismatch")
        rows[digits] = (item, vector)
    if set(rows) != {38, 40, 42}:
        raise ValueError("fine-grid inventory mismatch")
    return data, rows


def crn_difference(left, right):
    x = np.asarray(left["per_chain_projected_energy_over_inner_I"],
                   dtype=np.longdouble)
    y = np.asarray(right["per_chain_projected_energy_over_inner_I"],
                   dtype=np.longdouble)
    delta = x - y
    return (float(np.mean(delta, dtype=np.longdouble)),
            float(np.std(delta, ddof=1) / np.sqrt(len(delta))),
            [float(value) for value in delta])


def candidate_h_ratio(module, one_band, radial_points, natural18, h18,
                      basis, vector):
    natural = module.ResidualD18(
        basis, vector, center=one_band.ALPHA2,
        dilation=module.ALPHA1 / one_band.ALPHA2)
    return ((natural.evaluate(radial_points) / h18) *
            module.ld(natural.scale / natural18.scale))


def run(*, seed, chains, burn, draws):
    snapshots = {path: path.read_bytes() for path in
                 (FILE, LOWER_SCREEN, FINE_SOURCE, FINE_RESULT, FINE_TEST)}
    lower = load("active25_d14_fine_grid_lower", LOWER_SCREEN,
                 LOWER_SCREEN_SHA256)
    _lower_data, candidates = lower.load_candidates()
    original_row, basis, original_vector = candidates["D14"]
    fine_data, fine_rows = load_fine_candidates(basis)
    projection = lower.load(
        "active25_d14_fine_grid_projection", lower.BASE, lower.BASE_SHA256)
    d19 = projection.load(
        "active25_d14_fine_grid_h2", projection.D19_BRIDGE,
        projection.D19_BRIDGE_SHA256)
    state = projection.instrument(d19)
    row = d19.run(seed=seed, chains=chains, burn=burn, draws=draws)
    natural19, natural18_summary, count_projection = \
        projection.projection_from_capture(row, state, chains, draws)
    arrays = lower.captured_common_arrays(state, row, chains, draws)
    (module, one_band, radial_points, _radial, cap, natural18, h18,
     _g_ratio, _scale) = arrays
    original = lower.candidate_projection(
        projection, arrays, basis, original_vector, chains, draws)
    original_ratio = candidate_h_ratio(
        module, one_band, radial_points, natural18, h18, basis, original_vector)
    threshold = row["screen"]["sufficient_threshold"]
    original["candidate_path"] = original_row["candidate_path"]
    original["candidate_sha256"] = original_row["candidate_sha256"]
    screens = {}
    for digits in (38, 40, 42):
        exact, vector = fine_rows[digits]
        screen = lower.candidate_projection(
            projection, arrays, basis, vector, chains, draws)
        difference, difference_se, differences = crn_difference(
            screen, original)
        ratio = candidate_h_ratio(
            module, one_band, radial_points, natural18, h18, basis, vector)
        delta = ratio - original_ratio
        denominator = np.sum(original_ratio[cap] ** 2, dtype=np.longdouble)
        relative_l2 = float(np.sqrt(
            np.sum(delta[cap] ** 2, dtype=np.longdouble) / denominator))
        rms_scale = np.sqrt(denominator / max(1, int(np.sum(cap))))
        maximum_scaled_absolute = float(
            np.max(np.abs(delta[cap])) / rms_scale)
        value = screen["projected_energy_over_inner_I"]
        error = screen["projected_energy_over_inner_I_delta_standard_error"]
        exact_q_change = float(Q(exact["absolute_quotient_change"]))
        pass_gate = (value - 2 * error > threshold and
                     (abs(difference) <= 3 * max(difference_se, 1e-18) or
                      abs(difference) <= 1e-8) and
                     relative_l2 <= 1e-5 and exact_q_change < 1e-20)
        screen.update({
            "grid_digits": digits,
            "maximum_absolute_coefficient_error":
                exact["maximum_absolute_coefficient_error"],
            "maximum_reduced_denominator_bits":
                exact["maximum_reduced_denominator_bits"],
            "cache_free_exact_full_simplex_quotient": exact["exact_quotient"],
            "exact_full_simplex_quotient_absolute_change":
                exact["absolute_quotient_change"],
            "projected_minus_threshold": value - threshold,
            "three_SE_lower_projected_energy": value - 3 * error,
            "CRN_difference_from_original_D14": difference,
            "CRN_difference_standard_error": difference_se,
            "CRN_difference_by_chain": differences,
            "capped_proposal_weighted_relative_L2_H_change": relative_l2,
            "maximum_capped_H_change_in_original_RMS_units":
                maximum_scaled_absolute,
            "adoption_gate_pass": pass_gate,
            "conditional_decision": (
                "FINE GRID INDISTINGUISHABLE; EXACT A ELIGIBLE"
                if pass_gate else "FINE GRID REJECTED"),
        })
        screens[str(digits)] = screen
    passing = [digits for digits in (38, 40, 42)
               if screens[str(digits)]["adoption_gate_pass"]]
    selected = min(passing, default=None)
    if any(path.read_bytes() != payload for path, payload in snapshots.items()):
        raise RuntimeError("fine-grid screen source closure changed")
    row["format"] = "active25-d19-d14-fine-grid-projection-bridge-v2"
    row["source_sha256"] = sha256(snapshots[FILE])
    row["natural_D19_projection"] = natural19
    row["natural_D18_proposal_projection"] = natural18_summary
    row["count_radial_low_degree_projection"] = count_projection
    row["original_D14_projection"] = original
    row["D14_fine_common_grid_projections"] = screens
    row["fine_grid_selection"] = {
        "selected_grid_digits": selected,
        "rule": ("coarsest grid passing exact-q, CRN/absolute-difference, "
                 "relative-L2, and exact-threshold two-SE gates; the original "
                 "D14 0.020 three-SE gate is frozen separately"),
        "selection_is_numerical": True,
        "exact_A_launch_authorized": False,
    }
    row["fine_grid_exact_result"] = {
        "path": str(FINE_RESULT.relative_to(REPO)),
        "sha256": FINE_RESULT_SHA256, "status": fine_data["status"],
    }
    for path, expected in ((LOWER_SCREEN, LOWER_SCREEN_SHA256),
                           (FINE_SOURCE, FINE_SOURCE_SHA256),
                           (FINE_RESULT, FINE_RESULT_SHA256),
                           (FINE_TEST, FINE_TEST_SHA256)):
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
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
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
        "selected_grid_digits": result["fine_grid_selection"]
            ["selected_grid_digits"],
        "grids": {digits: {
            "projection": item["projected_energy_over_inner_I"],
            "CRN_difference": item["CRN_difference_from_original_D14"],
            "CRN_difference_standard_error": item[
                "CRN_difference_standard_error"],
            "relative_L2_H_change": item[
                "capped_proposal_weighted_relative_L2_H_change"],
            "pass": item["adoption_gate_pass"],
        } for digits, item in
        result["D14_fine_common_grid_projections"].items()},
    }, sort_keys=True))


if __name__ == "__main__":
    main()
