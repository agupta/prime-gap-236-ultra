#!/usr/bin/env python3
"""Bounded numerical oracle for cap-adapted D18 count coordinates.

This is discovery code, not an exact integrator.  Its primary outer coordinate
is the I-Riesz representer of the cross functional with the audited D18 inner
coordinate.  It also keeps the naturally dilated D18 outer coordinate and a
small gamma-lift comparison family explicitly.

The Monte Carlo proposal first samples the large-coordinate excesses uniformly
on the radially truncated count simplex

    x_i >= 0, sum(x_i) <= min(gamma_R, alpha2-R*delta).

Conditional on x, it samples the small coordinates uniformly on the simplex
sum(y)<=alpha2-R*delta-sum(x), and applies the exact variable-volume importance
weight before rejecting max(y)>delta or total<=alpha1.  This concentrates the
proposal on the narrow upper shell without changing its measure.  The D18
marginal is formed by exact rational antiderivatives before numerical point
evaluation.  Frozen/exact D0 count-stratum I values are estimated in the same
samples and form a mandatory geometry calibration.  Independent literal k=2
Fraction oracles check both the Riesz/Fubini factor convention and the
importance weight.  Nothing in this file launches an exact target or makes a
theorem claim.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time


# Keep numerical linear algebra single-threaded.  These assignments precede
# numpy's import deliberately.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
TEST_FILE = REPO / (
    "agents/structural-basis/tests/"
    "test_active25_d18_cap_adapted_oracle_v1.py")
SPEC_FILE = REPO / (
    "agents/structural-basis/ACTIVE25-D18-CAP-ADAPTED-ORACLE-V1.md")
CERT = REPO / (
    "agents/exact-integrator/results/"
    "aquarter_fullsimplex_k48_B18_refined_exact.json")
UNCAPPED = REPO / (
    "results/wide_c722_B18_piecewise_cinner1_couter_natural_exact.json")
ANALYTIC = REPO / (
    "agents/audit/results/"
    "wide_c722_nonuniform_active25_tail_analytic_audit.json")
D0 = REPO / "results/active25_count_cap_slack_shell_d0_v1.json"
DILATION = REPO / "scripts/full_simplex_dilated_vector_proxy.py"
POINT = REPO / "agents/structural-basis/code/importance_point_eval.py"

PINS = {
    CERT: "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58",
    UNCAPPED: "49ecca1b962d06a8ee793e7ce0a3dcdf4ef1fd38595ccd86c784950636d903fd",
    ANALYTIC: "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
    D0: "6e97c4b35d27e40f40e258dd00726d84f2dfc3c910ef9542250d45be9624e195",
    DILATION: "3219047bd9d339e15946947f68bd6484d23af722337ba70771c488e3e1238794",
    POINT: "ea88f6d29b744f59ad146bdebf9b2003a2d57e40eea5b7a03fb48f2309cdfc01",
}

K = 48
ALPHA1 = Q(103, 400)
ALPHA2 = Q(3211, 12000)
ETA1 = Q(97, 400)
ETA2 = Q(3031, 12000)
DELTA = Q(361, 50000)
OUTER_C = ALPHA1 / ALPHA2
AUDITED_SCHEDULE = (
    Q(597, 5000), Q(633, 5000), Q(669, 5000), Q(141, 1000),
    Q(737, 5000), Q(773, 5000), Q(1553, 10000), Q(809, 5000),
    Q(81, 500), Q(3329, 20000), Q(169, 1000), Q(339, 2000),
    Q(859, 5000), Q(1737, 10000), Q(219, 1250), Q(881, 5000),
    Q(441, 2500), Q(887, 5000), Q(891, 5000), Q(179, 1000),
    Q(449, 2500), Q(1801, 10000), Q(903, 5000), Q(1811, 10000),
    Q(363, 2000), Q(363, 2000),
)
D014_SCHEDULE = tuple(Q(value) for value in (
    "0.133029229", "0.147029229", "0.159772569", "0.161028601",
    "0.174700442", "0.178498580", "0.181436642", "0.183088653",
    "0.184802990", "0.186140204", "0.187160624", "0.188031238",
    "0.188703410", "0.195998220", "0.209998220", "0.223998220",
    "0.237993073", "0.251993073", "0.265993073", "0.279993073",
    "0.293993073", "0.307992806", "0.321992806", "0.335992806",
    "0.349992806", "0.363992806"))
D1OVER60_SCHEDULE = tuple(Q(value) for value in (
    "0.138362442", "0.155023058", "0.158665131", "0.171691048",
    "0.177687929", "0.180591939", "0.183406411", "0.185490751",
    "0.187015407", "0.188225669", "0.189142062", "0.199996597",
    "0.216660746", "0.233324918", "0.249991531", "0.266658144",
    "0.283324756", "0.299991369", "0.316657982", "0.333324595",
    "0.349991207", "0.366657820", "0.383324433", "0.399991045",
    "0.416657658", "0.433324271"))
GEOMETRIES = {
    "audited": {
        "approved": True, "delta": Q(361, 50000),
        "alpha2": Q(3211, 12000), "eta2": Q(3031, 12000),
        "schedule": AUDITED_SCHEDULE,
        "source": "independently audited active25 correlated lift",
    },
    "d014": {
        "approved": False, "delta": Q(7, 500),
        "alpha2": Q(79597, 300000), "eta2": Q(75097, 300000),
        "schedule": D014_SCHEDULE,
        "source": "unvalidated adaptive support optimizer d014 proxy",
    },
    "d1over60": {
        "approved": False, "delta": Q(1, 60),
        "alpha2": Q(237991, 900000), "eta2": Q(224491, 900000),
        "schedule": D1OVER60_SCHEDULE,
        "source": "unvalidated adaptive support optimizer d1over60 proxy",
    },
}
GEOMETRY_NAME = "audited"
SCHEDULE = AUDITED_SCHEDULE
SELECTED_COUNTS = tuple(range(9, 15))
RIEZS_FOCUS_COUNTS = tuple(range(1, 15))
CALIBRATION_COUNTS = tuple(range(6, 15))
MAX_ACTIVE_COUNT = 25
POINT_RELATIVE_TOLERANCE = Decimal("1e-7")


def configure_geometry(name):
    global GEOMETRY_NAME, ALPHA2, ETA2, DELTA, OUTER_C, SCHEDULE
    global MAX_ACTIVE_COUNT, CALIBRATION_COUNTS
    if name not in GEOMETRIES:
        raise ValueError("unknown support geometry")
    row = GEOMETRIES[name]
    GEOMETRY_NAME = name
    ALPHA2 = row["alpha2"]
    ETA2 = row["eta2"]
    DELTA = row["delta"]
    OUTER_C = ALPHA1 / ALPHA2
    SCHEDULE = row["schedule"]
    MAX_ACTIVE_COUNT = max(
        r for r, value in enumerate(SCHEDULE, 1) if r * DELTA < value)
    if name == "audited":
        CALIBRATION_COUNTS = tuple(range(6, 15))
    elif name == "d014":
        CALIBRATION_COUNTS = tuple(range(1, 10))
    else:
        CALIBRATION_COUNTS = tuple(range(1, 9))


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json(path: Path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite JSON token {token}")))


def ld(value) -> np.longdouble:
    value = Q(value)
    return (np.longdouble(value.numerator) /
            np.longdouble(value.denominator))


def beta(count: int) -> Q:
    if type(count) is not int or not 1 <= count <= len(SCHEDULE):
        raise ValueError("count has no active cap schedule")
    return SCHEDULE[count - 1]


def gamma(count: int) -> Q:
    answer = beta(count) - count * DELTA
    if answer <= 0:
        raise ValueError("count has no positive excess budget")
    return answer


def candidate_labels():
    answer = [("inner_d18", None, 0), ("riesz_d18", None, 0),
              ("natural_outer_d18", None, 0)]
    for count in SELECTED_COUNTS:
        answer.extend((("gamma_lift_d18", count, 0),
                       ("gamma_lift_d18", count, 1)))
    if len(answer) != 15 or len(set(answer)) != 15:
        raise ArithmeticError("candidate inventory changed")
    return tuple(answer)


def dilate_vector(basis, vector, factor):
    """Independent exact implementation of P(t) -> P(factor*t)."""
    index = {label: i for i, label in enumerate(basis)}
    if len(index) != len(basis):
        raise ValueError("duplicate D18 basis label")
    answer = [Q(0) for _ in basis]
    for coefficient, (a, lam) in zip(vector, basis):
        for b in range(a + 1):
            label = (b, lam)
            if label not in index:
                raise ValueError(f"D18 dilation is not closed at {label}")
            answer[index[label]] += (
                coefficient * math.comb(a, b) *
                (1 - factor) ** (a - b) *
                factor ** (b + sum(lam)))
    return tuple(answer)


class PowerSumOrbitEvaluator:
    """Evaluate monomial-symmetric orbits by a power-sum recurrence."""

    def __init__(self, partitions):
        canonical = {tuple(sorted(tuple(map(int, part)), reverse=True))
                     for part in partitions}
        canonical.add(())
        while True:
            enlarged = set(canonical)
            for part in canonical:
                if not part:
                    continue
                chosen = part[-1]
                rest = list(part)
                rest.remove(chosen)
                rest = tuple(rest)
                enlarged.add(rest)
                for exponent in set(rest):
                    merged = list(rest)
                    merged.remove(exponent)
                    merged.append(exponent + chosen)
                    enlarged.add(tuple(sorted(merged, reverse=True)))
            if enlarged == canonical:
                break
            canonical = enlarged
        self.partitions = tuple(sorted(
            canonical, key=lambda part: (len(part), sum(part), part)))
        self.index = {part: i for i, part in enumerate(self.partitions)}
        self.max_power = max((max(x) for x in self.partitions if x),
                             default=0)
        rows = []
        for part in self.partitions:
            if not part:
                rows.append(None)
                continue
            chosen = part[-1]
            rest = list(part)
            rest.remove(chosen)
            rest = tuple(rest)
            merges = []
            for exponent in sorted(set(rest)):
                merged = list(rest)
                merged.remove(exponent)
                merged.append(exponent + chosen)
                merged = tuple(sorted(merged, reverse=True))
                merges.append((self.index[merged],
                               merged.count(exponent + chosen)))
            rows.append((chosen, self.index[rest], part.count(chosen),
                         tuple(merges)))
        self.recurrences = tuple(rows)

    def evaluate(self, points):
        points = np.asarray(points, dtype=np.longdouble)
        if (points.ndim != 2 or points.shape[1] != K or
                not np.isfinite(points).all()):
            raise ValueError(f"points must be a finite N-by-{K} matrix")
        count = len(points)
        powers = {}
        current = np.ones_like(points)
        for exponent in range(1, self.max_power + 1):
            current *= points
            powers[exponent] = np.sum(current, axis=1,
                                      dtype=np.longdouble)
        values = np.zeros((len(self.partitions), count),
                          dtype=np.longdouble)
        values[self.index[()]] = 1
        for index, recurrence in enumerate(self.recurrences):
            if recurrence is None:
                continue
            exponent, rest, divisor, merges = recurrence
            answer = powers[exponent] * values[rest]
            for merged, multiplicity in merges:
                answer -= multiplicity * values[merged]
            values[index] = answer / divisor
        return values


class ResidualD18:
    """Cancellation-resistant evaluation of P(dilation*t), up to a scale."""

    def __init__(self, basis, vector, *, center, dilation):
        center, dilation = Q(center), Q(dilation)
        if dilation * center != ALPHA1:
            raise ValueError("residual center and dilation are inconsistent")
        self.basis = tuple(basis)
        self.vector = tuple(vector)
        self.center = center
        self.dilation = dilation
        self.orbits = PowerSumOrbitEvaluator(lam for _, lam in basis)
        self.max_residual = max(a for a, _ in basis)
        coefficients = defaultdict(Q)
        for theta, (a, lam) in zip(vector, basis):
            for power in range(a + 1):
                coefficients[(power, lam)] += (
                    theta * math.comb(a, power) *
                    (1 - ALPHA1) ** (a - power) *
                    dilation ** (power + sum(lam)))
        self.scale = max(abs(value) for value in coefficients.values())
        if self.scale <= 0:
            raise ArithmeticError("zero D18 scale")
        matrix = np.zeros((len(self.orbits.partitions),
                           self.max_residual + 1), dtype=np.longdouble)
        for (power, lam), value in coefficients.items():
            matrix[self.orbits.index[lam], power] += ld(value / self.scale)
        self.coefficients = matrix

    def evaluate(self, points):
        points = np.asarray(points, dtype=np.longdouble)
        orbit = self.orbits.evaluate(points)
        residual = ld(self.center) - np.sum(
            points, axis=1, dtype=np.longdouble)
        powers = np.ones((self.max_residual + 1, len(points)),
                         dtype=np.longdouble)
        for power in range(1, self.max_residual + 1):
            powers[power] = powers[power - 1] * residual
        by_orbit = self.coefficients @ powers
        answer = np.sum(orbit * by_orbit, axis=0, dtype=np.longdouble)
        if not np.isfinite(answer).all():
            raise ArithmeticError("nonfinite D18 point evaluation")
        return answer


class MarginalD18:
    """Exact-antiderivative D18 marginal, normalized with the inner F.

    For U=sum(x), the represented function is

        m_F(x) = integral_0^(alpha1-U) F(x,t) dt / inner_scale.

    ``omit_values`` evaluates this function on all 48 leave-one-coordinate-
    out vectors without changing the order or averaging the coordinates.
    """

    def __init__(self, basis, vector, inner_scale):
        coefficients = defaultdict(Q)
        for theta, (a, lam) in zip(vector, basis):
            distinguished = [(0, lam)] if len(lam) < K else []
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
                        theta * factor * (1 - ALPHA1) ** (a - c))
        coefficients = {key: value for key, value in coefficients.items()
                        if value}
        if len(coefficients) != 471:
            raise ArithmeticError("D18 marginal inventory changed")
        self.orbits = PowerSumOrbitEvaluator(rest for _, rest in coefficients)
        self.max_residual = max(power for power, _ in coefficients)
        self.inner_scale = Q(inner_scale)
        matrix = np.zeros((len(self.orbits.partitions),
                           self.max_residual + 1), dtype=np.longdouble)
        for (power, rest), value in coefficients.items():
            matrix[self.orbits.index[rest], power] += ld(
                value / self.inner_scale)
        self.coefficients = matrix

    def evaluate(self, padded_common):
        """Evaluate on a common vector padded by one zero coordinate."""
        points = np.asarray(padded_common, dtype=np.longdouble)
        orbit = self.orbits.evaluate(points)
        residual = ld(ALPHA1) - np.sum(
            points, axis=1, dtype=np.longdouble)
        answer = np.zeros(len(points), dtype=np.longdouble)
        power = np.ones(len(points), dtype=np.longdouble)
        for exponent in range(self.max_residual + 1):
            answer += (self.coefficients[:, exponent] @ orbit) * power
            power *= residual
        return answer

    def _omit_chunk(self, points):
        """All m_F(t without i) for a small N-by-48 point chunk."""
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
        values[self.orbits.index[()]] = np.ones((n, K),
                                                dtype=np.longdouble)
        for index, recurrence in enumerate(self.orbits.recurrences):
            if recurrence is None:
                continue
            exponent, rest, divisor, merges = recurrence
            answer = powers[exponent] * values[rest]
            for merged, multiplicity in merges:
                answer -= multiplicity * values[merged]
            values[index] = answer / divisor
        residual = ld(ALPHA1) - total[:, None] + points
        answer = np.zeros((n, K), dtype=np.longdouble)
        power = np.ones((n, K), dtype=np.longdouble)
        for exponent in range(self.max_residual + 1):
            active = np.flatnonzero(self.coefficients[:, exponent])
            if len(active):
                combined = np.zeros((n, K), dtype=np.longdouble)
                for orbit_index in active:
                    combined += (self.coefficients[orbit_index, exponent] *
                                 values[orbit_index])
                answer += combined * power
            power *= residual
        return answer

    def omit_values(self, points, chunk=128):
        points = np.asarray(points, dtype=np.longdouble)
        if points.ndim != 2 or points.shape[1] != K or chunk <= 0:
            raise ValueError("omit evaluator expects an N-by-48 matrix")
        rows = [self._omit_chunk(points[start:start + chunk])
                for start in range(0, len(points), chunk)]
        return np.concatenate(rows, axis=0)

    def riesz(self, points):
        points = np.asarray(points, dtype=np.longdouble)
        common_sums = (np.sum(points, axis=1, dtype=np.longdouble)[:, None] -
                       points)
        eligible = common_sums <= ld(ETA2)
        return np.sum(self.omit_values(points) * eligible, axis=1,
                      dtype=np.longdouble)


def _padd(left, right):
    size = max(len(left), len(right))
    return tuple((left[i] if i < len(left) else Q(0)) +
                 (right[i] if i < len(right) else Q(0))
                 for i in range(size))


def _pmul(left, right):
    answer = [Q(0)] * (len(left) + len(right) - 1)
    for i, x in enumerate(left):
        for j, y in enumerate(right):
            answer[i + j] += x * y
    return tuple(answer)


def _pscale(poly, scalar):
    return tuple(Q(scalar) * value for value in poly)


def _pcompose_linear(poly, constant, slope):
    answer = (Q(0),)
    for exponent, coefficient in enumerate(poly):
        term = (Q(1),)
        for _ in range(exponent):
            term = _pmul(term, (Q(constant), Q(slope)))
        answer = _padd(answer, _pscale(term, coefficient))
    return answer


def _pantiderivative(poly):
    return (Q(0),) + tuple(value / (i + 1)
                            for i, value in enumerate(poly))


def _peval(poly, value):
    answer = Q(0)
    for coefficient in reversed(poly):
        answer = answer * value + coefficient
    return answer


def _pintegral(poly, left, right):
    primitive = _pantiderivative(poly)
    return _peval(primitive, right) - _peval(primitive, left)


def low_k_riesz_oracle():
    """Literal exact k=2 Fubini/Riesz check on a nontrivial shell.

    F(x,t)=1+x+t lives on x+t<=A.  The symmetric outer cap is the band
    A<x+t<B with x,t<=eta.  Both cutoff-active fiber pieces are integrated
    as explicit Fraction polynomials; no production shell code is used.
    """
    a, b, eta = Q(1, 2), Q(3, 4), Q(2, 5)
    # m(x)=(A-x)(1+x)+(A-x)^2/2.
    width = (a, -Q(1))
    m = _padd(_pmul(width, (Q(1), Q(1))),
              _pscale(_pmul(width, width), Q(1, 2)))
    primitive_m = _pantiderivative(m)
    primitive_m2 = _pantiderivative(_pmul(m, m))
    intervals = (
        # x interval, lower fiber A-x, upper fiber eta or B-x.
        (a - eta, b - eta, (a, -Q(1)), (eta,)),
        (b - eta, eta, (a, -Q(1)), (b, -Q(1))),
    )
    direct_i = Q(0)
    cross_j_one = Q(0)
    for left, right, lower, upper in intervals:
        fiber_width = _padd(upper, _pscale(lower, -1))
        int_m = _padd(_pcompose_linear(primitive_m, upper[0],
                                       upper[1] if len(upper) > 1 else 0),
                      _pscale(_pcompose_linear(
                          primitive_m, lower[0],
                          lower[1] if len(lower) > 1 else 0), -1))
        int_m2 = _padd(_pcompose_linear(
            primitive_m2, upper[0], upper[1] if len(upper) > 1 else 0),
            _pscale(_pcompose_linear(
                primitive_m2, lower[0],
                lower[1] if len(lower) > 1 else 0), -1))
        marginal_h = _padd(_pmul(m, fiber_width), int_m)
        direct_integrand = _padd(
            _padd(_pmul(_pmul(m, m), fiber_width),
                  _pscale(_pmul(m, int_m), 2)), int_m2)
        direct_i += _pintegral(direct_integrand, left, right)
        cross_j_one += _pintegral(_pmul(m, marginal_h), left, right)
    cross_2j = 2 * cross_j_one
    if direct_i <= 0 or cross_2j != direct_i:
        raise ArithmeticError("literal k=2 Riesz identity failed")
    return {
        "k": 2, "inner": "F(x,t)=1+x+t on x+t<=1/2",
        "outer_cap": "1/2<x+t<3/4 and max(x,t)<=2/5",
        "common_cutoff": str(eta), "I_of_G_on_cap": str(direct_i),
        "sum_i_Ji_F_G": str(cross_2j),
        "factor_k": 2, "exact_identity_pass": True,
    }


def low_k_importance_oracle():
    """Exact k=2 check of the variable-volume importance factor.

    Take one selected large coordinate with delta=1/4, excess budget 1/10,
    and shell 7/20<t1+t2<2/5.  At excess x in [0,1/10], the conditional
    small simplex has length V=3/20-x, while the accepted portion has the
    constant length 1/20.  Both choices of the large coordinate give exact
    shell volume 2*(1/10)*(1/20)=1/100.
    """
    dimension, count = 2, 1
    vol_x = Q(1, 10)
    accepted_fiber = Q(1, 20)
    direct = Q(2) * vol_x * accepted_fiber
    # Under y~Uniform[0,V], E[1_accept * C(2,1)*VolX*V]
    # equals C(2,1)*VolX*(accepted fiber length), independently of x.
    conditional_expectations = tuple(
        upper_shell_importance_weight(dimension, count, vol_x, vmax) *
        accepted_fiber / vmax
        for vmax in (Q(3, 20), Q(1, 10), Q(1, 20)))
    if (direct != Q(1, 100) or
            any(value != direct for value in conditional_expectations)):
        raise ArithmeticError("literal k=2 importance weight failed")
    return {
        "k": 2, "count": 1, "delta": "1/4",
        "shell": "7/20<t1+t2<2/5", "excess_budget": "1/10",
        "direct_shell_volume": str(direct),
        "importance_expectation": str(conditional_expectations[0]),
        "checked_conditional_simplex_lengths": [
            "3/20", "1/10", "1/20"],
        "exact_identity_pass": True,
    }


def load_inputs():
    for path, expected in PINS.items():
        if sha256(path) != expected:
            raise RuntimeError(f"pinned cap-adapted input changed: {path}")
    cert = strict_json(CERT)
    uncapped = strict_json(UNCAPPED)
    analytic = strict_json(ANALYTIC)
    d0 = strict_json(D0)
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in cert.get("basis", ()))
    vector = tuple(Q(x) for x in cert.get("rational_vector", ()))
    if (cert.get("format") != "bv-even-exact-vector-v1" or
            (cert.get("k"), cert.get("degree")) != (K, 18) or
            cert.get("parameters") != {
                "alpha": "103/400", "beta1": "103/400",
                "beta2": "103/400", "beta3plus": "103/400",
                "delta": "7/250", "eta": "97/400"} or
            len(basis) != len(vector) or len(basis) != 471 or
            len(set(basis)) != 471):
        raise ValueError("audited D18 identity changed")
    if (uncapped.get("certificate_sha256") != PINS[CERT] or
            uncapped.get("parameters") != {
                "alpha1": "103/400", "alpha2": "3211/12000",
                "delta": "361/50000", "eta1": "97/400",
                "eta2": "3031/12000", "inner_c": "1", "k": 48,
                "outer_c": "3090/3211"}):
        raise ValueError("natural D18 dilation artifact changed")
    if (analytic.get("status") != "AUDIT PASS" or
            analytic.get("parameters", {}).get("outer_active") !=
            list(range(26)) or
            analytic.get("parameters", {}).get(
                "outer_schedule_through_first_empty") !=
            [str(x) for x in AUDITED_SCHEDULE]):
        raise ValueError("audited active25 cap changed")
    if (d0.get("format") !=
            "active25-count-cap-slack-shell-exact-v1" or
            d0.get("basis") != [[r, 0] for r in range(26)] or
            d0.get("dimension") != 26 or
            d0.get("maximum_cap_slack_degree") != 0 or
            d0.get("rigorous_matrix_entries") is not True):
        raise ValueError("exact D0 geometry calibration changed")
    if GEOMETRY_NAME == "audited":
        exact_diagonal = {i: Q(value) for i, j, value in
                          d0["I_upper_nonzero"] if i == j}
        if tuple(exact_diagonal.get(r, Q(0)) for r in range(26)) != \
                exact_shell_volumes():
            raise ArithmeticError(
                "independent shell-volume recurrence disagrees with frozen D0")
    outer = dilate_vector(basis, vector, OUTER_C)
    return cert, uncapped, d0, basis, vector, outer


def sparse_symmetric(entries, dimension):
    result = np.zeros((dimension, dimension), dtype=np.longdouble)
    for i, j, value in entries:
        if (type(i) is not int or type(j) is not int or
                not 0 <= j <= i < dimension):
            raise ValueError("malformed sparse symmetric entry")
        result[i, j] = result[j, i] = ld(Q(value))
    return result


def exact_stratum_volume(alpha, count):
    """Exact volume below total cutoff alpha in one symmetric count cell."""
    alpha = Q(alpha)
    if type(count) is not int or not 0 <= count <= MAX_ACTIVE_COUNT:
        raise ValueError("inactive exact stratum")
    if count == 0:
        top = int(alpha // DELTA)
        return sum((Q((-1) ** h * math.comb(K, h)) *
                    max(Q(0), alpha - h * DELTA) ** K
                    for h in range(top + 1)), Q(0)) / math.factorial(K)
    budget = gamma(count)
    small = K - count
    answer = Q(0)
    top = max(0, int(alpha // DELTA) - count)
    for h in range(top + 1):
        length = alpha - (count + h) * DELTA
        upper = min(budget, length)
        if upper <= 0:
            continue
        radial = sum((Q((-1) ** j * math.comb(small, j), count + j) *
                      length ** (small - j) * upper ** (count + j)
                      for j in range(small + 1)), Q(0))
        answer += (Q((-1) ** h * math.comb(small, h)) * radial /
                   (math.factorial(count - 1) * math.factorial(small)))
    return math.comb(K, count) * answer


def exact_shell_volumes():
    rows = [Q(0)] * 26
    for count in range(MAX_ACTIVE_COUNT + 1):
        value = (exact_stratum_volume(ALPHA2, count) -
                 exact_stratum_volume(ALPHA1, count))
        if value < 0:
            raise ArithmeticError("negative exact shell-stratum volume")
        rows[count] = value
    return tuple(rows)


def sample_count_cell(rng, dimension, count, samples):
    if (type(count) is not int or not 0 <= count <= MAX_ACTIVE_COUNT or
            type(samples) is not int or samples <= 0 or count > dimension):
        raise ValueError("invalid count-cell sample request")
    if count:
        budget = ld(gamma(count))
        simplex = rng.dirichlet(np.ones(count + 1), size=samples)
        excess = simplex[:, :count].astype(np.longdouble) * budget
        large = excess + ld(DELTA)
    else:
        excess = np.empty((samples, 0), dtype=np.longdouble)
        large = excess
    small_count = dimension - count
    small = (rng.random((samples, small_count)).astype(np.longdouble) *
             ld(DELTA))
    points = np.concatenate((large, small), axis=1)
    volume = count_cell_container_volume(dimension, count)
    return points, volume


def upper_shell_importance_weight(dimension, count, excess_volume, vmax):
    """Lebesgue-measure weight for the conditional upper-simplex proposal."""
    small = dimension - count
    return (math.comb(dimension, count) * excess_volume *
            vmax ** small / math.factorial(small))


def sample_upper_shell_importance(rng, dimension, count, samples):
    """Sample one symmetric count stratum with an unbiased radial proposal.

    The selected large-coordinate subset is represented by the first `count`
    coordinates; its binomial multiplicity is in `weights`.  The returned
    boolean mask enforces the small-coordinate cube and the lower shell edge.
    The upper shell edge is built into the conditional simplex proposal.
    """
    if (type(count) is not int or not 0 <= count <= MAX_ACTIVE_COUNT or
            type(samples) is not int or samples <= 0 or count > dimension):
        raise ValueError("invalid upper-shell sample request")
    radial_cap = ALPHA2 - count * DELTA
    if radial_cap <= 0:
        raise ValueError("count stratum cannot meet the upper shell edge")
    effective_budget = min(gamma(count), radial_cap) if count else Q(0)
    if count:
        simplex = rng.dirichlet(np.ones(count + 1), size=samples)
        excess = (simplex[:, :count].astype(np.longdouble) *
                  ld(effective_budget))
        large = excess + ld(DELTA)
        excess_sum = np.sum(excess, axis=1, dtype=np.longdouble)
        excess_volume = (ld(effective_budget) ** count /
                         math.factorial(count))
    else:
        excess = np.empty((samples, 0), dtype=np.longdouble)
        large = excess
        excess_sum = np.zeros(samples, dtype=np.longdouble)
        excess_volume = np.longdouble(1)
    small_count = dimension - count
    vmax = ld(radial_cap) - excess_sum
    if np.any(vmax < -np.longdouble("1e-18")):
        raise ArithmeticError("negative conditional small-coordinate budget")
    vmax = np.maximum(vmax, np.longdouble(0))
    simplex = rng.dirichlet(np.ones(small_count + 1), size=samples)
    small = simplex[:, :small_count].astype(np.longdouble) * vmax[:, None]
    points = np.concatenate((large, small), axis=1)
    weights = upper_shell_importance_weight(
        dimension, count, excess_volume, vmax)
    total = (count * ld(DELTA) + excess_sum +
             np.sum(small, axis=1, dtype=np.longdouble))
    accepted = ((np.max(small, axis=1) <= ld(DELTA)) &
                (total > ld(ALPHA1)) &
                (total < ld(ALPHA2) + np.longdouble("1e-18")))
    return points, weights, accepted


def sample_joint_upper_simplex_importance(rng, dimension, count, samples):
    """Variance-reduced equivalent of the conditional upper-shell law.

    Tilting the x proposal in `sample_upper_shell_importance` by
    Vmax**(dimension-count) makes (x,y,slack) uniform on a single
    dimension-simplex and makes the importance weight constant.  The cap on
    x, the small-coordinate cube, and the lower shell edge remain explicit
    rejection indicators.
    """
    if (type(count) is not int or not 0 <= count <= MAX_ACTIVE_COUNT or
            type(samples) is not int or samples <= 0 or count > dimension):
        raise ValueError("invalid joint upper-simplex sample request")
    radial_cap = ALPHA2 - count * DELTA
    if radial_cap <= 0:
        raise ValueError("count stratum cannot meet the upper shell edge")
    simplex = rng.dirichlet(np.ones(dimension + 1), size=samples)
    coordinates = (simplex[:, :dimension].astype(np.longdouble) *
                   ld(radial_cap))
    excess = coordinates[:, :count]
    small = coordinates[:, count:]
    points = np.concatenate((excess + ld(DELTA), small), axis=1)
    total = count * ld(DELTA) + np.sum(
        coordinates, axis=1, dtype=np.longdouble)
    if count:
        in_excess_cap = (np.sum(excess, axis=1, dtype=np.longdouble) <=
                         ld(gamma(count)))
    else:
        in_excess_cap = np.ones(samples, dtype=bool)
    accepted = (in_excess_cap &
                (np.max(small, axis=1) <= ld(DELTA)) &
                (total > ld(ALPHA1)) &
                (total < ld(ALPHA2) + np.longdouble("1e-18")))
    weight = (np.longdouble(math.comb(dimension, count)) *
              ld(radial_cap) ** dimension / math.factorial(dimension))
    return points, np.full(samples, weight, dtype=np.longdouble), accepted


def sample_oracle_stratum(rng, dimension, count, samples):
    """Select the frozen proposal appropriate to the support geometry."""
    if GEOMETRY_NAME == "audited":
        points, volume = sample_count_cell(rng, dimension, count, samples)
        total = np.sum(points, axis=1, dtype=np.longdouble)
        accepted = ((total > ld(ALPHA1)) & (total < ld(ALPHA2)))
        return (points,
                np.full(samples, volume, dtype=np.longdouble), accepted)
    return sample_joint_upper_simplex_importance(
        rng, dimension, count, samples)


def oracle_stratum_proposal_measure(dimension, count):
    """Constant importance weight of the geometry's active proposal."""
    if GEOMETRY_NAME == "audited":
        return count_cell_container_volume(dimension, count)
    radial_cap = ALPHA2 - count * DELTA
    return (np.longdouble(math.comb(dimension, count)) *
            ld(radial_cap) ** dimension / math.factorial(dimension))


