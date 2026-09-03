#!/usr/bin/env python3
"""Exact polygon moments with one fixed denominator per batch.

For a rational triangle, scale every vertex coordinate by a common integer
L.  If E is the maximum requested total degree, then

    L**(E+2) * (E+2)!

clears every requested monomial integral.  All affine expansion and simplex
moment accumulation can therefore be done with Python integers; Fraction
normalization occurs only once per final moment, not in the inner expansion.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
import math


def _integer_linear_powers(constant, u_coefficient, v_coefficient, degrees):
    requested = set(degrees)
    if not requested:
        return {}
    maximum = max(requested)
    if type(maximum) is not int or maximum < 0:
        raise ValueError("monomial degrees must be nonnegative integers")
    current = {(0, 0): 1}
    answer = {0: current} if 0 in requested else {}
    for degree in range(1, maximum + 1):
        following = defaultdict(int)
        if constant:
            for key, coefficient in current.items():
                following[key] += coefficient * constant
        if u_coefficient:
            for (u_power, v_power), coefficient in current.items():
                following[(u_power + 1, v_power)] += (
                    coefficient * u_coefficient)
        if v_coefficient:
            for (u_power, v_power), coefficient in current.items():
                following[(u_power, v_power + 1)] += (
                    coefficient * v_coefficient)
        current = {key: value for key, value in following.items() if value}
        if degree in requested:
            answer[degree] = current
    return answer


def _triangle_scaled_numerators(origin, first, second, requested,
                                coordinate_denominator, maximum_degree,
                                factorials, factorial_top):
    points = []
    for point in (origin, first, second):
        scaled = []
        for coordinate in point:
            coordinate = Q(coordinate)
            if coordinate_denominator % coordinate.denominator:
                raise ArithmeticError("coordinate denominator does not clear")
            scaled.append(
                coordinate.numerator *
                (coordinate_denominator // coordinate.denominator))
        points.append(tuple(scaled))
    (ox, oy), (fx, fy), (sx, sy) = points
    px, py = fx - ox, fy - oy
    qx, qy = sx - ox, sy - oy
    determinant = abs(px * qy - py * qx)
    if not determinant:
        return {power: 0 for power in requested}
    x_powers = _integer_linear_powers(
        ox, px, qx, (a for a, _ in requested))
    y_powers = _integer_linear_powers(
        oy, py, qy, (b for _, b in requested))
    denominator_powers = tuple(
        coordinate_denominator**degree
        for degree in range(maximum_degree + 1))
    answer = {}
    for x_power, y_power in requested:
        total_degree = x_power + y_power
        scale = denominator_powers[maximum_degree - total_degree]
        numerator = 0
        for (ux, vx), coefficient_x in x_powers[x_power].items():
            for (uy, vy), coefficient_y in y_powers[y_power].items():
                u_power, v_power = ux + uy, vx + vy
                denominator_factorial = factorials[u_power + v_power + 2]
                if factorial_top % denominator_factorial:
                    raise ArithmeticError("factorial ceiling does not clear")
                numerator += (
                    coefficient_x * coefficient_y *
                    factorials[u_power] * factorials[v_power] *
                    (factorial_top // denominator_factorial))
        answer[(x_power, y_power)] = determinant * scale * numerator
    return answer


def polygon_monomial_batch_fixed(polygon, powers):
    """Return the exact requested rational moments of a convex polygon."""
    requested = tuple(sorted(set(powers)))
    if any(type(a) is not int or type(b) is not int or a < 0 or b < 0
           for a, b in requested):
        raise ValueError("requested powers must be nonnegative integer pairs")
    if not requested:
        return {}
    if len(polygon) < 3:
        return {power: Q(0) for power in requested}
    maximum_degree = max(a + b for a, b in requested)
    coordinate_denominator = 1
    for point in polygon:
        if len(point) != 2:
            raise ValueError("polygon point is not two-dimensional")
        for coordinate in point:
            coordinate_denominator = math.lcm(
                coordinate_denominator, Q(coordinate).denominator)
    factorials = [1]
    for value in range(1, maximum_degree + 3):
        factorials.append(factorials[-1] * value)
    factorials = tuple(factorials)
    factorial_top = factorials[maximum_degree + 2]
    common_denominator = (
        coordinate_denominator ** (maximum_degree + 2) * factorial_top)
    numerators = {power: 0 for power in requested}
    anchor = polygon[0]
    for index in range(1, len(polygon) - 1):
        triangle = _triangle_scaled_numerators(
            anchor, polygon[index], polygon[index + 1], requested,
            coordinate_denominator, maximum_degree, factorials, factorial_top)
        for power, value in triangle.items():
            numerators[power] += value
    return {
        power: Q(numerator, common_denominator)
        for power, numerator in numerators.items()}

