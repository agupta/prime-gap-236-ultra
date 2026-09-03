#!/usr/bin/env python3
"""Grouped exact/multiprecision capped-support evaluation of one polynomial.

The input JSON gives explicit orbit labels and one rational coefficient vector.
Instead of evaluating thousands of orbit moments independently, this program
forms the complete bivariate integrand on each large-count/inclusion-exclusion
face, then performs one polygon integral.  The same grouping is used for every
intersection of the four distinguished-coordinate branches in J.

Default arithmetic is Fraction and is a certificate calculation.  The optional
``--decimal-dps`` mode uses the identical finite formulas for a faster discovery
value; it is not rigorous.
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
from functools import lru_cache
from math import comb, factorial
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

import exact_integrator as ei  # noqa: E402


_FORK_EVALUATOR = None
_FORK_I_GROUPED = None
_FORK_J_DATA = None


def _fork_i_r(r):
    """Fork worker entry point; large read-only objects are inherited by COW."""
    if _FORK_EVALUATOR is None or _FORK_I_GROUPED is None:
        raise RuntimeError("I fork globals were not initialized")
    return _FORK_EVALUATOR.evaluate_i_r(_FORK_I_GROUPED, r, False)


def _fork_j_r(r):
    """Fork worker entry point; Decimal monkeypatch closures are inherited."""
    if _FORK_EVALUATOR is None or _FORK_J_DATA is None:
        raise RuntimeError("J fork globals were not initialized")
    lrs, by_lr = _FORK_J_DATA
    return _FORK_EVALUATOR.evaluate_j_r(lrs, by_lr, r, False)


def precompute_orbits(labels, k):
    """Freeze all integer orbit products before an optional scalar monkeypatch."""
    needed = set()
    for _, lam in labels:
        for _, mu in labels:
            needed.add((lam, mu))
            for _, lr in ei.OneStratumSupport.split_at_distinguished(lam, k):
                for _, mr in ei.OneStratumSupport.split_at_distinguished(mu, k):
                    needed.add((lr, mr))
    return {key: ei.multiply_monomial_orbits(*key) for key in needed}


def install_decimal(orbit_table, dps):
    """Install Decimal as the scalar in a fresh exact_integrator process."""
    getcontext().prec = dps

    def mpq(numerator=0, denominator=None):
        if denominator is None:
            return Decimal(numerator)
        return Decimal(numerator) / Decimal(denominator)

    def orbit_lookup(lam, mu):
        key = (tuple(lam), tuple(mu))
        if key in orbit_table:
            return orbit_table[key]
        reverse = (key[1], key[0])
        if reverse in orbit_table:
            return orbit_table[reverse]
        raise KeyError(key)

    ei.Q = mpq
    ei.multiply_monomial_orbits = orbit_lookup

    @lru_cache(maxsize=None)
    def linear_power(c0, cz, cw, n):
        out = defaultdict(Decimal)
        for i in range(n + 1):
            for j in range(n - i + 1):
                h = n - i - j
                coefficient = (Decimal(factorial(n)) /
                               (Decimal(factorial(i)) * Decimal(factorial(j)) *
                                Decimal(factorial(h))))
                out[(i, j)] += (coefficient *
                                (Decimal(1) if i == 0 else cz ** i) *
                                (Decimal(1) if j == 0 else cw ** j) *
                                (Decimal(1) if h == 0 else c0 ** h))
        return tuple(out.items())

    ei._linear_power = linear_power

    def power(x, n):
        return Decimal(1) if n == 0 else x ** n

    @lru_cache(maxsize=None)
    def polygon_monomial(poly, az, aw):
        if not poly:
            return Decimal(0)
        answer = Decimal(0)
        ap = az + 1
        for idx, (x0, y0) in enumerate(poly):
            x1, y1 = poly[(idx + 1) % len(poly)]
            dx, dy = x1 - x0, y1 - y0
            if dy == 0:
                continue
            if dx == 0:
                answer += (power(x0, ap) *
                           (power(y1, aw + 1) - power(y0, aw + 1)) /
                           Decimal(ap * (aw + 1)))
            elif dx + dy == 0:
                constant = x0 + y0
                edge = Decimal(0)
                for i in range(ap + 1):
                    edge += (Decimal((-1) ** i * comb(ap, i)) /
                             Decimal(aw + i + 1) * power(constant, ap - i) *
                             (power(y1, aw + i + 1) - power(y0, aw + i + 1)))
                answer += edge / Decimal(ap)
            else:
                edge = Decimal(0)
                for i in range(ap + 1):
                    for j in range(aw + 1):
                        edge += (Decimal(comb(ap, i) * comb(aw, j)) /
                                 Decimal(i + j + 1) * power(x0, ap - i) *
                                 power(dx, i) * power(y0, aw - j) * power(dy, j))
                answer += dy * edge / Decimal(ap)
        return answer

    ei.polygon_monomial = polygon_monomial
    return mpq


def add_poly(target, source, factor):
    for monomial, value in source.items():
        target[monomial] += factor * value
        if target[monomial] == 0:
            del target[monomial]


class GroupedEvaluator:
    def __init__(self, support, labels, coefficients, scalar):
        self.support = support
        self.labels = labels
        self.coefficients = coefficients
        self.scalar = scalar
        self.zero = scalar(0)
        self.one = scalar(1)

    def clear_face_caches(self, clear_marginals=False):
        """Discard data which cannot be reused by a later (r,h) face.

        A degree-10/12 polynomial has hundreds of orbit densities and marginal
        polynomials on each face.  Keeping the unbounded ``lru_cache`` entries
        from every old face costs gigabytes but saves no work: ``outer``, r, and
        h have changed.  We retain them while all branch intersections on the
        current face are contracted and then release them deterministically.
        """
        self.orbit_density.cache_clear()
        for function in (ei._linear_power, ei.polygon_monomial, ei.polygon):
            clear = getattr(function, "cache_clear", None)
            if clear is not None:
                clear()
        if clear_marginals:
            clear = getattr(self.support._marginal_poly, "cache_clear", None)
            if clear is not None:
                clear()

    @staticmethod
    def clear_radial_caches():
        """Discard completed-r caches; a later r has different split lengths."""
        for function in (ei._large_shift_dp, ei._small_box_dp,
                         ei._selected_exponent_splits):
            clear = getattr(function, "cache_clear", None)
            if clear is not None:
                clear()

    @lru_cache(maxsize=None)
    def orbit_density(self, dimension, nu, r, h, max_h):
        """Angular density of P_nu on one fixed r,h aggregate face."""
        s = dimension - r
        if s < 0 or h < 0 or h > max_h:
            return {}
        density = defaultdict(self.scalar)
        for multiplicity, large, small in ei._selected_exponent_splits(
                dimension, nu, r):
            ld = ei._large_shift_dp(large, self.support.delta)
            sd = ei._small_box_dp(small, self.support.delta, max_h)
            for qdeg, lc0 in ld.items():
                lc = (lc0 / factorial(qdeg + r - 1)) if r else lc0
                zpower = qdeg + r - 1 if r else 0
                for (hh, pdeg), sc0 in sd.items():
                    if hh != h:
                        continue
                    sc = (sc0 / factorial(pdeg + s - 1)) if s else sc0
                    wpower = pdeg + s - 1 if s else 0
                    density[(zpower, wpower)] += multiplicity * lc * sc
        orbit_factor = ei.orbit_size(dimension, nu)
        return {mon: orbit_factor * value for mon, value in density.items() if value}

    def integrate_domain(self, polynomial, dimension, r, outer, constraints):
        if not polynomial or outer <= 0:
            return self.zero
        if dimension == 0:
            # Integration over no shared variables is evaluation at the sole
            # 0-dimensional point.  A constraint is feasible there exactly
            # when 0 <= cap.  Falling through to a fictitious w interval would
            # give a wrong k=1 marginal J.
            if any(cap < 0 for _, _, cap in constraints):
                return self.zero
            return polynomial.get((0, 0), self.zero)
        s = dimension - r
        if r and s:
            domain = ei.polygon(outer, constraints)
            return ei.integrate_poly_polygon(polynomial, domain)
        if r:
            lo, hi = self.zero, outer
            for az, aw, cap in constraints:
                if az > 0:
                    hi = min(hi, cap / az)
                elif az < 0:
                    lo = max(lo, cap / az)
                elif cap < 0:
                    return self.zero
            return ei._integrate_poly_z_interval(polynomial, lo, hi)
        lo, hi = self.zero, outer
        for az, aw, cap in constraints:
            if aw > 0:
                hi = min(hi, cap / aw)
            elif aw < 0:
                lo = max(lo, cap / aw)
            elif cap < 0:
                return self.zero
        return ei._integrate_poly_interval(polynomial, lo, hi)

    def square_residual_terms(self):
        """Coefficient of P_nu*(alpha-sum)^c in F^2."""
        terms = defaultdict(self.scalar)
        for i, (a, lam) in enumerate(self.labels):
            for j in range(i + 1):
                b, mu = self.labels[j]
                factor = self.coefficients[i] * self.coefficients[j]
                if i != j:
                    factor *= 2
                for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                    total = a + b
                    for c in range(total + 1):
                        terms[(nu, c)] += (factor * multiplicity * comb(total, c) *
                                          (self.one - self.support.alpha) ** (total - c))
        by_nu = defaultdict(dict)
        for (nu, c), value in terms.items():
            if value:
                by_nu[nu][c] = value
        return dict(by_nu)

    def evaluate_i_r(self, grouped, r, progress=False):
        """Evaluate every inclusion-exclusion face for one large count r."""
        answer = self.zero
        dimension = self.support.k
        faces = 0
        max_h = int(self.support.alpha // self.support.delta) - r
        if max_h < 0:
            return answer, faces
        constraints = ()
        if r:
            cap = self.support.beta(r) - r * self.support.delta
            if cap <= 0:
                return answer, faces
            constraints = ((self.one, self.zero, cap),)
        for h in range(max_h + 1):
            outer = self.support.alpha - (r + h) * self.support.delta
            if outer <= 0:
                continue
            total_poly = defaultdict(self.scalar)
            for nu, residuals in grouped.items():
                density = self.orbit_density(dimension, nu, r, h, max_h)
                if not density:
                    continue
                residual_poly = defaultdict(self.scalar)
                for c, coefficient in residuals.items():
                    add_poly(residual_poly,
                             dict(ei._linear_power(outer, -self.one, -self.one, c)),
                             coefficient)
                add_poly(total_poly, ei._poly_mul(density, residual_poly), self.one)
            answer += self.integrate_domain(
                dict(total_poly), dimension, r, outer, constraints)
            faces += 1
            if progress:
                print(f"I r={r} h={h} rfaces={faces} poly={len(total_poly)}",
                      flush=True)
            self.clear_face_caches()
        self.clear_radial_caches()
        return answer, faces

    def evaluate_i(self, progress=False, workers=1):
        grouped = self.square_residual_terms()
        max_r = min(self.support.k, self.support.max_large())
        r_values = list(range(max_r + 1))
        if workers == 1:
            results = [self.evaluate_i_r(grouped, r, progress) for r in r_values]
        else:
            global _FORK_EVALUATOR, _FORK_I_GROUPED
            _FORK_EVALUATOR = self
            _FORK_I_GROUPED = grouped
            context = multiprocessing.get_context("fork")
            try:
                with context.Pool(processes=workers) as pool:
                    results = pool.map(_fork_i_r, r_values, chunksize=1)
            finally:
                _FORK_EVALUATOR = None
                _FORK_I_GROUPED = None
        answer = sum((value for value, _ in results), self.zero)
        faces = sum(count for _, count in results)
        return answer, len(grouped), faces

    def marginal_components(self):
        components = defaultdict(self.scalar)
        for coefficient, (a, lam) in zip(self.coefficients, self.labels):
            for e, lr in self.support.split_at_distinguished(lam, self.support.k):
                components[(lr, e, a)] += coefficient
        return {key: value for key, value in components.items() if value}

    def branch_orbit_product(self, left, right, same_branch):
        """Map nu to its bivariate polynomial in one unordered branch pair."""
        combined = {}
        if same_branch:
            keys = list(left)
            for i, lr in enumerate(keys):
                for j in range(i + 1):
                    mr = keys[j]
                    pq = ei._poly_mul(left[lr], left[mr])
                    factor = self.scalar(2 if i != j else 1)
                    for nu, multiplicity in ei.multiply_monomial_orbits(lr, mr):
                        dest = combined.setdefault(nu, defaultdict(self.scalar))
                        add_poly(dest, pq, factor * multiplicity)
        else:
            for lr, p in left.items():
                for mr, q in right.items():
                    pq = ei._poly_mul(p, q)
                    for nu, multiplicity in ei.multiply_monomial_orbits(lr, mr):
                        dest = combined.setdefault(nu, defaultdict(self.scalar))
                        # The reversed branch order contributes the same domain
                        # and product, hence the factor two.
                        add_poly(dest, pq, self.scalar(2 * multiplicity))
        return {nu: dict(poly) for nu, poly in combined.items() if poly}

    def branch_domain(self, r, h, left, right):
        c1 = self.support._branch_constraints(r, h, left)
        c2 = self.support._branch_constraints(r, h, right)
        if c1 is None or c2 is None:
            return None
        return c1 + c2

    def evaluate_j_r(self, lrs, by_lr, r, progress=False):
        """Evaluate every marginal branch intersection for one large count r."""
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
            branch_polys = {}
            for branch in branches:
                branch_constraints = self.support._branch_constraints(r, h, branch)
                if dimension == 0:
                    # Mirror canonical_j_moment's half-open branch assignment
                    # exactly.  Cap feasibility alone cannot distinguish two
                    # branches which meet at the sole 0D point.
                    interval = self.support._branch_interval(0, 0, branch)
                    active = (interval is not None and
                              interval[0] <= 0 <= interval[1])
                else:
                    active = (branch_constraints is not None and
                              self.integrate_domain(
                                  {(0, 0): self.one}, dimension, r, outer,
                                  branch_constraints) > 0)
                if not active:
                    branch_polys[branch] = {}
                    continue
                block = {}
                for lr in lrs:
                    poly = defaultdict(self.scalar)
                    for e, a, value in by_lr[lr]:
                        add_poly(poly, dict(self.support._marginal_poly(
                            r, h, branch, e, a)), value)
                    if poly:
                        block[lr] = dict(poly)
                branch_polys[branch] = block

            for i, left_branch in enumerate(branches):
                left = branch_polys[left_branch]
                if not left:
                    continue
                for j in range(i + 1):
                    right_branch = branches[j]
                    right = branch_polys[right_branch]
                    if not right:
                        continue
                    # These pairs meet only on the affine boundary at which
                    # the active upper bound changes, hence have zero measure.
                    # Skipping before orbit multiplication avoids two costly
                    # contractions per generic face.  The s=0 tie is assigned
                    # once by _branch_constraints (Lbig is then None).
                    if (dimension != 0 and
                            ({left_branch, right_branch} == {"Sdelta", "Stotal"} or
                             {left_branch, right_branch} == {"Ltotal", "Lbig"})):
                        continue
                    constraints = self.branch_domain(
                        r, h, left_branch, right_branch)
                    if constraints is None or (dimension != 0 and
                            self.integrate_domain(
                                {(0, 0): self.one}, dimension, r, outer,
                                constraints) <= 0):
                        continue
                    combined = self.branch_orbit_product(
                        left, right, i == j)
                    total_poly = defaultdict(self.scalar)
                    for nu, marginal_poly in combined.items():
                        density = self.orbit_density(
                            dimension, nu, r, h, max_h)
                        if density:
                            add_poly(total_poly,
                                     ei._poly_mul(density, marginal_poly), self.one)
                    answer += self.integrate_domain(
                        dict(total_poly), dimension, r, outer, constraints)
                    integrals += 1
            if progress:
                print(f"J r={r} h={h} rintegrals={integrals}", flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return answer, integrals

    def evaluate_j(self, progress=False, workers=1):
        components = self.marginal_components()
        lrs = sorted({lr for lr, _, _ in components})
        by_lr = {lr: [(e, a, value) for (x, e, a), value in components.items()
                      if x == lr] for lr in lrs}
        max_r = min(self.support.k - 1, self.support.max_large())
        r_values = list(range(max_r + 1))
        if workers == 1:
            results = [self.evaluate_j_r(lrs, by_lr, r, progress) for r in r_values]
        else:
            global _FORK_EVALUATOR, _FORK_J_DATA
            _FORK_EVALUATOR = self
            _FORK_J_DATA = (lrs, by_lr)
            context = multiprocessing.get_context("fork")
            try:
                with context.Pool(processes=workers) as pool:
                    results = pool.map(_fork_j_r, r_values, chunksize=1)
            finally:
                _FORK_EVALUATOR = None
                _FORK_J_DATA = None
        answer = sum((value for value, _ in results), self.zero)
        integrals = sum(count for _, count in results)
        return answer, len(components), integrals


def parse_rational_decimal(text):
    value = Fraction(text)
    return Decimal(value.numerator) / Decimal(value.denominator)


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
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--i-stage")
    parser.add_argument("--resume-i-stage")
    parser.add_argument("--accept-i-stage-script-sha", action="append", default=[])
    parser.add_argument("--accept-legacy-i-stage-no-integrator-sha",
                        action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("workers must be positive")

    input_bytes = Path(args.input_json).read_bytes()
    raw = json.loads(input_bytes)
    input_hash = hashlib.sha256(input_bytes).hexdigest()
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    integrator_hash = hashlib.sha256(Path(ei.__file__).read_bytes()).hexdigest()
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    if len(labels) != len(raw["rational_vector"]):
        raise SystemExit("basis/vector dimension mismatch")

    orbit_table = precompute_orbits(labels, int(raw["k"]))
    if args.decimal_dps:
        scalar = install_decimal(orbit_table, args.decimal_dps)
        parse = parse_rational_decimal
        rigorous = False
    else:
        scalar = Fraction
        parse = Fraction
        rigorous = True
    parameters = [parse(x) for x in
                  (args.alpha, args.delta, args.eta, args.beta1,
                   args.beta2, args.beta3plus)]
    support = ei.OneStratumSupport(int(raw["k"]), *parameters)
    coefficients = [parse(x) for x in raw["rational_vector"]]
    evaluator = GroupedEvaluator(support, labels, coefficients, scalar)

    start = time.perf_counter()
    if args.resume_i_stage:
        stage = json.loads(Path(args.resume_i_stage).read_bytes())
        expected = {
            "input_sha256": input_hash,
            "script_sha256": script_hash,
            "integrator_sha256": integrator_hash,
            "decimal_dps": args.decimal_dps,
            "parameters": {"alpha": args.alpha, "delta": args.delta,
                           "eta": args.eta, "beta1": args.beta1,
                           "beta2": args.beta2, "beta3plus": args.beta3plus},
        }
        for key, value in expected.items():
            if (key == "integrator_sha256" and stage.get(key) is None and
                    args.accept_legacy_i_stage_no_integrator_sha and not rigorous):
                print("WARNING: accepting legacy non-rigorous I-stage without "
                      f"integrator SHA; current SHA is {value}", flush=True)
                continue
            if key == "script_sha256" and stage.get(key) != value:
                if (not rigorous and
                        stage.get(key) in args.accept_i_stage_script_sha):
                    print(f"WARNING: explicitly accepting I-stage script SHA "
                          f"{stage.get(key)} under current SHA {value}", flush=True)
                    continue
            if stage.get(key) != value:
                raise SystemExit(f"I-stage mismatch for {key}: "
                                 f"{stage.get(key)!r} != {value!r}")
        if stage.get("rigorous") != rigorous or not stage.get("i_complete"):
            raise SystemExit("I-stage arithmetic/status mismatch")
        denominator = parse(stage["denominator"])
        orbit_groups = int(stage["i_orbit_groups"])
        i_faces = int(stage["i_faces"])
        i_seconds = float(stage["i_seconds"])
        print(f"I RESUMED seconds={i_seconds:.6f} groups={orbit_groups} "
              f"faces={i_faces} rss_kib={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}",
              flush=True)
    else:
        denominator, orbit_groups, i_faces = evaluator.evaluate_i(
            args.progress, args.workers)
        i_seconds = time.perf_counter() - start
        stage = {
            "status": "grouped-fixed-vector-I-stage",
            "i_complete": True,
            "rigorous": rigorous,
            "decimal_dps": args.decimal_dps,
            "input_json": args.input_json,
            "input_sha256": input_hash,
            "script_sha256": script_hash,
            "integrator_sha256": integrator_hash,
            "parameters": {"alpha": args.alpha, "delta": args.delta,
                           "eta": args.eta, "beta1": args.beta1,
                           "beta2": args.beta2, "beta3plus": args.beta3plus},
            "i_orbit_groups": orbit_groups,
            "i_faces": i_faces,
            "i_seconds": i_seconds,
            "denominator_positive": denominator > 0,
            "denominator": str(denominator),
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "child_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        }
        stage_path = args.i_stage or ((args.output + ".I-stage.json")
                                      if args.output else None)
        if stage_path:
            Path(stage_path).write_text(json.dumps(stage, indent=2) + "\n",
                                        encoding="utf-8")
        print(f"I COMPLETE seconds={i_seconds:.6f} groups={orbit_groups} "
              f"faces={i_faces} rss_kib={stage['peak_rss_kib']} "
              f"stage={stage_path or '-'}", flush=True)
    after_i = time.perf_counter()
    j_value, components, branch_integrals = evaluator.evaluate_j(
        args.progress, args.workers)
    after_j = time.perf_counter()
    numerator = support.k * j_value
    elapsed = i_seconds + (after_j - after_i)
    result = {
        "status": ("exact-grouped-fixed-vector" if rigorous
                   else "multiprecision-grouped-fixed-vector-discovery"),
        "rigorous": rigorous,
        "decimal_dps": args.decimal_dps,
        "input_json": args.input_json,
        "k": support.k,
        "parameters": {"alpha": args.alpha, "delta": args.delta,
                       "eta": args.eta, "beta1": args.beta1,
                       "beta2": args.beta2, "beta3plus": args.beta3plus},
        "basis_dimension": len(labels),
        "workers": args.workers,
        "i_orbit_groups": orbit_groups,
        "i_faces": i_faces,
        "marginal_components": components,
        "j_branch_integrals": branch_integrals,
        "input_sha256": input_hash,
        "i_seconds": i_seconds,
        "j_seconds": after_j - after_i,
        "total_seconds": elapsed,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "peak_rss_note": ("parent and maximum single child are reported separately; "
                          "neither is their simultaneous sum"),
        "denominator_positive": denominator > 0,
        "margin_positive": numerator > denominator,
        "denominator": str(denominator),
        "j_value": str(j_value),
        "numerator": str(numerator),
        "quotient": str(numerator / denominator),
        "quotient_decimal_display": float(numerator / denominator),
        "margin": str(numerator - denominator),
        "script_sha256": script_hash,
        "integrator_sha256": integrator_hash,
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
