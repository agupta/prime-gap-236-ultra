#!/usr/bin/env python3
"""Reconstruct a fixed polynomial's cut-support quotient without a matrix.

The input is only a list of orbit labels and rational coefficients.  We first
combine the polynomial before integration.  For J, the four conditional
integration branches are combined into piecewise bivariate polynomials before
the outer orbit moments are evaluated.  This is intended to make a dense
high-degree eigenvector cheaper than constructing every pairwise matrix entry.

All arithmetic is ``fractions.Fraction``.  The implementation deliberately
imports the low-level recurrences from ``exact_integrator.py``; it does not read
or trust a serialized matrix.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from fractions import Fraction as Q
from math import factorial
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator", "src"))
sys.path.insert(0, SRC)

import exact_integrator as ei  # noqa: E402


def poly_addto(dst, src, factor=Q(1)):
    for mon, value in src.items():
        dst[mon] += factor * value
        if dst[mon] == 0:
            del dst[mon]


def _i_group_task(task):
    support, nu, terms = task
    value = sum(coefficient * support.orbit_support_moment(nu, power)
                for power, coefficient in terms)
    # Worker processes persist.  Keeping unbounded recurrence caches for all
    # 1,000+ orbit types causes swap thrashing; reuse is needed within one
    # orbit group, not between unrelated groups.
    support._piece_residual.cache_clear()
    support.canonical_support_residual.cache_clear()
    support.canonical_support_moment.cache_clear()
    ei._large_shift_dp.cache_clear()
    ei._small_box_dp.cache_clear()
    ei._selected_exponent_splits.cache_clear()
    return value


def fixed_i(support, labels, coeff, workers=1, progress=False):
    combined = defaultdict(Q)
    for i, (a, lam) in enumerate(labels):
        for j in range(i + 1):
            b, mu = labels[j]
            factor = coeff[i] * coeff[j] * (2 if i != j else 1)
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                combined[(nu, a + b)] += factor * multiplicity
    combined = {key: value for key, value in combined.items() if value}
    grouped = defaultdict(list)
    for (nu, power), value in combined.items():
        grouped[nu].append((power, value))
    tasks = [(support, nu, terms) for nu, terms in grouped.items()]
    if workers > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            values = []
            for idx, value in enumerate(pool.map(_i_group_task, tasks, chunksize=1), 1):
                values.append(value)
                if progress and (idx % 10 == 0 or idx == len(tasks)):
                    print(f"I progress orbit={idx}/{len(tasks)}", flush=True)
        ans = sum(values, Q(0))
    else:
        ans = Q(0)
        for idx, task in enumerate(tasks, 1):
            ans += _i_group_task(task)
            if progress and (idx % 10 == 0 or idx == len(tasks)):
                print(f"I progress orbit={idx}/{len(tasks)}", flush=True)
    return ans, len(combined)


def outer_orbit_poly(support, nu, r, h, br1, br2, integrand):
    """Integral of P_nu(u)*integrand(z,w) on one branch intersection."""
    ku = support.k - 1
    s = ku - r
    outer = support.eta - (r + h) * support.delta
    if outer <= 0:
        return Q(0)
    c1 = support._branch_constraints(r, h, br1)
    c2 = support._branch_constraints(r, h, br2)
    if c1 is None or c2 is None:
        return Q(0)
    if r and s:
        domain = ei.polygon(outer, c1 + c2)
        if not domain:
            return Q(0)
        interval = None
    elif r:
        i1 = support._branch_z_interval(r, h, br1)
        i2 = support._branch_z_interval(r, h, br2)
        if i1 is None or i2 is None:
            return Q(0)
        interval = (max(i1[0], i2[0]), min(i1[1], i2[1]))
        if interval[1] <= interval[0]:
            return Q(0)
        domain = None
    else:
        i1 = support._branch_interval(r, h, br1)
        i2 = support._branch_interval(r, h, br2)
        if i1 is None or i2 is None:
            return Q(0)
        interval = (max(i1[0], i2[0]), min(i1[1], i2[1]))
        if interval[1] <= interval[0]:
            return Q(0)
        domain = None

    ans = Q(0)
    max_h = int(support.eta // support.delta) - r
    for mult, large, small in ei._selected_exponent_splits(ku, nu, r):
        ld = ei._large_shift_dp(large, support.delta)
        sd = ei._small_box_dp(small, support.delta, max_h)
        for qdeg, lc0 in ld.items():
            lc = lc0 / factorial(qdeg + r - 1) if r else lc0
            zpow = qdeg + r - 1 if r else 0
            for (hh, pdeg), sc0 in sd.items():
                if hh != h:
                    continue
                sc = sc0 / factorial(pdeg + s - 1) if s else sc0
                wpow = pdeg + s - 1 if s else 0
                if r and s:
                    val = ei.integrate_poly_polygon(integrand, domain, zpow, wpow)
                elif r:
                    val = ei._integrate_poly_z_interval(
                        integrand, interval[0], interval[1], zpow)
                else:
                    val = ei._integrate_poly_interval(
                        integrand, interval[0], interval[1], wpow)
                ans += mult * lc * sc * val
    # ``_selected_exponent_splits`` integrates one canonical exponent vector.
    # The caller's ``nu`` denotes the full monomial orbit P_nu.
    return ei.orbit_size(ku, nu) * ans


def _outer_group_task(task):
    support, nu, r, h, pieces = task
    value = sum(outer_orbit_poly(support, nu, r, h, br1, br2, integrand)
                for br1, br2, integrand in pieces)
    # All branch pairs for this (r,h,nu) share the costly radial DPs and are
    # intentionally one task.  Clear only after exploiting that reuse.
    ei._large_shift_dp.cache_clear()
    ei._small_box_dp.cache_clear()
    ei._selected_exponent_splits.cache_clear()
    ei.polygon.cache_clear()
    ei.polygon_monomial.cache_clear()
    return value


def fixed_j(support, labels, coeff, progress=False, workers=1):
    # Coefficient of t^e (1-U-t)^a P_lr(u) before the t integration.
    components = defaultdict(Q)
    for value, (a, lam) in zip(coeff, labels):
        for e, lr in support.split_at_distinguished(lam, support.k):
            components[(lr, e, a)] += value
    components = {key: value for key, value in components.items() if value}
    lrs = sorted({lr for lr, _, _ in components})
    by_lr = {lr: [(e, a, value) for (x, e, a), value in components.items() if x == lr]
             for lr in lrs}
    branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
    answer = Q(0)
    outer_calls = 0
    max_r = min(support.k - 1, support.max_large())

    pool = (concurrent.futures.ProcessPoolExecutor(max_workers=workers)
            if workers > 1 else None)
    try:
      for r in range(max_r + 1):
        max_h = int(support.eta // support.delta) - r
        for h in range(max_h + 1):
            # H_br = sum_lr P_lr(u) * polynomial_lr(z,w).
            H = {}
            for br in branches:
                block = {}
                if support._branch_constraints(r, h, br) is None:
                    H[br] = block
                    continue
                for lr in lrs:
                    p = defaultdict(Q)
                    for e, a, value in by_lr[lr]:
                        poly_addto(p, dict(support._marginal_poly(r, h, br, e, a)), value)
                    if p:
                        block[lr] = dict(p)
                H[br] = block

            tasks = []
            for ib, br1 in enumerate(branches):
                for br2 in branches[ib:]:
                    if not H[br1] or not H[br2]:
                        continue
                    # These alternatives split at a common affine boundary;
                    # their domains have measure-zero intersection.
                    if {br1, br2} in ({"Sdelta", "Stotal"},
                                      {"Ltotal", "Lbig"}):
                        continue
                    # Combine the fixed polynomial *before* outer integration.
                    combined = {}
                    for lr, p in H[br1].items():
                        for mr, q in H[br2].items():
                            pq = ei._poly_mul(p, q)
                            for nu, multiplicity in ei.multiply_monomial_orbits(lr, mr):
                                if nu not in combined:
                                    combined[nu] = defaultdict(Q)
                                factor = multiplicity * (2 if br1 != br2 else 1)
                                poly_addto(combined[nu], pq, Q(factor))
                    for nu, p in combined.items():
                        if p:
                            tasks.append((support, nu, r, h, br1, br2, dict(p)))
            grouped_tasks = defaultdict(list)
            for _, nu, rr, hh, br1, br2, integrand in tasks:
                grouped_tasks[nu].append((br1, br2, integrand))
            compact = [(support, nu, r, h, pieces)
                       for nu, pieces in grouped_tasks.items()]
            values = (pool.map(_outer_group_task, compact, chunksize=1)
                      if pool is not None else map(_outer_group_task, compact))
            answer += sum(values, Q(0))
            outer_calls += len(tasks)
            # H contains plain dict copies, so the main process need not retain
            # every marginal polynomial from earlier support strata.
            support._marginal_poly.cache_clear()
            support._branch_constraints.cache_clear()
            if progress:
                print(f"progress r={r} h={h} outer_calls={outer_calls}", flush=True)
    finally:
        if pool is not None:
            pool.shutdown()
    return answer, len(components), outer_calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("--alpha", default="163/625")
    ap.add_argument("--delta", default="1/50")
    ap.add_argument("--eta", default="627/2500")
    ap.add_argument("--beta1", default="3/20")
    ap.add_argument("--beta2", default="3/20")
    ap.add_argument("--beta3plus", default="17/100")
    ap.add_argument("--output")
    ap.add_argument("--progress", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()

    raw = json.load(open(args.input_json, encoding="utf-8"))
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    coeff = [Q(x) for x in raw["rational_vector"]]
    if len(labels) != len(coeff):
        raise SystemExit("basis/vector length mismatch")
    support = ei.OneStratumSupport(int(raw["k"]), Q(args.alpha), Q(args.delta),
                                   Q(args.eta), Q(args.beta1), Q(args.beta2),
                                   Q(args.beta3plus))
    start = time.perf_counter()
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    den, iterms = fixed_i(support, labels, coeff, args.workers, args.progress)
    after_i = time.perf_counter()
    j, components, outer_calls = fixed_j(
        support, labels, coeff, args.progress, args.workers)
    num = support.k * j
    elapsed = time.perf_counter() - start
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = {
        "status": "exact-fixed-vector-reconstruction",
        "input_json": args.input_json,
        "k": support.k,
        "parameters": {"alpha": str(support.alpha), "delta": str(support.delta),
                       "eta": str(support.eta), "beta1": str(support.beta1),
                       "beta2": str(support.beta2), "beta3plus": str(support.beta3plus)},
        "basis_dimension": len(labels),
        "i_combined_terms": iterms,
        "marginal_components": components,
        "outer_integral_calls": outer_calls,
        "i_seconds": after_i - start,
        "total_seconds": elapsed,
        "workers": args.workers,
        "script_sha256": source_hash,
        "denominator_positive": den > 0,
        "exact_margin_positive": num - den > 0,
        "exact_quotient": str(num / den),
        "exact_quotient_decimal": float(num / den),
        "exact_margin": str(num - den),
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
