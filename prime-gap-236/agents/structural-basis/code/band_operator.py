#!/usr/bin/env python3
"""Low-memory value/gradient operator for the exact degree-band space.

This is a *discovery* program.  It reuses the audited support-face geometry in
``grouped_fixed_vector.py`` and replaces each polynomial coefficient by a
first-order jet.  One traversal therefore returns the value of each quadratic
form and its gradient in the 20 compressed coordinates.  A promising vector
must still be expanded and checked by the scalar Fraction evaluator.

The module is intentionally separate from the scalar certificate path.
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
from dataclasses import dataclass
from decimal import Decimal, getcontext, localcontext
from fractions import Fraction
from math import comb, factorial
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = os.path.dirname(os.path.abspath(__file__))
EXACT_AGENT = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator"))
EXACT_SRC = os.path.join(EXACT_AGENT, "src")
sys.path[:0] = [EXACT_AGENT, EXACT_SRC]

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import (  # noqa: E402
    GroupedEvaluator,
    install_decimal,
    precompute_orbits,
)


def _parse_fraction(text):
    return text if isinstance(text, Fraction) else Fraction(text)


def _parse_decimal(text):
    q = _parse_fraction(text)
    return Decimal(q.numerator) / Decimal(q.denominator)


@dataclass(frozen=True)
class BandMap:
    """Exact expanded labels, owners, weights, and the source coordinate."""

    labels: tuple
    owner: tuple
    weight_q: tuple
    theta0_q: tuple
    source_sha256: str = ""
    bands_sha256: str = ""

    @property
    def dimension(self):
        return len(self.theta0_q)

    @classmethod
    def from_source_and_bands(cls, source_json, bands_json):
        source_path = Path(source_json)
        bands_path = Path(bands_json)
        source_bytes = source_path.read_bytes()
        bands_bytes = bands_path.read_bytes()
        source = json.loads(source_bytes)
        bands = json.loads(bands_bytes)
        source_sha = hashlib.sha256(source_bytes).hexdigest()
        if bands.get("source_sha256") != source_sha:
            raise ValueError("degree-band source SHA mismatch")
        labels = tuple((int(a), tuple(int(x) for x in lam))
                       for a, lam in source["basis"])
        coefficients = tuple(_parse_fraction(x)
                             for x in source["rational_vector"])
        if len(labels) != len(coefficients) or len(labels) != len(set(labels)):
            raise ValueError("malformed or duplicate source basis")

        direction_terms = []
        theta0 = []
        for item in bands["core"]:
            label = (int(item["label"][0]),
                     tuple(int(x) for x in item["label"][1]))
            coefficient = _parse_fraction(item["coefficient"])
            direction_terms.append({label: Fraction(1)})
            theta0.append(coefficient)
        for degree in sorted(bands["bands"], key=int):
            block = {}
            for item in bands["bands"][degree]:
                label = (int(item["label"][0]),
                         tuple(int(x) for x in item["label"][1]))
                if label in block:
                    raise ValueError("duplicate label within a band")
                block[label] = _parse_fraction(item["coefficient"])
            direction_terms.append(block)
            theta0.append(Fraction(1))
        if len(direction_terms) != int(bands["compressed_basis_dimension"]):
            raise ValueError("compressed dimension mismatch")

        owner_by_label = {}
        weight_by_label = {}
        for direction, block in enumerate(direction_terms):
            for label, weight in block.items():
                if label in owner_by_label:
                    raise ValueError("label belongs to two directions")
                owner_by_label[label] = direction
                weight_by_label[label] = weight
        if set(owner_by_label) != set(labels):
            missing = set(labels) - set(owner_by_label)
            extra = set(owner_by_label) - set(labels)
            raise ValueError(f"band partition mismatch missing={missing} extra={extra}")
        owner = tuple(owner_by_label[label] for label in labels)
        weight = tuple(weight_by_label[label] for label in labels)
        expanded = tuple(weight[i] * theta0[owner[i]] for i in range(len(labels)))
        if expanded != coefficients:
            raise ValueError("theta0 does not reconstruct source vector")
        return cls(labels, owner, weight, tuple(theta0), source_sha,
                   hashlib.sha256(bands_bytes).hexdigest())

    @classmethod
    def from_explicit(cls, labels, owner, weights, theta0):
        labels = tuple((int(a), tuple(lam)) for a, lam in labels)
        return cls(labels, tuple(owner), tuple(map(_parse_fraction, weights)),
                   tuple(map(_parse_fraction, theta0)))

    def scalars(self, parse):
        return (tuple(parse(x) for x in self.weight_q),
                tuple(parse(x) for x in self.theta0_q))

    def expand(self, theta):
        if len(theta) != self.dimension:
            raise ValueError("theta dimension mismatch")
        return [self.weight_q[i] * _parse_fraction(theta[self.owner[i]])
                for i in range(len(self.labels))]


class Jet:
    """Immutable value plus a dense first derivative vector."""

    __slots__ = ("data",)

    def __init__(self, data):
        self.data = tuple(data)

    @classmethod
    def zero(cls, n, zero):
        return cls((zero,) * (n + 1))

    @classmethod
    def variable(cls, value, derivative, owner, n, zero):
        data = [zero] * (n + 1)
        data[0] = value
        data[owner + 1] = derivative
        return cls(data)

    @property
    def value(self):
        return self.data[0]

    @property
    def gradient(self):
        return self.data[1:]

    def __bool__(self):
        return any(self.data)

    def __eq__(self, other):
        if isinstance(other, Jet):
            return self.data == other.data
        if other == 0:
            return not self
        return False

    def __add__(self, other):
        if not isinstance(other, Jet):
            if other == 0:
                return self
            return NotImplemented
        return Jet(x + y for x, y in zip(self.data, other.data))

    __radd__ = __add__

    def __neg__(self):
        return Jet(-x for x in self.data)

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        if isinstance(other, Jet):
            x0, y0 = self.data[0], other.data[0]
            return Jet((x0 * y0,) + tuple(
                x0 * y + y0 * x
                for x, y in zip(self.data[1:], other.data[1:])))
        return Jet(x * other for x in self.data)

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        return Jet(x / other for x in self.data)

    def scaled(self, scalar):
        return self * scalar


def _jet_poly_add(target, source, factor):
    """Add a scalar- or Jet-valued polynomial into a Jet-valued target."""
    for monomial, value in source.items():
        target[monomial] = target[monomial] + factor * value
        if target[monomial] == 0:
            del target[monomial]


class BandOperator(GroupedEvaluator):
    """Grouped capped operator with a dense value/gradient coefficient jet."""

    def __init__(self, support, band_map, theta, scalar):
        self.band_map = band_map
        self.jet_dimension = band_map.dimension
        if len(theta) != self.jet_dimension:
            raise ValueError("theta dimension mismatch")
        self.theta = tuple(theta)
        weights = tuple(scalar(q.numerator, q.denominator)
                        if scalar is Fraction else
                        scalar(q.numerator) / scalar(q.denominator)
                        for q in band_map.weight_q)
        values = tuple(weights[i] * theta[band_map.owner[i]]
                       for i in range(len(band_map.labels)))
        super().__init__(support, list(band_map.labels), list(values), scalar)
        base_zero = scalar(0)
        self.base_zero = base_zero
        self.base_one = scalar(1)
        self.jet_zero = Jet.zero(self.jet_dimension, base_zero)
        # Keep GroupedEvaluator's ``zero`` scalar: it is also used as the zero
        # coefficient of support halfplanes.  Scalar-zero accumulators promote
        # to Jet on their first nonzero addition via Jet.__radd__.
        self.zero = base_zero
        self.one = self.base_one
        self.coefficient_jets = tuple(
            Jet.variable(values[i], weights[i], band_map.owner[i],
                         self.jet_dimension, base_zero)
            for i in range(len(values)))

    def _scalar_integrate_domain(self, polynomial, dimension, r, outer,
                                 constraints):
        if not polynomial or outer <= 0:
            return self.base_zero
        if dimension == 0:
            if any(cap < 0 for _, _, cap in constraints):
                return self.base_zero
            return polynomial.get((0, 0), self.base_zero)
        s = dimension - r
        if r and s:
            return ei.integrate_poly_polygon(
                polynomial, ei.polygon(outer, constraints))
        if r:
            lo, hi = self.base_zero, outer
            for az, _, cap in constraints:
                if az > 0:
                    hi = min(hi, cap / az)
                elif az < 0:
                    lo = max(lo, cap / az)
                elif cap < 0:
                    return self.base_zero
            return ei._integrate_poly_z_interval(polynomial, lo, hi)
        lo, hi = self.base_zero, outer
        for _, aw, cap in constraints:
            if aw > 0:
                hi = min(hi, cap / aw)
            elif aw < 0:
                lo = max(lo, cap / aw)
            elif cap < 0:
                return self.base_zero
        return ei._integrate_poly_interval(polynomial, lo, hi)

    def _domain_moment(self, monomial, dimension, r, outer, constraints):
        return self._scalar_integrate_domain(
            {monomial: self.base_one}, dimension, r, outer, constraints)

    def integrate_domain(self, polynomial, dimension, r, outer, constraints):
        """Integrate all jet channels using one shared monomial-moment pass."""
        if not polynomial:
            return self.jet_zero
        sample = next(iter(polynomial.values()))
        if not isinstance(sample, Jet):
            return self._scalar_integrate_domain(
                polynomial, dimension, r, outer, constraints)
        accum = [self.base_zero] * (self.jet_dimension + 1)
        for monomial, coefficient in polynomial.items():
            moment = self._domain_moment(
                monomial, dimension, r, outer, constraints)
            if moment:
                for channel, value in enumerate(coefficient.data):
                    accum[channel] += value * moment
        return Jet(accum)

    def square_residual_terms(self):
        """Jet coefficient of P_nu*(alpha-sum)^c in F(theta)^2."""
        terms = {}
        for i, (a, lam) in enumerate(self.labels):
            for j in range(i + 1):
                b, mu = self.labels[j]
                factor = self.coefficient_jets[i] * self.coefficient_jets[j]
                if i != j:
                    factor = factor * self.scalar(2)
                total = a + b
                for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                    for c in range(total + 1):
                        key = (nu, c)
                        scalar_factor = (self.scalar(multiplicity * comb(total, c)) *
                                         (self.base_one - self.support.alpha) **
                                         (total - c))
                        terms[key] = terms.get(key, self.jet_zero) + factor * scalar_factor
        by_nu = defaultdict(dict)
        for (nu, c), value in terms.items():
            if value:
                by_nu[nu][c] = value
        return dict(by_nu)

    def marginal_components(self):
        components = {}
        for coefficient, (a, lam) in zip(self.coefficient_jets, self.labels):
            for e, lr in self.support.split_at_distinguished(
                    lam, self.support.k):
                key = (lr, e, a)
                components[key] = components.get(key, self.jet_zero) + coefficient
        return {key: value for key, value in components.items() if value}

    def apply(self, progress=False, workers=1):
        """Return D, N, A*theta, B*theta and traversal counts."""
        start = time.perf_counter()
        i_jet, i_groups, i_faces = self.evaluate_i(progress, workers)
        after_i = time.perf_counter()
        j_jet, components, j_integrals = self.evaluate_j(progress, workers)
        after_j = time.perf_counter()
        k = self.scalar(self.support.k)
        denominator = i_jet.value
        numerator = k * j_jet.value
        a_theta = tuple(x / self.scalar(2) for x in i_jet.gradient)
        b_theta = tuple(k * x / self.scalar(2) for x in j_jet.gradient)
        euler_d = sum((x * y for x, y in zip(self.theta, i_jet.gradient)),
                      self.base_zero) - self.scalar(2) * denominator
        euler_n = sum((x * k * y for x, y in zip(self.theta, j_jet.gradient)),
                      self.base_zero) - self.scalar(2) * numerator
        return {
            "denominator": denominator,
            "numerator": numerator,
            "quotient": numerator / denominator,
            "a_theta": a_theta,
            "b_theta": b_theta,
            "grad_denominator": i_jet.gradient,
            "grad_numerator": tuple(k * x for x in j_jet.gradient),
            "euler_denominator_error": euler_d,
            "euler_numerator_error": euler_n,
            "i_orbit_groups": i_groups,
            "i_faces": i_faces,
            "marginal_components": components,
            "j_branch_integrals": j_integrals,
            "i_seconds": after_i - start,
            "j_seconds": after_j - after_i,
            "total_seconds": after_j - start,
        }


def full_simplex_i_preconditioner(band_map, k, alpha, scalar=Decimal,
                                  progress=False):
    """Closed Dirichlet reconstruction of the compressed full-simplex I form."""
    n = band_map.dimension
    zero, one = scalar(0), scalar(1)
    weights = [scalar(q.numerator) / scalar(q.denominator)
               if scalar is not Fraction else q for q in band_map.weight_q]
    matrix = [[zero for _ in range(n)] for _ in range(n)]
    moment_cache = {}

    def orbit_moment(nu, residual):
        key = (nu, residual)
        if key in moment_cache:
            return moment_cache[key]
        orbit = scalar(ei.orbit_size(k, nu))
        prod = 1
        for x in nu:
            prod *= factorial(x)
        total_nu = sum(nu)
        ans = zero
        for c in range(residual + 1):
            angular_num = comb(residual, c) * factorial(c) * prod
            degree = total_nu + k + c
            term = (scalar(angular_num) / scalar(factorial(degree)) *
                    (one - alpha) ** (residual - c) * alpha ** degree)
            ans += term
        ans *= orbit
        moment_cache[key] = ans
        return ans

    labels = band_map.labels
    for i, (a, lam) in enumerate(labels):
        oi, wi = band_map.owner[i], weights[i]
        for j in range(i + 1):
            b, mu = labels[j]
            oj, wj = band_map.owner[j], weights[j]
            value = zero
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                value += scalar(multiplicity) * orbit_moment(nu, a + b)
            value *= wi * wj
            if i == j:
                matrix[oi][oi] += value
            elif oi == oj:
                matrix[oi][oi] += scalar(2) * value
            else:
                matrix[oi][oj] += value
                matrix[oj][oi] += value
        if progress and (i + 1) % 16 == 0:
            print(f"preconditioner row {i + 1}/{len(labels)}", flush=True)
    return matrix


def dot(x, y, zero):
    return sum((a * b for a, b in zip(x, y)), zero)


def matvec(matrix, vector, zero):
    return [dot(row, vector, zero) for row in matrix]


def decimal_solve(matrix, rhs, precision=220):
    """Dense Decimal Gaussian elimination with scaled partial pivoting."""
    with localcontext() as ctx:
        ctx.prec = precision
        n = len(rhs)
        a = [[+matrix[i][j] for j in range(n)] + [+rhs[i]]
             for i in range(n)]
        scales = [max(abs(x) for x in row[:-1]) for row in a]
        for col in range(n):
            pivot = max(range(col, n),
                        key=lambda r: abs(a[r][col]) / scales[r]
                        if scales[r] else Decimal(0))
            if not a[pivot][col]:
                raise ArithmeticError("singular preconditioner")
            if pivot != col:
                a[col], a[pivot] = a[pivot], a[col]
                scales[col], scales[pivot] = scales[pivot], scales[col]
            p = a[col][col]
            for r in range(col + 1, n):
                if not a[r][col]:
                    continue
                factor = a[r][col] / p
                a[r][col] = Decimal(0)
                for j in range(col + 1, n + 1):
                    a[r][j] -= factor * a[col][j]
        x = [Decimal(0)] * n
        for i in range(n - 1, -1, -1):
            x[i] = (a[i][n] - sum((a[i][j] * x[j]
                                    for j in range(i + 1, n)), Decimal(0))) / a[i][i]
        return [+v for v in x]


def preconditioned_residual(theta, result, preconditioner, precision=220):
    """P-normalized residual correction, P-orthogonal to theta."""
    with localcontext() as ctx:
        ctx.prec = precision
        zero = Decimal(0)
        lam = +result["quotient"]
        residual = [+(b - lam * a)
                    for a, b in zip(result["a_theta"], result["b_theta"])]
        direction = decimal_solve(preconditioner, residual, precision)
        p_theta = matvec(preconditioner, theta, zero)
        p_dir = matvec(preconditioner, direction, zero)
        theta_norm = dot(theta, p_theta, zero)
        projection = dot(theta, p_dir, zero) / theta_norm
        direction = [d - projection * t for d, t in zip(direction, theta)]
        p_dir = matvec(preconditioner, direction, zero)
        norm2 = dot(direction, p_dir, zero)
        if norm2 <= 0:
            raise ArithmeticError("nonpositive P norm")
        norm = norm2.sqrt()
        return [+(x / norm) for x in direction], residual


def _render_number(x):
    return str(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--bands", required=True)
    ap.add_argument("--theta-json",
                    help="JSON list or object with a theta field; default theta0")
    ap.add_argument("--decimal-dps", type=int, default=90)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--alpha", default="79247/300000")
    ap.add_argument("--delta", default="1/100")
    ap.add_argument("--eta", default="76247/300000")
    ap.add_argument("--beta1", default="3/20")
    ap.add_argument("--beta2", default="3/20")
    ap.add_argument("--beta3plus", default="97/625")
    ap.add_argument("--progress", action="store_true")
    ap.add_argument("--preconditioner", action="store_true")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    if args.decimal_dps < 50:
        ap.error("discovery precision must be at least 50 digits")
    if args.workers < 1:
        ap.error("workers must be positive")
    getcontext().prec = args.decimal_dps
    band_map = BandMap.from_source_and_bands(args.source, args.bands)
    orbit_table = precompute_orbits(list(band_map.labels), 48)
    install_decimal(orbit_table, args.decimal_dps)
    parse = _parse_decimal
    support = ei.OneStratumSupport(
        48, parse(args.alpha), parse(args.delta), parse(args.eta),
        parse(args.beta1), parse(args.beta2), parse(args.beta3plus))
    _, theta0 = band_map.scalars(parse)
    theta = list(theta0)
    if args.theta_json:
        raw_theta = json.loads(Path(args.theta_json).read_text())
        if isinstance(raw_theta, dict):
            raw_theta = raw_theta["theta"]
        theta = [parse(x) for x in raw_theta]
    operator = BandOperator(support, band_map, theta, Decimal)
    result = operator.apply(args.progress, args.workers)
    output = {
        "status": "multiprecision-degree-band-gradient-discovery",
        "rigorous": False,
        "complete": True,
        "decimal_dps": args.decimal_dps,
        "workers": args.workers,
        "source_json": args.source,
        "source_sha256": band_map.source_sha256,
        "bands_json": args.bands,
        "bands_sha256": band_map.bands_sha256,
        "operator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "integrator_sha256": hashlib.sha256(Path(ei.__file__).read_bytes()).hexdigest(),
        "grouped_evaluator_sha256": hashlib.sha256(
            Path(os.path.join(EXACT_AGENT, "grouped_fixed_vector.py")).read_bytes()
        ).hexdigest(),
        "parameters": {"alpha": args.alpha, "delta": args.delta,
                       "eta": args.eta, "beta1": args.beta1,
                       "beta2": args.beta2, "beta3plus": args.beta3plus},
        "theta": [_render_number(x) for x in theta],
        "denominator": _render_number(result["denominator"]),
        "numerator": _render_number(result["numerator"]),
        "quotient": _render_number(result["quotient"]),
        "a_theta": [_render_number(x) for x in result["a_theta"]],
        "b_theta": [_render_number(x) for x in result["b_theta"]],
        "grad_denominator": [_render_number(x) for x in result["grad_denominator"]],
        "grad_numerator": [_render_number(x) for x in result["grad_numerator"]],
        "euler_denominator_error": _render_number(
            result["euler_denominator_error"]),
        "euler_numerator_error": _render_number(result["euler_numerator_error"]),
        "i_orbit_groups": result["i_orbit_groups"],
        "i_faces": result["i_faces"],
        "marginal_components": result["marginal_components"],
        "j_branch_integrals": result["j_branch_integrals"],
        "i_seconds": result["i_seconds"],
        "j_seconds": result["j_seconds"],
        "total_seconds": result["total_seconds"],
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    }
    if args.preconditioner:
        start = time.perf_counter()
        preconditioner = full_simplex_i_preconditioner(
            band_map, 48, support.alpha, Decimal, args.progress)
        direction, residual = preconditioned_residual(
            theta, result, preconditioner, max(220, args.decimal_dps))
        output["preconditioner_seconds"] = time.perf_counter() - start
        output["preconditioned_direction"] = [_render_number(x) for x in direction]
        output["residual"] = [_render_number(x) for x in residual]
    output["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
