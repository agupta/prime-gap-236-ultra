#!/usr/bin/env python3
"""CRN projection screen for natural D12/D14/D16 outer coordinates.

The frozen D19 one-band bridge supplies the target marginal G_D19 and the
same natural-D18 h^2 Markov chains used by its D19/D18 projection screen.
This wrapper evaluates three explicit, cache-free-reconstructed rational
lower-degree vectors on those identical retained points.  It reports

    A/I(F19), b/I(F19), and b^2/(A I(F19)),  b=48 J(F19,H),

with chain-dispersion standard errors and common-random-number comparisons.
The exact one-band threshold is the cache-free D19 inner deficit.  This file
has no exact producer, resume action, or launch authorization.
"""

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
BASE = FILE.with_name("active25_d19_truncated_one_band_projection_bridge_v1.py")
BASE_SHA256 = "132992f8c25ec52228a9bab407d4464cb614917dad43eb3eff6fb9eda7d82ef5"
BASE_TEST = REPO / (
    "agents/structural-basis/tests/"
    "test_active25_d19_truncated_one_band_projection_bridge_v1.py")
BASE_TEST_SHA256 = "2150bd54dcb7c129ca5955022b07ca7594874ff8f6ff323e248b7aa414b4ed1d"
LOWER_CHECKER = FILE.with_name("check_bv_d12_d14_d16_vectors_direct_v1.py")
LOWER_CHECKER_SHA256 = "9d5224cd36190dee55f3eebc69e78ef93f81273acaa29ba6db13cd1c5b2fe0b2"
LOWER_TEST = REPO / (
    "agents/structural-basis/tests/"
    "test_check_bv_d12_d14_d16_vectors_direct_v1.py")
LOWER_TEST_SHA256 = "99b4437b535b3049b56f46d8374135d86a17b0fafff8c58ecd53ffb31707179c"
LOWER_RESULT = REPO / (
    "agents/structural-basis/results/"
    "bv_D12_D14_D16_vectors_direct_exact_v1.json")
LOWER_RESULT_SHA256 = "77884ae1197beace517fd758323e53b92d4cc8ef055ddf873ae4cd858625dbe4"

MAX_WALL_SECONDS = 180
MAX_RSS_BYTES = 512 * 1024 * 1024
EXPECTED = {
    "D12": {
        "degree": 12, "dimension": 120, "A_groups": 1508,
        "H_split_groups": 267, "raw_left_right_pairs": 151656,
        "orbit_pair_types": 2910, "orbit_product_terms": 22729,
        "global_b_keys": 67880,
        "candidate_sha256":
            "b64591f6694d78dfe1dcf99d25a18058d987d94cdb3e1a02f7ade12af90ac4de",
    },
    "D14": {
        "degree": 14, "dimension": 195, "A_groups": 3034,
        "H_split_groups": 462, "raw_left_right_pairs": 262416,
        "orbit_pair_types": 4365, "orbit_product_terms": 41048,
        "global_b_keys": 104902,
        "candidate_sha256":
            "b2f8b726ed2051053fa0c516f605ad9a62e5193292ee8ae9c3f38eb13a59cd6e",
    },
    "D16": {
        "degree": 16, "dimension": 307, "A_groups": 5825,
        "H_split_groups": 769, "raw_left_right_pairs": 436792,
        "orbit_pair_types": 6499, "orbit_product_terms": 71460,
        "global_b_keys": 157438,
        "candidate_sha256":
            "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    },
}


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path, expected):
    if sha256(path) != expected:
        raise RuntimeError(f"pinned lower-degree bridge input changed: {path}")
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