def count_cell_container_volume(dimension, count):
    if not 0 <= count <= min(dimension, MAX_ACTIVE_COUNT):
        raise ValueError("inactive count-cell container")
    excess_volume = (ld(gamma(count)) ** count / math.factorial(count)
                     if count else np.longdouble(1))
    return (np.longdouble(math.comb(dimension, count)) * excess_volume *
            ld(DELTA) ** (dimension - count))


def outer_values(points, natural, inner, marginal):
    """Values of all outer coordinates (full label list with inner removed)."""
    points = np.asarray(points, dtype=np.longdouble)
    result = np.zeros((len(points), len(candidate_labels()) - 1),
                      dtype=np.longdouble)
    result[:, 0] = marginal.riesz(points)
    result[:, 1] = natural.evaluate(points)
    large = points > ld(DELTA)
    counts = np.sum(large, axis=1)
    for offset, count in enumerate(SELECTED_COUNTS):
        selected = counts == count
        if not np.any(selected):
            continue
        transformed = np.zeros((int(np.sum(selected)), K),
                               dtype=np.longdouble)
        excess = np.where(large[selected],
                          points[selected] - ld(DELTA), 0)
        transformed[:] = excess * ld(ALPHA1 / gamma(count))
        base = inner.evaluate(transformed)
        slack = 1 - np.sum(excess, axis=1, dtype=np.longdouble) / ld(
            gamma(count))
        result[selected, 2 + 2 * offset] = base
        result[selected, 3 + 2 * offset] = base * slack
    return result


