#!/usr/bin/env python3
"""Install a rigorous fixed-point interval scalar in the grouped integrator.

This mirrors the Decimal discovery backend, but every arithmetic result is an
integer-defined outward enclosure.  Support geometry retains a bounded exact
shadow so comparisons fail closed instead of being rounded.  Call only in a
fresh process: the installation intentionally replaces arithmetic hooks in
``exact_integrator``.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from functools import lru_cache
from math import comb, factorial
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE / "src"))

import exact_integrator as ei  # noqa: E402
from verify.dyadic_interval import DyadicInterval  # noqa: E402


def _clear_integrator_caches():
    for function in (
        ei.multiply_monomial_orbits,
        ei._linear_power,
        ei.polygon_monomial,
        ei.polygon,
        ei._large_shift_dp,
        ei._small_box_dp,
        ei._selected_exponent_splits,
    ):
        clear = getattr(function, "cache_clear", None)
        if clear is not None:
            clear()
    # These are class-method lru caches whose keys include a support object.
    # Exact-Fraction and exact-shadow interval support objects compare and
    # hash numerically equal, so every scalar-dependent value must be purged
    # before changing the arithmetic ring.
    for name in (
        "_piece_residual",
        "canonical_support_residual",
        "canonical_support_moment",
        "_branch_constraints",
        "_marginal_poly",
        "_j_piece",
        "canonical_j_moment",
        "basis_m1",
        "basis_j",
    ):
        function = getattr(ei.OneStratumSupport, name)
        clear = getattr(function, "cache_clear", None)
        if clear is None:
            raise RuntimeError(f"expected cached support method is absent: {name}")
        clear()


def install_dyadic(orbit_table, precision=512, shadow_bits=96):
    """Monkeypatch ``exact_integrator`` and return the interval constructor."""
    DyadicInterval.configure(precision, shadow_bits)
    _clear_integrator_caches()

    # Copy and validate the full integer structure-constant snapshot before
    # closing over it.  A caller mutation after installation must not alter
    # the arithmetic performed by an already configured backend.
    frozen_orbits = {}
    for raw_key, raw_value in dict(orbit_table).items():
        if (not isinstance(raw_key, tuple) or len(raw_key) != 2 or
                any(not isinstance(part, tuple) for part in raw_key)):
            raise ValueError("malformed orbit-table key")
        key = tuple(tuple(part) for part in raw_key)
        if any(any(not isinstance(x, int) or isinstance(x, bool) or x <= 0
                       for x in part) or tuple(sorted(part, reverse=True)) != part
                   for part in key):
            raise ValueError("orbit-table partitions are not canonical")
        if not isinstance(raw_value, tuple):
            raise ValueError("orbit-table expansion must be an immutable tuple")
        expansion = []
        seen_outputs = set()
        for item in raw_value:
            if (not isinstance(item, tuple) or len(item) != 2 or
                    not isinstance(item[0], tuple) or
                    not isinstance(item[1], int) or isinstance(item[1], bool) or
                    item[1] <= 0):
                raise ValueError("malformed orbit structure constant")
            output, multiplicity = item
            if (any(not isinstance(x, int) or isinstance(x, bool) or x <= 0
                    for x in output) or
                    tuple(sorted(output, reverse=True)) != output or
                    output in seen_outputs):
                raise ValueError("noncanonical/duplicate orbit output")
            seen_outputs.add(output)
            expansion.append((tuple(output), multiplicity))
        frozen_orbits[key] = tuple(expansion)
    for (lam, mu), expansion in frozen_orbits.items():
        reverse = frozen_orbits.get((mu, lam))
        if reverse is not None and reverse != expansion:
            raise ValueError("inconsistent reversed orbit products")

    def ivq(numerator=0, denominator=None):
        return DyadicInterval(numerator, denominator)

    def orbit_lookup(lam, mu):
        key = (tuple(lam), tuple(mu))
        if key in frozen_orbits:
            return frozen_orbits[key]
        reverse = (key[1], key[0])
        if reverse in frozen_orbits:
            return frozen_orbits[reverse]
        raise KeyError(key)

    ei.Q = ivq
    ei.multiply_monomial_orbits = orbit_lookup

    @lru_cache(maxsize=None)
    def linear_power(c0, cz, cw, n):
        out = defaultdict(DyadicInterval)
        for i in range(n + 1):
            for j in range(n - i + 1):
                h = n - i - j
                coefficient = DyadicInterval(
                    factorial(n), factorial(i) * factorial(j) * factorial(h))
                out[(i, j)] += (
                    coefficient *
                    (DyadicInterval(1) if i == 0 else cz ** i) *
                    (DyadicInterval(1) if j == 0 else cw ** j) *
                    (DyadicInterval(1) if h == 0 else c0 ** h)
                )
        return tuple(out.items())

    ei._linear_power = linear_power

    def power(x, n):
        return DyadicInterval(1) if n == 0 else x ** n

    @lru_cache(maxsize=None)
    def polygon_monomial(poly, az, aw):
        if not poly:
            return DyadicInterval(0)
        answer = DyadicInterval(0)
        ap = az + 1
        for idx, (x0, y0) in enumerate(poly):
            x1, y1 = poly[(idx + 1) % len(poly)]
            dx, dy = x1 - x0, y1 - y0
            if dy == 0:
                continue
            if dx == 0:
                answer += (power(x0, ap) *
                           (power(y1, aw + 1) - power(y0, aw + 1)) /
                           DyadicInterval(ap * (aw + 1)))
            elif dx + dy == 0:
                constant = x0 + y0
                edge = DyadicInterval(0)
                for i in range(ap + 1):
                    edge += (DyadicInterval((-1) ** i * comb(ap, i),
                                             aw + i + 1) *
                             power(constant, ap - i) *
                             (power(y1, aw + i + 1) -
                              power(y0, aw + i + 1)))
                answer += edge / DyadicInterval(ap)
            else:
                edge = DyadicInterval(0)
                for i in range(ap + 1):
                    for j in range(aw + 1):
                        edge += (DyadicInterval(comb(ap, i) * comb(aw, j),
                                                i + j + 1) *
                                 power(x0, ap - i) * power(dx, i) *
                                 power(y0, aw - j) * power(dy, j))
                answer += dy * edge / DyadicInterval(ap)
        return answer

    ei.polygon_monomial = polygon_monomial
    return ivq


__all__ = ["DyadicInterval", "install_dyadic"]
