#!/usr/bin/env python3
"""Exact forms for F0 times per-stratum multipliers of total degree <=2.

The channel order is 1,L,Z,L^2,LZ,Z^2.  This is deliberately a separate
module from the pinned degree-one evaluator and artifact.
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
from decimal import Decimal, localcontext
from fractions import Fraction
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

import exact_integrator as ei
from grouped_fixed_vector import add_poly
from robust_generalized_solve import solve_once
from stratum_linear import (
    StratumLinearEvaluator,
    independent_gram_indices,
    quadratic,
    render_blocks,
)


class StratumQuadraticEvaluator(StratumLinearEvaluator):
    """Six-channel exact evaluator for one fixed polynomial F0."""

    CHANNEL_POWERS = ((0, 0), (1, 0), (0, 1),
                      (2, 0), (1, 1), (0, 2))
    CHANNELS = ("1", "L", "Z", "L^2", "LZ", "Z^2")

    def _phi_polynomials(self, r, h):
        lbase = dict(ei._linear_power(
            self.scalar(r) * self.support.delta,
            self.one, self.zero, 1))
        zbase = dict(ei._linear_power(
            self.scalar(h) * self.support.delta,
            self.zero, self.one, 1))
        answer = []
        for a, b in self.CHANNEL_POWERS:
            answer.append(ei._poly_mul(
                dict(ei._linear_power(
                    self.scalar(r) * self.support.delta,
                    self.one, self.zero, a)),
                dict(ei._linear_power(
                    self.scalar(h) * self.support.delta,
                    self.zero, self.one, b))))
        # The explicit bases above make the aggregate-variable convention
        # auditable; these two assertions catch an exponent/axis swap.
        assert answer[1] == {key: value for key, value in lbase.items()
                             if value}
        assert answer[2] == {key: value for key, value in zbase.items()
                             if value}
        return tuple(answer)

    def evaluate_i_r_linear(self, grouped, r, progress=False):
        size = len(self.CHANNELS)
        block = [[self.zero for _ in range(size)] for _ in range(size)]
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
            for p in range(size):
                for q in range(p + 1):
                    integrand = ei._poly_mul(
                        base, ei._poly_mul(phi[p], phi[q]))
                    value = self.integrate_domain(
                        integrand, dimension, r, outer, constraints)
                    block[p][q] += value
                    if p != q:
                        block[q][p] += value
            faces += 1
            if progress:
                print(f"quadratic I r={r} h={h} faces={faces}", flush=True)
            self.clear_face_caches()
        self.clear_radial_caches()
        return block, faces

    def _shifted_marginal_block_by(self, lrs, by_lr, r, h, branch, shift):
        block = {}
        for lr in lrs:
            polynomial = defaultdict(self.scalar)
            for e, residual, value in by_lr[lr]:
                add_poly(polynomial, dict(self.support._marginal_poly(
                    r, h, branch, e + shift, residual)), value)
            if polynomial:
                block[lr] = dict(polynomial)
        return block

    def _scale_block(self, block, factor):
        if factor == self.one:
            return block
        return {lr: ei._poly_scale(poly, factor)
                for lr, poly in block.items() if poly}

    def _channel_branch_blocks(self, lrs, by_lr, r, h, dimension, outer):
        answer = {}
        lbase = (self.scalar(r) * self.support.delta,
                 self.one, self.zero)
        zbase = (self.scalar(h) * self.support.delta,
                 self.zero, self.one)
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
                answer[branch] = tuple({} for _ in self.CHANNELS)
                continue

            shifts = {j: self._shifted_marginal_block_by(
                lrs, by_lr, r, h, branch, j) for j in range(3)}
            channels = []
            small = branch in self.SMALL_BRANCHES
            for a, b in self.CHANNEL_POWERS:
                pieces = []
                upper = b if small else a
                for j in range(upper + 1):
                    if small:
                        multiplier = ei._poly_mul(
                            dict(ei._linear_power(*lbase, a)),
                            dict(ei._linear_power(*zbase, b - j)))
                        factor = self.scalar(comb(b, j))
                    else:
                        multiplier = ei._poly_mul(
                            dict(ei._linear_power(*lbase, a - j)),
                            dict(ei._linear_power(*zbase, b)))
                        factor = self.scalar(comb(a, j))
                    piece = self._multiply_block_poly(shifts[j], multiplier)
                    pieces.append(self._scale_block(piece, factor))
                channels.append(self._sum_blocks(*pieces))
            answer[branch] = tuple(channels)
        return answer

    def evaluate_j_r_linear(self, lrs, by_lr, r, progress=False):
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        answer = defaultdict(self.scalar)
        dimension = self.support.k - 1
        branch_domains = channel_integrals = 0
        max_h = int(self.support.eta // self.support.delta) - r
        if max_h < 0:
            return {}, branch_domains, channel_integrals
        size = len(self.CHANNELS)
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
                        channel_pairs = ((p, q) for p in range(size)
                                         for q in range(p + 1))
                    else:
                        channel_pairs = ((p, q) for p in range(size)
                                         for q in range(size))
                    for p, q in channel_pairs:
                        value = self._integrate_channel_product(
                            blocks[left_branch][p], blocks[right_branch][q],
                            dimension, r, h, outer, max_h, constraints)
                        left_label = (left_r, p)
                        right_label = (right_r, q)
                        key = self._ordered_label(left_label, right_label)
                        if (left_label == right_label and
                                left_branch != right_branch):
                            value *= 2
                        answer[key] += value
                        channel_integrals += 1
            if progress:
                print(f"quadratic J r={r} h={h} domains={branch_domains} "
                      f"channels={channel_integrals}", flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return dict(answer), branch_domains, channel_integrals

    def assemble_dense(self, i_blocks, j_entries):
        max_r = max(i_blocks, default=-1)
        size = len(self.CHANNELS)
        labels = [(r, p) for r in range(max_r + 1) for p in range(size)]
        positions = {label: i for i, label in enumerate(labels)}
        n = len(labels)
        a = [[self.zero for _ in range(n)] for _ in range(n)]
        b = [[self.zero for _ in range(n)] for _ in range(n)]
        for r, block in i_blocks.items():
            for p in range(size):
                for q in range(size):
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

    def evaluate_direct(self, coefficient_vector, progress=False):
        """Fresh traversal after inserting one explicit six-channel vector."""
        max_r = max(self._r_values_i(), default=-1)
        size = len(self.CHANNELS)
        if len(coefficient_vector) != size * (max_r + 1):
            raise ValueError("quadratic coefficient dimension mismatch")
        coefficients = {
            r: coefficient_vector[size * r:size * (r + 1)]
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
                    vector = coefficients.get(total_r, (self.zero,) * size)
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
                    print(f"quadratic direct J r={r} h={h} "
                          f"domains={j_domains}", flush=True)
                self.clear_face_caches(clear_marginals=True)
            self.clear_radial_caches()
        return denominator, self.scalar(self.support.k) * j_value, \
            i_faces, j_domains


def _validate_solves(solves):
    low, high = solves[0], solves[-1]
    precision = min(low["precision"], high["precision"])
    with localcontext() as context:
        context.prec = precision
        qlow = Decimal(low["rayleigh_quotient"])
        qhigh = Decimal(high["rayleigh_quotient"])
        tolerance = Decimal(10) ** (-(precision - 35))
        if abs(qlow - qhigh) > tolerance * max(Decimal(1), abs(qhigh)):
            raise ArithmeticError("cross-precision eigenvalue instability")
        for solve in solves:
            residual = Decimal(solve["relative_residual_bound"])
            residual_limit = Decimal(10) ** (-(solve["precision"] - 15))
            if residual > residual_limit:
                raise ArithmeticError("generalized-eigen residual too large")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--alpha", type=Fraction, required=True)
    parser.add_argument("--delta", type=Fraction, required=True)
    parser.add_argument("--eta", type=Fraction, required=True)
    parser.add_argument("--beta1", type=Fraction, required=True)
    parser.add_argument("--beta2", type=Fraction, required=True)
    parser.add_argument("--beta3plus", type=Fraction, required=True)
    parser.add_argument("--solve-precisions", default="100,160")
    parser.add_argument("--rational-denominator", type=int, default=10**9)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    precisions = [int(x) for x in args.solve_precisions.split(",")]
    if len(precisions) < 2 or min(precisions) < 80:
        parser.error("give at least two solve precisions >=80")
    input_bytes = Path(args.input_json).read_bytes()
    raw = json.loads(input_bytes)
    labels = [(int(a), tuple(int(x) for x in lam))
              for a, lam in raw["basis"]]
    fixed_coefficients = [Fraction(x) for x in raw["rational_vector"]]
    support = ei.OneStratumSupport(
        int(raw["k"]), args.alpha, args.delta, args.eta,
        args.beta1, args.beta2, args.beta3plus)
    evaluator = StratumQuadraticEvaluator(
        support, labels, fixed_coefficients, Fraction)

    start = time.perf_counter()
    forms = evaluator.evaluate_forms(args.progress)
    forms_seconds = time.perf_counter() - start
    active, discarded = independent_gram_indices(
        forms["a_matrix"], forms["labels"])
    reduced_a = [[forms["a_matrix"][i][j] for j in active] for i in active]
    reduced_b = [[forms["b_matrix"][i][j] for j in active] for i in active]
    solve_start = time.perf_counter()
    solves = [solve_once(reduced_a, reduced_b, p) for p in precisions]
    solve_seconds = time.perf_counter() - solve_start
    _validate_solves(solves)

    candidate = [Fraction(0) for _ in forms["labels"]]
    for i, value in zip(active, solves[-1]["vector"]):
        candidate[i] = Fraction(value).limit_denominator(
            args.rational_denominator)
    denominator = quadratic(forms["a_matrix"], candidate, Fraction(0))
    numerator = quadratic(forms["b_matrix"], candidate, Fraction(0))
    if denominator <= 0:
        raise ArithmeticError("selected exact denominator is not positive")
    direct_start = time.perf_counter()
    direct = evaluator.evaluate_direct(candidate, args.progress)
    direct_seconds = time.perf_counter() - direct_start
    if direct[:2] != (denominator, numerator):
        raise ArithmeticError("quadratic block/direct reconstruction mismatch")
    if direct[2:] != (forms["i_faces"], forms["j_branch_domains"]):
        raise ArithmeticError("quadratic block/direct traversal-count mismatch")

    output = {
        "status": "exact-stratum-quadratic-rational-vector",
        "rigorous_forms": True,
        "eigenvector_discovery_rigorous": False,
        "input_json": args.input_json,
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "stratum_linear_sha256": hashlib.sha256(
            (HERE / "stratum_linear.py").read_bytes()).hexdigest(),
        "robust_solver_sha256": hashlib.sha256(
            (HERE / "robust_generalized_solve.py").read_bytes()).hexdigest(),
        "grouped_evaluator_sha256": hashlib.sha256(
            (HERE / "grouped_fixed_vector.py").read_bytes()).hexdigest(),
        "integrator_sha256": hashlib.sha256(Path(ei.__file__).read_bytes()).hexdigest(),
        "k": support.k,
        "parameters": {"alpha": str(args.alpha), "delta": str(args.delta),
                       "eta": str(args.eta), "beta1": str(args.beta1),
                       "beta2": str(args.beta2),
                       "beta3plus": str(args.beta3plus)},
        "fixed_basis_dimension": len(labels),
        "quadratic_basis_dimension": len(forms["labels"]),
        "discovery_basis_dimension": len(active),
        "channel_powers": [list(x) for x in evaluator.CHANNEL_POWERS],
        "quadratic_labels": [[r, evaluator.CHANNELS[p]]
                             for r, p in forms["labels"]],
        "active_quadratic_labels": [
            [forms["labels"][i][0], evaluator.CHANNELS[forms["labels"][i][1]]]
            for i in active],
        "discarded_gram_dependent_labels": [
            [forms["labels"][i][0], evaluator.CHANNELS[forms["labels"][i][1]]]
            for i in discarded],
        "workers": 1,
        "parallelism_note": "serial-only six-channel traversal; no fork claim",
        "cross_precision_solves": solves,
        "cross_precision_stability_pass": True,
        "rational_denominator_limit": args.rational_denominator,
        "rational_vector": [str(x) for x in candidate],
        "denominator": str(denominator),
        "numerator": str(numerator),
        "quotient": str(numerator / denominator),
        "margin": str(numerator - denominator),
        "denominator_positive": True,
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
        "solve_seconds": solve_seconds,
        "direct_seconds": direct_seconds,
        "total_seconds": time.perf_counter() - start,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "i_blocks": render_blocks(forms["i_blocks"]),
        "j_entries": render_blocks(forms["j_entries"]),
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in (
        "quotient", "margin", "quadratic_basis_dimension",
        "discovery_basis_dimension", "discarded_gram_dependent_labels",
        "block_direct_bitwise_equal", "forms_seconds", "solve_seconds",
        "direct_seconds", "total_seconds")}, indent=2))


if __name__ == "__main__":
    main()
