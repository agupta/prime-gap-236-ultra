#!/usr/bin/env python3
"""Exact grouped forms for F0(t) times per-stratum span{1,L,Z}.

Here R is the number of coordinates above delta,
L=sum_{t_i>delta} t_i, and Z=sum_{t_i<=delta} t_i.  For fixed F0 the basis
is 1_R F0, 1_R L F0, 1_R Z F0.  I is block diagonal in R and J is block
tridiagonal.  This module is separate from the pinned scalar evaluator.  The
current driver is deliberately serial: its new multi-channel cache lifecycle
has not been given a separate fork audit, so it exposes no workers option and
records that limitation rather than silently claiming parallel equivalence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import sys
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import add_poly  # noqa: E402
from stratum_amplitude import StratumAmplitudeEvaluator  # noqa: E402


class StratumLinearEvaluator(StratumAmplitudeEvaluator):
    """Exact 3-channel (1,L,Z) blocks for one fixed polynomial F0."""

    CHANNELS = ("1", "L", "Z")

    def _phi_polynomials(self, r, h):
        return (
            {(0, 0): self.one},
            {(0, 0): self.scalar(r) * self.support.delta,
             (1, 0): self.one},
            {(0, 0): self.scalar(h) * self.support.delta,
             (0, 1): self.one},
        )

    def _i_face_polynomial(self, grouped, dimension, r, h, max_h, outer):
        total = defaultdict(self.scalar)
        for nu, residuals in grouped.items():
            density = self.orbit_density(dimension, nu, r, h, max_h)
            if not density:
                continue
            residual = defaultdict(self.scalar)
            for c, coefficient in residuals.items():
                add_poly(residual, dict(ei._linear_power(
                    outer, -self.one, -self.one, c)), coefficient)
            add_poly(total, ei._poly_mul(density, residual), self.one)
        return dict(total)

    def evaluate_i_r_linear(self, grouped, r, progress=False):
        block = [[self.zero for _ in self.CHANNELS] for _ in self.CHANNELS]
        dimension = self.support.k
        faces = 0
        max_h = int(self.support.alpha // self.support.delta) - r
        if max_h < 0:
            return block, faces
        constraints = ()
        if r:
            cap = self.support.beta(r) - r * self.support.delta
            if cap <= 0:
                return block, faces
            constraints = ((self.one, self.zero, cap),)
        for h in range(max_h + 1):
            outer = self.support.alpha - (r + h) * self.support.delta
            if outer <= 0:
                continue
            base = self._i_face_polynomial(
                grouped, dimension, r, h, max_h, outer)
            phi = self._phi_polynomials(r, h)
            for p in range(3):
                for q in range(p + 1):
                    integrand = ei._poly_mul(base, ei._poly_mul(phi[p], phi[q]))
                    value = self.integrate_domain(
                        integrand, dimension, r, outer, constraints)
                    block[p][q] += value
                    if p != q:
                        block[q][p] += value
            faces += 1
            if progress:
                print(f"linear I r={r} h={h} faces={faces}", flush=True)
            self.clear_face_caches()
        self.clear_radial_caches()
        return block, faces

    def evaluate_i_linear(self, progress=False):
        grouped = self.square_residual_terms()
        results = {}
        faces = 0
        for r in self._r_values_i():
            block, count = self.evaluate_i_r_linear(grouped, r, progress)
            results[r] = block
            faces += count
        return results, len(grouped), faces

    def _shifted_marginal_block(self, lrs, by_lr, r, h, branch):
        block = {}
        for lr in lrs:
            polynomial = defaultdict(self.scalar)
            for e, a, value in by_lr[lr]:
                add_poly(polynomial, dict(self.support._marginal_poly(
                    r, h, branch, e + 1, a)), value)
            if polynomial:
                block[lr] = dict(polynomial)
        return block

    def _multiply_block_poly(self, block, polynomial):
        return {lr: ei._poly_mul(value, polynomial)
                for lr, value in block.items() if value}

    def _sum_blocks(self, *blocks):
        answer = {}
        for block in blocks:
            for lr, polynomial in block.items():
                target = answer.setdefault(lr, defaultdict(self.scalar))
                add_poly(target, polynomial, self.one)
        return {lr: dict(poly) for lr, poly in answer.items() if poly}

    def _channel_branch_blocks(self, lrs, by_lr, r, h, dimension, outer):
        answer = {}
        lbase = {(0, 0): self.scalar(r) * self.support.delta,
                 (1, 0): self.one}
        zbase = {(0, 0): self.scalar(h) * self.support.delta,
                 (0, 1): self.one}
        for branch in ("Sdelta", "Stotal", "Ltotal", "Lbig"):
            constraints = self.support._branch_constraints(r, h, branch)
            if dimension == 0:
                interval = self.support._branch_interval(0, 0, branch)
                active = (interval is not None and
                          interval[0] <= self.zero <= interval[1])
            else:
                active = (constraints is not None and self.integrate_domain(
                    {(0, 0): self.one}, dimension, r, outer, constraints) > 0)
            if not active:
                answer[branch] = ({}, {}, {})
                continue
            block = {}
            for lr in lrs:
                polynomial = defaultdict(self.scalar)
                for e, a, value in by_lr[lr]:
                    add_poly(polynomial, dict(self.support._marginal_poly(
                        r, h, branch, e, a)), value)
                if polynomial:
                    block[lr] = dict(polynomial)
            # Do not infer that the shifted u-moment vanishes when the
            # unweighted marginal cancels.  Signed F0 can have integral zero
            # but first moment nonzero on the same geometric branch.
            shifted = self._shifted_marginal_block(
                lrs, by_lr, r, h, branch)
            lblock = self._multiply_block_poly(block, lbase)
            zblock = self._multiply_block_poly(block, zbase)
            if branch in self.SMALL_BRANCHES:
                zblock = self._sum_blocks(zblock, shifted)
            else:
                lblock = self._sum_blocks(lblock, shifted)
            answer[branch] = (block, lblock, zblock)
        return answer

    def _ordinary_orbit_product(self, left, right):
        combined = {}
        for lr, p in left.items():
            for mr, q in right.items():
                product = ei._poly_mul(p, q)
                for nu, multiplicity in ei.multiply_monomial_orbits(lr, mr):
                    destination = combined.setdefault(
                        nu, defaultdict(self.scalar))
                    add_poly(destination, product,
                             self.scalar(multiplicity))
        return {nu: dict(poly) for nu, poly in combined.items() if poly}

    def _integrate_channel_product(self, left, right, dimension, r, h,
                                   outer, max_h, constraints):
        combined = self._ordinary_orbit_product(left, right)
        total = defaultdict(self.scalar)
        for nu, marginal in combined.items():
            density = self.orbit_density(dimension, nu, r, h, max_h)
            if density:
                add_poly(total, ei._poly_mul(density, marginal), self.one)
        return self.integrate_domain(
            dict(total), dimension, r, outer, constraints)

    def _active_branch_pair(self, branch_blocks, left, right,
                            dimension, r, h, outer):
        # A signed base polynomial can have a zero ordinary marginal but a
        # nonzero first-u moment.  L/Z then retains the branch even though the
        # constant channel cancels, so activity cannot be keyed only to slot 0.
        if not any(branch_blocks[left]) or not any(branch_blocks[right]):
            return None
        if (dimension != 0 and
                ({left, right} == {"Sdelta", "Stotal"} or
                 {left, right} == {"Ltotal", "Lbig"})):
            return None
        constraints = self.branch_domain(r, h, left, right)
        if constraints is None:
            return None
        if dimension != 0 and self.integrate_domain(
                {(0, 0): self.one}, dimension, r, outer, constraints) <= 0:
            return None
        return constraints

    @staticmethod
    def _ordered_label(left, right):
        return (left, right) if left <= right else (right, left)

    def evaluate_j_r_linear(self, lrs, by_lr, r, progress=False):
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        answer = defaultdict(self.scalar)
        dimension = self.support.k - 1
        branch_domains = channel_integrals = 0
        max_h = int(self.support.eta // self.support.delta) - r
        if max_h < 0:
            return {}, branch_domains, channel_integrals
        for h in range(max_h + 1):
            if dimension == 0 and (r != 0 or h != 0):
                continue
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
                    branch_domains += 1
                    left_r = (r if left_branch in self.SMALL_BRANCHES
                              else r + 1)
                    right_r = (r if right_branch in self.SMALL_BRANCHES
                               else r + 1)
                    if left_branch == right_branch:
                        channel_pairs = ((p, q) for p in range(3)
                                         for q in range(p + 1))
                    else:
                        channel_pairs = ((p, q) for p in range(3)
                                         for q in range(3))
                    for p, q in channel_pairs:
                        value = self._integrate_channel_product(
                            blocks[left_branch][p], blocks[right_branch][q],
                            dimension, r, h, outer, max_h, constraints)
                        left_label = (left_r, p)
                        right_label = (right_r, q)
                        key = self._ordered_label(left_label, right_label)
                        if left_label == right_label and \
                                left_branch != right_branch:
                            value *= 2
                        answer[key] += value
                        channel_integrals += 1
            if progress:
                print(f"linear J r={r} h={h} domains={branch_domains} "
                      f"channels={channel_integrals}", flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return dict(answer), branch_domains, channel_integrals

    def evaluate_j_linear(self, progress=False):
        _, lrs, by_lr = self._j_component_data()
        answer = defaultdict(self.scalar)
        domains = channel_integrals = 0
        for r in self._r_values_j():
            block, count, channels = self.evaluate_j_r_linear(
                lrs, by_lr, r, progress)
            for key, value in block.items():
                answer[key] += value
            domains += count
            channel_integrals += channels
        return dict(answer), len(self.marginal_components()), domains, channel_integrals

    def assemble_dense(self, i_blocks, j_entries):
        max_r = max(i_blocks, default=-1)
        labels = [(r, p) for r in range(max_r + 1) for p in range(3)]
        positions = {label: i for i, label in enumerate(labels)}
        n = len(labels)
        a = [[self.zero for _ in range(n)] for _ in range(n)]
        b = [[self.zero for _ in range(n)] for _ in range(n)]
        for r, block in i_blocks.items():
            for p in range(3):
                for q in range(3):
                    a[positions[(r, p)]][positions[(r, q)]] = block[p][q]
        k = self.scalar(self.support.k)
        for (left, right), value in j_entries.items():
            if left not in positions or right not in positions:
                if value:
                    raise ArithmeticError("nonzero J entry outside I strata")
                continue
            i, j = positions[left], positions[right]
            b[i][j] += k * value
            if i != j:
                b[j][i] += k * value
        return labels, a, b

    def evaluate_forms(self, progress=False):
        i_blocks, groups, faces = self.evaluate_i_linear(progress)
        j_entries, components, domains, channel_integrals = \
            self.evaluate_j_linear(progress)
        labels, a, b = self.assemble_dense(i_blocks, j_entries)
        return {
            "labels": labels, "a_matrix": a, "b_matrix": b,
            "i_blocks": i_blocks, "j_entries": j_entries,
            "i_orbit_groups": groups, "i_faces": faces,
            "marginal_components": components,
            "j_branch_domains": domains,
            "j_channel_integrals": channel_integrals,
        }

    def _combine_channel_blocks(self, channels, coefficients):
        answer = {}
        for p, block in enumerate(channels):
            factor = coefficients[p]
            if not factor:
                continue
            for lr, polynomial in block.items():
                target = answer.setdefault(lr, defaultdict(self.scalar))
                add_poly(target, polynomial, factor)
        return {lr: dict(poly) for lr, poly in answer.items() if poly}

    def evaluate_direct(self, coefficient_vector, progress=False):
        """Fresh grouped evaluation after inserting one explicit 3R-vector."""
        max_r = max(self._r_values_i(), default=-1)
        if len(coefficient_vector) != 3 * (max_r + 1):
            raise ValueError("linear coefficient dimension mismatch")
        coefficients = {r: coefficient_vector[3 * r:3 * r + 3]
                        for r in range(max_r + 1)}
        grouped = self.square_residual_terms()
        denominator = self.zero
        i_faces = 0
        dimension = self.support.k
        for r in self._r_values_i():
            max_h = int(self.support.alpha // self.support.delta) - r
            constraints = ()
            if r:
                cap = self.support.beta(r) - r * self.support.delta
                if cap <= 0:
                    continue
                constraints = ((self.one, self.zero, cap),)
            for h in range(max_h + 1):
                outer = self.support.alpha - (r + h) * self.support.delta
                if outer <= 0:
                    continue
                base = self._i_face_polynomial(
                    grouped, dimension, r, h, max_h, outer)
                amplitude = defaultdict(self.scalar)
                for p, phi in enumerate(self._phi_polynomials(r, h)):
                    add_poly(amplitude, phi, coefficients[r][p])
                integrand = ei._poly_mul(
                    base, ei._poly_mul(dict(amplitude), dict(amplitude)))
                denominator += self.integrate_domain(
                    integrand, dimension, r, outer, constraints)
                i_faces += 1
                self.clear_face_caches()
            self.clear_radial_caches()

        _, lrs, by_lr = self._j_component_data()
        j_value = self.zero
        j_domains = 0
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        dimension = self.support.k - 1
        for r in self._r_values_j():
            max_h = int(self.support.eta // self.support.delta) - r
            for h in range(max_h + 1):
                if dimension == 0 and (r != 0 or h != 0):
                    continue
                outer = self.support.eta - (r + h) * self.support.delta
                if outer <= 0:
                    continue
                channels = self._channel_branch_blocks(
                    lrs, by_lr, r, h, dimension, outer)
                combined = {}
                for branch in branches:
                    total_r = (r if branch in self.SMALL_BRANCHES else r + 1)
                    vector = coefficients.get(total_r, (self.zero,) * 3)
                    combined[branch] = self._combine_channel_blocks(
                        channels[branch], vector)
                for i, left in enumerate(branches):
                    for right in branches[:i + 1]:
                        value = self._integrate_branch_pair(
                            combined, left, right, dimension, r, h,
                            outer, max_h)
                        if value is not None:
                            j_value += value
                            j_domains += 1
                if progress:
                    print(f"linear direct J r={r} h={h} domains={j_domains}",
                          flush=True)
                self.clear_face_caches(clear_marginals=True)
            self.clear_radial_caches()
        return denominator, self.scalar(self.support.k) * j_value, \
            i_faces, j_domains


def quadratic(matrix, vector, zero):
    return sum((vector[i] * matrix[i][j] * vector[j]
                for i in range(len(vector)) for j in range(len(vector))), zero)


def exact_determinant(matrix):
    """Bare exact determinant for the at-most-3 dimensional I blocks."""
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("determinant requires a square matrix")
    if not n:
        return 1
    work = [list(row) for row in matrix]
    answer = 1
    for column in range(n):
        pivot = next((i for i in range(column, n)
                      if work[i][column]), None)
        if pivot is None:
            return work[0][0] * 0
        if pivot != column:
            work[column], work[pivot] = work[pivot], work[column]
            answer = -answer
        value = work[column][column]
        answer *= value
        for i in range(column + 1, n):
            if not work[i][column]:
                continue
            factor = work[i][column] / value
            for j in range(column + 1, n):
                work[i][j] -= factor * work[column][j]
        # The pivot column below the diagonal is no longer used.
    return answer


def independent_gram_indices(matrix, labels):
    """Select an exact positive-definite coordinate subset in each R block.

    The full I form is a Gram form and is block diagonal in R, but it is not
    automatically nonsingular: for R=0, for example, L is identically zero.
    This routine does not assume invertibility.  It tests every successive
    principal minor exactly, discards a zero Schur-complement direction, and
    rejects a negative one.  The discarded coordinates are redundant in the
    finite function span; setting their candidate coefficients to zero loses
    no function direction.
    """
    if len(matrix) != len(labels) or any(len(row) != len(labels)
                                         for row in matrix):
        raise ValueError("Gram matrix/label dimension mismatch")
    by_r = defaultdict(list)
    for i, (r, _) in enumerate(labels):
        by_r[r].append(i)
    selected = []
    discarded = []
    for r in sorted(by_r):
        block_selected = []
        for candidate in by_r[r]:
            trial = block_selected + [candidate]
            principal = [[matrix[i][j] for j in trial] for i in trial]
            determinant = exact_determinant(principal)
            if determinant > 0:
                block_selected.append(candidate)
            elif determinant == 0:
                discarded.append(candidate)
            else:
                raise ArithmeticError(
                    f"I block {r} has a negative exact principal minor")
        selected.extend(block_selected)
    if not selected:
        raise ArithmeticError("I form has no positive direction")
    return selected, discarded


def render_blocks(value):
    if isinstance(value, dict):
        return {str(key): render_blocks(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [render_blocks(item) for item in value]
    return str(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--alpha", type=Fraction, required=True)
    parser.add_argument("--delta", type=Fraction, required=True)
    parser.add_argument("--eta", type=Fraction, required=True)
    parser.add_argument("--beta1", type=Fraction, required=True)
    parser.add_argument("--beta2", type=Fraction, required=True)
    parser.add_argument("--beta3plus", type=Fraction, required=True)
    parser.add_argument("--rational-denominator", type=int, default=10**9)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_bytes = Path(args.input_json).read_bytes()
    raw = json.loads(input_bytes)
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    coefficients = [Fraction(x) for x in raw["rational_vector"]]
    support = ei.OneStratumSupport(
        int(raw["k"]), args.alpha, args.delta, args.eta,
        args.beta1, args.beta2, args.beta3plus)
    evaluator = StratumLinearEvaluator(
        support, labels, coefficients, Fraction)
    start = time.perf_counter()
    forms = evaluator.evaluate_forms(args.progress)
    forms_seconds = time.perf_counter() - start
    active, discarded = independent_gram_indices(
        forms["a_matrix"], forms["labels"])
    reduced_a = [[forms["a_matrix"][i][j] for j in active] for i in active]
    reduced_b = [[forms["b_matrix"][i][j] for j in active] for i in active]
    floating_value, floating_vector = ei.float_generalized_eigen(
        reduced_a, reduced_b)
    rational_vector = [Fraction(0) for _ in forms["labels"]]
    for i, value in zip(active, floating_vector):
        rational_vector[i] = Fraction(float(value)).limit_denominator(
            args.rational_denominator)
    denominator = quadratic(forms["a_matrix"], rational_vector, Fraction(0))
    numerator = quadratic(forms["b_matrix"], rational_vector, Fraction(0))
    direct_start = time.perf_counter()
    direct = evaluator.evaluate_direct(rational_vector, args.progress)
    direct_seconds = time.perf_counter() - direct_start
    if direct[:2] != (denominator, numerator):
        raise ArithmeticError("linear block/direct reconstruction mismatch")
    output = {
        "status": "exact-stratum-linear-rational-vector",
        "rigorous_forms": True,
        "eigenvector_discovery_rigorous": False,
        "input_json": args.input_json,
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "stratum_amplitude_sha256": hashlib.sha256(Path(
            os.path.join(HERE, "stratum_amplitude.py")).read_bytes()).hexdigest(),
        "grouped_evaluator_sha256": hashlib.sha256(Path(
            os.path.join(HERE, "grouped_fixed_vector.py")).read_bytes()).hexdigest(),
        "integrator_sha256": hashlib.sha256(Path(ei.__file__).read_bytes()).hexdigest(),
        "k": support.k,
        "parameters": {"alpha": str(args.alpha), "delta": str(args.delta),
                       "eta": str(args.eta), "beta1": str(args.beta1),
                       "beta2": str(args.beta2),
                       "beta3plus": str(args.beta3plus)},
        "fixed_basis_dimension": len(labels),
        "linear_basis_dimension": len(forms["labels"]),
        "discovery_basis_dimension": len(active),
        "active_linear_labels": [[forms["labels"][i][0],
                                  evaluator.CHANNELS[forms["labels"][i][1]]]
                                 for i in active],
        "discarded_exact_null_labels": [
            [forms["labels"][i][0], evaluator.CHANNELS[forms["labels"][i][1]]]
            for i in discarded],
        "workers": 1,
        "parallelism_note": ("serial-only multi-channel traversal; no fork path "
                             "is implemented or claimed"),
        "linear_labels": [[r, evaluator.CHANNELS[p]]
                          for r, p in forms["labels"]],
        "floating_generalized_eigenvalue": repr(floating_value),
        "rational_denominator_limit": args.rational_denominator,
        "rational_vector": [str(x) for x in rational_vector],
        "denominator": str(denominator),
        "numerator": str(numerator),
        "quotient": str(numerator / denominator),
        "margin": str(numerator - denominator),
        "denominator_positive": denominator > 0,
        "margin_positive": numerator > denominator,
        "block_direct_bitwise_equal": True,
        "i_orbit_groups": forms["i_orbit_groups"],
        "i_faces": forms["i_faces"],
        "marginal_components": forms["marginal_components"],
        "j_branch_domains": forms["j_branch_domains"],
        "j_channel_integrals": forms["j_channel_integrals"],
        "direct_i_faces": direct[2],
        "direct_j_branch_domains": direct[3],
        "forms_seconds": forms_seconds,
        "direct_seconds": direct_seconds,
        "total_seconds": time.perf_counter() - start,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "i_blocks": render_blocks(forms["i_blocks"]),
        "j_entries": render_blocks(forms["j_entries"]),
    }
    rendered = json.dumps(output, indent=2) + "\n"
    Path(args.output).write_text(rendered)
    print(json.dumps({key: output[key] for key in (
        "floating_generalized_eigenvalue", "quotient", "margin",
        "linear_basis_dimension", "block_direct_bitwise_equal",
        "forms_seconds", "direct_seconds", "total_seconds")}, indent=2))


if __name__ == "__main__":
    main()