def gauss_nodes():
    nodes, weights = np.polynomial.legendre.leggauss(10)
    return (nodes.astype(np.longdouble), weights.astype(np.longdouble))


def matrix_mean_se(matrices):
    values = np.asarray(matrices, dtype=np.longdouble)
    mean = np.mean(values, axis=0, dtype=np.longdouble)
    if len(values) < 2:
        se = np.full_like(mean, np.inf)
    else:
        se = np.std(values, axis=0, ddof=1) / np.sqrt(len(values))
    return mean, se


def focus_calibration(observed, se, exact, pairs):
    rows = []
    for i, j in pairs:
        target = exact[i, j]
        estimate = observed[i, j]
        error = estimate - target
        standard_error = se[i, j]
        rows.append({
            "indices": [i, j],
            "estimate": str(estimate),
            "exact": str(target),
            "relative_error": float(abs(error / target)) if target else None,
            "z_score": (float(error / standard_error)
                        if standard_error > 0 and np.isfinite(standard_error)
                        else None),
        })
    maximum_relative = max(row["relative_error"] for row in rows
                           if row["relative_error"] is not None)
    finite_z = [abs(row["z_score"]) for row in rows
                if row["z_score"] is not None]
    maximum_z = max(finite_z, default=math.inf)
    return {"rows": rows, "maximum_relative_error": maximum_relative,
            "maximum_absolute_z": maximum_z,
            "pass": maximum_relative <= 0.20 and maximum_z <= 5.0}


