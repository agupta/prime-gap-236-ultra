#!/usr/bin/env python3
"""Lightweight search oracle for adaptive wide-support parameters.

This is discovery code.  It uses binary floating point to locate rational
candidates; ``verify_adaptive_support.py`` is the independent exact gate.
No module used by the staged active25 computation is imported.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, comb, factorial, floor


H = 1e-10
ZETA = H / 1000
R0 = H / 10
K = 48
CELLS = 16
BASE_DELTA = 361 / 50000
BASE_X = 121 / 12000
BASE_EPSILON = 3 / 400
BASE_SCHEDULE = (
    119469 / 1e6, 126689 / 1e6, 133909 / 1e6,
    141129 / 1e6, 148349 / 1e6, 155569 / 1e6,
    155569 / 1e6, 162789 / 1e6, 339 / 2000,
    339 / 2000, 339 / 2000, 339 / 2000, 1718 / 10000,
    1737 / 10000, 1752 / 10000, 1762 / 10000,
    1764 / 10000, 1774 / 10000, 1782 / 10000,
    1790 / 10000, 1796 / 10000, 1801 / 10000,
    1806 / 10000, 1811 / 10000, 1815 / 10000,
    1815 / 10000,
)


@dataclass(frozen=True)
class Parameters:
    delta: float
    x: float                    # A2-1/4 = outer omega
    epsilon: float = BASE_EPSILON
    cells: int = CELLS

    @property
    def alpha1(self):
        return .25 + self.epsilon

    @property
    def alpha2(self):
        return .25 + self.x + self.epsilon


def extend(head, delta):
    length = floor(1 / delta)
    if len(head) > length:
        return None
    return tuple(head) + (head[-1],) * (length - len(head))


def active(head, delta):
    return (0,) + tuple(i for i, value in enumerate(head, 1)
                       if i * delta <= value + 2e-15)


def bound(head, count):
    return 0.0 if count == 0 else head[count - 1]


def source_ok(p: Parameters):
    d, x, e = p.delta, p.x, p.epsilon
    if not (d > 0 and x > 0 and e > 0 and .25 + x + e < .5):
        return False
    sigma = .1 + H / 10
    gamma3 = .4 - H / 10
    aux = d + H / 4
    margins = []

    def da(g, w):
        return 5 * g / 7 - 2 / 7 - 24 * w / 7 - H

    def db(g, w):
        return 3 * g / 7 - 1 / 7 - 24 * w / 7 - H

    def ga(w):
        return .4 + 24 * w / 5 + 7 * d / 5 + 2 * H

    def gb(w):
        return 1 / 3 + 8 * w + 7 * d / 3 + 3 * H

    for w in (x / 2, x, 0.0):
        g_a, g_b = ga(w), gb(w)
        d3 = .5 - 3.5 * w - 9 * gamma3 / 8 - H
        margins += [
            .5 - g_a, g_a - g_b,
            da(g_a, w) - 2 * R0 - d,
            -2 - (24 * w + 7 * da(g_a, w) - 5 * g_a),
            -(8 * w + 3 * da(.5, w) - .5),
            g_a - 3 * ZETA - da(g_a, w) + R0,
            R0,
            db(g_b, w) - 2 * R0 - d,
            -1 - (24 * w + 7 * db(g_b, w) - 3 * g_b),
            -(8 * w + 3 * db(g_a, w) - g_a),
            g_b - 3 * ZETA - db(g_b, w) + R0,
            .5 - g_a - 2 * w - 6 * ZETA - db(g_a, w) + R0,
            2 * w + 9 * ZETA + 2 * R0,
            d3 - 2 * H - d,
            4 - (28 * w + 9 * gamma3 + 8 * d3),
            4 - (16 * w + 9 * gamma3 + 2 * d3),
            4 - (28 * w + 9 * gamma3 - d3),
            1 - 4 * w + 4 * d3,
            1 - 2 * d3 + 8 * w,
            1 / 12 - w,
            1 / 3 + d3 / 3 - 4 * w / 3 + H,
            .5 - (1 / 3 + 4 * d3 / 3 - 4 * w / 3 - H),
            1 - ((.5 - sigma) + (.5 + 2 * w)),
            1 - (1 - 2 * sigma + 4 * w),
            .5 - 2 * w,
            1 - (.5 + 2 * w) - 1 / 3,
            19 / 2 - 36 * (.25 + w) - 13 * d + 100 * H,
            21 / 25 - 16 * (.25 + w) / 5 - 2 * H - d,
            63 / 80 - 3 * (.25 + w) - 2 * H - d,
        ]
    # Repaired IIc applies whenever its gamma interval is nonempty; otherwise
    # the exact negative width is the emptiness certificate.
    gmin = .4 - H
    for w in (x / 2, x, 0.0):
        gmax = gb(w)
        if gmax < gmin:
            margins.append(gmin - gmax)
            continue
        margins += [
            gmax - gmin, aux - 2 * R0 - d,
            1 - (8 * w + 4 * aux + 2 * gmax),
            gmin - (32 * w + 10 * aux),
            4 * gmin - 48 * w - 16 * aux - 1,
            gmin - 4 * w - aux,
            gmin - 3 * ZETA - aux + R0,
            .5 - gmax - 2 * w - 6 * ZETA - aux + R0,
            .5 - gmax + 3 * ZETA + R0,
            2 * (aux - 2 * R0),
            H - 2 * (aux - d) - 58 * ZETA + R0,
            H - 6 * ZETA - R0,
            aux - d + H, 2 * R0,
        ]
    return min(margins) > 1e-14


def schedule_ok(head, p):
    full = extend(head, p.delta)
    if full is None or min(full) <= p.delta:
        return False
    return all(full[i - 1] <= full[i] + 2e-15 and
               full[i] <= full[i - 1] + p.delta + 2e-15
               for i in range(1, len(full)))


def fixed_capacities(delta, omega):
    gamma3 = .4 - H / 10
    d3 = .5 - 3.5 * omega - 9 * gamma3 / 8 - H
    return (
        (.4 + 24 * omega / 5 + 7 * delta / 5 - 2 * H,
         1 / 14 - 24 * omega / 7 - 2 * H),
        (1 / 3 + 4 * d3 / 3 - 4 * omega / 3 - H,
         1 / 6 - d3 / 3 + 4 * omega / 3 - H),
    )


def prefix_ok(groups, caps, delta):
    n = sum(c for c, _ in groups)
    total = sum(b for _, b in groups)
    if total < caps[0] - 1e-14:
        return True
    overload = total - caps[0]
    pools = tuple(groups) + ((n, total),)
    r = ceil(overload / delta - 2e-13)
    for count, cap in pools:
        if count <= 0 or count * delta < overload - 1e-14 or not 1 <= r <= count:
            continue
        upper = cap / count if r == 1 else \
            overload + (cap - overload) / (count - r + 1)
        if any(upper < value - 1e-14 for value in caps[1:]):
            return True
    return False


def two_bin_iib_ok(groups, delta, omega):
    """Old correlated continuum sweep, generalized to arbitrary groups."""
    total = sum(cap for _, cap in groups)
    n = sum(count for count, _ in groups)
    gb = 1 / 3 + 8 * omega + 7 * delta / 3 + 3 * H
    cmin = gb - 3 * ZETA - R0
    ksum = .5 - 2 * omega - 9 * ZETA - 2 * R0
    window = ksum - total
    if window <= 1e-14:
        return False
    largest = total - cmin
    if largest <= -1e-14:
        return True
    pools = tuple(groups) + ((n, total),)
    for r in range(1, ceil(largest / delta - 2e-13) + 1):
        found = False
        for count, cap in pools:
            if count < r:
                continue
            upper = cap / count if r == 1 else \
                (cap - (r - 1) * delta) / (count - r + 1)
            if upper < window - 1e-14:
                found = True
                break
        if not found:
            return False
    return True


def three_bin_iib_ok(groups, delta, omega):
    """Uniform-small-prefix three-bin certificate used during search.

    The exact verifier additionally permits the action to vary at all exact
    gamma breakpoints.  This cheaper oracle is deliberately stronger than
    necessary, hence every point it accepts has a simple exact certificate.
    """
    if two_bin_iib_ok(groups, delta, omega):
        return True
    ga = .4 + 24 * omega / 5 + 7 * delta / 5 + 2 * H
    emin = (3 * ga * 0)  # retain a visibly local assignment below
    gb = 1 / 3 + 8 * omega + 7 * delta / 3 + 3 * H
    emin = 2 * omega + 9 * ZETA + (3 * gb / 7 - 1 / 7 -
                                   24 * omega / 7 - H)
    maxq = min(sum(c for c, _ in groups), floor(emin / delta + 1e-12))
    (nl, bl), (nr, br) = groups
    for q in range(1, maxq + 1):
        for ql in range(max(0, q - nr), min(nl, q) + 1):
            qr = q - ql
            upper = ((ql * bl / nl if ql else 0) +
                     (qr * br / nr if qr else 0))
            if upper >= emin - 1e-14:
                continue
            rem = []
            if nl > ql:
                rem.append((nl - ql, bl - ql * delta))
            if nr > qr:
                rem.append((nr - qr, br - qr * delta))
            if len(rem) == 1:
                rem.append((0, 0.0))
            if two_bin_iib_ok(tuple(rem), delta, omega):
                return True
    return False


def family_ok(left, right, omega, p, dynamic=False):
    d = p.delta
    la, ra = active(left, d), active(right, d)
    fixed = fixed_capacities(d, omega)
    for m in la:
        for n in ra:
            if m + n == 0:
                continue
            groups = ((m, bound(left, m)), (n, bound(right, n)))
            if not all(prefix_ok(groups, caps, d) for caps in fixed):
                return False
            if not three_bin_iib_ok(groups, d, omega):
                return False
    if not dynamic:
        return True
    g0 = .4 - H
    g1 = 1 / 3 + 8 * omega + 7 * d / 3 + 3 * H
    if g1 < g0:
        return True
    for m in la:
        for n in ra:
            if m + n == 0:
                continue
            groups = ((m, bound(left, m)), (n, bound(right, n)))
            for iw in range(p.cells):
                wl, wu = omega * iw / p.cells, omega * (iw + 1) / p.cells
                for ig in range(p.cells):
                    gl = g0 + (g1 - g0) * ig / p.cells
                    gu = g0 + (g1 - g0) * (ig + 1) / p.cells
                    caps = (gl - 2 * d - 8 * wu - H,
                            .5 - gu - 2 * wu - H,
                            4 * wl + d - H, 8 * wl)
                    if min(caps) < -1e-14 or not prefix_ok(groups, caps, d):
                        return False
    return True


def feasible(head, p, quick=False):
    if not source_ok(p) or not schedule_ok(head, p):
        return False
    inner = (p.alpha1,) * max(1, floor(1 / p.delta))
    cross_dynamic = (1 / 3 + 4 * p.x + 7 * p.delta / 3 + 3 * H >=
                     .4 - H)
    near_dynamic = (1 / 3 + 7 * p.delta / 3 + 3 * H >= .4 - H)
    if not family_ok(inner, head, p.x / 2, p, dynamic=cross_dynamic):
        return False
    if not family_ok(head, inner, p.x / 2, p, dynamic=cross_dynamic):
        return False
    if not family_ok(head, head, p.x, p):
        return False
    if not family_ok(head, head, 0.0, p, dynamic=near_dynamic):
        return False
    return quick or family_ok(head, head, p.x, p, dynamic=True)


def raise_at(head, index, amount, delta):
    """Least pointwise enlargement raising one zero-based cap by amount."""
    out = list(head)
    target = out[index] + amount
    for j in range(index, -1, -1):
        out[j] = max(out[j], target - (index - j) * delta)
    for j in range(index + 1, len(out)):
        out[j] = max(out[j], target)
    return tuple(out)


def optimize_schedule(p, start=BASE_SCHEDULE, rounds=2):
    head = tuple(start)
    if not feasible(head, p):
        return None
    # Frozen D18 target count order, followed by geometric cleanup.
    order = (8, 7, 9, 6, 10, 5, 11, 12, 4, 13, 3, 14, 2, 15,
             1, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26)
    for _ in range(rounds):
        for count in order:
            i = count - 1
            if i >= len(head):
                continue
            lo, hi = 0.0, .04
            while feasible(raise_at(head, i, hi, p.delta), p, quick=True):
                hi *= 2
                if hi > .2:
                    break
            # A cheap fixed-family pass brackets the candidate.  The full
            # 16x16 dynamic check is then used in a second, shorter bisection.
            for _ in range(15):
                mid = (lo + hi) / 2
                trial = raise_at(head, i, mid, p.delta)
                if feasible(trial, p, quick=True):
                    lo = mid
                else:
                    hi = mid
            fixed_hi, lo = lo, 0.0
            for _ in range(11):
                mid = (lo + fixed_hi) / 2
                trial = raise_at(head, i, mid, p.delta)
                if feasible(trial, p):
                    lo = mid
                else:
                    fixed_hi = mid
            if lo:
                head = raise_at(head, i, max(0.0, lo - 5e-8), p.delta)
    return head


def shell_volume(alpha, delta, count, beta):
    """Float copy of the exact inclusion-exclusion stratum volume."""
    if count == 0:
        return sum(((-1) ** h * comb(K, h) *
                    max(0.0, alpha - h * delta) ** K)
                   for h in range(floor(alpha / delta) + 1)) / factorial(K)
    gamma = beta - count * delta
    if gamma <= 0:
        return 0.0
    small = K - count
    ans = 0.0
    for h in range(max(0, floor(alpha / delta) - count) + 1):
        length = alpha - (count + h) * delta
        upper = min(gamma, length)
        if upper <= 0:
            continue
        radial = sum(((-1) ** j * comb(small, j) /
                      (count + j) * length ** (small - j) *
                      upper ** (count + j))
                     for j in range(small + 1))
        ans += ((-1) ** h * comb(small, h) * radial /
                (factorial(count - 1) * factorial(small)))
    return comb(K, count) * ans


def volume_rows(head, p):
    rows = []
    for count in active(head, p.delta):
        beta = 0.0 if count == 0 else head[count - 1]
        value = (shell_volume(p.alpha2, p.delta, count, beta) -
                 shell_volume(p.alpha1, p.delta, count, beta))
        rows.append((count, value))
    return rows


def main():
    # Stay strictly inside 3*x+delta < 3/80; this parameterizes the main
    # direct-HB face while leaving 3e-5 scalar slack, as at the baseline.
    for delta in (.00722, .008, .009, .010, .011, .012, .014, .016):
        x = (.03747 - delta) / 3
        p = Parameters(delta, x)
        print("parameter", delta, x, "base", feasible(BASE_SCHEDULE, p))
        head = optimize_schedule(p, rounds=1)
        if head is None:
            continue
        rows = volume_rows(head, p)
        print(" schedule", ",".join(f"{v:.9f}" for v in head))
        print(" active", active(head, delta)[-1], "mass", sum(v for _, v in rows),
              "count-mass", [(r, v) for r, v in rows if 5 <= r <= 13])


if __name__ == "__main__":
    main()
