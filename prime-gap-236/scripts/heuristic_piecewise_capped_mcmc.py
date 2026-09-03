#!/usr/bin/env python3
"""F-squared-targeted MCMC probe of the capped piecewise D16 candidate.

This is discovery code, never a certificate.  It targets the exact uncapped
integrands with a reversible pair-redistribution Markov kernel.  Consequently
the sampled observables are especially simple:

* on the outer I shell, the cap indicator has mean I_cap/I_full;
* on the positive envelope M_inner^2+(a M_outer,full)^2, the ratio of the
  sampled H_cap^2/envelope and H_full^2/envelope means is J_cap/J_full.

The resulting fixed-vector quotient estimate can guide the expensive exact
stratum contraction.  Autocorrelation and finite burn-in are not rigorously
bounded, so even tiny reported standard errors remain heuristic.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
HELPER_PATH = REPO / "scripts/heuristic_capped_piecewise_probe.py"
INNER_ETA2 = REPO / "results/wide_c722_D16_inner_eta2_exact.json"
SPEC = importlib.util.spec_from_file_location("capped_probe_helper", HELPER_PATH)
H = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)


def point_polynomial(points, orbit, point_coeff, alpha):
    values = orbit.evaluate(points)
    residual = np.longdouble(alpha) - points.sum(axis=1)
    radial = np.stack([residual ** c for c in range(17)], axis=1)
    return np.einsum("np,pc,nc->n", values, point_coeff, radial,
                     optimize=True)


def common_marginals(points, orbit, inner_marginal, outer_marginal,
                     exponents, nodes, weights):
    values = orbit.evaluate(points)
    total = points.sum(axis=1)
    large = points > H.ld(H.DELTA)
    count = large.sum(axis=1)
    large_sum = np.where(large, points, np.longdouble(0)).sum(axis=1)
    qi = np.einsum("np,pce->nce", values, inner_marginal, optimize=True)
    qo = np.einsum("np,pce->nce", values, outer_marginal, optimize=True)
    inner = H.marginal_on_support(
        qi, total, count, large_sum, H.ld(H.ALPHA1), H.ld(H.ALPHA1),
        exponents, nodes, weights, False)
    high_cap = H.marginal_on_support(
        qo, total, count, large_sum, H.ld(H.ALPHA2), H.ld(H.ALPHA2),
        exponents, nodes, weights, True)
    low_cap = H.marginal_on_support(
        qo, total, count, large_sum, H.ld(H.ALPHA1), H.ld(H.ALPHA2),
        exponents, nodes, weights, True)
    high_full = H.marginal_on_support(
        qo, total, count, large_sum, H.ld(H.ALPHA2), H.ld(H.ALPHA2),
        exponents, nodes, weights, False)
    low_full = H.marginal_on_support(
        qo, total, count, large_sum, H.ld(H.ALPHA1), H.ld(H.ALPHA2),
        exponents, nodes, weights, False)
    return inner, high_cap - low_cap, high_full - low_full, count


def propose(points, upper, rng):
    n, dimension = points.shape
    slack = np.longdouble(upper) - points.sum(axis=1)
    augmented = np.concatenate([points, slack[:, None]], axis=1)
    i = rng.integers(0, dimension + 1, size=n)
    j = rng.integers(0, dimension, size=n)
    j = j + (j >= i)
    fraction = rng.random(n).astype(np.longdouble)
    row = np.arange(n)
    total = augmented[row, i] + augmented[row, j]
    augmented[row, i] = total * fraction
    augmented[row, j] = total * (1 - fraction)
    return augmented[:, :dimension]


def accept_log(current_log, candidate_log, rng):
    draw = rng.random(len(current_log))
    log_uniform = np.log(np.maximum(draw, np.finfo(float).tiny))
    return log_uniform.astype(np.longdouble) < candidate_log - current_log


def log_square(value, valid=None):
    answer = np.full(len(value), -np.inf, dtype=np.longdouble)
    mask = value != 0
    if valid is not None:
        mask &= valid
    answer[mask] = 2 * np.log(np.abs(value[mask]))
    return answer


def group_summary(samples, groups):
    samples = np.asarray(samples, dtype=np.longdouble)
    if samples.ndim != 2:
        raise ValueError("samples must be step by chain")
    n = samples.shape[1]
    if n % groups:
        raise ValueError("chain count must be divisible by groups")
    grouped = samples.reshape(samples.shape[0], groups, n // groups)
    group_means = grouped.mean(axis=(0, 2), dtype=np.longdouble)
    mean = group_means.mean(dtype=np.longdouble)
    se = group_means.std(ddof=1) / np.sqrt(np.longdouble(groups))
    return mean, se, group_means


def initialize_shell(rng, chains):
    pieces = []
    needed = chains
    while needed:
        points, _ = H.simplex_dirichlet(
            rng, max(needed * 2, 64), H.K, H.ld(H.ALPHA2), 1.0, 1.0)
        accepted = points[points.sum(axis=1) > H.ld(H.ALPHA1)]
        pieces.append(accepted[:needed])
        needed -= min(needed, len(accepted))
    return np.concatenate(pieces, axis=0)


def run_i(rng, chains, burnin, steps, thin, orbit, outer_point):
    points = initialize_shell(rng, chains)
    value = point_polynomial(points, orbit, outer_point, H.ld(H.ALPHA2))
    log_density = log_square(value)
    if not np.isfinite(log_density).all():
        raise ArithmeticError("invalid initial I density")
    observations = []
    count_rows = []
    accepted = proposed = 0
    for step in range(burnin + steps * thin):
        candidate = propose(points, H.ld(H.ALPHA2), rng)
        shell = candidate.sum(axis=1) > H.ld(H.ALPHA1)
        cvalue = point_polynomial(
            candidate, orbit, outer_point, H.ld(H.ALPHA2))
        clog = log_square(cvalue, shell)
        take = accept_log(log_density, clog, rng)
        points[take] = candidate[take]
        value[take] = cvalue[take]
        log_density[take] = clog[take]
        accepted += int(take.sum())
        proposed += chains
        if step >= burnin and (step - burnin + 1) % thin == 0:
            large = points > H.ld(H.DELTA)
            count = large.sum(axis=1)
            large_sum = np.where(
                large, points, np.longdouble(0)).sum(axis=1)
            beta = np.array([
                np.longdouble(np.inf) if int(r) == 0
                else H.ld(H.schedule_q(int(r))) for r in count])
            cap = (count == 0) | (large_sum <= beta)
            observations.append(cap.astype(np.longdouble))
            count_rows.append(count.copy())
        if (step + 1) % max(1, (burnin + steps * thin) // 10) == 0:
            print(f"I step {step + 1}/{burnin + steps * thin}", flush=True)
    return np.stack(observations), np.stack(count_rows), accepted / proposed


def run_j(rng, chains, burnin, steps, thin, orbit, inner_marginal,
          outer_marginal, exponents, nodes, weights, amplitude):
    points, _ = H.simplex_dirichlet(
        rng, chains, H.K - 1, H.ld(H.ETA2), 1.0, 1.0)
    inner, capped, full, count = common_marginals(
        points, orbit, inner_marginal, outer_marginal, exponents,
        nodes, weights)
    hfull = inner + amplitude * full
    hcap = inner + amplitude * capped
    density = inner * inner + (amplitude * full) ** 2
    log_density = np.log(density)
    if not np.isfinite(log_density).all():
        raise ArithmeticError("invalid initial J density")
    observations = []
    count_rows = []
    accepted = proposed = 0
    for step in range(burnin + steps * thin):
        candidate = propose(points, H.ld(H.ETA2), rng)
        ci, cc, cf, ccount = common_marginals(
            candidate, orbit, inner_marginal, outer_marginal, exponents,
            nodes, weights)
        chfull = ci + amplitude * cf
        chcap = ci + amplitude * cc
        cdensity = ci * ci + (amplitude * cf) ** 2
        clog = np.log(cdensity)
        take = accept_log(log_density, clog, rng)
        points[take] = candidate[take]
        hfull[take] = chfull[take]
        hcap[take] = chcap[take]
        density[take] = cdensity[take]
        log_density[take] = clog[take]
        count[take] = ccount[take]
        accepted += int(take.sum())
        proposed += chains
        if step >= burnin and (step - burnin + 1) % thin == 0:
            observations.append(np.stack(
                ((hcap * hcap - hfull * hfull) / density,
                 hfull * hfull / density), axis=1))
            count_rows.append(count.copy())
        if (step + 1) % max(1, (burnin + steps * thin) // 10) == 0:
            print(f"J step {step + 1}/{burnin + steps * thin}", flush=True)
    return np.stack(observations), np.stack(count_rows), accepted / proposed


def histogram(counts, maximum):
    flat = counts.ravel()
    return [int(np.sum(flat == r)) for r in range(maximum + 1)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chains", type=int, default=256)
    parser.add_argument("--groups", type=int, default=8)
    parser.add_argument("--burnin", type=int, default=100)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--thin", type=int, default=2)
    parser.add_argument("--seed", type=int, default=2360481)
    parser.add_argument("--only", choices=("i", "j", "both"), default="both")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if (args.chains < args.groups or args.chains % args.groups or
            args.groups < 2 or min(args.burnin, args.steps, args.thin) < 1):
        parser.error("invalid chain/group/step schedule")

    source = H.strict_load(H.VECTOR)
    uncapped = H.strict_load(H.UNCAPPED)
    inner_eta2 = H.strict_load(INNER_ETA2)
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in source["basis"])
    vector = tuple(Q(x) for x in source["rational_vector"])
    inner_coeff = H.residual_coefficients(basis, vector, H.ALPHA1, Q(1))
    outer_coeff = H.residual_coefficients(
        basis, vector, H.ALPHA2, H.C_OUT)
    required = {lam for _, lam in inner_coeff}
    for _, lam in tuple(inner_coeff) + tuple(outer_coeff):
        for exponent in set(lam):
            rest = list(lam)
            rest.remove(exponent)
            required.add(tuple(rest))
    orbit = H.VectorizedOrbitEvaluator(sorted(required))
    _, inner_marginal, exponents = H.coefficient_arrays(
        inner_coeff, orbit.partitions)
    outer_point, outer_marginal, _ = H.coefficient_arrays(
        outer_coeff, orbit.partitions)
    nodes, weights = np.polynomial.legendre.leggauss(9)
    nodes = nodes.astype(np.longdouble)
    weights = weights.astype(np.longdouble)
    row = next(x for x in uncapped["rows"]
               if x["name"] == "rationalized_stationary")
    amplitude_q = Q(row["outer_amplitude"])
    amplitude = H.ld(amplitude_q)
    exact_denominator = H.ld(Q(row["exact_denominator"]))
    exact_numerator = H.ld(Q(row["exact_numerator"]))
    a00 = H.ld(Q(uncapped["I_matrix"][0][0]))
    a11 = H.ld(Q(uncapped["I_matrix"][1][1]))
    b11 = H.ld(Q(uncapped["kJ_matrix"][1][1]))
    b_inner_eta2 = H.ld(Q(inner_eta2["numerator_48J"]))

    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    result = {
        "status": "HEURISTIC ONLY", "rigorous": False,
        "theorem_ready": False,
        "never_implies": ["an exact quotient", "Proposition 1", "H1<=236"],
        "parameters": vars(args) | {"output": None,
                                     "outer_amplitude": str(amplitude_q)},
        "source_hashes": {
            str(H.VECTOR.relative_to(REPO)): H.sha256(H.VECTOR),
            str(H.UNCAPPED.relative_to(REPO)): H.sha256(H.UNCAPPED),
            str(HELPER_PATH.relative_to(REPO)): H.sha256(HELPER_PATH),
            str(INNER_ETA2.relative_to(REPO)): H.sha256(INNER_ETA2),
        },
    }
    i_mean = np.longdouble(1)
    j_mean = np.longdouble(1)
    if args.only in ("i", "both"):
        obs, counts, acceptance = run_i(
            rng, args.chains, args.burnin, args.steps, args.thin,
            orbit, outer_point)
        i_mean, i_se, group_means = group_summary(obs, args.groups)
        result["I"] = {
            "estimated_cap_ratio": str(i_mean),
            "group_standard_error": str(i_se),
            "group_means": [str(x) for x in group_means],
            "acceptance": acceptance,
            "large_count_histogram": histogram(counts, H.K),
        }
    if args.only in ("j", "both"):
        obs, counts, acceptance = run_j(
            rng, args.chains, args.burnin, args.steps, args.thin,
            orbit, inner_marginal, outer_marginal, exponents, nodes,
            weights, amplitude)
        delta_obs, full_obs = obs[:, :, 0], obs[:, :, 1]
        delta_mean, delta_se, delta_groups = group_summary(
            delta_obs, args.groups)
        full_mean, full_se, full_groups = group_summary(
            full_obs, args.groups)
        envelope_48j = b_inner_eta2 + amplitude * amplitude * b11
        numerator_delta_groups = envelope_48j * delta_groups
        numerator_groups = exact_numerator + numerator_delta_groups
        ratio_groups = numerator_groups / exact_numerator
        j_mean = ratio_groups.mean(dtype=np.longdouble)
        j_se = ratio_groups.std(ddof=1) / np.sqrt(np.longdouble(args.groups))
        result["J"] = {
            "estimated_candidate_cap_ratio": str(j_mean),
            "group_standard_error": str(j_se),
            "group_ratio_means": [str(x) for x in ratio_groups],
            "cap_minus_full_over_envelope_mean": str(delta_mean),
            "cap_minus_full_over_envelope_standard_error": str(delta_se),
            "full_over_envelope_mean": str(full_mean),
            "full_over_envelope_standard_error": str(full_se),
            "exact_envelope_48J": str(envelope_48j),
            "acceptance": acceptance,
            "common_large_count_histogram": histogram(counts, H.K - 1),
        }
    capped_denominator = a00 + amplitude * amplitude * a11 * i_mean
    capped_numerator = exact_numerator * j_mean
    result["fixed_amplitude_estimate"] = {
        "uncapped_quotient": str(exact_numerator / exact_denominator),
        "capped_denominator": str(capped_denominator),
        "capped_numerator": str(capped_numerator),
        "capped_quotient": str(capped_numerator / capped_denominator),
    }
    result["wall_seconds"] = time.monotonic() - started
    result["script_sha256_before_output"] = H.sha256(FILE)
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
        print(f"sha256 {hashlib.sha256(payload.encode()).hexdigest()}")
    print(json.dumps({
        "status": result["status"],
        "fixed_amplitude_estimate": result["fixed_amplitude_estimate"],
        "I": result.get("I"), "J": result.get("J"),
        "wall_seconds": result["wall_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