def lower_riesz_quotient(inner_q, normalized_riesz_norm):
    """Largest root after replacing the unknown nonnegative B(H,H) by 0."""
    inner_q = float(inner_q)
    normalized_riesz_norm = float(normalized_riesz_norm)
    if not (0 <= inner_q < 2 and normalized_riesz_norm >= 0 and
            math.isfinite(inner_q) and math.isfinite(normalized_riesz_norm)):
        raise ValueError("invalid lower Riesz pencil")
    return (inner_q + math.sqrt(inner_q * inner_q +
                                4 * normalized_riesz_norm)) / 2


def screen_decision(calibrated, mean, standard_error, threshold):
    if min(mean, standard_error, threshold) < 0:
        raise ValueError("negative Riesz screen input")
    if calibrated and mean - 2 * standard_error > threshold:
        return "GATED EXACT COMPUTATION WARRANTED"
    if calibrated and mean + 2 * standard_error < threshold:
        return "HEURISTIC FALSIFICATION"
    return "HEURISTIC INCONCLUSIVE"


def point_consistency(inner, natural, basis, vector, outer, seed):
    """High-precision literal sum at two points, independent of recurrence."""
    rng = np.random.default_rng(seed)
    raw = rng.dirichlet(np.ones(K + 1), size=2)[:, :K]
    inner_points = raw * float(ALPHA1)
    outer_points = raw * float(ALPHA2)

    def decimal_orbit(point, lam):
        # Dynamic elementary-monomial recurrence over exponent multiplicities.
        exponents = tuple(sorted(set(lam)))
        target = tuple(lam.count(x) for x in exponents)
        states = {tuple(0 for _ in exponents): Decimal(1)}
        for coordinate in point:
            new = dict(states)
            for state, value in states.items():
                for slot, exponent in enumerate(exponents):
                    if state[slot] < target[slot]:
                        nxt = list(state)
                        nxt[slot] += 1
                        nxt = tuple(nxt)
                        new[nxt] = new.get(nxt, Decimal(0)) + value * (
                            coordinate ** exponent)
            states = new
        return states.get(target, Decimal(0))

    def literal(points, coefficients):
        answers = []
        with localcontext() as context:
            context.prec = 70
            for row in points:
                point = [Decimal(str(x)) for x in row]
                residual = Decimal(1) - sum(point, Decimal(0))
                orbit_cache = {}
                total = Decimal(0)
                for coefficient, (a, lam) in zip(coefficients, basis):
                    if lam not in orbit_cache:
                        orbit_cache[lam] = decimal_orbit(point, lam)
                    total += (Decimal(coefficient.numerator) /
                              Decimal(coefficient.denominator) *
                              residual ** a * orbit_cache[lam])
                answers.append(total)
        return answers

    inner_literal = literal(inner_points, vector)
    outer_literal = literal(outer_points, outer)
    inner_fast = inner.evaluate(inner_points)
    natural_fast = natural.evaluate(outer_points)
    rows = []
    squared_absolute = []
    squared_relative = []
    for name, literals, fast, scale in (
            ("inner", inner_literal, inner_fast, inner.scale),
            ("natural_outer", outer_literal, natural_fast, natural.scale)):
        for index, (expected, actual) in enumerate(zip(literals, fast)):
            normalized = expected / (Decimal(scale.numerator) /
                                     Decimal(scale.denominator))
            relative = abs(Decimal(str(actual)) - normalized) / max(
                abs(normalized), Decimal("1e-100"))
            absolute = abs(Decimal(str(actual)) - normalized)
            square_absolute = abs(Decimal(str(actual)) ** 2 - normalized ** 2)
            square_relative = square_absolute / max(
                abs(normalized ** 2), Decimal("1e-100"))
            rows.append({"polynomial": name, "point": index,
                         "normalized_expected": str(normalized),
                         "normalized_observed": str(actual),
                         "absolute_error": str(absolute),
                         "relative_error": str(relative),
                         "squared_integrand_absolute_error": str(
                             square_absolute),
                         "squared_integrand_relative_error": str(
                             square_relative)})
            squared_absolute.append(square_absolute)
            squared_relative.append(square_relative)
    maximum = max(Decimal(row["relative_error"]) for row in rows)
    maximum_absolute = max(Decimal(row["absolute_error"]) for row in rows)
    if maximum > POINT_RELATIVE_TOLERANCE:
        raise ArithmeticError(
            f"long-double D18 evaluator failed point oracle: {maximum}")
    return {
        "rows": rows, "maximum_relative_error": str(maximum),
        "maximum_normalized_absolute_error": str(maximum_absolute),
        "maximum_squared_integrand_absolute_error": str(
            max(squared_absolute)),
        "maximum_squared_integrand_relative_error": str(
            max(squared_relative)),
        "maximum_diagonal_Gram_integrand_absolute_perturbation": str(
            max(squared_absolute)),
        "maximum_diagonal_Gram_integrand_relative_perturbation": str(
            max(squared_relative)),
        "accepted_relative_tolerance": str(POINT_RELATIVE_TOLERANCE),
        "largest_squared-integrand_relative_effect_at_tolerance": str(
            2 * POINT_RELATIVE_TOLERANCE + POINT_RELATIVE_TOLERANCE ** 2),
        "tolerance_scope":
            "floating arithmetic tripwire only; not a rigorous error bound",
        "pass": True,
    }


