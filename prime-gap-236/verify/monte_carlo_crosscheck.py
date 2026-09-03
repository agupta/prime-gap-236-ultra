#!/usr/bin/env python3
"""Independent Monte Carlo cross-check of the exact total-sum integrator.

Sampling is directly in the full simplices.  Membership and the one-coordinate
marginal are evaluated from Definition 1, without using the exact
inclusion--exclusion or polygon code.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from total_sum_search import TotalSumIntegrator  # noqa: E402


DELTA = 7 / 250
L = 521 / 2000
QCAP = 491 / 2000
B12 = 3 / 20
B3 = 17 / 100


def direct_membership(t: np.ndarray) -> np.ndarray:
    total = t.sum(axis=1)
    big = t > DELTA
    count = big.sum(axis=1)
    bigsum = (t * big).sum(axis=1)
    cap = np.where(count == 0, np.inf, np.where(count <= 2, B12, B3))
    return (total < L) & (bigsum <= cap)


def direct_marginal_length(common: np.ndarray) -> np.ndarray:
    u = common.sum(axis=1)
    big = common > DELTA
    r = big.sum(axis=1)
    y = (common * big).sum(axis=1)
    bsmall = np.where(r <= 2, B12, B3)
    bnext = np.where(r + 1 <= 2, B12, B3)
    exists = (r == 0) | (y <= bsmall)
    support_cap = np.where(r == 0, B12, np.maximum(DELTA, bnext - y))
    return np.where(exists, np.maximum(0.0, np.minimum(L - u, support_cap)), 0.0)


def simplex_batch(rng: np.random.Generator, rows: int, coordinates: int, cap: float) -> np.ndarray:
    e = rng.exponential(size=(rows, coordinates + 1))
    return cap * e[:, :coordinates] / e.sum(axis=1, keepdims=True)


def mean_se(total: float, total_sq: float, n: int) -> tuple[float, float]:
    mean = total / n
    var = max(0.0, total_sq / n - mean * mean)
    return mean, math.sqrt(var / n)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--samples", type=int, default=1_000_000)
    ap.add_argument("--batch", type=int, default=20_000)
    ap.add_argument("--seed", type=int, default=236)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    si = si2 = sj = sj2 = 0.0
    done = 0
    while done < args.samples:
        n = min(args.batch, args.samples - done)
        t = simplex_batch(rng, n, args.k, L)
        v = direct_membership(t).astype(float)
        si += float(v.sum())
        si2 += float((v * v).sum())

        c = simplex_batch(rng, n, args.k - 1, QCAP)
        h2 = direct_marginal_length(c) ** 2
        sj += float(h2.sum())
        sj2 += float((h2 * h2).sum())
        done += n

    mi, sei = mean_se(si, si2, args.samples)
    mj, sej = mean_se(sj, sj2, args.samples)
    vi = L ** args.k / math.factorial(args.k)
    vj = QCAP ** (args.k - 1) / math.factorial(args.k - 1)
    i_est, i_se = vi * mi, vi * sei
    j_est, j_se = vj * mj, vj * sej

    exact = TotalSumIntegrator(args.k)
    i_exact = float(exact.i_moment(0))
    j_exact = float(exact.j_entry(0, 0))
    iz = "n/a (zero sampled variance)" if i_se == 0 else f"{(i_est-i_exact)/i_se:.3f}"
    jz = "n/a (zero sampled variance)" if j_se == 0 else f"{(j_est-j_exact)/j_se:.3f}"
    print(f"samples={args.samples} seed={args.seed}")
    print(f"I_est={i_est:.17e} se={i_se:.3e} exact={i_exact:.17e} z={iz}")
    print(f"J_est={j_est:.17e} se={j_se:.3e} exact={j_exact:.17e} z={jz}")
    print(f"quotient_est={args.k*j_est/i_est:.12f} exact={args.k*j_exact/i_exact:.12f}")


if __name__ == "__main__":
    main()
