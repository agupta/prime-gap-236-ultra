#!/usr/bin/env python3
"""Heuristic MCMC discovery of a capped, count-tagged D16 outer pencil.

The output is not rigorous.  It estimates the legitimate finite subspace

    F_inner 1_inner,  F_outer 1_outer 1_{R=r}  (r in an explicit list)

on the audited volume-ramp support.  I samples target the uncapped outer
F_outer^2 law, while J samples target the positive envelope
M_inner^2+M_outer,full^2.  Exact uncapped normalizers convert sampled
dimensionless moments into a discovery matrix.  Every winning vector still
requires a fresh exact or outward-rounded reconstruction.
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
MCMC_PATH = REPO / "scripts/heuristic_piecewise_capped_mcmc.py"
SPEC = importlib.util.spec_from_file_location("piecewise_mcmc", MCMC_PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
H = M.H


def prepare():
    source = H.strict_load(H.VECTOR)
    uncapped = H.strict_load(H.UNCAPPED)
    inner_eta2 = H.strict_load(M.INNER_ETA2)
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in source["basis"])
    vector = tuple(Q(x) for x in source["rational_vector"])
    ci = H.residual_coefficients(basis, vector, H.ALPHA1, Q(1))
    co = H.residual_coefficients(basis, vector, H.ALPHA2, H.C_OUT)
    required = {lam for _, lam in ci}
    for _, lam in tuple(ci) + tuple(co):
        for exponent in set(lam):
            rest = list(lam)
            rest.remove(exponent)
            required.add(tuple(rest))
    orbit = H.VectorizedOrbitEvaluator(sorted(required))
    _, mi, exponents = H.coefficient_arrays(ci, orbit.partitions)
    po, mo, _ = H.coefficient_arrays(co, orbit.partitions)
    nodes, weights = np.polynomial.legendre.leggauss(9)
    exact = {
        "a00": H.ld(Q(uncapped["I_matrix"][0][0])),
        "a11_full": H.ld(Q(uncapped["I_matrix"][1][1])),
        "b00": H.ld(Q(uncapped["kJ_matrix"][0][0])),
        "b11_full": H.ld(Q(uncapped["kJ_matrix"][1][1])),
        "b_inner_eta2": H.ld(Q(inner_eta2["numerator_48J"])),
    }
    return (orbit, po, mi, mo, exponents,
            nodes.astype(np.longdouble), weights.astype(np.longdouble),
            exact)


def outer_marginal_parts(points, orbit, inner_marginal, outer_marginal,
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
    hsmall, hlarge = H.marginal_support_parts(
        qo, total, count, large_sum, H.ld(H.ALPHA2), H.ld(H.ALPHA2),
        exponents, nodes, weights, True)
    lsmall, llarge = H.marginal_support_parts(
        qo, total, count, large_sum, H.ld(H.ALPHA1), H.ld(H.ALPHA2),
        exponents, nodes, weights, True)
    high_full = H.marginal_on_support(
        qo, total, count, large_sum, H.ld(H.ALPHA2), H.ld(H.ALPHA2),
        exponents, nodes, weights, False)
    low_full = H.marginal_on_support(
        qo, total, count, large_sum, H.ld(H.ALPHA1), H.ld(H.ALPHA2),
        exponents, nodes, weights, False)
    return inner, hsmall - lsmall, hlarge - llarge, \
        high_full - low_full, count


def group_bincount(groups, count, weight, size):
    answer = np.zeros((groups.max() + 1, size), dtype=np.longdouble)
    for group in range(groups.max() + 1):
        mask = groups == group
        answer[group] = np.bincount(
            count[mask], weights=np.asarray(weight[mask], dtype=np.float64),
            minlength=size).astype(np.longdouble)
    return answer


def run_i(rng, chains, groups, burnin, steps, thin, orbit, outer_point):
    points = M.initialize_shell(rng, chains)
    value = M.point_polynomial(points, orbit, outer_point, H.ld(H.ALPHA2))
    log_density = M.log_square(value)
    group_index = np.repeat(np.arange(groups), chains // groups)
    counts = np.zeros((groups, H.K + 1), dtype=np.longdouble)
    accepted = proposed = records = 0
    for step in range(burnin + steps * thin):
        candidate = M.propose(points, H.ld(H.ALPHA2), rng)
        shell = candidate.sum(axis=1) > H.ld(H.ALPHA1)
        cvalue = M.point_polynomial(
            candidate, orbit, outer_point, H.ld(H.ALPHA2))
        clog = M.log_square(cvalue, shell)
        take = M.accept_log(log_density, clog, rng)
        points[take], value[take], log_density[take] = (
            candidate[take], cvalue[take], clog[take])
        accepted += int(take.sum())
        proposed += chains
        if step >= burnin and (step - burnin + 1) % thin == 0:
            large = points > H.ld(H.DELTA)
            r = large.sum(axis=1)
            lsum = np.where(large, points, np.longdouble(0)).sum(axis=1)
            beta = np.array([np.longdouble(np.inf) if int(x) == 0
                             else H.ld(H.schedule_q(int(x))) for x in r])
            cap = (r == 0) | (lsum <= beta)
            counts += group_bincount(
                group_index, r, cap.astype(np.longdouble), H.K + 1)
            records += 1
        if (step + 1) % max(1, (burnin + steps * thin) // 10) == 0:
            print(f"I-count step {step + 1}/{burnin + steps * thin}",
                  flush=True)
    counts /= np.longdouble(records * (chains // groups))
    return counts, accepted / proposed


def run_j(rng, chains, groups, burnin, steps, thin, orbit,
          inner_marginal, outer_marginal, exponents, nodes, weights):
    points, _ = H.simplex_dirichlet(
        rng, chains, H.K - 1, H.ld(H.ETA2), 1.0, 1.0)
    inner, small, large, full, count = outer_marginal_parts(
        points, orbit, inner_marginal, outer_marginal, exponents,
        nodes, weights)
    density = inner * inner + full * full
    log_density = np.log(density)
    group_index = np.repeat(np.arange(groups), chains // groups)
    cross = np.zeros((groups, H.K), dtype=np.longdouble)
    diagonal = np.zeros((groups, H.K), dtype=np.longdouble)
    adjacent = np.zeros((groups, H.K - 1), dtype=np.longdouble)
    common_counts = np.zeros((groups, H.K), dtype=np.longdouble)
    accepted = proposed = records = 0
    for step in range(burnin + steps * thin):
        candidate = M.propose(points, H.ld(H.ETA2), rng)
        ci, cs, cl, cf, cc = outer_marginal_parts(
            candidate, orbit, inner_marginal, outer_marginal, exponents,
            nodes, weights)
        cdensity = ci * ci + cf * cf
        clog = np.log(cdensity)
        take = M.accept_log(log_density, clog, rng)
        points[take] = candidate[take]
        for current, proposed_values in (
                (inner, ci), (small, cs), (large, cl), (full, cf),
                (density, cdensity), (log_density, clog), (count, cc)):
            current[take] = proposed_values[take]
        accepted += int(take.sum())
        proposed += chains
        if step >= burnin and (step - burnin + 1) % thin == 0:
            inv = 1 / density
            cross += group_bincount(
                group_index, count, inner * small * inv, H.K)
            cross += group_bincount(
                group_index, count + 1, inner * large * inv, H.K)
            diagonal += group_bincount(
                group_index, count, small * small * inv, H.K)
            diagonal += group_bincount(
                group_index, count + 1, large * large * inv, H.K)
            adjacent += group_bincount(
                group_index, count, small * large * inv, H.K - 1)
            common_counts += group_bincount(
                group_index, count, np.ones(chains), H.K)
            records += 1
        if (step + 1) % max(1, (burnin + steps * thin) // 10) == 0:
            print(f"J-count step {step + 1}/{burnin + steps * thin}",
                  flush=True)
    normalization = np.longdouble(records * (chains // groups))
    return ({"cross": cross / normalization,
             "diagonal": diagonal / normalization,
             "adjacent": adjacent / normalization,
             "common_counts": common_counts / normalization},
            accepted / proposed)


def top_eigenvalue(exact, i_frequency, j_moments, counts):
    counts = tuple(counts)
    n = len(counts) + 1
    A = np.zeros(n, dtype=np.longdouble)
    B = np.zeros((n, n), dtype=np.longdouble)
    A[0], B[0, 0] = exact["a00"], exact["b00"]
    envelope = exact["b_inner_eta2"] + exact["b11_full"]
    for i, r in enumerate(counts, 1):
        A[i] = exact["a11_full"] * i_frequency[r]
        B[0, i] = B[i, 0] = envelope * j_moments["cross"][r]
        B[i, i] = envelope * j_moments["diagonal"][r]
    for i, r in enumerate(counts, 1):
        if r + 1 in counts:
            j = counts.index(r + 1) + 1
            B[i, j] = B[j, i] = envelope * j_moments["adjacent"][r]
    if np.any(A <= 0):
        return np.longdouble("nan"), A, B
    scale = np.sqrt(A)
    whitened = np.asarray(B / scale[:, None] / scale[None, :],
                          dtype=np.float64)
    value = np.linalg.eigvalsh(whitened)[-1]
    return np.longdouble(value), A, B


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chains", type=int, default=128)
    parser.add_argument("--groups", type=int, default=8)
    parser.add_argument("--burnin", type=int, default=300)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--thin", type=int, default=2)
    parser.add_argument("--seed", type=int, default=2360484)
    parser.add_argument("--counts", default="6,7,8,9,10,11,12,13,14,15")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    counts = tuple(int(x) for x in args.counts.split(",") if x)
    if (args.chains < args.groups or args.chains % args.groups or
            args.groups < 2 or min(args.burnin, args.steps, args.thin) < 1 or
            not counts or len(counts) != len(set(counts)) or
            any(not 0 <= r < H.K for r in counts)):
        parser.error("invalid schedule or count list")

    orbit, po, mi, mo, exponents, nodes, weights, exact = prepare()
    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    ifreq, iaccept = run_i(
        rng, args.chains, args.groups, args.burnin, args.steps, args.thin,
        orbit, po)
    jmom, jaccept = run_j(
        rng, args.chains, args.groups, args.burnin, args.steps, args.thin,
        orbit, mi, mo, exponents, nodes, weights)
    group_q = []
    for group in range(args.groups):
        moments = {key: value[group] for key, value in jmom.items()}
        q, _, _ = top_eigenvalue(exact, ifreq[group], moments, counts)
        group_q.append(q)
    mean_i = ifreq.mean(axis=0, dtype=np.longdouble)
    mean_j = {key: value.mean(axis=0, dtype=np.longdouble)
              for key, value in jmom.items()}
    q, A, B = top_eigenvalue(exact, mean_i, mean_j, counts)
    result = {
        "status": "HEURISTIC ONLY", "rigorous": False,
        "theorem_ready": False,
        "never_implies": ["an exact quotient", "Proposition 1", "H1<=236"],
        "parameters": {"chains": args.chains, "groups": args.groups,
                       "burnin": args.burnin, "steps": args.steps,
                       "thin": args.thin, "seed": args.seed,
                       "counts": list(counts)},
        "source_hashes": {
            str(MCMC_PATH.relative_to(REPO)): H.sha256(MCMC_PATH),
            str(H.UNCAPPED.relative_to(REPO)): H.sha256(H.UNCAPPED),
            str(M.INNER_ETA2.relative_to(REPO)): H.sha256(M.INNER_ETA2),
        },
        "estimated_top_quotient": str(q),
        "group_top_quotients": [str(x) for x in group_q],
        "group_quotient_standard_error": str(
            np.asarray(group_q).std(ddof=1) /
            np.sqrt(np.longdouble(args.groups))),
        "I_acceptance": iaccept, "J_acceptance": jaccept,
        "I_capped_frequency_by_count": [str(x) for x in mean_i],
        "J_common_count_frequency": [str(x) for x in
                                     mean_j["common_counts"]],
        "I_diagonal": [str(x) for x in A],
        "kJ_matrix": [[str(x) for x in row] for row in B],
        "wall_seconds": time.monotonic() - started,
        "script_sha256_before_output": H.sha256(FILE),
    }
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
        print(f"sha256 {hashlib.sha256(payload.encode()).hexdigest()}")
    print(json.dumps({
        "status": result["status"],
        "estimated_top_quotient": result["estimated_top_quotient"],
        "group_top_quotients": result["group_top_quotients"],
        "group_quotient_standard_error": result[
            "group_quotient_standard_error"],
        "I_acceptance": iaccept, "J_acceptance": jaccept,
        "wall_seconds": result["wall_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
