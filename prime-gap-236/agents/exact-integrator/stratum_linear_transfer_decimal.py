#!/usr/bin/env python3
"""Decimal direct traversal for a transferred per-stratum affine multiplier.

This is a cheap discovery probe: it applies one already-rational affine
multiplier vector to a different fixed polynomial.  The denominator may be
contracted from a source-pinned batched I-stage, while J is rebuilt after
inserting the multiplier before branch squaring.  It does not claim that the
transferred vector optimizes the new finite-dimensional space.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import resource
import sys
import time
from collections import defaultdict
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import (  # noqa: E402
    add_poly,
    install_decimal,
    precompute_orbits,
)
from stratum_linear import StratumLinearEvaluator  # noqa: E402


PINNED = {
    "stratum_amplitude":
        "d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887",
    "stratum_linear":
        "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
    "grouped":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "robust_solver":
        "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e",
}
PINNED_MATRIX_DRIVER_SHA = \
    "ba3ff83b186e7784634a97bf82f13ae3abdd4a4e753b226f0eaed23d659dfbc0"
EXPECTED_STAGE_DEPENDENCIES = {
    "driver": PINNED_MATRIX_DRIVER_SHA,
    "stratum_linear": PINNED["stratum_linear"],
    "grouped": PINNED["grouped"],
    "integrator": PINNED["integrator"],
    "robust_solver": PINNED["robust_solver"],
}
PARAMETERS = {
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
    "beta1": "3/20",
    "beta2": "3/20",
    "beta3plus": "97/625",
}


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_pinned_bytes(path, expected_sha256, description):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise SystemExit(
            f"{description} SHA-256 mismatch: expected {expected_sha256}, "
            f"got {actual}")
    return raw, actual


def require_exact_stage_dependencies(value):
    if value != EXPECTED_STAGE_DEPENDENCIES:
        raise SystemExit("I-stage dependency dictionary is not exactly pinned")


def parse_stage_entries(raw):
    answer = {}
    for token, value in raw.items():
        key = ast.literal_eval(token)
        if not (isinstance(key, tuple) and len(key) == 2):
            raise ValueError("malformed staged I key")
        answer[key] = Decimal(value)
    return answer


def contract(entries, coefficients):
    answer = next(iter(entries.values()), Decimal(0)) * 0
    for (left, right), value in entries.items():
        term = coefficients.get(left, Decimal(0)) * \
            coefficients.get(right, Decimal(0)) * value
        answer += term * (1 if left == right else 2)
    return answer


class TransferEvaluator(StratumLinearEvaluator):
    def evaluate_j_r_transfer(self, lrs, by_lr, amplitudes, r,
                              progress=False):
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        dimension = self.support.k - 1
        max_h = int(self.support.eta // self.support.delta) - r
        answer = self.zero
        domains = 0
        if max_h < 0:
            return answer, domains
        for h in range(max_h + 1):
            outer = self.support.eta - (r + h) * self.support.delta
            if outer <= 0:
                continue
            channels = self._channel_branch_blocks(
                lrs, by_lr, r, h, dimension, outer)
            combined = {}
            for branch in branches:
                total_r = r if branch in self.SMALL_BRANCHES else r + 1
                vector = amplitudes.get(
                    total_r, (self.zero, self.zero, self.zero))
                combined[branch] = self._combine_channel_blocks(
                    channels[branch], vector)
            for i, left in enumerate(branches):
                for right in branches[:i + 1]:
                    value = self._integrate_branch_pair(
                        combined, left, right, dimension, r, h,
                        outer, max_h)
                    if value is not None:
                        answer += value
                        domains += 1
            if progress:
                print(f"transfer J r={r} h={h} domains={domains}",
                      flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return answer, domains


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("multiplier_json")
    parser.add_argument("i_stage_json")
    parser.add_argument("--expect-input-sha256", required=True)
    parser.add_argument("--expect-multiplier-sha256", required=True)
    parser.add_argument("--expect-i-stage-sha256", required=True)
    parser.add_argument("--decimal-dps", type=int, default=100)
    parser.add_argument("--linear-cutoff", type=int, default=11)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.decimal_dps < 90 or not 0 <= args.linear_cutoff <= 15:
        parser.error("require dps>=90 and 0<=linear-cutoff<=15")

    paths = {
        "driver": Path(__file__),
        "stratum_amplitude": HERE / "stratum_amplitude.py",
        "stratum_linear": HERE / "stratum_linear.py",
        "grouped": HERE / "grouped_fixed_vector.py",
        "integrator": HERE / "src/exact_integrator.py",
        "robust_solver": HERE / "robust_generalized_solve.py",
    }
    hashes_start = {key: file_sha(path) for key, path in paths.items()}
    if any(hashes_start[key] != value for key, value in PINNED.items()):
        raise SystemExit("pinned arithmetic dependency mismatch")
    input_bytes, input_sha = read_pinned_bytes(
        args.input_json, args.expect_input_sha256, "fixed-polynomial input")
    multiplier_bytes, multiplier_sha = read_pinned_bytes(
        args.multiplier_json, args.expect_multiplier_sha256,
        "transferred multiplier")
    raw = json.loads(input_bytes)
    multiplier = json.loads(multiplier_bytes)
    if int(raw.get("k", -1)) != 48 or int(multiplier.get("k", -1)) != 48:
        raise SystemExit("this transfer probe is pinned to k=48")
    if multiplier.get("status") != "exact-stratum-linear-rational-vector" or \
            not multiplier.get("rigorous_forms") or \
            not multiplier.get("block_direct_bitwise_equal"):
        raise SystemExit("multiplier source did not pass its exact gates")
    source_labels = [(int(r), ("1", "L", "Z").index(channel))
                     for r, channel in multiplier["linear_labels"]]
    if source_labels != [(r, p) for r in range(16) for p in range(3)]:
        raise SystemExit("multiplier coordinate list is malformed")
    source_vector = [Fraction(x) for x in multiplier["rational_vector"]]
    if len(source_vector) != 48:
        raise SystemExit("multiplier vector dimension mismatch")

    stage_bytes, stage_sha = read_pinned_bytes(
        args.i_stage_json, args.expect_i_stage_sha256, "I-stage")
    stage = json.loads(stage_bytes)
    if stage.get("status") != "multiprecision-stratum-linear-I-stage" or \
            not stage.get("complete") or stage.get("rigorous") is not False:
        raise SystemExit("malformed I-stage status")
    if int(stage.get("decimal_dps", -1)) != args.decimal_dps or \
            int(stage.get("linear_cutoff", -1)) != args.linear_cutoff or \
            stage.get("input_sha256") != input_sha or \
            stage.get("parameters") != PARAMETERS:
        raise SystemExit("I-stage parameters/input do not match transfer")
    require_exact_stage_dependencies(stage.get("dependency_hashes"))
    expected_nominal = 16 + 2 * (args.linear_cutoff + 1)
    if int(stage.get("nominal_dimension", -1)) != expected_nominal:
        raise SystemExit("I-stage nominal dimension is inconsistent")
    if (stage.get("i_orbit_groups"), stage.get("i_faces")) != \
            ((20 if len(raw["basis"]) == 12 else 1575), 312):
        raise SystemExit("I-stage traversal counts are incomplete")

    getcontext().prec = args.decimal_dps
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    rational_base = [Fraction(x) for x in raw["rational_vector"]]
    if len(labels) != len(rational_base) or len(labels) not in (12, 272):
        raise SystemExit("fixed polynomial basis/vector mismatch")
    orbit_table = precompute_orbits(labels, 48)
    scalar = install_decimal(orbit_table, args.decimal_dps)
    support = ei.OneStratumSupport(
        48, *[scalar(Fraction(PARAMETERS[key]).numerator,
                     Fraction(PARAMETERS[key]).denominator)
              for key in ("alpha", "delta", "eta", "beta1", "beta2",
                          "beta3plus")])
    base = [scalar(x.numerator, x.denominator) for x in rational_base]
    evaluator = TransferEvaluator(support, labels, base, scalar)
    coefficients = {
        label: (scalar(value.numerator, value.denominator)
                if label[1] == 0 or label[0] <= args.linear_cutoff
                else scalar(0))
        for label, value in zip(source_labels, source_vector)
    }
    amplitudes = {r: tuple(coefficients[(r, p)] for p in range(3))
                  for r in range(16)}
    i_entries = parse_stage_entries(stage["i_entries"])
    expected_i_keys = {((r, p), (r, q)) for r in range(16)
                       for p in ((0, 1, 2)
                                 if r <= args.linear_cutoff else (0,))
                       for q in ((0, 1, 2)
                                 if r <= args.linear_cutoff else (0,))
                       if q <= p}
    if set(i_entries) != expected_i_keys:
        raise SystemExit("I-stage entry set is incomplete")
    i_by_r = [contract({key: value for key, value in i_entries.items()
                        if key[0][0] == r}, coefficients)
              for r in range(16)]
    denominator = sum(i_by_r, Decimal(0))
    if denominator <= 0:
        raise ArithmeticError("transferred multiplier denominator is not positive")

    components, lrs, by_lr = evaluator._j_component_data()
    start = time.perf_counter()
    j_by_r = []
    domains = 0
    for r in evaluator._r_values_j():
        value, count = evaluator.evaluate_j_r_transfer(
            lrs, by_lr, amplitudes, r, args.progress)
        j_by_r.append(value)
        domains += count
    j_seconds = time.perf_counter() - start
    numerator = scalar(48) * sum(j_by_r, evaluator.zero)
    quotient = numerator / denominator
    hashes_end = {key: file_sha(path) for key, path in paths.items()}
    stage_sha_end = file_sha(args.i_stage_json)
    gates = {
        "dependencies_unchanged": hashes_start == hashes_end,
        "i_stage_unchanged": stage_sha_end == stage_sha,
        "input_and_multiplier_pinned": True,
        "i_stage_complete": True,
        "denominator_positive": denominator > 0,
        "j_counts_complete": len(components) ==
            (19 if len(labels) == 12 else 695) and domains == 1200,
        "finite": all(x.is_finite() for x in
                      (denominator, numerator, quotient)),
    }
    passed = all(gates.values())
    output = {
        "status": ("multiprecision-transferred-affine-candidate" if passed
                   else "rejected-transferred-affine-candidate"),
        "rigorous": False,
        "complete": True,
        "space_note": ("one transferred rational multiplier candidate; "
                       "not the D12 affine-space optimum"),
        "theorem_ready": False,
        "historical_transitive_provenance_limitation": (
            "the already-running I-stage producer did not record its "
            "transitive stratum_amplitude.py hash; this transfer pins and "
            "checks the current file, but a positive theorem run must be "
            "recomputed end-to-end with the generator recording it"),
        "decimal_dps": args.decimal_dps,
        "linear_cutoff": args.linear_cutoff,
        "input_json": args.input_json,
        "input_sha256": input_sha,
        "multiplier_json": args.multiplier_json,
        "multiplier_sha256": multiplier_sha,
        "i_stage_json": args.i_stage_json,
        "i_stage_sha256": stage_sha,
        "parameters": PARAMETERS,
        "dependency_hashes": hashes_start,
        "fixed_basis_dimension": len(labels),
        "multiplier_dimension": 48,
        "transferred_vector": [str(coefficients[label])
                               for label in source_labels],
        "denominator": str(denominator),
        "numerator": str(numerator),
        "quotient": str(quotient),
        "margin": str(numerator - denominator),
        "denominator_positive": True,
        "margin_positive": numerator > denominator,
        "marginal_components": len(components),
        "j_branch_domains": domains,
        "i_by_r": [str(x) for x in i_by_r],
        "j_by_common_r": [str(x) for x in j_by_r],
        "j_seconds": j_seconds,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "gates": gates,
        "gates_passed": passed,
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in (
        "status", "quotient", "margin", "margin_positive",
        "j_seconds", "peak_rss_kib", "gates_passed")}, indent=2))
    if not passed:
        raise SystemExit("transferred candidate failed a gate")


if __name__ == "__main__":
    main()
