#!/usr/bin/env python3
"""Exact monomial moments of a rational convex polygon by Green's theorem.

For a counterclockwise boundary and nonnegative integers ``a,b``,

    integral_P x^a y^b dxdy
      = sum_edges int_0^1 x(t)^(a+1)y(t)^b y'(t)dt / (a+1).

Scale all vertex coordinates by their common denominator ``L``.  If ``E``
is the largest requested total degree and ``T=(E+2)!``, every summand is an
integer over ``L^(E+2) T^2``: its only remaining divisors are ``a+1`` and
``i+j+1``, both divisors of ``T``.  The implementation therefore performs
all edge expansions and accumulation with integers and creates one Fraction
per requested final moment.

The public routine deliberately fails closed unless the supplied cyclic
polygon is convex (collinear boundary vertices are allowed).  Every polygon
created by the pinned capped-simplex half-plane intersection has this form.
"""

from __future__ import annotations

from fractions import Fraction as Q
import math


def _linear_powers(constant, coefficient, requested):
    requested = set(requested)
    if not requested:
        return {}
    maximum = max(requested)
    if type(maximum) is not int or maximum < 0:
        raise ValueError("linear-power degrees must be nonnegative integers")
    current = (1,)
    answer = {0: current} if 0 in requested else {}
    for degree in range(1, maximum + 1):
        following = [0] * (degree + 1)
        for index, value in enumerate(current):
            following[index] += constant * value
            following[index + 1] += coefficient * value
        current = tuple(following)
        if degree in requested:
            answer[degree] = current
    return answer


def _scaled_vertices(polygon):
    denominator = 1
    rational = []
    for point in polygon:
        if len(point) != 2:
            raise ValueError("polygon point is not two-dimensional")
        converted = tuple(map(Q, point))
        rational.append(converted)
        for coordinate in converted:
            denominator = math.lcm(denominator, coordinate.denominator)
    scaled = tuple(tuple(
        coordinate.numerator * (denominator // coordinate.denominator)
        for coordinate in point) for point in rational)
    return scaled, denominator


def _orientation(scaled):
    """Return +1/-1 for a convex cyclic polygon; fail on nonconvex input."""
    number = len(scaled)
    if len(set(scaled)) != number:
        raise ValueError("polygon vertices are not distinct")
    turns = set()
    for index in range(number):
        first = scaled[index]
        second = scaled[(index + 1) % number]
        third = scaled[(index + 2) % number]
        cross = ((second[0] - first[0]) * (third[1] - second[1]) -
                 (second[1] - first[1]) * (third[0] - second[0]))
        if cross:
            turns.add(1 if cross > 0 else -1)
    if len(turns) > 1:
        raise ValueError("polygon vertices are not in convex cyclic order")
    twice_area = sum(
        scaled[index][0] * scaled[(index + 1) % number][1] -
        scaled[index][1] * scaled[(index + 1) % number][0]
        for index in range(number))
    if not twice_area:
        if turns:
            raise ValueError(
                "noncollinear polygon has zero signed boundary area")
        return 0
    orientation = 1 if twice_area > 0 else -1
    if turns and turns != {orientation}:
        raise ValueError("polygon orientation and local turns disagree")
    # Local turn signs alone do not exclude a convex loop traversed more than
    # once (or every possible self-intersection).  For a convex cyclic
    # boundary, every vertex lies in the same closed half-plane of every
    # oriented edge.  This global check is tiny for the target polygons and
    # is also sufficient to validate the fan/boundary interpretation.
    for index, first in enumerate(scaled):
        second = scaled[(index + 1) % number]
        dx, dy = second[0] - first[0], second[1] - first[1]
        for point in scaled:
            cross = dx * (point[1] - first[1]) - dy * (point[0] - first[0])
            if orientation * cross < 0:
                raise ValueError(
                    "polygon violates a convex supporting half-plane")
    return orientation


def polygon_monomial_batch_green(polygon, powers):
    """Return exact requested moments for a rational convex polygon."""
    requested = tuple(sorted(set(powers)))
    if any(type(a) is not int or type(b) is not int or a < 0 or b < 0
           for a, b in requested):
        raise ValueError("requested powers must be nonnegative integer pairs")
    if not requested:
        return {}
    if len(polygon) < 3:
        return {power: Q(0) for power in requested}
    scaled, coordinate_denominator = _scaled_vertices(polygon)
    orientation = _orientation(scaled)
    if not orientation:
        return {power: Q(0) for power in requested}
    maximum_degree = max(a + b for a, b in requested)
    factorial_top = math.factorial(maximum_degree + 2)
    common_denominator = (
        coordinate_denominator ** (maximum_degree + 2) * factorial_top**2)
    coordinate_scales = tuple(
        coordinate_denominator**degree
        for degree in range(maximum_degree + 1))
    numerators = {power: 0 for power in requested}

    x_degrees = {a + 1 for a, _ in requested}
    y_degrees = {b for _, b in requested}
    for index, (x0, y0) in enumerate(scaled):
        x1, y1 = scaled[(index + 1) % len(scaled)]
        dx, dy = x1 - x0, y1 - y0
        if not dy:
            continue
        x_powers = _linear_powers(x0, dx, x_degrees)
        y_powers = _linear_powers(y0, dy, y_degrees)
        for a, b in requested:
            edge_sum = 0
            for i, x_coefficient in enumerate(x_powers[a + 1]):
                if not x_coefficient:
                    continue
                for j, y_coefficient in enumerate(y_powers[b]):
                    if y_coefficient:
                        edge_sum += (
                            x_coefficient * y_coefficient *
                            (factorial_top // (i + j + 1)))
            # One copy of factorial_top clears (i+j+1), and the other
            # independently clears (a+1).
            degree_scale = coordinate_scales[maximum_degree - (a + b)]
            numerators[(a, b)] += (
                dy * edge_sum * (factorial_top // (a + 1)) * degree_scale)

    return {
        power: Q(orientation * numerator, common_denominator)
        for power, numerator in numerators.items()}
