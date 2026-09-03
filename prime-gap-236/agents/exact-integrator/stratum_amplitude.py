#!/usr/bin/env python3
"""Grouped diagonal/tridiagonal forms for fixed-vector stratum amplitudes.

For a fixed symmetric polynomial F0 and R(t)=#{i:t_i>delta}, this module
reconstructs the finite space F(t)=a_R(t) F0(t).  It reuses the audited scalar
face geometry but does not read a matrix or moment cache.
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
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import (  # noqa: E402
    GroupedEvaluator,
    add_poly,
    install_decimal,
    parse_rational_decimal,
    precompute_orbits,
)


_FORK_EVALUATOR = None
_FORK_I_GROUPED = None
_FORK_J_DATA = None
_FORK_AMPLITUDES = None


def _fork_i_block(r):
    return r, _FORK_EVALUATOR.evaluate_i_r(_FORK_I_GROUPED, r, False)


def _fork_j_block(r):
    return r, _FORK_EVALUATOR.evaluate_j_r_blocks(*_FORK_J_DATA, r, False)


def _fork_j_amplitude(r):
    return r, _FORK_EVALUATOR.evaluate_j_r_amplitude(
        *_FORK_J_DATA, r, _FORK_AMPLITUDES, False)


class StratumAmplitudeEvaluator(GroupedEvaluator):
    """One fixed F0, with a scalar amplitude for each total large count."""

    SMALL_BRANCHES = frozenset(("Sdelta", "Stotal"))
    LARGE_BRANCHES = frozenset(("Ltotal", "Lbig"))

    def _r_values_i(self):
        return list(range(min(self.support.k, self.support.max_large()) + 1))

    def _r_values_j(self):
        return list(range(min(self.support.k - 1,
                              self.support.max_large()) + 1))

    def evaluate_i_blocks(self, progress=False, workers=1):
        """Return I_R before the ordinary parent sum discards R."""
        grouped = self.square_residual_terms()
        r_values = self._r_values_i()
        if workers == 1:
            results = [(r, self.evaluate_i_r(grouped, r, progress))
                       for r in r_values]
        else:
            global _FORK_EVALUATOR, _FORK_I_GROUPED
            _FORK_EVALUATOR, _FORK_I_GROUPED = self, grouped
            try:
                with multiprocessing.get_context("fork").Pool(workers) as pool:
                    results = pool.map(_fork_i_block, r_values, chunksize=1)
            finally:
                _FORK_EVALUATOR = _FORK_I_GROUPED = None
        values = {r: value for r, (value, _) in results}
        return values, len(grouped), sum(item[1][1] for item in results)

    def _branch_blocks(self, lrs, by_lr, r, h, dimension, outer):
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        blocks = {}
        for branch in branches:
            constraints = self.support._branch_constraints(r, h, branch)
            if dimension == 0:
                interval = self.support._branch_interval(0, 0, branch)
                active = (interval is not None and
                          interval[0] <= self.zero <= interval[1])
            else:
                active = (constraints is not None and self.integrate_domain(
                    {(0, 0): self.one}, dimension, r, outer, constraints) > 0)
            if not active:
                blocks[branch] = {}
                continue
            block = {}
            for lr in lrs:
                polynomial = defaultdict(self.scalar)
                for e, a, value in by_lr[lr]:
                    add_poly(polynomial, dict(self.support._marginal_poly(
                        r, h, branch, e, a)), value)
                if polynomial:
                    block[lr] = dict(polynomial)
            blocks[branch] = block
        return blocks

    @staticmethod
    def _branch_class(left, right):
        if left in StratumAmplitudeEvaluator.SMALL_BRANCHES and \
                right in StratumAmplitudeEvaluator.SMALL_BRANCHES:
            return 0  # S_r^2
        if left in StratumAmplitudeEvaluator.LARGE_BRANCHES and \
                right in StratumAmplitudeEvaluator.LARGE_BRANCHES:
            return 2  # L_r^2
        return 1      # already 2*S_r*L_r in the unordered square

    def _integrate_branch_pair(self, blocks, left_branch, right_branch,
                               dimension, r, h, outer, max_h):
        left, right = blocks[left_branch], blocks[right_branch]
        if not left or not right:
            return None
        if (dimension != 0 and
                ({left_branch, right_branch} == {"Sdelta", "Stotal"} or
                 {left_branch, right_branch} == {"Ltotal", "Lbig"})):
            return None
        constraints = self.branch_domain(r, h, left_branch, right_branch)
        if constraints is None or (dimension != 0 and self.integrate_domain(
                {(0, 0): self.one}, dimension, r, outer, constraints) <= 0):
            return None
        combined = self.branch_orbit_product(
            left, right, left_branch == right_branch)
        total = defaultdict(self.scalar)
        for nu, marginal_polynomial in combined.items():
            density = self.orbit_density(dimension, nu, r, h, max_h)
            if density:
                add_poly(total, ei._poly_mul(density, marginal_polynomial),
                         self.one)
        return self.integrate_domain(
            dict(total), dimension, r, outer, constraints)

    def evaluate_j_r_blocks(self, lrs, by_lr, r, progress=False):
        """Return (S2_r, twoSL_r, L2_r) for one common stratum r."""
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        answer = [self.zero, self.zero, self.zero]
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
            blocks = self._branch_blocks(lrs, by_lr, r, h, dimension, outer)
            for i, left_branch in enumerate(branches):
                for right_branch in branches[:i + 1]:
                    value = self._integrate_branch_pair(
                        blocks, left_branch, right_branch,
                        dimension, r, h, outer, max_h)
                    if value is None:
                        continue
                    answer[self._branch_class(left_branch, right_branch)] += value
                    integrals += 1
            if progress:
                print(f"stratum J r={r} h={h} integrals={integrals}",
                      flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return tuple(answer), integrals

    def _j_component_data(self):
        components = self.marginal_components()
        lrs = sorted({lr for lr, _, _ in components})
        by_lr = {lr: [(e, a, value)
                      for (x, e, a), value in components.items() if x == lr]
                 for lr in lrs}
        return components, lrs, by_lr

    def evaluate_j_blocks(self, progress=False, workers=1):
        components, lrs, by_lr = self._j_component_data()
        r_values = self._r_values_j()
        if workers == 1:
            results = [(r, self.evaluate_j_r_blocks(
                lrs, by_lr, r, progress)) for r in r_values]
        else:
            global _FORK_EVALUATOR, _FORK_J_DATA
            _FORK_EVALUATOR, _FORK_J_DATA = self, (lrs, by_lr)
            try:
                with multiprocessing.get_context("fork").Pool(workers) as pool:
                    results = pool.map(_fork_j_block, r_values, chunksize=1)
            finally:
                _FORK_EVALUATOR = _FORK_J_DATA = None
        values = {r: value for r, (value, _) in results}
        return values, len(components), sum(item[1][1] for item in results)

    def assemble_forms(self, i_by_r, j_by_r):
        """Return diagonal A and diagonal/superdiagonal B=kJ."""
        max_r = max(i_by_r, default=-1)
        zero, k, two = self.zero, self.scalar(self.support.k), self.scalar(2)
        a_diagonal = [i_by_r.get(r, zero) for r in range(max_r + 1)]
        b_diagonal = []
        b_superdiagonal = []
        for r in range(max_r + 1):
            ss = j_by_r.get(r, (zero, zero, zero))[0]
            ll_previous = j_by_r.get(r - 1, (zero, zero, zero))[2]
            b_diagonal.append(k * (ss + ll_previous))
            if r < max_r:
                two_sl = j_by_r.get(r, (zero, zero, zero))[1]
                b_superdiagonal.append(k * two_sl / two)
        return a_diagonal, b_diagonal, b_superdiagonal

    @staticmethod
    def tridiagonal_quadratic(diagonal, superdiagonal, vector, zero):
        answer = sum((diagonal[i] * vector[i] * vector[i]
                      for i in range(len(diagonal))), zero)
        answer += sum((2 * superdiagonal[i] * vector[i] * vector[i + 1]
                       for i in range(len(superdiagonal))), zero)
        return answer

    def evaluate_all_blocks(self, progress=False, workers=1):
        i_by_r, i_groups, i_faces = self.evaluate_i_blocks(progress, workers)
        j_by_r, components, j_integrals = self.evaluate_j_blocks(
            progress, workers)
        a_diag, b_diag, b_super = self.assemble_forms(i_by_r, j_by_r)
        one = [self.one] * len(a_diag)
        denominator = self.tridiagonal_quadratic(
            a_diag, (), one, self.zero)
        numerator = self.tridiagonal_quadratic(
            b_diag, b_super, one, self.zero)
        return {
            "i_by_r": i_by_r,
            "j_by_common_r": j_by_r,
            "a_diagonal": a_diag,
            "b_diagonal": b_diag,
            "b_superdiagonal": b_super,
            "all_ones_denominator": denominator,
            "all_ones_numerator": numerator,
            "i_orbit_groups": i_groups,
            "i_faces": i_faces,
            "marginal_components": components,
            "j_branch_integrals": j_integrals,
        }

    @staticmethod
    def _amplitude(amplitudes, index, zero):
        return amplitudes[index] if 0 <= index < len(amplitudes) else zero

    def _scale_block(self, block, factor):
        if not factor:
            return {}
        return {lr: {monomial: factor * value
                     for monomial, value in polynomial.items() if factor * value}
                for lr, polynomial in block.items()}

    def evaluate_j_r_amplitude(self, lrs, by_lr, r, amplitudes,
                               progress=False):
        """Directly insert a_r/a_(r+1) before squaring the marginal."""
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        answer = self.zero
        dimension = self.support.k - 1
        integrals = 0
        max_h = int(self.support.eta // self.support.delta) - r
        if max_h < 0:
            return answer, integrals
        for h in range(max_h + 1):
            if dimension == 0 and (r != 0 or h != 0):
                continue
            outer = self.support.eta - (r + h) * self.support.delta
            if outer <= 0:
                continue
            blocks = self._branch_blocks(lrs, by_lr, r, h, dimension, outer)
            for branch in branches:
                total_r = r if branch in self.SMALL_BRANCHES else r + 1
                blocks[branch] = self._scale_block(
                    blocks[branch], self._amplitude(
                        amplitudes, total_r, self.zero))
            for i, left_branch in enumerate(branches):
                for right_branch in branches[:i + 1]:
                    value = self._integrate_branch_pair(
                        blocks, left_branch, right_branch,
                        dimension, r, h, outer, max_h)
                    if value is not None:
                        answer += value
                        integrals += 1
            if progress:
                print(f"amplitude J r={r} h={h} integrals={integrals}",
                      flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return answer, integrals

    def evaluate_amplitudes_direct(self, amplitudes, i_by_r=None,
                                   progress=False, workers=1):
        """Direct J reconstruction for one explicit amplitude vector."""
        amplitudes = tuple(amplitudes)
        if i_by_r is None:
            i_by_r, _, _ = self.evaluate_i_blocks(progress, workers)
        denominator = sum((value * self._amplitude(
            amplitudes, r, self.zero) ** 2 for r, value in i_by_r.items()),
            self.zero)
        components, lrs, by_lr = self._j_component_data()
        r_values = self._r_values_j()
        if workers == 1:
            results = [(r, self.evaluate_j_r_amplitude(
                lrs, by_lr, r, amplitudes, progress)) for r in r_values]
        else:
            global _FORK_EVALUATOR, _FORK_J_DATA, _FORK_AMPLITUDES
            _FORK_EVALUATOR = self
            _FORK_J_DATA = (lrs, by_lr)
            _FORK_AMPLITUDES = amplitudes
            try:
                with multiprocessing.get_context("fork").Pool(workers) as pool:
                    results = pool.map(_fork_j_amplitude, r_values, chunksize=1)
            finally:
                _FORK_EVALUATOR = _FORK_J_DATA = _FORK_AMPLITUDES = None
        j_value = sum((item[1][0] for item in results), self.zero)
        return denominator, self.scalar(self.support.k) * j_value, \
            len(components), sum(item[1][1] for item in results)


def _render(value):
    if isinstance(value, dict):
        return {str(key): _render(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_render(item) for item in value]
    return str(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--alpha", required=True)
    parser.add_argument("--delta", required=True)
    parser.add_argument("--eta", required=True)
    parser.add_argument("--beta1", required=True)
    parser.add_argument("--beta2", required=True)
    parser.add_argument("--beta3plus", required=True)
    parser.add_argument("--decimal-dps", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--amplitudes-json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")

    input_bytes = Path(args.input_json).read_bytes()
    raw = json.loads(input_bytes)
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    if len(labels) != len(raw["rational_vector"]):
        raise SystemExit("basis/vector dimension mismatch")
    orbit_table = precompute_orbits(labels, int(raw["k"]))
    if args.decimal_dps:
        getcontext().prec = args.decimal_dps
        scalar = install_decimal(orbit_table, args.decimal_dps)
        parse = parse_rational_decimal
        rigorous = False
    else:
        scalar, parse, rigorous = Fraction, Fraction, True
    parameters = [parse(value) for value in (
        args.alpha, args.delta, args.eta, args.beta1,
        args.beta2, args.beta3plus)]
    support = ei.OneStratumSupport(int(raw["k"]), *parameters)
    coefficients = [parse(value) for value in raw["rational_vector"]]
    evaluator = StratumAmplitudeEvaluator(
        support, labels, coefficients, scalar)
    start = time.perf_counter()
    result = evaluator.evaluate_all_blocks(args.progress, args.workers)
    amplitudes = None
    if args.amplitudes_json:
        amplitude_raw = json.loads(Path(args.amplitudes_json).read_text())
        if isinstance(amplitude_raw, dict):
            amplitude_raw = amplitude_raw["amplitudes"]
        amplitudes = [parse(value) for value in amplitude_raw]
        direct = evaluator.evaluate_amplitudes_direct(
            amplitudes, result["i_by_r"], args.progress, args.workers)
        result["amplitudes"] = amplitudes
        result["direct_amplitude_denominator"] = direct[0]
        result["direct_amplitude_numerator"] = direct[1]
        result["direct_amplitude_quotient"] = direct[1] / direct[0]
        result["direct_amplitude_j_integrals"] = direct[3]
    elapsed = time.perf_counter() - start
    output = {
        "status": ("exact-stratum-amplitude-blocks" if rigorous else
                   "multiprecision-stratum-amplitude-blocks-discovery"),
        "rigorous": rigorous,
        "decimal_dps": args.decimal_dps,
        "input_json": args.input_json,
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "grouped_evaluator_sha256": hashlib.sha256(Path(
            os.path.join(HERE, "grouped_fixed_vector.py")).read_bytes()).hexdigest(),
        "integrator_sha256": hashlib.sha256(Path(ei.__file__).read_bytes()).hexdigest(),
        "k": support.k,
        "parameters": {name: text for name, text in zip(
            ("alpha", "delta", "eta", "beta1", "beta2", "beta3plus"),
            (args.alpha, args.delta, args.eta, args.beta1,
             args.beta2, args.beta3plus))},
        "basis_dimension": len(labels),
        "workers": args.workers,
        "elapsed_seconds": elapsed,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        **{key: _render(value) for key, value in result.items()},
    }
    rendered = json.dumps(output, indent=2) + "\n"
    Path(args.output).write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