def marginal_point_consistency(inner, marginal, seed):
    """Compare exact-antiderivative marginal to ten-node fiber quadrature."""
    rng = np.random.default_rng(seed)
    common = rng.dirichlet(np.ones(K), size=3)[:, :K - 1]
    common = common.astype(np.longdouble) * ld(ETA2) * np.longdouble("0.91")
    padded = np.concatenate(
        (common, np.zeros((len(common), 1), dtype=np.longdouble)), axis=1)
    expected = marginal.evaluate(padded)
    nodes, weights = gauss_nodes()
    total = np.sum(common, axis=1, dtype=np.longdouble)
    upper = ld(ALPHA1) - total
    observed = np.zeros(len(common), dtype=np.longdouble)
    for node, weight in zip(nodes, weights):
        half = upper / 2
        t = half * (node + 1)
        points = np.concatenate((common, t[:, None]), axis=1)
        observed += half * weight * inner.evaluate(points)
    relative = np.abs(observed - expected) / np.maximum(
        np.abs(expected), np.longdouble("1e-100"))
    maximum = float(np.max(relative))
    if maximum > 1e-8:
        raise ArithmeticError(
            f"exact-antiderivative D18 marginal mismatch: {maximum}")
    return {"relative_errors": [float(x) for x in relative],
            "maximum_relative_error": maximum, "pass": True,
            "quadrature_nodes": 10}


