#!/usr/bin/env python3
"""Batched multiprecision D1 stratum-multiplier discovery.

This is a discovery-only port for a fixed high-degree polynomial.  It batches
the {1,L,Z} channel moments so each geometric monomial and orbit density is
evaluated once per face/branch pair, stages I before J, records per-R mass, and
uses a symmetric all-spectrum Decimal Cholesky/Jacobi solve.  A positive
candidate would still need independent exact reconstruction.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import multiprocessing
import os
import resource
import sys
import time
from collections import defaultdict
from decimal import Decimal, getcontext, localcontext
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
from robust_generalized_solve import (  # noqa: E402
    cholesky,
    dot,
    inverse_lower,
    jacobi_symmetric,
    matmul,
    matvec,
    transpose,
)
from stratum_linear import StratumLinearEvaluator  # noqa: E402


PINNED_DEPENDENCY_HASHES = {
    "stratum_linear":
        "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
    "grouped":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "robust_solver":
        "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e",
}


_FORK_EVALUATOR = None
_FORK_I_GROUPED = None
_FORK_J_DATA = None


def _fork_i(r):
    return _FORK_EVALUATOR.evaluate_i_r_batched(_FORK_I_GROUPED, r, False)


def _fork_j(r):
    return _FORK_EVALUATOR.evaluate_j_r_batched(_FORK_J_DATA, r, False)


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class BatchedStratumLinearEvaluator(StratumLinearEvaluator):
    """D1 forms with all constants and a cutoff for the L/Z channels."""

    def __init__(self, support, labels, coefficients, scalar, linear_cutoff):
        super().__init__(support, labels, coefficients, scalar)
        self.linear_cutoff = linear_cutoff

    def channels_for_r(self, r):
        return (0, 1, 2) if r <= self.linear_cutoff else (0,)

    def nominal_labels(self):
        return [(r, p) for r in self._r_values_i()
                for p in self.channels_for_r(r)]

    def _integrate_channels(self, polynomials, dimension, r, outer,
                            constraints):
        monomials = set()
        for polynomial in polynomials:
            monomials.update(polynomial)
        moments = {monomial: self.integrate_domain(
            {monomial: self.one}, dimension, r, outer, constraints)
                   for monomial in monomials}
        return tuple(sum((coefficient * moments[monomial]
                          for monomial, coefficient in polynomial.items()),
                         self.zero)
                     for polynomial in polynomials)

    def evaluate_i_r_batched(self, grouped, r, progress=False):
        entries = defaultdict(self.scalar)
        dimension = self.support.k
        faces = 0
        max_h = int(self.support.alpha // self.support.delta) - r
        if max_h < 0:
            return r, {}, faces
        constraints = ()
        if r:
            cap = self.support.beta(r) - r * self.support.delta
            if cap <= 0:
                return r, {}, faces
            constraints = ((self.one, self.zero, cap),)
        channels = self.channels_for_r(r)
        pairs = [(p, q) for p in channels for q in channels if q <= p]
        for h in range(max_h + 1):
            outer = self.support.alpha - (r + h) * self.support.delta
            if outer <= 0:
                continue
            base = self._i_face_polynomial(
                grouped, dimension, r, h, max_h, outer)
            phi = self._phi_polynomials(r, h)
            polynomials = [ei._poly_mul(
                base, ei._poly_mul(phi[p], phi[q])) for p, q in pairs]
            values = self._integrate_channels(
                polynomials, dimension, r, outer, constraints)
            for pair, value in zip(pairs, values):
                entries[pair] += value
            faces += 1
            if progress:
                print(f"batched D1 I r={r} h={h} faces={faces}", flush=True)
            self.clear_face_caches()
        self.clear_radial_caches()
        return r, dict(entries), faces

    def evaluate_i_batched(self, progress=False, workers=1):
        grouped = self.square_residual_terms()
        r_values = list(self._r_values_i())
        if workers == 1:
            results = [self.evaluate_i_r_batched(grouped, r, progress)
                       for r in r_values]
        else:
            global _FORK_EVALUATOR, _FORK_I_GROUPED
            _FORK_EVALUATOR, _FORK_I_GROUPED = self, grouped
            try:
                with multiprocessing.get_context("fork").Pool(workers) as pool:
                    results = pool.map(_fork_i, r_values, chunksize=1)
            finally:
                _FORK_EVALUATOR = _FORK_I_GROUPED = None
        entries = {}
        by_r = {}
        faces = 0
        for r, block, count in results:
            by_r[r] = block
            for (p, q), value in block.items():
                entries[((r, p), (r, q))] = value
            faces += count
        return entries, by_r, len(grouped), faces

    def _combined_channel_product(self, left, right, same_branch,
                                  same_channel):
        if same_branch and same_channel:
            return self.branch_orbit_product(left, right, True)
        return self._ordinary_orbit_product(left, right)

    def _integrate_combined_channels(self, combined, dimension, r, h,
                                     outer, max_h, constraints):
        totals = [defaultdict(self.scalar) for _ in combined]
        all_nu = set().union(*(block.keys() for block in combined))
        for nu in all_nu:
            density = self.orbit_density(dimension, nu, r, h, max_h)
            if not density:
                continue
            for index, block in enumerate(combined):
                polynomial = block.get(nu)
                if polynomial:
                    add_poly(totals[index],
                             ei._poly_mul(density, polynomial), self.one)
        return self._integrate_channels(
            totals, dimension, r, outer, constraints)

    def evaluate_j_r_batched(self, component_data, r, progress=False):
        lrs, by_lr = component_data
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        entries = defaultdict(self.scalar)
        dimension = self.support.k - 1
        domains = channel_integrals = 0
        max_h = int(self.support.eta // self.support.delta) - r
        if max_h < 0:
            return r, {}, domains, channel_integrals
        for h in range(max_h + 1):
            outer = self.support.eta - (r + h) * self.support.delta
            if outer <= 0:
                continue
            blocks = self._channel_branch_blocks(
                lrs, by_lr, r, h, dimension, outer)
            for i, left_branch in enumerate(branches):
                for right_branch in branches[:i + 1]:
                    constraints = self._active_branch_pair(
                        blocks, left_branch, right_branch,
                        dimension, r, h, outer)
                    if constraints is None:
                        continue
                    left_r = (r if left_branch in self.SMALL_BRANCHES
                              else r + 1)
                    right_r = (r if right_branch in self.SMALL_BRANCHES
                               else r + 1)
                    left_channels = self.channels_for_r(left_r)
                    right_channels = self.channels_for_r(right_r)
                    if left_branch == right_branch:
                        pairs = [(p, q) for p in left_channels
                                 for q in right_channels if q <= p]
                    else:
                        pairs = [(p, q) for p in left_channels
                                 for q in right_channels]
                    combined = [self._combined_channel_product(
                        blocks[left_branch][p], blocks[right_branch][q],
                        left_branch == right_branch, p == q)
                                for p, q in pairs]
                    values = self._integrate_combined_channels(
                        combined, dimension, r, h, outer, max_h, constraints)
                    for (p, q), value in zip(pairs, values):
                        left_label, right_label = (left_r, p), (right_r, q)
                        key = self._ordered_label(left_label, right_label)
                        if (left_label == right_label and
                                left_branch != right_branch):
                            value *= 2
                        entries[key] += value
                    domains += 1
                    channel_integrals += len(pairs)
            if progress:
                print(f"batched D1 J r={r} h={h} domains={domains} "
                      f"channels={channel_integrals}", flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return r, dict(entries), domains, channel_integrals

    def evaluate_j_batched(self, progress=False, workers=1):
        components, lrs, by_lr = self._j_component_data()
        component_data = (lrs, by_lr)
        r_values = list(self._r_values_j())
        if workers == 1:
            results = [self.evaluate_j_r_batched(component_data, r, progress)
                       for r in r_values]
        else:
            global _FORK_EVALUATOR, _FORK_J_DATA
            _FORK_EVALUATOR, _FORK_J_DATA = self, component_data
            try:
                with multiprocessing.get_context("fork").Pool(workers) as pool:
                    results = pool.map(_fork_j, r_values, chunksize=1)
            finally:
                _FORK_EVALUATOR = _FORK_J_DATA = None
        total = defaultdict(self.scalar)
        by_r = {}
        domains = channel_integrals = 0
        for r, entries, count, channels in results:
            by_r[r] = entries
            for key, value in entries.items():
                total[key] += value
            domains += count
            channel_integrals += channels
        return dict(total), by_r, len(components), domains, channel_integrals


def assemble(evaluator, i_entries, j_entries):
    labels = evaluator.nominal_labels()
    positions = {label: i for i, label in enumerate(labels)}
    n = len(labels)
    zero = evaluator.zero
    a = [[zero for _ in range(n)] for _ in range(n)]
    b = [[zero for _ in range(n)] for _ in range(n)]
    for (left, right), value in i_entries.items():
        i, j = positions[left], positions[right]
        a[i][j] += value
        if i != j:
            a[j][i] += value
    k = evaluator.scalar(evaluator.support.k)
    for (left, right), value in j_entries.items():
        if left not in positions or right not in positions:
            if value:
                raise ArithmeticError("nonzero J entry outside nominal pilot")
            continue
        i, j = positions[left], positions[right]
        b[i][j] += k * value
        if i != j:
            b[j][i] += k * value
    return labels, a, b


def solve_decimal(a, b, precision):
    with localcontext() as context:
        context.prec = precision
        a = [[+x for x in row] for row in a]
        b = [[+x for x in row] for row in b]
        scales = [a[i][i].sqrt() for i in range(len(a))]
        if any(x <= 0 for x in scales):
            raise ArithmeticError("nonpositive retained Gram diagonal")
        sa = [[a[i][j] / scales[i] / scales[j]
               for j in range(len(a))] for i in range(len(a))]
        sb = [[b[i][j] / scales[i] / scales[j]
               for j in range(len(a))] for i in range(len(a))]
        lower = cholesky(sa)
        inverse = inverse_lower(lower)
        reduced = matmul(matmul(inverse, sb), transpose(inverse))
        reduced = [[(reduced[i][j] + reduced[j][i]) / 2
                    for j in range(len(a))] for i in range(len(a))]
        values, vectors, rotations = jacobi_symmetric(reduced, precision)
        index = max(range(len(values)), key=values.__getitem__)
        y = [vectors[i][index] for i in range(len(a))]
        w = matvec(transpose(inverse), y)
        vector = [w[i] / scales[i] for i in range(len(a))]
        norm = max(abs(x) for x in vector)
        vector = [x / norm for x in vector]
        av, bv = matvec(a, vector), matvec(b, vector)
        denominator, numerator = dot(vector, av), dot(vector, bv)
        quotient = numerator / denominator
        residual = max(abs(bv[i] - quotient * av[i])
                       for i in range(len(a)))
        residual_scale = max(Decimal(1), max(abs(x) for x in bv),
                             abs(quotient) * max(abs(x) for x in av))
        euler_a = abs(2 * denominator - 2 * dot(vector, av))
        euler_b = abs(2 * numerator - 2 * dot(vector, bv))
        return {
            "precision": precision,
            "rayleigh_quotient": str(quotient),
            "relative_residual": str(residual / residual_scale),
            "jacobi_rotations": rotations,
            "euler_a_error": str(euler_a),
            "euler_b_error": str(euler_b),
            "vector": [str(x) for x in vector],
        }


def quadratic(matrix, vector):
    return sum((vector[i] * matrix[i][j] * vector[j]
                for i in range(len(vector)) for j in range(len(vector))),
               Decimal(0))


def contract_entries(entries, vector_by_label, factor=Decimal(1)):
    answer = Decimal(0)
    for (left, right), value in entries.items():
        term = vector_by_label.get(left, Decimal(0)) * \
            vector_by_label.get(right, Decimal(0)) * value
        answer += factor * term * (1 if left == right else 2)
    return answer


def render_entries(entries):
    return {repr(key): str(value) for key, value in entries.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--expect-input-sha256", required=True)
    parser.add_argument("--decimal-dps", type=int, default=100)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--linear-cutoff", type=int, choices=range(0, 16),
                        default=10)
    parser.add_argument("--alpha", default="79247/300000")
    parser.add_argument("--delta", default="1/100")
    parser.add_argument("--eta", default="76247/300000")
    parser.add_argument("--beta1", default="3/20")
    parser.add_argument("--beta2", default="3/20")
    parser.add_argument("--beta3plus", default="97/625")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.decimal_dps < 90 or args.workers not in (1, 2):
        parser.error("require decimal-dps>=90 and one or two workers")

    paths = {
        "driver": Path(__file__),
        "stratum_linear": HERE / "stratum_linear.py",
        "grouped": HERE / "grouped_fixed_vector.py",
        "integrator": HERE / "src/exact_integrator.py",
        "robust_solver": HERE / "robust_generalized_solve.py",
    }
    hashes_start = {key: file_sha(path) for key, path in paths.items()}
    for key, expected in PINNED_DEPENDENCY_HASHES.items():
        if hashes_start.get(key) != expected:
            raise SystemExit(
                f"pinned dependency mismatch for {key}: "
                f"expected {expected}, got {hashes_start.get(key)}")
    input_bytes = Path(args.input_json).read_bytes()
    input_sha256 = hashlib.sha256(input_bytes).hexdigest()
    if input_sha256 != args.expect_input_sha256:
        raise SystemExit(
            "input SHA-256 mismatch: expected "
            f"{args.expect_input_sha256}, got {input_sha256}")
    raw = json.loads(input_bytes)
    if int(raw.get("k", -1)) != 48:
        raise SystemExit("pinned port requires k=48")
    labels = [(int(a), tuple(int(x) for x in lam))
              for a, lam in raw["basis"]]
    if len(labels) != len(set(labels)) or len(labels) not in (12, 272):
        raise SystemExit("expected ordered D4 or D12 no-ones basis")
    rational_coefficients = [Fraction(x) for x in raw["rational_vector"]]
    if len(rational_coefficients) != len(labels):
        raise SystemExit("fixed-vector dimension mismatch")

    getcontext().prec = args.decimal_dps
    orbit_table = precompute_orbits(labels, 48)
    scalar = install_decimal(orbit_table, args.decimal_dps)
    parameters = {key: getattr(args, key) for key in
                  ("alpha", "delta", "eta", "beta1", "beta2", "beta3plus")}
    support = ei.OneStratumSupport(
        48, *[scalar(Fraction(parameters[key]).numerator,
                     Fraction(parameters[key]).denominator)
              for key in parameters])
    coefficients = [scalar(x.numerator, x.denominator)
                    for x in rational_coefficients]
    evaluator = BatchedStratumLinearEvaluator(
        support, labels, coefficients, scalar, args.linear_cutoff)

    start = time.perf_counter()
    i_entries, i_by_r, groups, faces = evaluator.evaluate_i_batched(
        args.progress, args.workers)
    i_seconds = time.perf_counter() - start
    stage = {
        "status": "multiprecision-stratum-linear-I-stage",
        "rigorous": False,
        "complete": True,
        "decimal_dps": args.decimal_dps,
        "workers": args.workers,
        "linear_cutoff": args.linear_cutoff,
        "nominal_dimension": len(evaluator.nominal_labels()),
        "input_sha256": input_sha256,
        "parameters": parameters,
        "dependency_hashes": hashes_start,
        "i_orbit_groups": groups,
        "i_faces": faces,
        "i_seconds": i_seconds,
        "i_entries": render_entries(i_entries),
        "baseline_i_by_r": [str(i_by_r[r].get((0, 0), Decimal(0)))
                            for r in sorted(i_by_r)],
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_peak_rss_kib": resource.getrusage(
            resource.RUSAGE_CHILDREN).ru_maxrss,
    }
    stage_path = args.output + ".I-stage.json"
    Path(stage_path).write_text(json.dumps(stage, indent=2) + "\n")
    print("I_STAGE_COMPLETE " + json.dumps({
        "path": stage_path, "i_seconds": i_seconds,
        "i_faces": faces, "groups": groups,
        "nominal_dimension": stage["nominal_dimension"]}), flush=True)

    _, lrs, by_lr = evaluator._j_component_data()
    # evaluate_j_batched rebuilds this data internally; the explicit values
    # above force malformed component data to fail before the long J stage.
    if not lrs or not by_lr:
        raise ArithmeticError("empty marginal component decomposition")
    j_start = time.perf_counter()
    j_entries, j_by_r, components, domains, channel_integrals = \
        evaluator.evaluate_j_batched(args.progress, args.workers)
    j_seconds = time.perf_counter() - j_start

    nominal_labels, a, b = assemble(evaluator, i_entries, j_entries)
    null_label = (0, 1)
    if null_label not in nominal_labels:
        raise ArithmeticError("expected R0-L null label is absent")
    null_index = nominal_labels.index(null_label)
    if any(a[null_index]) or any(row[null_index] for row in a) or \
            any(b[null_index]) or any(row[null_index] for row in b):
        raise ArithmeticError("R0-L direction is not exactly null")
    active_indices = [i for i in range(len(nominal_labels)) if i != null_index]
    active_labels = [nominal_labels[i] for i in active_indices]
    reduced_a = [[a[i][j] for j in active_indices] for i in active_indices]
    reduced_b = [[b[i][j] for j in active_indices] for i in active_indices]
    solve_start = time.perf_counter()
    solve = solve_decimal(reduced_a, reduced_b, args.decimal_dps)
    solve_seconds = time.perf_counter() - solve_start
    active_vector = [Decimal(x) for x in solve["vector"]]
    full_vector = [Decimal(0)] * len(nominal_labels)
    for i, value in zip(active_indices, active_vector):
        full_vector[i] = value
    denominator, numerator = quadratic(a, full_vector), quadratic(b, full_vector)
    quotient = numerator / denominator
    solver_quotient = Decimal(solve["rayleigh_quotient"])
    solver_full_rayleigh_error = abs(quotient - solver_quotient) / max(
        Decimal(1), abs(quotient), abs(solver_quotient))
    if solver_full_rayleigh_error > \
            Decimal(10) ** (-(args.decimal_dps - 12)):
        raise ArithmeticError("solver/full-matrix Rayleigh mismatch")
    vector_by_label = dict(zip(nominal_labels, full_vector))
    i_mass = [contract_entries({
        key: value for key, value in i_entries.items() if key[0][0] == r},
        vector_by_label) for r in sorted(i_by_r)]
    j_mass = [Decimal(48) * contract_entries(entries, vector_by_label)
              for r, entries in sorted(j_by_r.items())]
    baseline_vector = {label: (Decimal(1) if label[1] == 0 else Decimal(0))
                       for label in nominal_labels}
    baseline_i = [contract_entries({
        key: value for key, value in i_entries.items() if key[0][0] == r},
        baseline_vector) for r in sorted(i_by_r)]
    baseline_j = [Decimal(48) * contract_entries(entries, baseline_vector)
                  for r, entries in sorted(j_by_r.items())]
    mass_scale_i = max(abs(denominator), abs(sum(i_mass, Decimal(0))),
                       Decimal(10) ** (-args.decimal_dps))
    mass_scale_j = max(abs(numerator), abs(sum(j_mass, Decimal(0))),
                       Decimal(10) ** (-args.decimal_dps))
    i_mass_relative_error = abs(
        sum(i_mass, Decimal(0)) - denominator) / mass_scale_i
    j_mass_relative_error = abs(
        sum(j_mass, Decimal(0)) - numerator) / mass_scale_j
    mass_tolerance = Decimal(10) ** (-(args.decimal_dps - 12))
    hashes_end = {key: file_sha(path) for key, path in paths.items()}
    gates = {
        "dependencies_unchanged": hashes_start == hashes_end,
        "complete_counts": (groups == (20 if len(labels) == 12 else 1575) and
                            faces == 312 and
                            components == (19 if len(labels) == 12 else 695) and
                            domains == 1200),
        "nominal_retained_dimensions": (
            (args.linear_cutoff == 10 and len(nominal_labels) == 38 and
             len(active_labels) == 37) or
            (args.linear_cutoff == 11 and len(nominal_labels) == 40 and
             len(active_labels) == 39) or
            args.linear_cutoff not in (10, 11)),
        "null_direction_exact": True,
        "denominator_positive": denominator > 0,
        "rayleigh_recomputed": quotient == numerator / denominator,
        "solver_full_rayleigh_agreement": solver_full_rayleigh_error <=
            Decimal(10) ** (-(args.decimal_dps - 12)),
        "i_mass_sums": i_mass_relative_error <= mass_tolerance,
        "j_mass_sums": j_mass_relative_error <= mass_tolerance,
        "baseline_mass_positive": sum(baseline_i, Decimal(0)) > 0,
        "finite": all(x.is_finite() for x in
                      (denominator, numerator, quotient)) and all(
            Decimal(x).is_finite() for x in
            (solve["relative_residual"], solve["euler_a_error"],
             solve["euler_b_error"])),
        "residual_below_guard": Decimal(solve["relative_residual"]) <=
            Decimal(10) ** (-(args.decimal_dps - 15)),
    }
    passed = all(gates.values())
    output = {
        "status": ("multiprecision-stratum-linear-pilot" if passed else
                   "rejected-stratum-linear-pilot"),
        "rigorous": False,
        "complete": True,
        "decimal_dps": args.decimal_dps,
        "workers": args.workers,
        "linear_cutoff": args.linear_cutoff,
        "space_note": ("strict pilot: all R constants, L/Z only through "
                       f"R={args.linear_cutoff}; not a full D1 optimum"),
        "input_json": args.input_json,
        "input_sha256": input_sha256,
        "fixed_basis_dimension": len(labels),
        "parameters": parameters,
        "dependency_hashes": hashes_start,
        "nominal_dimension": len(nominal_labels),
        "retained_dimension": len(active_labels),
        "nominal_labels": [[r, evaluator.CHANNELS[p]]
                           for r, p in nominal_labels],
        "active_labels": [[r, evaluator.CHANNELS[p]] for r, p in active_labels],
        "discarded_exact_null_labels": [[0, "L"]],
        "vector": [str(x) for x in full_vector],
        "denominator": str(denominator),
        "numerator": str(numerator),
        "quotient": str(quotient),
        "margin": str(numerator - denominator),
        "solver_full_relative_rayleigh_error":
            str(solver_full_rayleigh_error),
        "solver": solve,
        "gates": gates,
        "gates_passed": passed,
        "i_orbit_groups": groups,
        "i_faces": faces,
        "marginal_components": components,
        "j_branch_domains": domains,
        "j_channel_integrals": channel_integrals,
        "candidate_i_by_r": [str(x) for x in i_mass],
        "candidate_j_by_common_r": [str(x) for x in j_mass],
        "i_mass_relative_error": str(i_mass_relative_error),
        "j_mass_relative_error": str(j_mass_relative_error),
        "baseline_i_by_r": [str(x) for x in baseline_i],
        "baseline_j_by_common_r": [str(x) for x in baseline_j],
        "baseline_denominator": str(sum(baseline_i, Decimal(0))),
        "baseline_numerator": str(sum(baseline_j, Decimal(0))),
        "baseline_quotient": str(sum(baseline_j, Decimal(0)) /
                                 sum(baseline_i, Decimal(0))),
        "i_seconds": i_seconds,
        "j_seconds": j_seconds,
        "solve_seconds": solve_seconds,
        "total_seconds": time.perf_counter() - start,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_peak_rss_kib": resource.getrusage(
            resource.RUSAGE_CHILDREN).ru_maxrss,
        "i_stage_json": stage_path,
        "i_entries": render_entries(i_entries),
        "j_entries": render_entries(j_entries),
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in (
        "status", "quotient", "margin", "baseline_quotient",
        "nominal_dimension", "retained_dimension", "i_seconds",
        "j_seconds", "solve_seconds", "total_seconds", "gates_passed")},
        indent=2))
    if not passed:
        raise SystemExit("stratum-linear pilot failed a gate")


if __name__ == "__main__":
    main()