def load_candidates():
    for path, expected in ((LOWER_CHECKER, LOWER_CHECKER_SHA256),
                           (LOWER_TEST, LOWER_TEST_SHA256),
                           (LOWER_RESULT, LOWER_RESULT_SHA256)):
        if sha256(path) != expected:
            raise RuntimeError(f"lower-degree exact provenance changed: {path}")
    data = strict_json(LOWER_RESULT)
    if (data.get("format") !=
            "bv-d12-d14-d16-vectors-cache-free-direct-check-v1" or
            data.get("status") !=
            "INDEPENDENT EXACT LOWER-DEGREE PARTICULAR VECTORS PASS" or
            data.get("rigorous") is not True or
            data.get("cache_read") is not False or
            data.get("serialized_matrix_entries_read") is not False or
            data.get("checker_sha256") != LOWER_CHECKER_SHA256 or
            data.get("parameters") != {
                "alpha": "103/400", "eta": "97/400",
                "source_delta": "7/250", "target_delta": "1/60",
                "full_simplex_delta_independence_exact": True}):
        raise ValueError("lower-degree exact reconstruction identity mismatch")
    rows = {}
    for row in data.get("rows", ()):
        name = row.get("name")
        expected = EXPECTED.get(name)
        counts = row.get("term_counts", {})
        basis = tuple((int(a), tuple(int(x) for x in lam))
                      for a, lam in row.get("basis", ()))
        vector = tuple(Q(x) for x in row.get("rational_vector", ()))
        if (expected is None or name in rows or
                row.get("degree") != expected["degree"] or
                row.get("basis_dimension") != expected["dimension"] or
                row.get("candidate_sha256") != expected["candidate_sha256"] or
                counts.get("square_product_groups") != expected["A_groups"] or
                counts.get("marginal_groups") != expected["dimension"] or
                len(basis) != expected["dimension"] or
                len(vector) != expected["dimension"] or
                len(set(basis)) != expected["dimension"] or
                not any(vector) or Q(row["exact_denominator"]) <= 0 or
                not 0 < Q(row["exact_quotient"]) < 1):
            raise ValueError("lower-degree reconstructed candidate mismatch")
        rows[name] = (row, basis, vector)
    if set(rows) != set(EXPECTED):
        raise ValueError("lower-degree candidate inventory mismatch")
    return data, rows


def structural_b_inventory(ei, basis, marginal):
    """Count global canonical keys before exact coefficient cancellation.

    H is first transported exactly within its canonical B_D space.  Splitting
    only the distinguished coordinate gives (a,e,lambda_rest); multiplying
    lambda_rest by each of the 568 D19 marginal orbits and collecting
    (a,e,p,nu) happens once globally, before any count/face geometry.
    """
    marginal_keys = []
    for orbit_index, mu in enumerate(marginal.orbits.partitions):
        for power in np.flatnonzero(marginal.coefficients[orbit_index]):
            marginal_keys.append((int(power), mu))
    if len(marginal_keys) != 568:
        raise ArithmeticError("D19 marginal key inventory changed")
    h_split = {
        (a, exponent, rest)
        for a, lam in basis
        for exponent, rest in ei.OneStratumSupport.split_at_distinguished(
            lam, 48)
    }
    orbit_cache = {}
    global_keys = set()
    for a, exponent, rest in h_split:
        for power, mu in marginal_keys:
            key = (rest, mu)
            products = orbit_cache.get(key)
            if products is None:
                products = tuple(
                    nu for nu, _ in ei.multiply_monomial_orbits(rest, mu))
                orbit_cache[key] = products
            for nu in products:
                global_keys.add((a, exponent, power, nu))
    return {
        "D19_marginal_groups": len(marginal_keys),
        "H_distinguished_split_groups": len(h_split),
        "raw_Hsplit_times_marginal_pairs": len(h_split) * len(marginal_keys),
        "unique_rest_orbit_pair_types": len(orbit_cache),
        "rest_orbit_product_terms": sum(len(x) for x in orbit_cache.values()),
        "global_canonical_b_keys_before_coefficient_cancellation":
            len(global_keys),
        "key": "(H residual power a, distinguished exponent e, marginal residual power p, common orbit nu)",
        "scope": (
            "exact structural inventory; coefficients and exact geometry moments "
            "are not evaluated by this screen"),
    }


def captured_common_arrays(state, row, chains, draws):
    module = state["module"]
    one_band = state["one_band"]
    flat = state["full_points"]
    radial_points = state["radial_points"]
    if flat.shape != (chains * draws, module.K):
        raise ArithmeticError("captured chain shape changed")
    totals = np.sum(flat, axis=1, dtype=np.longdouble)
    radial = totals <= module.ld(one_band.ALPHA2)
    if (int(np.sum(radial)) != len(radial_points) or
            not np.array_equal(flat[radial], radial_points)):
        raise ArithmeticError("captured radial ordering changed")
    large = radial_points > module.ld(one_band.DELTA)
    counts = np.sum(large, axis=1)
    large_sums = np.sum(np.where(large, radial_points, 0), axis=1,
                        dtype=np.longdouble)
    cap = counts == 0
    for count, bound in enumerate(one_band.SCHEDULE, start=1):
        if bound > count * one_band.DELTA:
            cap |= ((counts == count) &
                    (large_sums <= module.ld(bound)))
    _cert, _uncapped, _d0, basis18, vector18, _outer18 = module.load_inputs()
    natural18 = module.ResidualD18(
        basis18, vector18, center=module.ALPHA2,
        dilation=module.ALPHA1 / module.ALPHA2)
    h18 = natural18.evaluate(radial_points)
    if np.any(h18 == 0):
        raise ArithmeticError("proposal polynomial vanished at retained point")
    g_ratio = ((state["target_g_normalized"] / h18) *
               module.ld(state["target_marginal"].normalization /
                         natural18.scale))
    scale = float(Q(row["exact_bridge_forms"]["A11_over_A00"]))
    return module, one_band, radial_points, radial, cap, natural18, h18, g_ratio, scale