def run_oracle(*, seed, batches, base_samples, focus_samples):
    if (type(seed) is not int or type(batches) is not int or
            type(base_samples) is not int or type(focus_samples) is not int or
            not 2 <= batches <= 8 or not 32 <= base_samples <= 512 or
            not base_samples <= focus_samples <= 4096 or
            batches * (26 * base_samples +
                       len(RIEZS_FOCUS_COUNTS) * focus_samples) > 250000):
        raise ValueError("oracle schedule exceeds bounded envelope")
    start_bytes = {path: path.read_bytes() for path in PINS}
    self_start = FILE.read_bytes()
    cert, uncapped, d0, basis, vector, outer = load_inputs()
    inner = ResidualD18(basis, vector, center=ALPHA1, dilation=1)
    natural = ResidualD18(basis, vector, center=ALPHA2,
                          dilation=OUTER_C)
    marginal = MarginalD18(basis, vector, inner.scale)
    point_oracle = point_consistency(
        inner, natural, basis, vector, outer, seed + 1000003)
    marginal_oracle = marginal_point_consistency(
        inner, marginal, seed + 1000033)
    low_k = low_k_riesz_oracle()
    low_k_importance = low_k_importance_oracle()
    exact_i0 = np.zeros((26, 26), dtype=np.longdouble)
    for count, value in enumerate(exact_shell_volumes()):
        exact_i0[count, count] = ld(value)
    dimension = len(candidate_labels())
    rng = np.random.default_rng(seed)
    i_batches, ci_batches, s_count_batches = [], [], []
    batch_s, batch_lower_q = [], []
    started = time.monotonic()
    for batch_index in range(batches):
        imat = np.zeros((dimension, dimension), dtype=np.longdouble)
        ci = np.zeros((26, 26), dtype=np.longdouble)
        s_by_count = np.zeros(26, dtype=np.longdouble)
        imat[0, 0] = ld(Q(cert["exact_denominator"]) / inner.scale ** 2)

        # I: independently stratify every total-large-count cell.
        for count in range(MAX_ACTIVE_COUNT + 1):
            samples = (focus_samples if count in RIEZS_FOCUS_COUNTS else
                       base_samples)
            points, weights, shell = sample_oracle_stratum(
                rng, K, count, samples)
            evaluation_points = points.copy()
            evaluation_points[~shell] = 0
            values = outer_values(
                evaluation_points, natural, inner, marginal)
            values[~shell] = 0
            contribution = (values.T @ (values * weights[:, None])) / samples
            imat[1:, 1:] += contribution
            s_by_count[count] = contribution[0, 0] / imat[0, 0]
            ci[count, count] += np.mean(
                weights * shell, dtype=np.longdouble)
        i_batches.append(imat)
        ci_batches.append(ci)
        s_count_batches.append(s_by_count)
        normalized_s = float(imat[1, 1] / imat[0, 0])
        q0 = float(Q(cert["exact_quotient"]))
        lower_q = lower_riesz_quotient(q0, normalized_s)
        batch_s.append(normalized_s)
        batch_lower_q.append(lower_q)
        print(f"cap-adapted oracle batch {batch_index + 1}/{batches}: "
              f"s/I={normalized_s:.9g}, q_lower={lower_q:.9f}",
              file=sys.stderr, flush=True)

    imean, ise = matrix_mean_se(i_batches)
    cimean, cise = matrix_mean_se(ci_batches)
    # Both active proposals have a constant per-count importance weight.  The
    # D0 control is therefore a scaled Bernoulli mean, for which the pooled
    # iid standard error is less noisy than four empirical batch rows.
    cise_pooled = np.zeros_like(cise)
    for count in range(MAX_ACTIVE_COUNT + 1):
        proposal_measure = oracle_stratum_proposal_measure(K, count)
        probability = min(np.longdouble(1), max(
            np.longdouble(0),
            cimean[count, count] / proposal_measure))
        per_batch = (focus_samples if count in RIEZS_FOCUS_COUNTS else
                     base_samples)
        cise_pooled[count, count] = proposal_measure * np.sqrt(
            probability * (1 - probability) / (batches * per_batch))
    cise = cise_pooled
    focus_i_pairs = [(r, r) for r in CALIBRATION_COUNTS]
    i_calibration = focus_calibration(
        cimean, cise, exact_i0, focus_i_pairs)
    calibration_pass = i_calibration["pass"]
    inner_q = float(Q(cert["exact_quotient"]))
    deficit = 1 - inner_q
    s_mean = float(np.mean(batch_s))
    s_se = float(np.std(batch_s, ddof=1) / math.sqrt(len(batch_s)))
    q_mean = float(np.mean(batch_lower_q))
    q_se = float(np.std(batch_lower_q, ddof=1) /
                 math.sqrt(len(batch_lower_q)))
    s_count_mean, s_count_se = matrix_mean_se(s_count_batches)
    lower_2se = s_mean - 2 * s_se
    upper_2se = s_mean + 2 * s_se
    decision = screen_decision(calibration_pass, s_mean, s_se, deficit)
    # Projection of G onto each comparison coordinate, in I units.  This is
    # the exact Riesz formula evaluated with numerical I entries; no shell-J
    # self block is silently assumed.
    comparisons = {}
    for index, label in enumerate(candidate_labels()[2:], start=2):
        captured = (float(imean[1, index] ** 2 /
                          (imean[index, index] * imean[0, 0]))
                    if imean[index, index] > 0 else 0.0)
        comparisons[str(label)] = {
            "captured_riesz_norm_over_inner_I": captured,
            "fraction_of_estimated_cap_riesz_norm": (
                captured / s_mean if s_mean > 0 else 0.0),
        }
    uncapped_i = Q(cert["exact_denominator"])
    uncapped_outer_i = Q(uncapped["I_matrix"][1][1])
    uncapped_cross = Q(uncapped["kJ_matrix"][0][1])
    uncapped_projection = uncapped_cross ** 2 / uncapped_outer_i / uncapped_i
    elapsed = time.monotonic() - started
    if (FILE.read_bytes() != self_start or
            any(path.read_bytes() != data for path, data in start_bytes.items())):
        raise RuntimeError("oracle source closure changed during run")
    matrices = {
        "I": [[str(value) for value in row] for row in imean],
        "I_standard_error": [[str(value) for value in row] for row in ise],
    }
    return {
        "format": "active25-d18-cap-adapted-bounded-oracle-v1",
        "status": (("HEURISTIC CALIBRATED" if calibration_pass else
                    "HEURISTIC CALIBRATION FAIL") if
                   GEOMETRIES[GEOMETRY_NAME]["approved"] else
                   ("CONDITIONAL HEURISTIC CALIBRATED" if calibration_pass
                    else "CONDITIONAL HEURISTIC CALIBRATION FAIL")),
        "rigorous": False,
        "theorem_ready": False,
        "launch_authorized": False,
        "exact_target_started": False,
        "basis": [list(label) for label in candidate_labels()],
        "basis_dimension": dimension,
        "coordinate_scales": {
            "inner_residual_coefficient_scale": str(inner.scale),
            "natural_outer_residual_coefficient_scale": str(natural.scale),
        },
        "formula": {
            "inner_marginal":
                "m_F(x)=1_{sum(x)<=eta2} integral_0^(alpha1-sum(x)) F(x,u)du",
            "riesz_coordinate":
                "G_F(t)=sum_i m_F(t without coordinate i), restricted to the active25 shell",
            "exact_cross_identity":
                "48J(F,H)=integral_shell H(t)G_F(t)dt",
            "riesz_self_identity":
                "for H=G_F on shell: 48J(F,H)=I(H)=integral_shell G_F^2",
            "large_excess": "x_i=(t_i-delta)_+",
            "cap_excess_budget": "gamma_R=B_R-R*delta",
            "importance_proposal": (
                "x uniform on sum(x)<=g_eff=min(gamma_R,alpha2-R*delta); "
                "given x, y uniform on sum(y)<=Vmax=alpha2-R*delta-sum(x)"),
            "importance_weight": (
                "binom(48,R)*g_eff^R/R!*Vmax^(48-R)/(48-R)!"),
            "importance_indicators":
                "max(y)<=delta and R*delta+sum(x)+sum(y)>alpha1",
            "adaptive_variance_reduction": (
                "tilt x density by Vmax^(48-R), equivalently sample "
                "(x,y,slack) uniformly on the 48-simplex of radius "
                "alpha2-R*delta; constant weight "
                "binom(48,R)*(alpha2-R*delta)^48/48!"),
            "gamma_transport":
                "u_i=(alpha1/gamma_R)*x_i for large i; u_i=0 otherwise",
            "coordinates":
                "1_{N=R} P_D18(u)*(1-sum(x)/gamma_R)^d, d in {0,1}",
            "unchanged_coordinates": [
                "P_D18(t) on the inner simplex",
                "P_D18((alpha1/alpha2)t) on the complete active25 shell",
            ],
        },
        "parameters": {
            "geometry": GEOMETRY_NAME,
            "geometry_analytically_approved": GEOMETRIES[
                GEOMETRY_NAME]["approved"],
            "geometry_source": GEOMETRIES[GEOMETRY_NAME]["source"],
            "k": K, "alpha1": str(ALPHA1), "alpha2": str(ALPHA2),
            "eta1": str(ETA1), "eta2": str(ETA2),
            "eta_UV_common_cutoff": str(ETA2),
            "eta_UV_cutoff_enforced_in_each_leave_one_out_term": True,
            "delta": str(DELTA), "outer_c": str(OUTER_C),
            "selected_counts": list(SELECTED_COUNTS),
            "riesz_focus_counts": list(RIEZS_FOCUS_COUNTS),
            "gamma_by_selected_count": {
                str(r): (str(gamma(r)) if r <= MAX_ACTIVE_COUNT else None)
                for r in SELECTED_COUNTS},
            },
            "outer_schedule": [str(x) for x in SCHEDULE],
        "schedule": {"seed": seed, "batches": batches,
                     "base_samples_per_stratum": base_samples,
                     "focus_samples_per_stratum": focus_samples,
                     "proposal": (
                         "uniform count-cell rejection" if
                         GEOMETRY_NAME == "audited" else
                         "joint upper-simplex importance (Vmax-power tilt)"),
                     "workers": 1},
        "point_evaluator_calibration": point_oracle,
        "marginal_antiderivative_calibration": marginal_oracle,
        "literal_low_k_riesz_calibration": low_k,
        "literal_low_k_importance_calibration": low_k_importance,
        "exact_D0_geometry_calibration": {
            "I": i_calibration,
            "pass": calibration_pass,
            "exact_target": ("frozen independently computed D0 matrix" if
                             GEOMETRY_NAME == "audited" else
                             "local exact Fraction inclusion-exclusion; support remains unvalidated"),
            "acceptance_rule":
                "each focus entry relative error <=0.20 and |z|<=5",
        },
        "rayleigh_screen": {
            "inner_only_exact_q": inner_q,
            "inner_deficit_to_one": deficit,
            "cap_riesz_norm_over_inner_I_estimate": s_mean,
            "cap_riesz_norm_standard_error": s_se,
            "cap_riesz_norm_lower_two_standard_errors": lower_2se,
            "cap_riesz_norm_upper_two_standard_errors": upper_2se,
            "sufficient_threshold": deficit,
            "sufficient_test": "I(G_cap)/I(F) > 1-q_F",
            "lower_pencil_q_estimate": q_mean,
            "lower_pencil_q_standard_error": q_se,
            "batch_cap_riesz_norm": batch_s,
            "batch_lower_pencil_q": batch_lower_q,
            "comparison_coordinate_projections": comparisons,
            "cap_riesz_norm_by_count": {
                str(r): {"estimate_over_inner_I": float(s_count_mean[r]),
                         "standard_error": float(s_count_se[r])}
                for r in range(26)},
            "uncapped_exact_natural_D18_projection_over_inner_I": str(
                uncapped_projection),
            "uncapped_exact_natural_D18_projection_decimal": float(
                uncapped_projection),
            "cap_riesz_over_uncapped_projection_lower_bound_ratio": (
                s_mean / float(uncapped_projection)),
            "screen_decision": decision,
            "decision_is_conditional_on_support_approval": not GEOMETRIES[
                GEOMETRY_NAME]["approved"],
            "decision_eligible": calibration_pass,
            "shell_J_self_used": False,
        },
        "matrices": matrices,
        "wall_seconds": elapsed,
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "source_sha256": sha256(self_start),
        "source_hashes": {str(path.relative_to(REPO)): digest
                          for path, digest in PINS.items()},
        "never_implies": ["an exact integral", "a certified quotient",
                          "Proposition 1", "H1<=236"],
    }


