#!/usr/bin/env python3
"""Hostile exact low-dimensional tests for ``symmetric_cutoff_cross.py``.

The oracle in this file does not use the production support decomposition,
orbit algebra, marginal recurrence, radialization, or polygon integrator.  It
expands the literal two-variable polynomials and clips the four literal
large/small cells in the original ``(u,t)`` coordinates.  Green's theorem is
then used to integrate each resulting rational polygon exactly.

For k=2 this is already enough to exercise both possible common-large counts,
all four distinguished-coordinate branches, a nonconstant B schedule,
residual dilation, orbit multiplicities, the Definition-5 cutoff, and the
single final factor k.  The I oracle likewise integrates the literal outer
band, independently of the production radial stratum integrator.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
from itertools import permutations, product
import importlib.util
from math import comb, factorial
from pathlib import Path
import random
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TARGET = REPO / "agents/exact-projection-engine/symmetric_cutoff_cross.py"
FRONTIER = REPO / (
    "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py"
)
RADIAL = REPO / "verify/exact_capped_certificate.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("hostile_cross_target", TARGET)
F = load("hostile_cross_frontier", FRONTIER)
R = load("hostile_cross_radial", RADIAL)

ZERO = Q(0)
ONE = Q(1)


def add_poly(target, source, factor=ONE):
    for monomial, coefficient in source.items():
        target[monomial] += factor * coefficient
        if not target[monomial]:
            del target[monomial]


def multiply_poly(left, right):
    answer = defaultdict(Q)
    for (i, j), a in left.items():
        for (p, q), b in right.items():
            answer[(i + p, j + q)] += a * b
    return {key: value for key, value in answer.items() if value}


def orbit_poly_2(part):
    """Literal unnormalised monomial orbit in two named coordinates."""
    if len(part) > 2:
        return {}
    padded = tuple(part) + (0,) * (2 - len(part))
    return {exponents: ONE for exponents in set(permutations(padded))}


def literal_orbit_value(part, coordinates):
    """Brute-force orbit value, intentionally unsuitable for production."""
    if len(part) > len(coordinates):
        return ZERO
    padded = tuple(part) + (0,) * (len(coordinates) - len(part))
    return sum(
        (
            product_value
            for exponents in set(permutations(padded))
            for product_value in [
                _coordinate_monomial(exponents, coordinates)
            ]
        ),
        ZERO,
    )


def _coordinate_monomial(exponents, coordinates):
    value = ONE
    for exponent, coordinate in zip(exponents, coordinates, strict=True):
        value *= coordinate ** exponent
    return value


def literal_terms_value(terms, coordinates):
    residual = ONE - sum(coordinates, ZERO)
    return sum(
        Q(coefficient) * residual ** power
        * literal_orbit_value(part, coordinates)
        for (power, part), coefficient in terms.items()
    )


def literal_marginal_value(terms, shared, alpha):
    """Brute-force named-monomial integration in the last coordinate."""
    k = len(shared) + 1
    upper = alpha - sum(shared, ZERO)
    if upper <= 0:
        return ZERO
    one_minus_shared = ONE - sum(shared, ZERO)
    answer = ZERO
    for (residual_power, part), coefficient in terms.items():
        padded = tuple(part) + (0,) * (k - len(part))
        for exponents in set(permutations(padded)):
            angular = _coordinate_monomial(exponents[:-1], shared)
            t_power = exponents[-1]
            for j in range(residual_power + 1):
                n = t_power + j + 1
                answer += (
                    Q(coefficient) * angular
                    * comb(residual_power, j) * ((-1) ** j)
                    * one_minus_shared ** (residual_power - j)
                    * upper ** n / n
                )
    return answer


def residual_power_2(power):
    """Expand ``(1-u-t)^power`` without using the production recurrence."""
    answer = defaultdict(Q)
    for i in range(power + 1):
        for j in range(power - i + 1):
            constant = power - i - j
            coefficient = Q(factorial(power),
                            factorial(i) * factorial(j) * factorial(constant))
            answer[(i, j)] += coefficient * ((-1) ** (i + j))
    return dict(answer)


def terms_poly_2(terms):
    answer = defaultdict(Q)
    for (power, part), coefficient in terms.items():
        add_poly(
            answer,
            multiply_poly(residual_power_2(power), orbit_poly_2(part)),
            Q(coefficient),
        )
    return {key: value for key, value in answer.items() if value}


def marginal_in_second(poly, alpha):
    """Integrate a literal polynomial from ``t=0`` to ``alpha-u``."""
    answer = defaultdict(Q)
    for (u_power, t_power), coefficient in poly.items():
        n = t_power + 1
        coefficient /= n
        for j in range(n + 1):
            answer[u_power + j] += (
                coefficient * comb(n, j) * alpha ** (n - j) * ((-1) ** j)
            )
    return {power: value for power, value in answer.items() if value}


def marginal_times_outer(inner_terms, outer_terms, alpha_f):
    marginal = marginal_in_second(terms_poly_2(inner_terms), alpha_f)
    outer = terms_poly_2(outer_terms)
    answer = defaultdict(Q)
    for u_power, left in marginal.items():
        for (i, j), right in outer.items():
            answer[(u_power + i, j)] += left * right
    return {key: value for key, value in answer.items() if value}


def clip_polygon(polygon, a, b, cap):
    """Clip a CCW rational polygon by ``a*u+b*t <= cap``."""
    if not polygon:
        return []
    answer = []
    previous = polygon[-1]
    f_previous = a * previous[0] + b * previous[1] - cap
    previous_inside = f_previous <= 0
    for current in polygon:
        f_current = a * current[0] + b * current[1] - cap
        current_inside = f_current <= 0
        if current_inside != previous_inside:
            denominator = f_previous - f_current
            if not denominator:
                raise ArithmeticError("inconsistent parallel clipping edge")
            theta = f_previous / denominator
            answer.append((
                previous[0] + theta * (current[0] - previous[0]),
                previous[1] + theta * (current[1] - previous[1]),
            ))
        if current_inside:
            answer.append(current)
        previous = current
        f_previous = f_current
        previous_inside = current_inside
    clean = []
    for point in answer:
        if not clean or point != clean[-1]:
            clean.append(point)
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()
    return clean


def polygon_monomial(polygon, u_power, t_power):
    """Exact polygon moment from an independently expanded Green integral."""
    if len(polygon) < 3:
        return ZERO
    area2 = sum(
        polygon[i][0] * polygon[(i + 1) % len(polygon)][1]
        - polygon[(i + 1) % len(polygon)][0] * polygon[i][1]
        for i in range(len(polygon))
    )
    if not area2:
        return ZERO
    if area2 < 0:
        polygon = list(reversed(polygon))
    answer = ZERO
    a = u_power + 1
    for index, (u0, t0) in enumerate(polygon):
        u1, t1 = polygon[(index + 1) % len(polygon)]
        du, dt = u1 - u0, t1 - t0
        if not dt:
            continue
        edge = ZERO
        for i in range(a + 1):
            for j in range(t_power + 1):
                edge += (
                    Q(comb(a, i) * comb(t_power, j), i + j + 1)
                    * u0 ** (a - i) * du ** i
                    * t0 ** (t_power - j) * dt ** j
                )
        answer += dt * edge / a
    return answer


def integrate_polygon(poly, constraints):
    # Every audited support lies in [0,1]^2.  Starting with the unit square
    # keeps the literal coordinate bounds visible instead of inferring them
    # from a simplex parameter.
    polygon = [(ZERO, ZERO), (ONE, ZERO), (ONE, ONE), (ZERO, ONE)]
    for a, b, cap in constraints:
        polygon = clip_polygon(polygon, a, b, cap)
        if len(polygon) < 3:
            return ZERO
    return sum(
        coefficient * polygon_monomial(polygon, i, j)
        for (i, j), coefficient in poly.items()
    )


def beta(schedule, count):
    if count <= 0:
        raise ValueError("no zero-index cap")
    return schedule[min(count, len(schedule)) - 1]


def cell_constraints(*, alpha, eta, delta, schedule, u_large, t_large):
    constraints = [
        (-ONE, ZERO, ZERO),       # u >= 0
        (ZERO, -ONE, ZERO),       # t >= 0
        (ONE, ZERO, eta),         # literal Definition-5 cutoff
        (ONE, ONE, alpha),        # endpoint total support
    ]
    constraints.append(
        (-ONE, ZERO, -delta) if u_large else (ONE, ZERO, delta)
    )
    constraints.append(
        (ZERO, -ONE, -delta) if t_large else (ZERO, ONE, delta)
    )
    number_large = int(u_large) + int(t_large)
    if number_large:
        constraints.append((
            ONE if u_large else ZERO,
            ONE if t_large else ZERO,
            beta(schedule, number_large),
        ))
    return constraints


def direct_cross_branch(poly, *, alpha, eta, delta, schedule,
                        common_r, branch):
    """Literal branch integral in the original (u,t) coordinates."""
    if common_r not in (0, 1):
        raise ValueError("the independent oracle is deliberately k=2 only")
    u_large = bool(common_r)
    t_large = branch.startswith("L")
    constraints = cell_constraints(
        alpha=alpha, eta=eta, delta=delta, schedule=schedule,
        u_large=u_large, t_large=t_large,
    )
    if branch == "Sdelta":
        constraints.append((ONE, ZERO, alpha - delta))
    elif branch == "Stotal":
        constraints.append((-ONE, ZERO, -(alpha - delta)))
    elif branch in ("Ltotal", "Lbig"):
        threshold = alpha - beta(schedule, common_r + 1)
        if common_r == 0:
            # The shared coordinate is small, so it is exactly the W which
            # decides whether total or the large-coordinate cap is active.
            constraints.append(
                (-ONE, ZERO, -threshold)
                if branch == "Ltotal" else (ONE, ZERO, threshold)
            )
        else:
            # There is no shared small coordinate.  At equality assign the
            # coincident upper bound to Lbig, matching the radial convention.
            if branch == "Ltotal" and not ZERO > threshold:
                return ZERO
            if branch == "Lbig" and not ZERO <= threshold:
                return ZERO
    else:
        raise ValueError(branch)
    return integrate_polygon(poly, constraints)


def direct_cross_endpoint(poly, *, alpha, eta, delta, schedule):
    return {
        r: {
            branch: direct_cross_branch(
                poly, alpha=alpha, eta=eta, delta=delta,
                schedule=schedule, common_r=r, branch=branch,
            )
            for branch in M.BRANCHES
        }
        for r in (0, 1)
    }


def direct_i_stratum(poly, *, alpha, delta, schedule, number_large):
    """Literal k=2 I endpoint on cells with a fixed large count."""
    answer = ZERO
    for u_large, t_large in product((False, True), repeat=2):
        if int(u_large) + int(t_large) != number_large:
            continue
        constraints = cell_constraints(
            alpha=alpha,
            eta=ONE,  # I has no Definition-5 common-coordinate cutoff.
            delta=delta,
            schedule=schedule,
            u_large=u_large,
            t_large=t_large,
        )
        answer += integrate_polygon(poly, constraints)
    return answer


def production_cross(inner_terms, outer_terms, *, alpha_f, alpha_low,
                     alpha_high, eta, delta, schedule):
    inner_basis = tuple(inner_terms)
    inner_vector = tuple(inner_terms.values())
    outer_basis = tuple(outer_terms)
    outer_vector = tuple(outer_terms.values())
    marginal = M.marginal_polynomial(
        F.ei, inner_basis, inner_vector, 2, alpha_f,
    )
    components = M.distinguished_components(
        F.ei, outer_basis, outer_vector, 2,
    )
    kernel, _ = M.global_cross_kernel(F.ei, marginal, components)
    families, _ = M.primitive_tagged_families(
        kernel, alpha_f=alpha_f, delta=delta,
    )
    total = ZERO
    diagnostics = {}
    for r in (0, 1):
        shard, row = M.radialized_band_cross_r(
            R, families, k=2, alpha_high=alpha_high,
            alpha_low=alpha_low, alpha_f=alpha_f, eta=eta,
            delta=delta, schedule=schedule, common_r=r,
        )
        total += shard
        diagnostics[r] = row
    return total, diagnostics, kernel


def production_i(outer_terms, *, alpha_low, alpha_high, delta, schedule):
    square = M.square_residual_terms(F.ei, outer_terms)
    rows = {}
    total = ZERO
    for r in range(3):
        value, row = M.radialized_band_i_r(
            R, square, k=2, alpha_high=alpha_high,
            alpha_low=alpha_low, delta=delta, schedule=schedule,
            number_large=r,
        )
        rows[r] = (value, row)
        total += value
    return total, rows


class IndependentLiteralCrossAudit(unittest.TestCase):
    maxDiff = None

    BASIS = (
        (0, ()),
        (1, ()),
        (2, ()),
        (0, (2,)),
        (1, (2,)),
        (0, (3,)),
        (0, (2, 2)),
        (0, (3, 2)),
    )

    GEOMETRY = dict(
        alpha_f=Q(7, 20),
        alpha_low=Q(3, 10),
        alpha_high=Q(2, 5),
        eta=Q(7, 25),
        delta=Q(1, 10),
        # beta_1 > alpha_low-delta makes the truncated-small and
        # total-limited-large pieces genuinely positive in k=2.  beta_2 is
        # different while still obeying beta_1 <= beta_2 <= beta_1+delta.
        schedule=(Q(1, 4), Q(31, 100)),
    )

    def assert_literal_match(self, inner_terms, outer_terms, geometry=None):
        geometry = dict(self.GEOMETRY if geometry is None else geometry)
        observed, diagnostics, kernel = production_cross(
            inner_terms, outer_terms, **geometry,
        )
        poly = marginal_times_outer(
            inner_terms, outer_terms, geometry["alpha_f"],
        )
        high = direct_cross_endpoint(
            poly,
            alpha=geometry["alpha_high"],
            eta=geometry["eta"],
            delta=geometry["delta"],
            schedule=geometry["schedule"],
        )
        low = direct_cross_endpoint(
            poly,
            alpha=geometry["alpha_low"],
            eta=geometry["eta"],
            delta=geometry["delta"],
            schedule=geometry["schedule"],
        )
        branch_names = set()
        raw_band = ZERO
        for r in (0, 1):
            for branch in M.BRANCHES:
                expected_high = high[r][branch]
                expected_low = low[r][branch]
                got_high = diagnostics[r]["high"].get(branch, ZERO)
                got_low = diagnostics[r]["low"].get(branch, ZERO)
                self.assertEqual(got_high, expected_high, (r, branch, "high"))
                self.assertEqual(got_low, expected_low, (r, branch, "low"))
                if got_high or got_low:
                    branch_names.add(branch)
                raw_band += expected_high - expected_low
        # This explicitly detects both omission and duplication of the sole
        # Proposition-1 factor k=2.
        self.assertEqual(observed, 2 * raw_band)

        support_type = F.shell.ScheduledStratumSupport
        high_support = support_type.make(
            2, geometry["alpha_high"], geometry["eta"],
            geometry["delta"], geometry["schedule"],
        )
        low_support = support_type.make(
            2, geometry["alpha_low"], geometry["eta"],
            geometry["delta"], geometry["schedule"],
        )
        face_value, _ = M.evaluate_band_cross(
            F, kernel, high=high_support, low=low_support,
            alpha_f=geometry["alpha_f"], eta=geometry["eta"],
        )
        self.assertEqual(face_value, observed)
        return observed, branch_names

    def assert_i_match(self, outer_terms, geometry=None):
        geometry = dict(self.GEOMETRY if geometry is None else geometry)
        observed, rows = production_i(outer_terms, **{
            key: geometry[key]
            for key in ("alpha_low", "alpha_high", "delta", "schedule")
        })
        squared = multiply_poly(
            terms_poly_2(outer_terms), terms_poly_2(outer_terms),
        )
        expected = ZERO
        for r in range(3):
            high = direct_i_stratum(
                squared, alpha=geometry["alpha_high"],
                delta=geometry["delta"], schedule=geometry["schedule"],
                number_large=r,
            )
            low = direct_i_stratum(
                squared, alpha=geometry["alpha_low"],
                delta=geometry["delta"], schedule=geometry["schedule"],
                number_large=r,
            )
            self.assertEqual(rows[r][1]["high"], high, (r, "I high"))
            self.assertEqual(rows[r][1]["low"], low, (r, "I low"))
            self.assertEqual(rows[r][0], high - low, (r, "I band"))
            expected += high - low
        self.assertEqual(observed, expected)
        return observed

    def test_exhaustive_basis_pairs_all_branches(self):
        branches = set()
        for inner_label in self.BASIS:
            for outer_label in self.BASIS:
                _, seen = self.assert_literal_match(
                    {inner_label: ONE}, {outer_label: ONE},
                )
                branches.update(seen)
        self.assertEqual(branches, set(M.BRANCHES))

    def test_deterministic_random_linear_combinations(self):
        generator = random.Random(236_048)
        branches = set()
        for case in range(16):
            inner = {
                label: Q(generator.randint(-4, 4), generator.randint(1, 7))
                for label in self.BASIS
            }
            outer = {
                label: Q(generator.randint(-4, 4), generator.randint(1, 7))
                for label in self.BASIS
            }
            inner = {key: value for key, value in inner.items() if value}
            outer = {key: value for key, value in outer.items() if value}
            _, seen = self.assert_literal_match(inner, outer)
            branches.update(seen)
            self.assert_i_match(outer)
        self.assertEqual(branches, set(M.BRANCHES))

    def test_deterministic_random_literal_geometries(self):
        generator = random.Random(48_236_2026)
        labels = self.BASIS[:6]
        for case in range(12):
            delta_units = generator.choice((8, 10, 12))
            low_units = generator.randint(34, 43)
            high_units = low_units + generator.randint(3, 10)
            eta_units = generator.randint(15, low_units - 1)
            beta1_units = generator.randint(delta_units + 1, low_units + 5)
            beta2_units = beta1_units + generator.randint(0, delta_units)
            geometry = dict(
                alpha_f=Q(low_units, 120),
                alpha_low=Q(low_units, 120),
                alpha_high=Q(high_units, 120),
                eta=Q(eta_units, 120),
                delta=Q(delta_units, 120),
                schedule=(Q(beta1_units, 120), Q(beta2_units, 120)),
            )
            inner = {
                label: Q(generator.randint(-3, 3), generator.randint(1, 5))
                for label in labels
            }
            outer = {
                label: Q(generator.randint(-3, 3), generator.randint(1, 5))
                for label in labels
            }
            inner = {key: value for key, value in inner.items() if value}
            outer = {key: value for key, value in outer.items() if value}
            if not inner:
                inner = {(0, ()): ONE}
            if not outer:
                outer = {(0, ()): ONE}
            self.assert_literal_match(inner, outer, geometry)
            self.assert_i_match(outer, geometry)

    def test_target_geometry_dilation_and_exact_scales(self):
        alpha_low = Q(103, 400)
        alpha_high = Q(9500917, 36000000)
        geometry = dict(
            alpha_f=alpha_low,
            alpha_low=alpha_low,
            alpha_high=alpha_high,
            eta=Q(8960917, 36000000),
            delta=Q(1, 60),
            schedule=(Q(140375, 1000000), Q(157041, 1000000)),
        )
        base_inner_vector = (Q(3, 5), Q(-7, 11), Q(5, 13), Q(2, 3))
        base_outer_vector = (Q(-4, 7), Q(9, 10), Q(6, 17), Q(-5, 8))
        basis = ((0, ()), (2, ()), (1, (2,)), (0, (3, 2)))
        dilation = alpha_low / alpha_high

        base_inner = dict(zip(basis, base_inner_vector, strict=True))
        base_outer = M.dilate_residual_terms(
            basis, base_outer_vector, dilation,
        )
        base_cross, _ = self.assert_literal_match(
            base_inner, base_outer, geometry,
        )
        base_i = self.assert_i_match(base_outer, geometry)

        scaled_inner_vector = M.scale_vector(base_inner_vector, 10**87)
        scaled_outer_vector = M.scale_vector(base_outer_vector, 10**38)
        scaled_inner = dict(zip(basis, scaled_inner_vector, strict=True))
        scaled_outer = M.dilate_residual_terms(
            basis, scaled_outer_vector, dilation,
        )
        scaled_cross, branches = self.assert_literal_match(
            scaled_inner, scaled_outer, geometry,
        )
        scaled_i = self.assert_i_match(scaled_outer, geometry)
        self.assertEqual(scaled_cross, base_cross * 10**125)
        self.assertEqual(scaled_i, base_i * 10**76)
        # The literal k=48 schedule, projected down to k=2, makes the
        # truncated-small and total-limited-large cells empty.  Those branches
        # are exercised under the separate compatible nonuniform schedule.
        self.assertTrue(branches)

        # Direct polynomial evaluation also checks that the natural dilation
        # is alpha_low/alpha_high (not its reciprocal) and commutes with scale.
        point = (Q(1, 101), Q(3, 103))
        base_original_terms = dict(zip(basis, base_outer_vector, strict=True))
        expected = literal_terms_value(
            base_original_terms,
            tuple(dilation * coordinate for coordinate in point),
        )
        self.assertEqual(
            literal_terms_value(base_outer, point), expected,
        )
        self.assertEqual(
            literal_terms_value(scaled_outer, point), expected * 10**38,
        )

    def test_kernel_against_bruteforce_named_monomials_k4(self):
        k, alpha_f = 4, Q(7, 20)
        inner_terms = {
            (0, ()): Q(2, 3),
            (2, ()): Q(-5, 7),
            (1, (2,)): Q(11, 13),
            (0, (3, 2)): Q(-7, 5),
            (0, (2, 2)): Q(3, 11),
            (1, (4, 3, 2)): Q(5, 17),
        }
        outer_terms = {
            (1, ()): Q(-4, 9),
            (0, (2,)): Q(8, 7),
            (2, (3,)): Q(-9, 11),
            (0, (3, 2)): Q(13, 19),
            (1, (2, 2)): Q(-6, 5),
            (0, (4, 3, 2)): Q(7, 23),
        }
        marginal = M.marginal_polynomial(
            F.ei, tuple(inner_terms), tuple(inner_terms.values()), k, alpha_f,
        )
        components = M.distinguished_components(
            F.ei, tuple(outer_terms), tuple(outer_terms.values()), k,
        )
        kernel, _ = M.global_cross_kernel(F.ei, marginal, components)
        for shared, t in (
            ((Q(1, 41), Q(2, 43), Q(3, 47)), Q(5, 53)),
            ((Q(4, 101), Q(7, 103), Q(9, 107)), Q(11, 109)),
            ((Q(1, 20), Q(1, 30), Q(1, 40)), Q(1, 50)),
        ):
            u_sum = sum(shared, ZERO)
            expected = (
                literal_marginal_value(inner_terms, shared, alpha_f)
                * literal_terms_value(outer_terms, shared + (t,))
            )
            observed = ZERO
            for orbit, block in kernel.items():
                orbit_value = literal_orbit_value(orbit, shared)
                for (inner_power, t_power, residual_power), coefficient \
                        in block.items():
                    observed += (
                        coefficient * orbit_value
                        * (alpha_f - u_sum) ** inner_power
                        * t ** t_power
                        * (ONE - u_sum - t) ** residual_power
                    )
            self.assertEqual(observed, expected)

    def test_coincident_large_upper_bounds_are_not_double_counted(self):
        geometry = dict(
            alpha_f=Q(7, 20),
            alpha_low=Q(3, 10),
            alpha_high=Q(2, 5),
            eta=Q(1, 4),
            delta=Q(1, 10),
            schedule=(Q(2, 5), Q(2, 5)),
        )
        inner = {(0, ()): ONE, (1, (2,)): Q(2, 7)}
        outer = {(1, ()): Q(3, 11), (0, (3, 2)): Q(-5, 13)}
        value, branches = self.assert_literal_match(inner, outer, geometry)
        self.assertTrue(value)
        self.assertIn("Lbig", branches)

    def test_cutoff_and_high_low_orientation_are_detectable(self):
        inner = {(0, ()): ONE, (1, (2,)): Q(2, 3)}
        outer = {(0, ()): Q(-3, 5), (0, (3, 2)): Q(7, 11)}
        observed, _ = self.assert_literal_match(inner, outer)

        altered = dict(self.GEOMETRY)
        altered["eta"] = Q(3, 20)
        cut, _ = self.assert_literal_match(inner, outer, altered)
        self.assertNotEqual(observed, cut)

        reversed_geometry = dict(self.GEOMETRY)
        reversed_geometry["alpha_low"] = self.GEOMETRY["alpha_high"]
        reversed_geometry["alpha_high"] = self.GEOMETRY["alpha_low"]
        reversed_value, _ = self.assert_literal_match(
            inner, outer, reversed_geometry,
        )
        self.assertEqual(reversed_value, -observed)


if __name__ == "__main__":
    unittest.main()