def candidate_projection(projection, arrays, basis, vector, chains, draws):
    (module, one_band, radial_points, radial, cap, natural18, h18,
     g_ratio, scale) = arrays
    natural = module.ResidualD18(
        basis, vector, center=one_band.ALPHA2,
        dilation=module.ALPHA1 / one_band.ALPHA2)
    values = natural.evaluate(radial_points)
    h_ratio = ((values / h18) *
               module.ld(natural.scale / natural18.scale))
    a_flat = np.zeros(chains * draws, dtype=np.longdouble)
    b_flat = np.zeros(chains * draws, dtype=np.longdouble)
    a_flat[radial] = h_ratio * h_ratio * cap
    b_flat[radial] = h_ratio * g_ratio * cap
    to_chains = lambda values: values.reshape(draws, chains).T
    summary = projection.projection_summary(
        to_chains(a_flat), to_chains(b_flat), scale)
    summary.update({
        "H": (
            "natural dilation from alpha1=103/400 to the frozen one-band "
            "endpoint 9500917/36000000, then restriction to its verified cap"),
        "importance_proposal": "frozen natural-D18 h^2 on the old full shell",
        "same_retained_points_as_D19_and_D18_screens": True,
        "captured_radial_draws": int(np.sum(radial)),
        "captured_capped_draws": int(np.sum(cap)),
    })
    return summary