def build_preflight():
    cert, uncapped, d0, basis, vector, outer = load_inputs()
    exact_diagonal = exact_shell_volumes()
    selected_volume = sum((exact_diagonal[r] for r in SELECTED_COUNTS), Q(0))
    focus_volume = sum((exact_diagonal[r] for r in RIEZS_FOCUS_COUNTS), Q(0))
    total_volume = sum(exact_diagonal, Q(0))
    return {
        "format": "active25-d18-cap-adapted-preflight-v1",
        "status": "DISABLED NUMERICAL ORACLE PLAN",
        "launch_authorized": False,
        "exact_target_started": False,
        "theorem_ready": False,
        "basis": [list(label) for label in candidate_labels()],
        "basis_dimension": len(candidate_labels()),
        "audited_D18_terms": len(basis),
        "natural_dilation": str(OUTER_C),
        "geometry": GEOMETRY_NAME,
        "geometry_analytically_approved": GEOMETRIES[
            GEOMETRY_NAME]["approved"],
        "geometry_source": GEOMETRIES[GEOMETRY_NAME]["source"],
        "selected_counts": list(SELECTED_COUNTS),
        "riesz_focus_counts": list(RIEZS_FOCUS_COUNTS),
        "selected_exact_D0_shell_volume_fraction": str(
            selected_volume / total_volume),
        "riesz_focus_exact_D0_shell_volume_fraction": str(
            focus_volume / total_volume),
        "oracle_envelope": {
            "workers": 1, "batches": [2, 8],
            "base_samples_per_stratum": [32, 512],
            "focus_samples_per_stratum": [32, 4096],
            "maximum_weighted_samples": 250000,
            "hard_wall_seconds": 180,
            "address_space_limit_mib": 512,
        },
        "exact_continuation": {
            "authorized": False,
            "resume_supported": False,
            "required_before_design": [
                "two independently seeded calibrated oracle passes",
                "lower two-standard-error s_cap/I(F) exceeds 1-q_F",
                "independent reconstruction design and root authorization",
            ],
            "finite_exact_reduction": (
                "expand integral G^2 as 48 diagonal leave-one-out terms plus "
                "48*47 ordered off-diagonal terms; count-stratify each term "
                "and split the two distinguished coordinates at delta and "
                "the explicit eta2 inequalities"),
            "no_shell_J_required": True,
        },
        "source_hashes": {str(path.relative_to(REPO)): digest
                          for path, digest in PINS.items()},
        "source_sha256": sha256(FILE),
    }


