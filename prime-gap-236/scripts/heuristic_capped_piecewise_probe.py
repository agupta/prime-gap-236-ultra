#!/usr/bin/env python3
"""Heuristic control-variate probe for the capped piecewise D16 candidate.

This program is deliberately segregated from the exact certificate path.  It
uses pseudorandom uniform-simplex samples and floating-point arithmetic to
estimate how much the independently audited volume-ramp cap changes the exact
uncapped two-band pencil.  The known uncapped matrix is used as a control
variate.  Every output is labelled non-rigorous and can only authorize (or
deprioritize) a subsequent exact contraction.

The polynomial is evaluated in residual coordinates ``alpha-sum(t)``.  Direct
evaluation in the published ``1-sum(t)`` coordinates loses many digits for the
D16 vector and is intentionally not used.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import json
from math import comb, factorial, lgamma
from pathlib import Path
import sys
import time

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
CODE = REPO / "agents/structural-basis/code"
sys.path.insert(0, str(CODE))

from importance_point_eval import MonomialSymmetricPointEvaluator  # noqa: E402


K = 48
ALPHA1 = Q(103, 400)
ALPHA2 = Q(3211, 12000)
ETA1 = Q(97, 400)
ETA2 = Q(3031, 12000)
DELTA = Q(361, 50000)
C_OUT = ALPHA1 / ALPHA2
VECTOR = REPO / "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"
UNCAPPED = REPO / "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ld(value) -> np.longdouble:
    value = Q(value)
    return np.longdouble(str(value.numerator)) / np.longdouble(
        str(value.denominator))


def strict_load(path: Path):
    def reject(token):
        raise ValueError(f"non-exact JSON token {token}")

    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate key {key}")
            answer[key] = value
        return answer

    return json.loads(path.read_text(), object_pairs_hook=pairs,
                      parse_float=reject, parse_constant=reject)


def schedule_q(r: int) -> Q:
    if r <= 0:
        raise ValueError("schedule is only defined for a positive count")
    return min(Q(49, 625) + (r - 1) * DELTA, Q(1599, 10000))


def residual_coefficients(basis, vector, alpha, dilation=Q(1)):
    """Coefficients of F(dilation*t) about alpha-sum(t).

    Here dilation*alpha is the original polynomial's residual center ALPHA1.
    """
    if dilation * alpha != ALPHA1:
        raise ValueError("residual center does not match the dilation")
    answer = defaultdict(Q)
    for theta, (a, lam) in zip(vector, basis):
        for c in range(a + 1):
            answer[(c, lam)] += (theta * comb(a, c) *
                                 (1 - ALPHA1) ** (a - c) *
                                 dilation ** (c + sum(lam)))
    return {key: value for key, value in answer.items() if value}


class VectorizedOrbitEvaluator:
    def __init__(self, partitions):
        scalar = MonomialSymmetricPointEvaluator(partitions)
        self.partitions = scalar.partitions
        self.states = scalar.states
        self.index = scalar.index
        self.transitions = scalar.transitions
        self.descending = scalar.descending
        self.exponents = scalar.exponents
        self.zero_index = self.index[tuple(0 for _ in self.exponents)]

    def evaluate(self, points):
        points = np.asarray(points, dtype=np.longdouble)
        if points.ndim != 2:
            raise ValueError("points must be a matrix")
        values = np.zeros((len(points), len(self.states)),
                          dtype=np.longdouble)
        values[:, self.zero_index] = 1
        for coordinate in points.T:
            powers = {e: coordinate ** e for e in self.exponents}
            for source in self.descending:
                for target, exponent in self.transitions[source]:
                    values[:, target] += values[:, source] * powers[exponent]
        columns = [self.index[tuple(sum(1 for part in p if part == e)
                                    for e in self.exponents)]
                   for p in self.partitions]
        return values[:, columns]


def coefficient_arrays(coefficients, partitions):
    index = {p: i for i, p in enumerate(partitions)}
    exponents = (0, 2, 4, 6, 8, 10, 12, 14, 16)
    eindex = {e: i for i, e in enumerate(exponents)}
    point = np.zeros((len(partitions), 17), dtype=np.longdouble)
    marginal = np.zeros((len(partitions), 17, len(exponents)),
                        dtype=np.longdouble)
    for (c, lam), theta in coefficients.items():
        value = ld(theta)
        point[index[lam], c] += value
        marginal[index[lam], c, eindex[0]] += value
        for exponent in set(lam):
            rest = list(lam)
            rest.remove(exponent)
            marginal[index[tuple(rest)], c, eindex[exponent]] += value
    return point, marginal, exponents


def simplex_dirichlet(rng, count, dimension, upper, physical_shape,
                      slack_shape):
    """Return proposal points and p_uniform/p_proposal weights."""
    parameters = np.array([physical_shape] * dimension + [slack_shape],
                          dtype=np.float64)
    gamma = rng.gamma(parameters, size=(count, dimension + 1))
    y = gamma / gamma.sum(axis=1)[:, None]
    log_constant = (lgamma(dimension + 1) +
                    dimension * lgamma(physical_shape) +
                    lgamma(slack_shape) -
                    lgamma(dimension * physical_shape + slack_shape))
    log_weight = (np.longdouble(log_constant) -
                  np.longdouble(physical_shape - 1) *
                  np.log(y[:, :dimension].astype(np.longdouble)).sum(axis=1) -
                  np.longdouble(slack_shape - 1) *
                  np.log(y[:, dimension].astype(np.longdouble)))
    weight = np.exp(log_weight)
    points = y[:, :dimension].astype(np.longdouble) * np.longdouble(upper)
    return points, weight


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
        rp = np.stack([rr ** c for c in range(17)], axis=1)
        tp = np.stack([t ** e for e in exponents], axis=1)
        value = np.einsum("nce,nc,ne->n", qtensor, rp, tp,
                          optimize=True)
        answer += half * weight * value
    return answer


def marginal_support_parts(qtensor, common_sum, large_count, large_sum,
                           alpha, residual_center, exponents, nodes, weights,
                           capped):
    n = len(common_sum)
    total_upper = np.longdouble(alpha) - common_sum
    if not capped:
        whole = interval_integral(
            qtensor, np.longdouble(residual_center) - common_sum,
            np.zeros(n, dtype=np.longdouble),
            np.maximum(total_upper, np.longdouble(0)), exponents,
            nodes, weights)
        return whole, np.zeros(n, dtype=np.longdouble)

    beta_r = np.array([
        np.longdouble(np.inf) if int(r) == 0 else ld(schedule_q(int(r)))
        for r in large_count], dtype=np.longdouble)
    beta_next = np.array([ld(schedule_q(int(r) + 1))
                          for r in large_count], dtype=np.longdouble)
    common_ok = (large_count == 0) | (large_sum <= beta_r)
    small_upper = np.where(
        common_ok,
        np.minimum(np.longdouble(DELTA), total_upper),
        np.longdouble(0))
    small_upper = np.maximum(small_upper, np.longdouble(0))
    large_upper = np.minimum(total_upper, beta_next - large_sum)
    large_upper = np.maximum(large_upper, np.longdouble(DELTA))
    residual = np.longdouble(residual_center) - common_sum
    small = interval_integral(
        qtensor, residual, np.zeros(n, dtype=np.longdouble), small_upper,
        exponents, nodes, weights)
    large = interval_integral(
        qtensor, residual,
        np.full(n, np.longdouble(DELTA), dtype=np.longdouble),
        large_upper, exponents, nodes, weights)
    return small, large


def marginal_on_support(qtensor, common_sum, large_count, large_sum,
                        alpha, residual_center, exponents, nodes, weights,
                        capped):
    small, large = marginal_support_parts(
        qtensor, common_sum, large_count, large_sum, alpha,
        residual_center, exponents, nodes, weights, capped)
    return small + large


def largest_generalized(a00, a11, b00, b01, b11):
    if a00 <= 0 or a11 <= 0:
        return np.longdouble("nan")
    x = b00 / a00
    z = b11 / a11
    y = b01 / np.sqrt(a00 * a11)
    return (x + z + np.sqrt((x - z) ** 2 + 4 * y ** 2)) / 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=int, default=20)
    parser.add_argument("--samples-per-batch", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=236048)
    parser.add_argument("--physical-shape", type=float, default=1.0)
    parser.add_argument("--slack-shape", type=float, default=1.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.batches < 2 or args.samples_per_batch < 10:
        parser.error("need at least two batches and ten samples per batch")
    if args.physical_shape <= 0 or args.slack_shape <= 0:
        parser.error("Dirichlet shapes must be positive")

    source = strict_load(VECTOR)
    exact = strict_load(UNCAPPED)
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in source["basis"])
    vector = tuple(Q(x) for x in source["rational_vector"])
    if source.get("k") != K or source.get("degree") != 16:
        raise ValueError("unexpected source vector")
    inner_coeff = residual_coefficients(basis, vector, ALPHA1, Q(1))
    outer_coeff = residual_coefficients(basis, vector, ALPHA2, C_OUT)
    required = {lam for _, lam in inner_coeff}
    for _, lam in tuple(inner_coeff) + tuple(outer_coeff):
        for exponent in set(lam):
            rest = list(lam)
            rest.remove(exponent)
            required.add(tuple(rest))
    orbit = VectorizedOrbitEvaluator(sorted(required))
    inner_point, inner_marginal, exponents = coefficient_arrays(
        inner_coeff, orbit.partitions)
    outer_point, outer_marginal, _ = coefficient_arrays(
        outer_coeff, orbit.partitions)
    # Nine-point Gauss-Legendre is exact for every degree-at-most-16 fiber
    # polynomial before floating-point rounding.
    nodes, weights = np.polynomial.legendre.leggauss(9)
    nodes = nodes.astype(np.longdouble)
    weights = weights.astype(np.longdouble)

    imat = [[Q(x) for x in row] for row in exact["I_matrix"]]
    bmat = [[Q(x) for x in row] for row in exact["kJ_matrix"]]
    a00, a11_full = ld(imat[0][0]), ld(imat[1][1])
    b00, b01_full, b11_full = (ld(bmat[0][0]), ld(bmat[0][1]),
                                      ld(bmat[1][1]))
    vi = ld(ALPHA2) ** K / ld(factorial(K))
    vj = ld(ETA2) ** (K - 1) / ld(factorial(K - 1))
    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    rows = []
    for batch in range(args.batches):
        ni = args.samples_per_batch
        points, iw = simplex_dirichlet(
            rng, ni, K, ld(ALPHA2), args.physical_shape,
            args.slack_shape)
        values = orbit.evaluate(points)
        total = points.sum(axis=1)
        residual = ld(ALPHA2) - total
        radial = np.stack([residual ** c for c in range(17)], axis=1)
        g = np.einsum("np,pc,nc->n", values, outer_point, radial,
                      optimize=True)
        large = points > ld(DELTA)
        r = large.sum(axis=1)
        lsum = np.where(large, points, np.longdouble(0)).sum(axis=1)
        beta = np.array([np.longdouble(np.inf) if int(x) == 0
                         else ld(schedule_q(int(x))) for x in r])
        shell = total > ld(ALPHA1)
        cap = shell & ((r == 0) | (lsum <= beta))
        i_delta = vi * np.mean(iw *
                               (cap.astype(np.int8) - shell.astype(np.int8))
                               * g * g, dtype=np.longdouble)
        i_direct = vi * np.mean(iw * cap * g * g, dtype=np.longdouble)
        i_full_mc = vi * np.mean(iw * shell * g * g, dtype=np.longdouble)

        common, jw = simplex_dirichlet(
            rng, ni, K - 1, ld(ETA2), args.physical_shape,
            args.slack_shape)
        cvalues = orbit.evaluate(common)
        csum = common.sum(axis=1)
        clarge = common > ld(DELTA)
        cr = clarge.sum(axis=1)
        clsum = np.where(clarge, common, np.longdouble(0)).sum(axis=1)
        qi = np.einsum("np,pce->nce", cvalues, inner_marginal,
                       optimize=True)
        qo = np.einsum("np,pce->nce", cvalues, outer_marginal,
                       optimize=True)
        min_ = marginal_on_support(
            qi, csum, cr, clsum, ld(ALPHA1), ld(ALPHA1), exponents,
            nodes, weights, False)
        mhi_cap = marginal_on_support(
            qo, csum, cr, clsum, ld(ALPHA2), ld(ALPHA2), exponents,
            nodes, weights, True)
        mlo_cap = marginal_on_support(
            qo, csum, cr, clsum, ld(ALPHA1), ld(ALPHA2), exponents,
            nodes, weights, True)
        mout_cap = mhi_cap - mlo_cap
        mhi_full = marginal_on_support(
            qo, csum, cr, clsum, ld(ALPHA2), ld(ALPHA2), exponents,
            nodes, weights, False)
        mlo_full = marginal_on_support(
            qo, csum, cr, clsum, ld(ALPHA1), ld(ALPHA2), exponents,
            nodes, weights, False)
        mout_full = mhi_full - mlo_full
        factor = ld(K) * vj
        b01_delta = factor * np.mean(
            jw * min_ * (mout_cap - mout_full), dtype=np.longdouble)
        b11_delta = factor * np.mean(
            jw * (mout_cap * mout_cap - mout_full * mout_full),
            dtype=np.longdouble)
        a11 = a11_full + i_delta
        b01 = b01_full + b01_delta
        b11 = b11_full + b11_delta
        q = largest_generalized(a00, a11, b00, b01, b11)
        rows.append({
            "batch": batch,
            "a11_delta": str(i_delta), "a11_direct": str(i_direct),
            "a11_full_mc": str(i_full_mc),
            "b01_delta": str(b01_delta), "b11_delta": str(b11_delta),
            "b01_full_mc": str(factor * np.mean(
                jw * min_ * mout_full, dtype=np.longdouble)),
            "b11_full_mc": str(factor * np.mean(
                jw * mout_full * mout_full, dtype=np.longdouble)),
            "b00_mc": str(factor * np.mean(
                jw * (csum <= ld(ETA1)) * min_ * min_,
                dtype=np.longdouble)),
            "i_weight_ess": str(iw.sum() ** 2 / (iw * iw).sum()),
            "j_weight_ess": str(jw.sum() ** 2 / (jw * jw).sum()),
            "q_from_batch_control_variate": str(q),
        })
        print(f"batch {batch + 1}/{args.batches} q={q}", flush=True)

    def mean_field(name):
        return sum(np.longdouble(row[name]) for row in rows) / len(rows)

    da = mean_field("a11_delta")
    dc = mean_field("b01_delta")
    dd = mean_field("b11_delta")
    a11 = a11_full + da
    b01 = b01_full + dc
    b11 = b11_full + dd
    q = largest_generalized(a00, a11, b00, b01, b11)
    batch_q = np.array([np.longdouble(
        row["q_from_batch_control_variate"]) for row in rows])
    q_se = batch_q.std(ddof=1) / np.sqrt(np.longdouble(len(rows)))
    result = {
        "status": "HEURISTIC ONLY",
        "rigorous": False,
        "theorem_ready": False,
        "never_implies": ["an exact quotient", "Proposition 1", "H1<=236"],
        "parameters": {
            "k": K, "batches": args.batches,
            "samples_per_batch": args.samples_per_batch,
            "seed": args.seed, "inner_c": "1",
            "outer_c": str(C_OUT), "arithmetic": str(np.dtype(np.longdouble)),
            "physical_shape": args.physical_shape,
            "slack_shape": args.slack_shape,
        },
        "source_hashes": {str(VECTOR.relative_to(REPO)): sha256(VECTOR),
                          str(UNCAPPED.relative_to(REPO)): sha256(UNCAPPED)},
        "script_sha256_before_output": sha256(FILE),
        "control_variate_matrix": {
            "A00_exact": str(a00), "A11_estimate": str(a11),
            "B00_exact": str(b00), "B01_estimate": str(b01),
            "B11_estimate": str(b11),
        },
        "estimated_largest_quotient": str(q),
        "batch_quotient_standard_error": str(q_se),
        "calibration_means": {
            name: str(mean_field(name)) for name in
            ("a11_direct", "a11_full_mc", "b01_full_mc",
             "b11_full_mc", "b00_mc")
        },
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
        args.output.write_text(payload)
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
