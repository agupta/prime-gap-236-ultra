#!/usr/bin/env python3
"""Heuristic active-25 cap probe for the exact uncapped D18 two-band pencil.

This is a search instrument, never a certificate.  It samples the uniform
simplex (or a caller-selected Dirichlet proposal), estimates only the change
caused by the analytically audited nonuniform cap, and adds that change to the
exact uncapped 2-by-2 matrix.  The independent uncapped Monte Carlo estimates
are serialized as calibration diagnostics.

The audited exact path does not import this file.  A favorable result merely
prioritizes an exact capped contraction.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from math import comb, factorial
from pathlib import Path
import sys
import time

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
BASE_PATH = REPO / "scripts/heuristic_capped_piecewise_probe.py"
VECTOR = REPO / (
    "agents/exact-integrator/results/"
    "aquarter_fullsimplex_k48_B18_refined_exact.json")
UNCAPPED = REPO / (
    "results/wide_c722_B18_piecewise_cinner1_couter_natural_exact.json")
ANALYTIC = REPO / (
    "agents/audit/results/"
    "wide_c722_nonuniform_active25_tail_analytic_audit.json")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


base = load_module("heuristic_capped_piecewise_probe_base", BASE_PATH)

K = 48
DEGREE = 18
ALPHA1 = Q(103, 400)
ALPHA2 = Q(3211, 12000)
ETA1 = Q(97, 400)
ETA2 = Q(3031, 12000)
DELTA = Q(361, 50000)
C_OUT = ALPHA1 / ALPHA2
SCHEDULE = (
    Q(597, 5000), Q(633, 5000), Q(669, 5000), Q(141, 1000),
    Q(737, 5000), Q(773, 5000), Q(1553, 10000), Q(809, 5000),
    Q(81, 500), Q(3329, 20000), Q(169, 1000), Q(339, 2000),
    Q(859, 5000), Q(1737, 10000), Q(219, 1250), Q(881, 5000),
    Q(441, 2500), Q(887, 5000), Q(891, 5000), Q(179, 1000),
    Q(449, 2500), Q(1801, 10000), Q(903, 5000), Q(1811, 10000),
    Q(363, 2000), Q(363, 2000),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schedule_q(r: int) -> Q:
    if r <= 0:
        raise ValueError("schedule is only defined for a positive count")
    return SCHEDULE[min(r, len(SCHEDULE)) - 1]


def residual_coefficients(basis, vector, alpha, dilation=Q(1)):
    if dilation * alpha != ALPHA1:
        raise ValueError("residual center does not match dilation")
    answer = defaultdict(Q)
    for theta, (a, lam) in zip(vector, basis):
        for c in range(a + 1):
            answer[(c, lam)] += (theta * comb(a, c) *
                                 (1 - ALPHA1) ** (a - c) *
                                 dilation ** (c + sum(lam)))
    return {key: value for key, value in answer.items() if value}


def coefficient_arrays(coefficients, partitions):
    index = {p: i for i, p in enumerate(partitions)}
    exponents = tuple(range(0, DEGREE + 1, 2))
    eindex = {e: i for i, e in enumerate(exponents)}
    point = np.zeros((len(partitions), DEGREE + 1), dtype=np.longdouble)
    marginal = np.zeros(
        (len(partitions), DEGREE + 1, len(exponents)),
        dtype=np.longdouble)
    for (c, lam), theta in coefficients.items():
        value = base.ld(theta)
        point[index[lam], c] += value
        marginal[index[lam], c, eindex[0]] += value
        for exponent in set(lam):
            rest = list(lam)
            rest.remove(exponent)
            marginal[index[tuple(rest)], c, eindex[exponent]] += value
    return point, marginal, exponents


def interval_integral(qtensor, residual, lower, upper, exponents,
                      nodes, weights):
    lower = np.asarray(lower, dtype=np.longdouble)
    upper = np.asarray(upper, dtype=np.longdouble)
    half = np.maximum((upper - lower) / 2, np.longdouble(0))
    middle = (upper + lower) / 2
    answer = np.zeros(len(residual), dtype=np.longdouble)
    for node, weight in zip(nodes, weights):
        t = middle + half * node
        rr = residual - t
        rp = np.stack([rr ** c for c in range(DEGREE + 1)], axis=1)
        tp = np.stack([t ** e for e in exponents], axis=1)
        value = np.einsum("nce,nc,ne->n", qtensor, rp, tp,
                          optimize=True)
        answer += half * weight * value
    return answer


def marginal_on_support(qtensor, common_sum, large_count, large_sum,
                        alpha, residual_center, exponents, nodes, weights,
                        capped):
    n = len(common_sum)
    total_upper = np.longdouble(alpha) - common_sum
    residual = np.longdouble(residual_center) - common_sum
    if not capped:
        return interval_integral(
            qtensor, residual, np.zeros(n, dtype=np.longdouble),
            np.maximum(total_upper, np.longdouble(0)), exponents,
            nodes, weights)

    beta_r = np.array([
        np.longdouble(np.inf) if int(r) == 0 else base.ld(schedule_q(int(r)))
        for r in large_count], dtype=np.longdouble)
    beta_next = np.array([base.ld(schedule_q(int(r) + 1))
                          for r in large_count], dtype=np.longdouble)
    common_ok = (large_count == 0) | (large_sum <= beta_r)
    small_upper = np.where(
        common_ok, np.minimum(np.longdouble(DELTA), total_upper),
        np.longdouble(0))
    small_upper = np.maximum(small_upper, np.longdouble(0))
    large_upper = np.minimum(total_upper, beta_next - large_sum)
    large_upper = np.maximum(large_upper, np.longdouble(DELTA))
    small = interval_integral(
        qtensor, residual, np.zeros(n, dtype=np.longdouble), small_upper,
        exponents, nodes, weights)
    large = interval_integral(
        qtensor, residual,
        np.full(n, np.longdouble(DELTA), dtype=np.longdouble),
        large_upper, exponents, nodes, weights)
    return small + large


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=int, default=20)
    parser.add_argument("--samples-per-batch", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=23601825)
    parser.add_argument("--physical-shape", type=float, default=1.0)
    parser.add_argument("--slack-shape", type=float, default=1.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.batches < 2 or args.samples_per_batch < 10:
        parser.error("need at least two batches and ten samples per batch")
    if args.physical_shape <= 0 or args.slack_shape <= 0:
        parser.error("Dirichlet shapes must be positive")

    source = base.strict_load(VECTOR)
    exact = base.strict_load(UNCAPPED)
    analytic = base.strict_load(ANALYTIC)
    if (source.get("k"), source.get("degree")) != (K, DEGREE):
        raise ValueError("unexpected D18 source vector")
    if (exact.get("certificate_sha256") != sha256(VECTOR) or
            exact.get("parameters", {}).get("outer_c") != str(C_OUT)):
        raise ValueError("uncapped D18 provenance mismatch")
    expected_schedule = [str(x) for x in SCHEDULE]
    if (analytic.get("status") != "AUDIT PASS" or
            analytic.get("schedule_id") !=
            "nonuniform-outer-active25-tail-v4" or
            analytic.get("parameters", {}).get(
                "outer_schedule_through_first_empty") != expected_schedule):
        raise ValueError("active25 analytic support mismatch")

    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in source["basis"])
    vector = tuple(Q(x) for x in source["rational_vector"])
    inner_coeff = residual_coefficients(basis, vector, ALPHA1, Q(1))
    outer_coeff = residual_coefficients(basis, vector, ALPHA2, C_OUT)
    required = {lam for _, lam in inner_coeff}
    for _, lam in tuple(inner_coeff) + tuple(outer_coeff):
        for exponent in set(lam):
            rest = list(lam)
            rest.remove(exponent)
            required.add(tuple(rest))
    orbit = base.VectorizedOrbitEvaluator(sorted(required))
    inner_point, inner_marginal, exponents = coefficient_arrays(
        inner_coeff, orbit.partitions)
    outer_point, outer_marginal, _ = coefficient_arrays(
        outer_coeff, orbit.partitions)
    # Ten-point Gauss--Legendre exactly integrates a degree-18 fiber
    # polynomial in exact arithmetic (floating evaluation remains heuristic).
    nodes, weights = np.polynomial.legendre.leggauss(10)
    nodes = nodes.astype(np.longdouble)
    weights = weights.astype(np.longdouble)

    imat = [[Q(x) for x in row] for row in exact["I_matrix"]]
    bmat = [[Q(x) for x in row] for row in exact["kJ_matrix"]]
    a00, a11_full = base.ld(imat[0][0]), base.ld(imat[1][1])
    b00, b01_full, b11_full = (
        base.ld(bmat[0][0]), base.ld(bmat[0][1]), base.ld(bmat[1][1]))
    vi = base.ld(ALPHA2) ** K / base.ld(factorial(K))
    vj = base.ld(ETA2) ** (K - 1) / base.ld(factorial(K - 1))
    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    rows = []
    for batch in range(args.batches):
        ni = args.samples_per_batch
        points, iw = base.simplex_dirichlet(
            rng, ni, K, base.ld(ALPHA2), args.physical_shape,
            args.slack_shape)
        values = orbit.evaluate(points)
        total = points.sum(axis=1)
        residual = base.ld(ALPHA2) - total
        radial = np.stack([residual ** c for c in range(DEGREE + 1)], axis=1)
        g = np.einsum("np,pc,nc->n", values, outer_point, radial,
                      optimize=True)
        large = points > base.ld(DELTA)
        count = large.sum(axis=1)
        large_sum = np.where(large, points, np.longdouble(0)).sum(axis=1)
        beta = np.array([
            np.longdouble(np.inf) if int(r) == 0 else base.ld(schedule_q(int(r)))
            for r in count])
        shell = total > base.ld(ALPHA1)
        cap = shell & ((count == 0) | (large_sum <= beta))
        i_delta = vi * np.mean(
            iw * (cap.astype(np.int8) - shell.astype(np.int8)) * g * g,
            dtype=np.longdouble)
        i_direct = vi * np.mean(iw * cap * g * g, dtype=np.longdouble)
        i_full_mc = vi * np.mean(iw * shell * g * g, dtype=np.longdouble)

        common, jw = base.simplex_dirichlet(
            rng, ni, K - 1, base.ld(ETA2), args.physical_shape,
            args.slack_shape)
        cvalues = orbit.evaluate(common)
        csum = common.sum(axis=1)
        clarge = common > base.ld(DELTA)
        cr = clarge.sum(axis=1)
        clsum = np.where(clarge, common, np.longdouble(0)).sum(axis=1)
        qi = np.einsum("np,pce->nce", cvalues, inner_marginal,
                       optimize=True)
        qo = np.einsum("np,pce->nce", cvalues, outer_marginal,
                       optimize=True)
        min_ = marginal_on_support(
            qi, csum, cr, clsum, ALPHA1, ALPHA1, exponents,
            nodes, weights, False)
        mhi_cap = marginal_on_support(
            qo, csum, cr, clsum, ALPHA2, ALPHA2, exponents,
            nodes, weights, True)
        mlo_cap = marginal_on_support(
            qo, csum, cr, clsum, ALPHA1, ALPHA2, exponents,
            nodes, weights, True)
        mout_cap = mhi_cap - mlo_cap
        mhi_full = marginal_on_support(
            qo, csum, cr, clsum, ALPHA2, ALPHA2, exponents,
            nodes, weights, False)
        mlo_full = marginal_on_support(
            qo, csum, cr, clsum, ALPHA1, ALPHA2, exponents,
            nodes, weights, False)
        mout_full = mhi_full - mlo_full
        factor = base.ld(K) * vj
        b01_delta = factor * np.mean(
            jw * min_ * (mout_cap - mout_full), dtype=np.longdouble)
        b11_delta = factor * np.mean(
            jw * (mout_cap * mout_cap - mout_full * mout_full),
            dtype=np.longdouble)
        q = base.largest_generalized(
            a00, a11_full + i_delta, b00,
            b01_full + b01_delta, b11_full + b11_delta)
        row = {
            "batch": batch, "a11_delta": str(i_delta),
            "a11_direct": str(i_direct), "a11_full_mc": str(i_full_mc),
            "b01_delta": str(b01_delta), "b11_delta": str(b11_delta),
            "b01_full_mc": str(factor * np.mean(
                jw * min_ * mout_full, dtype=np.longdouble)),
            "b11_full_mc": str(factor * np.mean(
                jw * mout_full * mout_full, dtype=np.longdouble)),
            "b00_mc": str(factor * np.mean(
                jw * (csum <= base.ld(ETA1)) * min_ * min_,
                dtype=np.longdouble)),
            "i_weight_ess": str(iw.sum() ** 2 / (iw * iw).sum()),
            "j_weight_ess": str(jw.sum() ** 2 / (jw * jw).sum()),
            "q_from_batch_control_variate": str(q),
        }
        rows.append(row)
        print(f"batch {batch + 1}/{args.batches} q={q}", flush=True)

    def mean_field(name):
        return sum(np.longdouble(row[name]) for row in rows) / len(rows)

    da, dc, dd = (mean_field(x) for x in
                  ("a11_delta", "b01_delta", "b11_delta"))
    q = base.largest_generalized(
        a00, a11_full + da, b00, b01_full + dc, b11_full + dd)
    batch_q = np.array([
        np.longdouble(row["q_from_batch_control_variate"]) for row in rows])
    q_se = batch_q.std(ddof=1) / np.sqrt(np.longdouble(len(rows)))
    result = {
        "status": "HEURISTIC ONLY", "rigorous": False,
        "theorem_ready": False,
        "never_implies": ["an exact quotient", "Proposition 1", "H1<=236"],
        "parameters": {
            "k": K, "degree": DEGREE, "batches": args.batches,
            "samples_per_batch": args.samples_per_batch, "seed": args.seed,
            "inner_c": "1", "outer_c": str(C_OUT),
            "physical_shape": args.physical_shape,
            "slack_shape": args.slack_shape,
            "arithmetic": str(np.dtype(np.longdouble)),
            "outer_schedule": [str(x) for x in SCHEDULE],
        },
        "source_hashes": {
            str(BASE_PATH.relative_to(REPO)): sha256(BASE_PATH),
            str(VECTOR.relative_to(REPO)): sha256(VECTOR),
            str(UNCAPPED.relative_to(REPO)): sha256(UNCAPPED),
            str(ANALYTIC.relative_to(REPO)): sha256(ANALYTIC),
        },
        "script_sha256_before_output": sha256(FILE),
        "control_variate_matrix": {
            "A00_exact": str(a00), "A11_estimate": str(a11_full + da),
            "B00_exact": str(b00), "B01_estimate": str(b01_full + dc),
            "B11_estimate": str(b11_full + dd),
        },
        "estimated_largest_quotient": str(q),
        "batch_quotient_standard_error": str(q_se),
        "calibration_means": {name: str(mean_field(name)) for name in
                              ("a11_direct", "a11_full_mc", "b01_full_mc",
                               "b11_full_mc", "b00_mc")},
        "exact_uncapped_calibration_targets": {
            "A11": str(a11_full), "B01": str(b01_full),
            "B11": str(b11_full), "B00": str(b00),
        },
        "wall_seconds": time.monotonic() - started,
        "batches": rows,
    }
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as handle:
            handle.write(payload)
        print(f"sha256 {hashlib.sha256(payload.encode()).hexdigest()}")
    print(json.dumps({
        "status": result["status"],
        "estimated_largest_quotient": result["estimated_largest_quotient"],
        "batch_quotient_standard_error": result[
            "batch_quotient_standard_error"],
        "calibration_means": result["calibration_means"],
        "wall_seconds": result["wall_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
