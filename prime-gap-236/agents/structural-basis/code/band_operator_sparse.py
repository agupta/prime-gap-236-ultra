#!/usr/bin/env python3
"""Sparse/structure-of-arrays degree-band value-and-gradient operator.

This discovery operator is algebraically equivalent to ``band_operator.py``.
It exploits the fact that every expanded label belongs to exactly one band:

* an F^2 label-pair has at most two nonzero owner derivatives;
* marginal direction blocks partition the scalar marginal components;
* summing branch products over all directions therefore costs only one or two
  additional full bilinear contractions, rather than twenty dense Jet
  contractions.

Support geometry and scalar moments are inherited unchanged from the audited
``GroupedEvaluator``.  A candidate still requires scalar exact reconstruction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import resource
import sys
import time
from collections import defaultdict
from decimal import Decimal, getcontext
from fractions import Fraction
from math import comb
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
EXACT_AGENT = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator"))
sys.path[:0] = [HERE, EXACT_AGENT, os.path.join(EXACT_AGENT, "src")]

import exact_integrator as ei  # noqa: E402
from band_operator import BandMap, _parse_decimal  # noqa: E402
from grouped_fixed_vector import (GroupedEvaluator, add_poly, install_decimal,  # noqa: E402
                                  precompute_orbits)


_FORK_SPARSE = None
_FORK_I_GROUPED = None
_FORK_J_COMPONENTS = None


def _fork_i(r):
    return _FORK_SPARSE.evaluate_i_r(_FORK_I_GROUPED, r, False)


def _fork_j(r):
    return _FORK_SPARSE.evaluate_j_r(_FORK_J_COMPONENTS, r, False)


class SparseBandOperator(GroupedEvaluator):
    def __init__(self, support, band_map, theta, scalar):
        self.band_map = band_map
        self.channel_count = band_map.dimension + 1
        self.theta = tuple(theta)
        if len(theta) != band_map.dimension:
            raise ValueError("theta dimension mismatch")
        if scalar is Fraction:
            weights = list(band_map.weight_q)
        else:
            weights = [scalar(q.numerator) / scalar(q.denominator)
                       for q in band_map.weight_q]
        coefficients = [weights[i] * theta[band_map.owner[i]]
                        for i in range(len(band_map.labels))]
        super().__init__(support, list(band_map.labels), coefficients, scalar)
        self.weights = weights

    def _new_cell(self):
        return [self.zero, {}]

    def square_residual_channels(self):
        """Map nu,c to [value,{owner: derivative}] with sparse pair updates."""
        terms = {}
        for i, (a, lam) in enumerate(self.labels):
            ci, wi, oi = (self.coefficients[i], self.weights[i],
                          self.band_map.owner[i])
            for j in range(i + 1):
                b, mu = self.labels[j]
                cj, wj, oj = (self.coefficients[j], self.weights[j],
                              self.band_map.owner[j])
                if i == j:
                    value_factor = ci * ci
                    derivatives = ((oi, self.scalar(2) * ci * wi),)
                else:
                    value_factor = self.scalar(2) * ci * cj
                    if oi == oj:
                        derivatives = ((oi, self.scalar(2) *
                                        (wi * cj + ci * wj)),)
                    else:
                        derivatives = ((oi, self.scalar(2) * wi * cj),
                                       (oj, self.scalar(2) * ci * wj))
                total = a + b
                for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                    for c in range(total + 1):
                        residual_factor = (self.scalar(multiplicity * comb(total, c)) *
                                           (self.one - self.support.alpha) **
                                           (total - c))
                        key = (nu, c)
                        cell = terms.get(key)
                        if cell is None:
                            cell = self._new_cell()
                            terms[key] = cell
                        cell[0] += value_factor * residual_factor
                        grad = cell[1]
                        for owner, derivative in derivatives:
                            grad[owner] = (grad.get(owner, self.zero) +
                                           derivative * residual_factor)
        grouped = defaultdict(dict)
        for (nu, c), (value, gradient) in terms.items():
            gradient = {d: x for d, x in gradient.items() if x}
            if value or gradient:
                grouped[nu][c] = (value, gradient)
        return dict(grouped)

    def _integrate_channels(self, channels, dimension, r, outer, constraints):
        """One scalar geometry moment per monomial, dotted into all channels."""
        monomials = set()
        for poly in channels:
            monomials.update(poly)
        moments = {mon: self.integrate_domain(
            {mon: self.one}, dimension, r, outer, constraints)
                   for mon in monomials}
        return tuple(sum((coefficient * moments[mon]
                          for mon, coefficient in poly.items()), self.zero)
                     for poly in channels)

    def evaluate_i_r(self, grouped, r, progress=False):
        answer = [self.zero] * self.channel_count
        dimension = self.support.k
        faces = 0
        max_h = int(self.support.alpha // self.support.delta) - r
        if max_h < 0:
            return tuple(answer), faces
        constraints = ()
        if r:
            cap = self.support.beta(r) - r * self.support.delta
            if cap <= 0:
                return tuple(answer), faces
            constraints = ((self.one, self.zero, cap),)
        for h in range(max_h + 1):
            outer = self.support.alpha - (r + h) * self.support.delta
            if outer <= 0:
                continue
            total = [defaultdict(self.scalar) for _ in range(self.channel_count)]
            for nu, residuals in grouped.items():
                density = self.orbit_density(dimension, nu, r, h, max_h)
                if not density:
                    continue
                for c, (value, gradient) in residuals.items():
                    power = ei._linear_power(outer, -self.one, -self.one, c)
                    for (di, dj), density_value in density.items():
                        for (pi, pj), power_value in power:
                            monomial = (di + pi, dj + pj)
                            base = density_value * power_value
                            if value:
                                total[0][monomial] += base * value
                            for owner, derivative in gradient.items():
                                total[owner + 1][monomial] += base * derivative
            values = self._integrate_channels(
                total, dimension, r, outer, constraints)
            for channel, value in enumerate(values):
                answer[channel] += value
            faces += 1
            if progress:
                print(f"sparse I r={r} h={h} faces={faces}", flush=True)
            self.clear_face_caches()
        self.clear_radial_caches()
        return tuple(answer), faces

    def evaluate_i(self, progress=False, workers=1):
        grouped = self.square_residual_channels()
        r_values = list(range(min(self.support.k, self.support.max_large()) + 1))
        if workers == 1:
            results = [self.evaluate_i_r(grouped, r, progress) for r in r_values]
        else:
            global _FORK_SPARSE, _FORK_I_GROUPED
            _FORK_SPARSE, _FORK_I_GROUPED = self, grouped
            try:
                with multiprocessing.get_context("fork").Pool(workers) as pool:
                    results = pool.map(_fork_i, r_values, chunksize=1)
            finally:
                _FORK_SPARSE = _FORK_I_GROUPED = None
        answer = [self.zero] * self.channel_count
        for values, _ in results:
            for channel, value in enumerate(values):
                answer[channel] += value
        self.i_channels_by_r = {
            r: values for r, (values, _) in zip(r_values, results)}
        return tuple(answer), len(grouped), sum(x[1] for x in results)

    def marginal_component_channels(self):
        """Scalar components and per-owner derivative components."""
        value = defaultdict(self.scalar)
        directions = [defaultdict(self.scalar)
                      for _ in range(self.band_map.dimension)]
        for coefficient, weight, owner, (a, lam) in zip(
                self.coefficients, self.weights, self.band_map.owner, self.labels):
            for e, lr in self.support.split_at_distinguished(lam, self.support.k):
                key = (lr, e, a)
                value[key] += coefficient
                directions[owner][key] += weight
        return ({k: x for k, x in value.items() if x},
                [{k: x for k, x in block.items() if x} for block in directions])

    @staticmethod
    def _by_lr(components):
        lrs = sorted({lr for lr, _, _ in components})
        return (lrs, {lr: [(e, a, value)
                           for (x, e, a), value in components.items() if x == lr]
                      for lr in lrs})

    def _branch_block(self, r, h, branch, lrs, by_lr):
        block = {}
        for lr in lrs:
            poly = defaultdict(self.scalar)
            for e, a, value in by_lr[lr]:
                add_poly(poly, dict(self.support._marginal_poly(
                    r, h, branch, e, a)), value)
            if poly:
                block[lr] = dict(poly)
        return block

    def _ordered_product(self, left, right, factor=1):
        combined = {}
        scalar_factor = self.scalar(factor)
        for lr, p in left.items():
            for mr, q in right.items():
                pq = ei._poly_mul(p, q)
                for nu, multiplicity in ei.multiply_monomial_orbits(lr, mr):
                    dest = combined.setdefault(nu, defaultdict(self.scalar))
                    add_poly(dest, pq, scalar_factor * multiplicity)
        return {nu: dict(poly) for nu, poly in combined.items() if poly}

    def _add_combined(self, target, source):
        for nu, poly in source.items():
            dest = target.setdefault(nu, defaultdict(self.scalar))
            add_poly(dest, poly, self.one)

    def branch_product_channels(self, left_value, right_value,
                                left_dirs, right_dirs, same_branch):
        channels = [{} for _ in range(self.channel_count)]
        channels[0] = self.branch_orbit_product(
            left_value, right_value, same_branch)
        for direction in range(self.band_map.dimension):
            if same_branch:
                if left_dirs[direction]:
                    channels[direction + 1] = self._ordered_product(
                        left_value, left_dirs[direction], 2)
            else:
                block = {}
                if left_dirs[direction]:
                    self._add_combined(block, self._ordered_product(
                        left_dirs[direction], right_value, 2))
                if right_dirs[direction]:
                    self._add_combined(block, self._ordered_product(
                        left_value, right_dirs[direction], 2))
                channels[direction + 1] = {
                    nu: dict(poly) for nu, poly in block.items() if poly}
        return channels

    def evaluate_j_r(self, component_data, r, progress=False):
        value_data, direction_data = component_data
        value_lrs, value_by_lr = value_data
        direction_lr_data = direction_data
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        answer = [self.zero] * self.channel_count
        dimension = self.support.k - 1
        integrals = 0
        max_h = int(self.support.eta // self.support.delta) - r
        if max_h < 0:
            return tuple(answer), integrals
        for h in range(max_h + 1):
            if dimension == 0 and (r != 0 or h != 0):
                continue
            outer = self.support.eta - (r + h) * self.support.delta
            if outer <= 0:
                continue
            branch_values = {}
            branch_dirs = {}
            for branch in branches:
                constraints = self.support._branch_constraints(r, h, branch)
                if dimension == 0:
                    interval = self.support._branch_interval(0, 0, branch)
                    active = (interval is not None and
                              interval[0] <= 0 <= interval[1])
                else:
                    active = (constraints is not None and self.integrate_domain(
                        {(0, 0): self.one}, dimension, r, outer, constraints) > 0)
                if not active:
                    branch_values[branch] = {}
                    branch_dirs[branch] = [{} for _ in direction_lr_data]
                    continue
                branch_values[branch] = self._branch_block(
                    r, h, branch, value_lrs, value_by_lr)
                branch_dirs[branch] = [self._branch_block(
                    r, h, branch, lrs, by_lr) if lrs else {}
                    for lrs, by_lr in direction_lr_data]
            for i, left_branch in enumerate(branches):
                left_value = branch_values[left_branch]
                for j in range(i + 1):
                    right_branch = branches[j]
                    right_value = branch_values[right_branch]
                    if (dimension != 0 and
                            ({left_branch, right_branch} == {"Sdelta", "Stotal"} or
                             {left_branch, right_branch} == {"Ltotal", "Lbig"})):
                        continue
                    constraints = self.branch_domain(
                        r, h, left_branch, right_branch)
                    if (constraints is None or self.integrate_domain(
                            {(0, 0): self.one}, dimension, r, outer,
                            constraints) <= 0):
                        continue
                    combined = self.branch_product_channels(
                        left_value, right_value,
                        branch_dirs[left_branch], branch_dirs[right_branch],
                        i == j)
                    if not any(combined):
                        continue
                    total = [defaultdict(self.scalar)
                             for _ in range(self.channel_count)]
                    all_nu = set().union(*(block.keys() for block in combined))
                    for nu in all_nu:
                        density = self.orbit_density(
                            dimension, nu, r, h, max_h)
                        if not density:
                            continue
                        for channel, block in enumerate(combined):
                            marginal_poly = block.get(nu)
                            if marginal_poly:
                                add_poly(total[channel],
                                         ei._poly_mul(density, marginal_poly),
                                         self.one)
                    values = self._integrate_channels(
                        total, dimension, r, outer, constraints)
                    for channel, value in enumerate(values):
                        answer[channel] += value
                    integrals += 1
            if progress:
                print(f"sparse J r={r} h={h} integrals={integrals}", flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return tuple(answer), integrals

    def evaluate_j(self, progress=False, workers=1):
        component_values, directions = self.marginal_component_channels()
        component_data = (self._by_lr(component_values),
                          [self._by_lr(block) for block in directions])
        r_values = list(range(min(self.support.k - 1,
                                  self.support.max_large()) + 1))
        if workers == 1:
            results = [self.evaluate_j_r(component_data, r, progress)
                       for r in r_values]
        else:
            global _FORK_SPARSE, _FORK_J_COMPONENTS
            _FORK_SPARSE, _FORK_J_COMPONENTS = self, component_data
            try:
                with multiprocessing.get_context("fork").Pool(workers) as pool:
                    results = pool.map(_fork_j, r_values, chunksize=1)
            finally:
                _FORK_SPARSE = _FORK_J_COMPONENTS = None
        answer = [self.zero] * self.channel_count
        for values, _ in results:
            for channel, channel_value in enumerate(values):
                answer[channel] += channel_value
        self.j_channels_by_r = {
            r: values for r, (values, _) in zip(r_values, results)}
        count = len(component_values)
        return tuple(answer), count, sum(x[1] for x in results)

    def apply(self, progress=False, workers=1):
        start = time.perf_counter()
        i_channels, i_groups, i_faces = self.evaluate_i(progress, workers)
        after_i = time.perf_counter()
        j_channels, components, j_integrals = self.evaluate_j(progress, workers)
        after_j = time.perf_counter()
        k, two = self.scalar(self.support.k), self.scalar(2)
        denominator, numerator = i_channels[0], k * j_channels[0]
        grad_d = i_channels[1:]
        grad_n = tuple(k * x for x in j_channels[1:])
        return {
            "denominator": denominator,
            "numerator": numerator,
            "quotient": numerator / denominator,
            "a_theta": tuple(x / two for x in grad_d),
            "b_theta": tuple(x / two for x in grad_n),
            "grad_denominator": grad_d,
            "grad_numerator": grad_n,
            "euler_denominator_error": sum(
                (x * y for x, y in zip(self.theta, grad_d)), self.zero) -
                two * denominator,
            "euler_numerator_error": sum(
                (x * y for x, y in zip(self.theta, grad_n)), self.zero) -
                two * numerator,
            "i_orbit_groups": i_groups,
            "i_faces": i_faces,
            "marginal_components": components,
            "j_branch_integrals": j_integrals,
            "i_seconds": after_i - start,
            "j_seconds": after_j - after_i,
            "total_seconds": after_j - start,
            "i_value_by_r": tuple(self.i_channels_by_r[r][0]
                                  for r in sorted(self.i_channels_by_r)),
            "j_value_by_r": tuple(self.j_channels_by_r[r][0]
                                  for r in sorted(self.j_channels_by_r)),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--bands", required=True)
    ap.add_argument("--decimal-dps", type=int, default=90)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--alpha", default="79247/300000")
    ap.add_argument("--delta", default="1/100")
    ap.add_argument("--eta", default="76247/300000")
    ap.add_argument("--beta1", default="3/20")
    ap.add_argument("--beta2", default="3/20")
    ap.add_argument("--beta3plus", default="97/625")
    ap.add_argument("--progress", action="store_true")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    operator_path = Path(__file__)
    band_dependency_path = Path(HERE) / "band_operator.py"
    grouped_path = Path(os.path.join(EXACT_AGENT, "grouped_fixed_vector.py"))
    integrator_path = Path(ei.__file__)
    operator_hash_start = hashlib.sha256(operator_path.read_bytes()).hexdigest()
    band_dependency_hash_start = hashlib.sha256(
        band_dependency_path.read_bytes()).hexdigest()
    grouped_hash_start = hashlib.sha256(grouped_path.read_bytes()).hexdigest()
    integrator_hash_start = hashlib.sha256(integrator_path.read_bytes()).hexdigest()
    getcontext().prec = args.decimal_dps
    band_map = BandMap.from_source_and_bands(args.source, args.bands)
    source = json.loads(Path(args.source).read_bytes())
    if int(source.get("k", -1)) != 48:
        raise SystemExit("this pinned driver requires source k=48")
    orbit_table = precompute_orbits(list(band_map.labels), 48)
    install_decimal(orbit_table, args.decimal_dps)
    support = ei.OneStratumSupport(
        48, *[_parse_decimal(x) for x in
              (args.alpha, args.delta, args.eta, args.beta1,
               args.beta2, args.beta3plus)])
    _, theta = band_map.scalars(_parse_decimal)
    result = SparseBandOperator(
        support, band_map, theta, Decimal).apply(args.progress, args.workers)
    operator_hash_end = hashlib.sha256(operator_path.read_bytes()).hexdigest()
    band_dependency_hash_end = hashlib.sha256(
        band_dependency_path.read_bytes()).hexdigest()
    grouped_hash_end = hashlib.sha256(grouped_path.read_bytes()).hexdigest()
    integrator_hash_end = hashlib.sha256(integrator_path.read_bytes()).hexdigest()
    expected_params = {
        "alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
        "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
        "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625),
    }
    actual_param_text = {
        "alpha": args.alpha, "delta": args.delta, "eta": args.eta,
        "beta1": args.beta1, "beta2": args.beta2,
        "beta3plus": args.beta3plus,
    }
    baseline_path = Path(EXACT_AGENT) / "results" / \
        "c10_capped_fullD12_vector_grouped_mp100.json"
    baseline_bytes = baseline_path.read_bytes()
    baseline = json.loads(baseline_bytes)
    baseline_sha = hashlib.sha256(baseline_bytes).hexdigest()
    tolerance = Decimal(1).scaleb(-50)

    def close_relative(x, y):
        return abs(x - y) <= tolerance * abs(y)

    numeric_vectors = [theta, result["a_theta"], result["b_theta"],
                       result["grad_denominator"], result["grad_numerator"]]
    euler_d_relative = (abs(result["euler_denominator_error"]) /
                        abs(result["denominator"]))
    euler_n_relative = (abs(result["euler_numerator_error"]) /
                        abs(result["numerator"]))
    gates = {
        "decimal_dps_at_least_90": args.decimal_dps >= 90,
        "source_sha_pinned": band_map.source_sha256 ==
            "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
        "bands_sha_pinned": band_map.bands_sha256 ==
            "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9",
        "operator_unchanged_during_run": operator_hash_start == operator_hash_end,
        "band_dependency_sha_pinned_and_unchanged": band_dependency_hash_start ==
            band_dependency_hash_end ==
            "e4fbf7a97d061d362c32b54bf0d49a89c4195b965e96d7ab89a2581bc907c073",
        "grouped_sha_pinned_and_unchanged": grouped_hash_start == grouped_hash_end ==
            "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
        "integrator_sha_pinned_and_unchanged": integrator_hash_start ==
            integrator_hash_end ==
            "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
        "source_k48_dim272_banddim20": (int(source.get("k", -1)) == 48 and
            len(band_map.labels) == 272 and band_map.dimension == 20),
        "parameters_exact_c10": all(Fraction(actual_param_text[key]) == value
                                    for key, value in expected_params.items()),
        "all_vectors_length20": all(len(vector) == 20 for vector in numeric_vectors),
        "all_numbers_finite": all(x.is_finite() for vector in numeric_vectors
                                  for x in vector) and all(
            result[key].is_finite() for key in
            ("denominator", "numerator", "quotient",
             "euler_denominator_error", "euler_numerator_error")),
        "gradient_halves_match": (all(a * 2 == g for a, g in zip(
            result["a_theta"], result["grad_denominator"])) and all(
            b * 2 == g for b, g in zip(
                result["b_theta"], result["grad_numerator"]))),
        "denominator_positive": result["denominator"] > 0,
        "quotient_recomputed": result["quotient"] ==
            result["numerator"] / result["denominator"],
        "euler_relative_below_1e50": (euler_d_relative <= tolerance and
                                      euler_n_relative <= tolerance),
        "complete_traversal_counts": (result["i_orbit_groups"] == 1575 and
            result["i_faces"] == 312 and result["marginal_components"] == 695 and
            result["j_branch_integrals"] == 1200),
        "stratum_buckets_sum": (sum(result["i_value_by_r"], Decimal(0)) ==
            result["denominator"] and 48 * sum(
                result["j_value_by_r"], Decimal(0)) == result["numerator"]),
        "baseline_artifact_sha_pinned": baseline_sha ==
            "02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9",
        "baseline_dependencies_match": (baseline.get("input_sha256") ==
            band_map.source_sha256 and baseline.get("script_sha256") ==
            grouped_hash_start and baseline.get("integrator_sha256") ==
            integrator_hash_start and baseline.get("parameters") ==
            {key: str(value) for key, value in expected_params.items()}),
        "baseline_forms_50_digits": (close_relative(
            result["denominator"], Decimal(baseline["denominator"])) and
            close_relative(result["numerator"], Decimal(baseline["numerator"])) and
            close_relative(result["quotient"], Decimal(baseline["quotient"]))),
    }
    gates_passed = all(gates.values())
    output = {
        "status": ("multiprecision-degree-band-gradient-discovery" if gates_passed
                   else "rejected-degree-band-gradient-discovery"),
        "implementation": "sparse-structure-of-arrays",
        "rigorous": False,
        "complete": True,
        "decimal_dps": args.decimal_dps,
        "workers": args.workers,
        "source_json": args.source,
        "source_sha256": band_map.source_sha256,
        "bands_json": args.bands,
        "bands_sha256": band_map.bands_sha256,
        "operator_sha256": operator_hash_start,
        "band_operator_dependency_sha256": band_dependency_hash_start,
        "integrator_sha256": integrator_hash_start,
        "grouped_evaluator_sha256": grouped_hash_start,
        "baseline_json": str(baseline_path),
        "baseline_sha256": baseline_sha,
        "parameters": {"alpha": args.alpha, "delta": args.delta,
                       "eta": args.eta, "beta1": args.beta1,
                       "beta2": args.beta2, "beta3plus": args.beta3plus},
        "theta": [str(x) for x in theta],
        **{key: ([str(x) for x in value] if isinstance(value, tuple) else
                 str(value) if isinstance(value, Decimal) else value)
           for key, value in result.items()},
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "gates_passed": gates_passed,
        "gates": gates,
        "euler_denominator_relative": str(euler_d_relative),
        "euler_numerator_relative": str(euler_n_relative),
        "baseline_relative_tolerance": str(tolerance),
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    if not gates_passed:
        raise SystemExit("gradient discovery failed one or more fail-closed gates")


if __name__ == "__main__":
    main()