def canonical_json(value) -> bytes:
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
    limit = 512 * 1024 * 1024
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    new_hard = hard if hard != resource.RLIM_INFINITY else limit
    resource.setrlimit(resource.RLIMIT_AS, (min(limit, new_hard), new_hard))
    signal.alarm(180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--oracle", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--geometry", choices=tuple(GEOMETRIES),
                        default="audited")
    parser.add_argument("--seed", type=int, default=2361801)
    parser.add_argument("--batches", type=int, default=4)
    parser.add_argument("--base-samples", type=int, default=64)
    parser.add_argument("--focus-samples", type=int, default=512)
    args = parser.parse_args()
    if args.preflight_only == args.oracle:
        parser.error("choose exactly one of --preflight-only and --oracle")
    configure_geometry(args.geometry)
    if args.preflight_only:
        if args.output is not None:
            parser.error("preflight prints to stdout and accepts no output")
        print(json.dumps(build_preflight(), sort_keys=True, indent=2))
        return
    if args.output is None:
        parser.error("--oracle requires --output")
    apply_limits()
    result = run_oracle(seed=args.seed, batches=args.batches,
                        base_samples=args.base_samples,
                        focus_samples=args.focus_samples)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload), "status": result["status"],
        "s_over_I": result["rayleigh_screen"][
            "cap_riesz_norm_over_inner_I_estimate"],
        "q_lower": result["rayleigh_screen"][
            "lower_pencil_q_estimate"],
        "wall_seconds": result["wall_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
