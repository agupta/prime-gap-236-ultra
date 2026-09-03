#!/usr/bin/env python3
"""Fast common-family Monte Carlo proxy for support parameter scans.

For each integer q, use F(t)=(1-sum(t)/R)^q on the supplied support.  I and
J are estimated by uniform-simplex sampling, with the t integral in J done
analytically.  The estimator is heuristic, but uses no unstable high-order
Irwin--Hall subtraction and is suitable for locating a delta turnover.
"""

from __future__ import annotations

import argparse
import math

import numpy as np


def simplex_batch(rng, rows: int, dimension: int):
    e = rng.exponential(1.0, size=(rows, dimension + 1))
    return e[:, :dimension] / e.sum(axis=1)[:, None]


def bound_for_count(count, b1, b2, b):
    return np.where(count == 1, b1, np.where(count == 2, b2, b))


def estimate(args, seed):
    rng = np.random.default_rng(seed)
    k, d = args.k, args.delta
    R, V = args.A + args.epsilon, args.A - args.epsilon
    powers = np.array([int(v) for v in args.powers.split(",")], dtype=int)
    isum = np.zeros(len(powers))
    jsum = np.zeros(len(powers))
    iaccept = jbase_accept = 0
    done = 0
    while done < args.samples:
        take = min(args.batch, args.samples - done)
        # Denominator: uniform on the full R-simplex.
        u = R * simplex_batch(rng, take, k)
        s = u.sum(axis=1)
        large = u > d
        counts = large.sum(axis=1)
        lsum = (u * large).sum(axis=1)
        caps = bound_for_count(counts, args.b1, args.b2, args.b)
        accept = (counts == 0) | (lsum <= caps)
        slack = np.maximum(0.0, 1 - s / R)
        for z, q in enumerate(powers):
            isum[z] += np.sum(accept * slack ** (2 * q))
        iaccept += int(accept.sum())

        # Numerator base: uniform on the V-simplex in k-1 coordinates.
        x = V * simplex_batch(rng, take, k - 1)
        sx = x.sum(axis=1)
        large = x > d
        counts = large.sum(axis=1)
        lsum = (x * large).sum(axis=1)
        room = R - sx
        caps = bound_for_count(counts, args.b1, args.b2, args.b)
        small_ok = (counts == 0) | (lsum <= caps)
        small_hi = np.where(small_ok, np.minimum(d, room), 0.0)
        next_caps = bound_for_count(counts + 1, args.b1, args.b2, args.b)
        large_hi = np.minimum(room, next_caps - lsum)
        large_hi = np.maximum(large_hi, d)
        jbase_accept += int(np.count_nonzero((small_hi > 0) | (large_hi > d)))
        for z, q in enumerate(powers):
            qp = q + 1
            base = np.maximum(0.0, 1 - sx / R)
            at_small = np.maximum(0.0, 1 - (sx + small_hi) / R)
            hsmall = R * (base**qp - at_small**qp) / qp
            at_delta = np.maximum(0.0, 1 - (sx + d) / R)
            at_large = np.maximum(0.0, 1 - (sx + large_hi) / R)
            hlarge = R * (at_delta**qp - at_large**qp) / qp
            Hval = hsmall + hlarge
            jsum[z] += np.sum(Hval * Hval)
        done += take

    imean, jmean = isum / args.samples, jsum / args.samples
    factor = k * k * V ** (k - 1) / R**k
    quotients = factor * jmean / imean
    return powers, quotients, iaccept / args.samples, jbase_accept / args.samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--delta", type=float, required=True)
    ap.add_argument("--A", type=float, required=True)
    ap.add_argument("--epsilon", type=float, default=0.005)
    ap.add_argument("--b1", type=float, required=True)
    ap.add_argument("--b2", type=float, required=True)
    ap.add_argument("--b", type=float, required=True)
    ap.add_argument("--powers", default="0,2,4,6,8,10,12,16,20")
    ap.add_argument("--samples", type=int, default=1000000)
    ap.add_argument("--batch", type=int, default=50000)
    ap.add_argument("--replicates", type=int, default=2)
    ap.add_argument("--seed", type=int, default=236)
    args = ap.parse_args()
    print("HEURISTIC FIXED-F MONTE CARLO")
    for rep in range(args.replicates):
        powers, quotients, ia, ja = estimate(args, args.seed + 1009 * rep)
        best = int(np.argmax(quotients))
        print("rep", rep, "I/J support acceptance", ia, ja)
        print("powers", powers.tolist())
        print("quotients", [float(v) for v in quotients])
        print("best", int(powers[best]), float(quotients[best]))


if __name__ == "__main__":
    main()