def run(*, seed, chains, burn, draws):
    starts = {path: path.read_bytes() for path in
              (FILE, BASE, BASE_TEST, LOWER_CHECKER, LOWER_TEST, LOWER_RESULT)}
    projection = load("active25_d19_lower_projection_base", BASE, BASE_SHA256)
    lower_data, candidates = load_candidates()
    d19 = projection.load(
        "active25_d19_lower_projection_h2", projection.D19_BRIDGE,
        projection.D19_BRIDGE_SHA256)
    state = projection.instrument(d19)
    row = d19.run(seed=seed, chains=chains, burn=burn, draws=draws)
    natural19, natural18, count_projection = projection.projection_from_capture(
        row, state, chains, draws)
    arrays = captured_common_arrays(state, row, chains, draws)

    # The checker module is loaded solely to bind the exact-integrator
    # canonical orbit multiplication used by the structural cost inventory.
    lower_checker = load(
        "active25_lower_vector_checker_for_inventory", LOWER_CHECKER,
        LOWER_CHECKER_SHA256)
    scan = lower_checker.load_module(
        "active25_lower_projection_inventory_scan", lower_checker.SCAN)
    threshold = row["screen"]["sufficient_threshold"]
    projections = {}
    for name in ("D12", "D14", "D16"):
        exact_row, basis, vector = candidates[name]
        summary = candidate_projection(
            projection, arrays, basis, vector, chains, draws)
        cost = structural_b_inventory(
            scan.ei, basis, state["target_marginal"])
        expected = EXPECTED[name]
        observed = (
            cost["H_distinguished_split_groups"],
            cost["raw_Hsplit_times_marginal_pairs"],
            cost["unique_rest_orbit_pair_types"],
            cost["rest_orbit_product_terms"],
            cost["global_canonical_b_keys_before_coefficient_cancellation"],
        )
        wanted = (
            expected["H_split_groups"], expected["raw_left_right_pairs"],
            expected["orbit_pair_types"], expected["orbit_product_terms"],
            expected["global_b_keys"],
        )
        if observed != wanted:
            raise ArithmeticError(f"{name} structural cost inventory changed")
        value = summary["projected_energy_over_inner_I"]
        error = summary["projected_energy_over_inner_I_delta_standard_error"]
        lower3 = value - 3 * error
        base_chains = np.asarray(
            natural19["per_chain_projected_energy_over_inner_I"],
            dtype=np.longdouble)
        candidate_chains = np.asarray(
            summary["per_chain_projected_energy_over_inner_I"],
            dtype=np.longdouble)
        differences = candidate_chains - base_chains
        diff_mean = float(np.mean(differences, dtype=np.longdouble))
        diff_se = float(np.std(differences, ddof=1) / math.sqrt(chains))
        summary.update({
            "candidate_degree": exact_row["degree"],
            "candidate_basis_dimension": exact_row["basis_dimension"],
            "candidate_path": exact_row["candidate_path"],
            "candidate_sha256": exact_row["candidate_sha256"],
            "cache_free_direct_result_sha256": LOWER_RESULT_SHA256,
            "cache_free_exact_inner_quotient": exact_row["exact_quotient"],
            "legacy_integrator_source_present_in_current_tree":
                exact_row["legacy_integrator_source_present_in_current_tree"],
            "provenance_note": exact_row["candidate_provenance"],
            "exact_A_square_product_groups": expected["A_groups"],
            "exact_b_global_collection_inventory": cost,
            "exact_sufficient_threshold": row["screen"]
                ["exact_sufficient_threshold"],
            "projected_minus_threshold": value - threshold,
            "three_SE_lower_projected_energy": lower3,
            "three_SE_lower_margin_over_threshold": lower3 - threshold,
            "CRN_difference_from_natural_D19_projection": diff_mean,
            "CRN_difference_standard_error": diff_se,
            "conditional_decision": (
                "GATED LOWER-DEGREE EXACT A,b COMPUTATION WARRANTED"
                if lower3 > threshold else
                "LOWER-DEGREE PROJECTION INCONCLUSIVE"),
        })
        projections[name] = summary

    eligible = [
        name for name in ("D12", "D14", "D16")
        if projections[name]["three_SE_lower_projected_energy"] > threshold]
    chosen = min(
        eligible,
        key=lambda name: projections[name]["exact_b_global_collection_inventory"]
            ["global_canonical_b_keys_before_coefficient_cancellation"],
        default=None)
    selection = {
        "rule": (
            "among prespecified candidates whose three-SE lower projection "
            "exceeds the exact D19 deficit, minimize global canonical b keys"),
        "chosen_candidate": chosen,
        "exact_launch_authorized": False,
        "selection_is_heuristic_not_a_proof": True,
    }
    if chosen is not None:
        selection.update({
            "chosen_projected_energy_over_inner_I": projections[chosen]
                ["projected_energy_over_inner_I"],
            "chosen_three_SE_lower_margin_over_threshold": projections[chosen]
                ["three_SE_lower_margin_over_threshold"],
            "chosen_global_b_key_inventory": projections[chosen]
                ["exact_b_global_collection_inventory"]
                ["global_canonical_b_keys_before_coefficient_cancellation"],
        })

    if any(path.read_bytes() != payload for path, payload in starts.items()):
        raise RuntimeError("lower-degree bridge source closure changed during run")
    row["format"] = "active25-d19-lower-degree-projection-bridge-v1"
    row["source_sha256"] = sha256(starts[FILE])
    row["projection_base_source_sha256"] = BASE_SHA256
    row["lower_degree_exact_reconstruction"] = {
        "path": str(LOWER_RESULT.relative_to(REPO)),
        "sha256": LOWER_RESULT_SHA256,
        "checker_path": str(LOWER_CHECKER.relative_to(REPO)),
        "checker_sha256": LOWER_CHECKER_SHA256,
        "test_path": str(LOWER_TEST.relative_to(REPO)),
        "test_sha256": LOWER_TEST_SHA256,
        "status": lower_data["status"],
    }
    row["natural_D19_projection"] = natural19
    row["natural_D18_proposal_projection"] = natural18
    row["count_radial_low_degree_projection"] = count_projection
    row["lower_degree_natural_projections"] = projections
    row["exact_candidate_selection"] = selection
    row["source_hashes"][str(BASE.relative_to(REPO))] = BASE_SHA256
    row["source_hashes"][str(BASE_TEST.relative_to(REPO))] = BASE_TEST_SHA256
    row["source_hashes"][str(LOWER_CHECKER.relative_to(REPO))] = \
        LOWER_CHECKER_SHA256
    row["source_hashes"][str(LOWER_TEST.relative_to(REPO))] = LOWER_TEST_SHA256
    row["source_hashes"][str(LOWER_RESULT.relative_to(REPO))] = \
        LOWER_RESULT_SHA256
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
    result = run(seed=args.seed, chains=args.chains,
                 burn=args.burn, draws=args.draws)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"],
        "output_sha256": sha256(payload),
        "threshold": result["screen"]["sufficient_threshold"],
        "projections": {
            name: {
                "b2_over_A_I": item["projected_energy_over_inner_I"],
                "standard_error": item[
                    "projected_energy_over_inner_I_delta_standard_error"],
                "three_SE_lower_margin": item[
                    "three_SE_lower_margin_over_threshold"],
            } for name, item in
            result["lower_degree_natural_projections"].items()},
        "chosen": result["exact_candidate_selection"]["chosen_candidate"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
