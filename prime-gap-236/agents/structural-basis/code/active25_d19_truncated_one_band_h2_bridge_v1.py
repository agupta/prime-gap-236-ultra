#!/usr/bin/env python3
"""Cache-conditional D19 Riesz screen on the verified truncated one band.

The sampler retains the already calibrated, exactly normalized D18 natural
outer ``h^2`` proposal.  It evaluates the Riesz representer of the explicit
568-term canonical-degree-19 inner vector and importance-weights by
``(G_D19/h_D18)^2``.  Thus the proposal needs no new D19 outer contraction:

  I(G_D19 1_V)/I(F_D19)
    = I(h_D18)/I(F_D19) E_h2[(G_D19/h_D18)^2 1_V].

The vector-selection provenance is cache-conditional, but a separately pinned
checker has reconstructed this particular vector's I and J directly, without
reading cache or serialized matrix entries.  This remains a bounded numerical
screen and never authorizes exact production.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import sys


os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
ONE_BAND = FILE.with_name(
    "active25_d18_truncated_one_band_h2_bridge_v1.py")
ONE_BAND_SHA256 = (
    "1e15d2a568c497586389ec7b3dd7e336f05e9a2d0b3583345194a13221ee55e0")
D19 = REPO / ("agents/structural-basis/results/"
              "bv_D19_krylov20_cacheconditional_v1.json")
D19_SHA256 = (
    "986563579cb7fa8653f774100e9fd1cc966761261eef53052b8be8e61f96d276")
DIRECT_CHECKER = REPO / "verify/check_bv_rational_vector_direct_v1.py"
DIRECT_CHECKER_SHA256 = (
    "63bd2a3adc84191d212d52d3175179f583a1257d7c862f1ee07ecaa2ade3b7d3")
DIRECT_TEST = REPO / "verify/test_check_bv_rational_vector_direct_v1.py"
DIRECT_TEST_SHA256 = (
    "a8d5dd13cf73dc3c59f89dbfdee21819cbc4c230ed063d7bdec42d57bcf81247")
DIRECT_RESULT = REPO / "verify/results/bv_D19_krylov20_direct_exact_v1.json"
DIRECT_RESULT_SHA256 = (
    "a71b9bacf9fbe9ce21d6d0f3c23eec69baa917c46157c402d2d60e6565517d0b")
PRODUCER = REPO / "agents/structural-basis/code/krylov_bv_d20_from_d18_v1.py"
PRODUCER_SHA256 = (
    "6dc0857cc40b5b47bfe65bfd7ccf50d98891df0251cf52f6adee56549cbf5993")
RUN_BASIS = REPO / "agents/exact-integrator/run_basis.py"
RUN_BASIS_SHA256 = (
    "f660a30d8dd83f13459e0412ded1e28c7ec0864abb41ad04a396475a7905e1d4")
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
INTEGRATOR_SHA256 = (
    "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52")
CACHE_READER = REPO / "agents/small-delta-frontier/certify_bv_cached.py"
CACHE_READER_SHA256 = (
    "1e1e9aece98190b06684be1c206583de72969218b4ec5a5dfaf374fb7d26d387")
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
SCAN_SHA256 = (
    "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9")
D18_CERT = REPO / ("agents/exact-integrator/results/"
                   "aquarter_fullsimplex_k48_B18_refined_exact.json")
D18_CERT_SHA256 = (
    "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58")
CACHE = Path("/tmp/bv_d20_d19_snapshot.sqlite3")
CACHE_SHA256 = (
    "334465acd8f48f5451ba40f821a8b330398614088cca78c558576649e2393fa3")
MAX_WALL_SECONDS = 180
MAX_RSS_BYTES = 512 * 1024 * 1024
EXPECTED_DIMENSION = 568
EXPECTED_CANONICAL_DEGREE = 19


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def streaming_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


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
        raise RuntimeError(f"pinned D19 bridge dependency changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_d19():
    pins = ((D19, D19_SHA256),
            (DIRECT_CHECKER, DIRECT_CHECKER_SHA256),
            (DIRECT_TEST, DIRECT_TEST_SHA256),
            (DIRECT_RESULT, DIRECT_RESULT_SHA256),
            (PRODUCER, PRODUCER_SHA256),
            (RUN_BASIS, RUN_BASIS_SHA256),
            (INTEGRATOR, INTEGRATOR_SHA256),
            (CACHE_READER, CACHE_READER_SHA256),
            (SCAN, SCAN_SHA256),
            (D18_CERT, D18_CERT_SHA256))
    for path, expected in pins:
        if sha256(path) != expected:
            raise RuntimeError(f"pinned D19 provenance input changed: {path}")
    candidate = strict_json(D19)
    direct = strict_json(DIRECT_RESULT)
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in direct.get("basis", ()))
    vector = tuple(Q(x) for x in direct.get("rational_vector", ()))
    source_hashes = candidate.get("source_hashes", {})
    if (candidate.get("format") !=
            "bv-d20-krylov-refinement-cacheconditional-v1" or
            candidate.get("status") !=
            "EXACT PARTICULAR VECTOR CONDITIONAL ON CACHE" or
            candidate.get("rigorous_given_cache_entries") is not True or
            candidate.get("cache_entries_independently_reconstructed") is not False or
            candidate.get("input_mode") != "cache-snapshot-prefix" or
            candidate.get("basis_dimension") != EXPECTED_DIMENSION or
            candidate.get("seed_dimension") != 471 or
            candidate.get("cache_misses") != 0 or
            candidate.get("checker_sha256") != PRODUCER_SHA256 or
            candidate.get("source_run_sha256") is not None or
            candidate.get("rationalization_significant_digits") != 75 or
            candidate.get("parameters") != {
                "alpha": "103/400", "beta1": "103/400",
                "beta2": "103/400", "beta3plus": "103/400",
                "delta": "7/250", "eta": "97/400"} or
            direct.get("format") !=
                "bv-rational-vector-cache-free-direct-check-v1" or
            direct.get("status") !=
                "INDEPENDENT EXACT PARTICULAR INNER VECTOR PASS" or
            direct.get("rigorous") is not True or
            direct.get("cache_read") is not False or
            direct.get("serialized_matrix_entries_read") is not False or
            direct.get("candidate_sha256") != D19_SHA256 or
            direct.get("candidate_producer_sha256") != PRODUCER_SHA256 or
            direct.get("checker_sha256") != DIRECT_CHECKER_SHA256 or
            direct.get("basis_degree") != EXPECTED_CANONICAL_DEGREE or
            direct.get("basis_dimension") != EXPECTED_DIMENSION or
            direct.get("k") != 48 or
            direct.get("parameters") != {
                "alpha": "103/400", "eta": "97/400",
                "full_simplex_delta_independence_exact": True,
                "source_delta": "7/250", "target_delta": "1/60"} or
            direct.get("term_counts") != {
                "marginal": 568, "marginal_square": 13955,
                "square": 13955} or
            len(basis) != EXPECTED_DIMENSION or
            len(vector) != EXPECTED_DIMENSION or
            len(set(basis)) != EXPECTED_DIMENSION or
            max(a + sum(lam) for a, lam in basis) !=
                EXPECTED_CANONICAL_DEGREE or
            source_hashes.get(str(CACHE)) != CACHE_SHA256 or
            source_hashes.get(str(D18_CERT.relative_to(REPO))) !=
                D18_CERT_SHA256 or
            source_hashes.get(str(RUN_BASIS.relative_to(REPO))) !=
                RUN_BASIS_SHA256 or
            source_hashes.get(str(INTEGRATOR.relative_to(REPO))) !=
                INTEGRATOR_SHA256 or
            source_hashes.get(str(CACHE_READER.relative_to(REPO))) !=
                CACHE_READER_SHA256):
        raise ValueError("D19 vector/cache provenance mismatch")
    candidate_basis = tuple((int(a), tuple(int(x) for x in lam))
                            for a, lam in candidate["basis"])
    candidate_vector = tuple(Q(x) for x in candidate["rational_vector"])
    if basis != candidate_basis or vector != candidate_vector:
        raise ValueError("cache-free direct result changed the explicit vector")
    inner_i = Q(direct["exact_denominator"])
    inner_48j = Q(direct["exact_numerator"])
    deficit_ratio = Q(direct["exact_normalized_deficit"])
    if (inner_i <= 0 or inner_i - inner_48j <= 0 or
            deficit_ratio != (inner_i - inner_48j) / inner_i or
            Q(direct["exact_quotient"]) != inner_48j / inner_i or
            Q(direct["exact_deficit"]) != inner_i - inner_48j):
        raise ArithmeticError("D19 exact inner forms mismatch")
    return candidate, direct, basis, vector, inner_i, inner_48j


class GenericMarginal:
    """Numerical exact-antiderivative marginal for an explicit 48D vector."""

    def __init__(self, module, basis, vector, normalization,
                 expected_inventory):
        coefficients = defaultdict(Q)
        for theta, (a, lam) in zip(vector, basis):
            distinguished = [(0, lam)] if len(lam) < module.K else []
            for exponent in sorted(set(lam)):
                rest = list(lam)
                rest.remove(exponent)
                distinguished.append((exponent, tuple(rest)))
            for exponent, rest in distinguished:
                for c in range(a + 1):
                    power = exponent + c + 1
                    factor = Q(
                        math.comb(a, c) * math.factorial(exponent) *
                        math.factorial(c), math.factorial(exponent + c + 1))
                    coefficients[(power, rest)] += (
                        theta * factor * (1 - module.ALPHA1) ** (a - c))
        coefficients = {key: value for key, value in coefficients.items()
                        if value}
        if len(coefficients) != expected_inventory:
            raise ArithmeticError("explicit marginal inventory changed")
        self.module = module
        self.orbits = module.PowerSumOrbitEvaluator(
            rest for _, rest in coefficients)
        self.max_residual = max(power for power, _ in coefficients)
        self.normalization = Q(normalization)
        matrix = np.zeros((len(self.orbits.partitions),
                           self.max_residual + 1), dtype=np.longdouble)
        for (power, rest), value in coefficients.items():
            matrix[self.orbits.index[rest], power] += module.ld(
                value / self.normalization)
        self.coefficients = matrix

    def evaluate(self, padded_common):
        points = np.asarray(padded_common, dtype=np.longdouble)
        orbit = self.orbits.evaluate(points)
        residual = self.module.ld(self.module.ALPHA1) - np.sum(
            points, axis=1, dtype=np.longdouble)
        answer = np.zeros(len(points), dtype=np.longdouble)
        power = np.ones(len(points), dtype=np.longdouble)
        for exponent in range(self.max_residual + 1):
            answer += (self.coefficients[:, exponent] @ orbit) * power
            power *= residual
        return answer

    def _omit_chunk(self, points):
        points = np.asarray(points, dtype=np.longdouble)
        n = len(points)
        total = np.sum(points, axis=1, dtype=np.longdouble)
        powers = {}
        current = np.ones_like(points)
        for exponent in range(1, self.orbits.max_power + 1):
            current *= points
            powers[exponent] = (
                np.sum(current, axis=1, dtype=np.longdouble)[:, None] -
                current)
        values = [None] * len(self.orbits.partitions)
        values[self.orbits.index[()]] = np.ones(
            (n, self.module.K), dtype=np.longdouble)
        for index, recurrence in enumerate(self.orbits.recurrences):
            if recurrence is None:
                continue
            exponent, rest, divisor, merges = recurrence
            answer = powers[exponent] * values[rest]
            for merged, multiplicity in merges:
                answer -= multiplicity * values[merged]
            values[index] = answer / divisor
        residual = self.module.ld(self.module.ALPHA1) - total[:, None] + points
        answer = np.zeros((n, self.module.K), dtype=np.longdouble)
        power = np.ones((n, self.module.K), dtype=np.longdouble)
        for exponent in range(self.max_residual + 1):
            active = np.flatnonzero(self.coefficients[:, exponent])
            if len(active):
                combined = np.zeros((n, self.module.K), dtype=np.longdouble)
                for orbit_index in active:
                    combined += (self.coefficients[orbit_index, exponent] *
                                 values[orbit_index])
                answer += combined * power
            power *= residual
        return answer

    def omit_values(self, points, chunk=128):
        points = np.asarray(points, dtype=np.longdouble)
        if (points.ndim != 2 or points.shape[1] != self.module.K or
                chunk <= 0):
            raise ValueError("omit evaluator expects an N-by-48 matrix")
        return np.concatenate([
            self._omit_chunk(points[start:start + chunk])
            for start in range(0, len(points), chunk)], axis=0)

    def riesz(self, points):
        points = np.asarray(points, dtype=np.longdouble)
        common_sums = (np.sum(points, axis=1, dtype=np.longdouble)[:, None] -
                       points)
        eligible = common_sums <= self.module.ld(self.module.ETA2)
        return np.sum(self.omit_values(points) * eligible, axis=1,
                      dtype=np.longdouble)


def configure_hybrid_engine(one_band, basis19, vector19, inner_i19):
    bridge = one_band.configure_engine()
    original_configure = bridge.configure
    original_exact_forms = bridge.exact_forms
    state = {}

    def configure(module, geometry):
        original_configure(module, geometry)
        original_marginal = module.MarginalD18

        class HybridMarginal:
            def __init__(self, basis, vector, inner_scale):
                self.calibration = original_marginal(
                    basis, vector, inner_scale)
                # Normalize D19 with the D18 inner scale so the engine's
                # existing scale cancellation yields raw G_D19/h_D18.
                self.target = GenericMarginal(
                    module, basis19, vector19, inner_scale,
                    EXPECTED_DIMENSION)

            def evaluate(self, padded_common):
                return self.calibration.evaluate(padded_common)

            def riesz(self, points):
                if module.ETA2 == one_band.ETA:
                    return self.target.riesz(points)
                return self.calibration.riesz(points)

        module.MarginalD18 = HybridMarginal
        state["module"] = module
        state["original_marginal"] = original_marginal

    def exact_forms(module, geometry, cert, uncapped):
        forms = original_exact_forms(module, geometry, cert, uncapped)
        a11 = Q(uncapped["I_matrix"][1][1])
        b01 = Q(uncapped["kJ_matrix"][0][1])
        forms["A11_over_A00"] = a11 / inner_i19
        forms["B01_over_A00"] = b01 / inner_i19
        forms["projection_over_A00"] = b01 * b01 / (a11 * inner_i19)
        forms["target_inner_source_path"] = str(D19.relative_to(REPO))
        forms["target_inner_source_sha256"] = D19_SHA256
        return forms

    bridge.configure = configure
    bridge.exact_forms = exact_forms
    return bridge, state


def target_point_calibration(module, basis, vector, seed):
    inner = module.ResidualD18(
        basis, vector, center=module.ALPHA1, dilation=1)
    outer_c = module.ALPHA1 / module.ALPHA2
    outer_vector = module.dilate_vector(basis, vector, outer_c)
    natural = module.ResidualD18(
        basis, vector, center=module.ALPHA2, dilation=outer_c)
    point = module.point_consistency(
        inner, natural, basis, vector, outer_vector, seed + 5000003)
    marginal = GenericMarginal(
        module, basis, vector, inner.scale, EXPECTED_DIMENSION)
    old_eta = module.ETA2
    try:
        module.ETA2 = Q(8960917, 36000000)
        marginal_point = module.marginal_point_consistency(
            inner, marginal, seed + 5000033)
    finally:
        module.ETA2 = old_eta
    return point, marginal_point


def run(*, seed, chains, burn, draws):
    start = {path: path.read_bytes() for path in
             (FILE, ONE_BAND, D19, DIRECT_CHECKER, DIRECT_TEST,
              DIRECT_RESULT, PRODUCER, RUN_BASIS, INTEGRATOR,
              CACHE_READER, SCAN, D18_CERT)}
    one_band = load("active25_d19_one_band_geometry", ONE_BAND,
                    ONE_BAND_SHA256)
    one_band.validate_support()
    d19, direct, basis19, vector19, inner_i19, inner_48j19 = load_d19()
    bridge, state = configure_hybrid_engine(
        one_band, basis19, vector19, inner_i19)
    row = bridge.run(geometry=one_band.GEOMETRY, seed=seed, chains=chains,
                     burn=burn, draws=draws, cap_result=None)
    point, marginal_point = target_point_calibration(
        state["module"], basis19, vector19, seed)
    if any(path.read_bytes() != payload for path, payload in start.items()):
        raise RuntimeError("D19 bridge source closure changed during run")
    lower = row["screen"]["by_radial_band"]["lower_outer"]
    estimate = lower["capped_G_norm_over_inner_I"]
    error = lower["capped_G_norm_standard_error"]
    threshold = (inner_i19 - inner_48j19) / inner_i19
    row["format"] = "active25-d19-truncated-one-band-h2-bridge-v1"
    row["status"] = (row["status"] +
                     "; CACHE-FREE EXACT INNER FORMS")
    row["rigorous"] = False
    row["source_sha256"] = sha256(start[FILE])
    row["geometry_wrapper_source_sha256"] = ONE_BAND_SHA256
    row["target_inner"] = {
        "label": "canonical_degree_19_568_term_krylov20",
        "basis_dimension": EXPECTED_DIMENSION,
        "maximum_weighted_degree": EXPECTED_CANONICAL_DEGREE,
        "artifact": str(D19.relative_to(REPO)),
        "artifact_sha256": D19_SHA256,
        "cache_free_direct_result": str(DIRECT_RESULT.relative_to(REPO)),
        "cache_free_direct_result_sha256": DIRECT_RESULT_SHA256,
        "cache_free_direct_checker_sha256": DIRECT_CHECKER_SHA256,
        "cache_free_direct_test_sha256": DIRECT_TEST_SHA256,
        "cache_free_direct_result_rigorous": True,
        "cache_read_by_direct_checker": False,
        "serialized_matrix_entries_read_by_direct_checker": False,
        "producer_sha256": PRODUCER_SHA256,
        "input_mode": d19["input_mode"],
        "cache_snapshot": str(CACHE),
        "cache_snapshot_sha256": CACHE_SHA256,
        "cache_hits": d19["cache_hits"],
        "cache_misses": d19["cache_misses"],
        "cache_entries_independently_reconstructed": False,
        "selection_provenance_rigorous_given_cache_entries": True,
        "inner_forms_independently_reconstructed_without_cache": True,
        "source_run_sha256": None,
        "rationalization_significant_digits": 75,
        "exact_I": str(inner_i19),
        "exact_48J": str(inner_48j19),
        "exact_deficit_over_I": str(threshold),
        "exact_deficit_over_I_decimal": float(threshold),
    }
    row["proposal"] = {
        "coordinate": "frozen natural D18 outer dilation",
        "reason": "exact A11 and cross calibration already frozen",
        "importance_identity": (
            "I(G_D19*1_V)/I(F_D19)=(I(h_D18)/I(F_D19))*"
            "E_h2[(G_D19/h_D18)^2*1_V]"),
        "proposal_cross_calibration_uses_D18_not_D19": True,
    }
    row["target_point_evaluator_calibration"] = point
    row["target_marginal_antiderivative_calibration"] = marginal_point
    row["screen"]["one_band_capped_G_norm_over_inner_I"] = estimate
    row["screen"]["one_band_capped_G_norm_standard_error"] = error
    row["screen"]["sufficient_threshold"] = float(threshold)
    row["screen"]["exact_sufficient_threshold"] = str(threshold)
    row["screen"]["criterion"] = (
        "I(G_D19*1_V)/I(F_D19) > 1-48J(F_D19,F_D19)/I(F_D19)")
    row["screen"]["lower_two_standard_errors"] = estimate - 2 * error
    row["screen"]["upper_two_standard_errors"] = estimate + 2 * error
    row["screen"]["conditional_decision"] = (
        "GATED EXACT COMPUTATION WARRANTED" if estimate - 2 * error >
        float(threshold) else "HEURISTIC INCONCLUSIVE" if
        estimate + 2 * error >= float(threshold) else
        "HEURISTIC FALSIFICATION")
    row["source_hashes"][str(ONE_BAND.relative_to(REPO))] = ONE_BAND_SHA256
    row["source_hashes"][str(D19.relative_to(REPO))] = D19_SHA256
    row["source_hashes"][str(DIRECT_CHECKER.relative_to(REPO))] = \
        DIRECT_CHECKER_SHA256
    row["source_hashes"][str(DIRECT_TEST.relative_to(REPO))] = \
        DIRECT_TEST_SHA256
    row["source_hashes"][str(DIRECT_RESULT.relative_to(REPO))] = \
        DIRECT_RESULT_SHA256
    row["source_hashes"][str(PRODUCER.relative_to(REPO))] = PRODUCER_SHA256
    row["source_hashes"][str(RUN_BASIS.relative_to(REPO))] = RUN_BASIS_SHA256
    row["source_hashes"][str(INTEGRATOR.relative_to(REPO))] = INTEGRATOR_SHA256
    row["source_hashes"][str(CACHE_READER.relative_to(REPO))] = \
        CACHE_READER_SHA256
    row["source_hashes"][str(SCAN.relative_to(REPO))] = SCAN_SHA256
    row["selection_cache_sha256_recorded_but_not_read"] = CACHE_SHA256
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
        "decision": row["screen"]["conditional_decision"],
        "wall_seconds": row["wall_seconds"],
        "peak_rss_kib": row["peak_rss_kib"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
