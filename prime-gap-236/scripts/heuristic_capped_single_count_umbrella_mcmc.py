#!/usr/bin/env python3
"""Umbrella-MCMC search probe for one capped outer count coordinate.

This is deliberately non-rigorous discovery code.  It estimates the genuine
two-dimensional pencil spanned by the audited inner D16 polynomial and the
naturally dilated outer D16 polynomial restricted to a single total large
count.  A known, piecewise-constant umbrella weight makes a rare count visible;
division by that weight and self-normalization recover expectations for the
original F-squared targets.  Every useful output still requires fresh exact or
outward-rounded integration.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
BASE_PATH = REPO / "scripts/heuristic_capped_count_pencil_mcmc.py"
SPEC = importlib.util.spec_from_file_location("count_pencil", BASE_PATH)
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)
M, H = C.M, C.H


def group_sum(groups, values):
    answer = np.zeros(groups.max() + 1, dtype=np.longdouble)
    for group in range(groups.max() + 1):
        answer[group] = values[groups == group].sum(dtype=np.longdouble)
    return answer


def umbrella(count, target, factor):
    return np.where(count == target, factor, np.longdouble(1))


def run_i(rng, chains, groups, burnin, steps, thin, target, factor,
          orbit, outer_point):
    points = M.initialize_shell(rng, chains)
    value = M.point_polynomial(points, orbit, outer_point, H.ld(H.ALPHA2))
    count = (points > H.ld(H.DELTA)).sum(axis=1)
    weight = umbrella(count, target, factor)
    log_density = M.log_square(value) + np.log(weight)
    group = np.repeat(np.arange(groups), chains // groups)
    numerator = np.zeros(groups, dtype=np.longdouble)
    denominator = np.zeros(groups, dtype=np.longdouble)
    visits = np.zeros(groups, dtype=np.longdouble)
    records = accepted = proposed = 0
    total_steps = burnin + steps * thin
    for step in range(total_steps):
        candidate = M.propose(points, H.ld(H.ALPHA2), rng)
        shell = candidate.sum(axis=1) > H.ld(H.ALPHA1)
        cvalue = M.point_polynomial(
            candidate, orbit, outer_point, H.ld(H.ALPHA2))
        ccount = (candidate > H.ld(H.DELTA)).sum(axis=1)
        cweight = umbrella(ccount, target, factor)
        clog = M.log_square(cvalue, shell) + np.log(cweight)
        take = M.accept_log(log_density, clog, rng)
        points[take], value[take], count[take], weight[take], log_density[take] = (
            candidate[take], cvalue[take], ccount[take], cweight[take],
            clog[take])
        accepted += int(take.sum())
        proposed += chains
        if step >= burnin and (step - burnin + 1) % thin == 0:
            large = points > H.ld(H.DELTA)
            large_sum = np.where(
                large, points, np.longdouble(0)).sum(axis=1)
            beta = np.array([
                np.longdouble(np.inf) if int(r) == 0
                else H.ld(H.schedule_q(int(r))) for r in count])
            hit = (count == target) & (large_sum <= beta)
            inv_weight = 1 / weight
            numerator += group_sum(group, hit * inv_weight)
            denominator += group_sum(group, inv_weight)
            visits += group_sum(group, count == target)
            records += 1
        if (step + 1) % max(1, total_steps // 10) == 0:
            print(f"I umbrella step {step + 1}/{total_steps}", flush=True)
    probability = numerator / denominator
    return (probability, denominator,
            visits / (records * (chains // groups)), accepted / proposed)


def run_j(rng, chains, groups, burnin, steps, thin, target, factor,
          orbit, inner_marginal, outer_marginal, exponents, nodes, weights):
    points, _ = H.simplex_dirichlet(
        rng, chains, H.K - 1, H.ld(H.ETA2), 1.0, 1.0)
    inner, small, large, full, count = C.outer_marginal_parts(
        points, orbit, inner_marginal, outer_marginal, exponents,
        nodes, weights)
    density = inner * inner + full * full
    # Either common count can feed total count ``target``.
    biased = ((count == target) | (count + 1 == target))
    umbrella_weight = np.where(biased, factor, np.longdouble(1))
    log_density = np.log(density) + np.log(umbrella_weight)
    group = np.repeat(np.arange(groups), chains // groups)
    cross_num = np.zeros(groups, dtype=np.longdouble)
    diag_num = np.zeros(groups, dtype=np.longdouble)
    denominator = np.zeros(groups, dtype=np.longdouble)
    visits = np.zeros(groups, dtype=np.longdouble)
    records = accepted = proposed = 0
    total_steps = burnin + steps * thin
    for step in range(total_steps):
        candidate = M.propose(points, H.ld(H.ETA2), rng)
        ci, cs, cl, cf, cc = C.outer_marginal_parts(
            candidate, orbit, inner_marginal, outer_marginal, exponents,
            nodes, weights)
        cdensity = ci * ci + cf * cf
        cbiased = ((cc == target) | (cc + 1 == target))
        cweight = np.where(cbiased, factor, np.longdouble(1))
        clog = np.log(cdensity) + np.log(cweight)
        take = M.accept_log(log_density, clog, rng)
        points[take] = candidate[take]
        for current, proposed_values in (
                (inner, ci), (small, cs), (large, cl), (full, cf),
                (count, cc), (density, cdensity),
                (umbrella_weight, cweight), (log_density, clog)):
            current[take] = proposed_values[take]
        accepted += int(take.sum())
        proposed += chains
        if step >= burnin and (step - burnin + 1) % thin == 0:
            selected = (small * (count == target) +
                        large * (count + 1 == target))
            inv = 1 / (density * umbrella_weight)
            cross_num += group_sum(group, inner * selected * inv)
            diag_num += group_sum(group, selected * selected * inv)
            denominator += group_sum(group, 1 / umbrella_weight)
            visits += group_sum(group, biased)
            records += 1
        if (step + 1) % max(1, total_steps // 10) == 0:
            print(f"J umbrella step {step + 1}/{total_steps}", flush=True)
    return ({"cross": cross_num / denominator,
             "diagonal": diag_num / denominator}, denominator,
            visits / (records * (chains // groups)), accepted / proposed)


def top_2d(a00, arr, b00, b0r, brr):
    w00 = b00 / a00
    w11 = brr / arr
    w01 = b0r / np.sqrt(a00 * arr)
    return ((w00 + w11) / 2 +
            np.sqrt(((w00 - w11) / 2) ** 2 + w01 * w01))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chains", type=int, default=256)
    parser.add_argument("--groups", type=int, default=16)
    parser.add_argument("--burnin", type=int, default=400)
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--thin", type=int, default=2)
    parser.add_argument("--seed", type=int, default=2360486)
    parser.add_argument("--target", type=int, default=15)
    parser.add_argument("--i-factor", type=int, default=32)
    parser.add_argument("--j-factor", type=int, default=16)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if (args.chains < args.groups or args.chains % args.groups or
            args.groups < 2 or min(args.burnin, args.steps, args.thin,
                                   args.i_factor, args.j_factor) < 1 or
            not 1 <= args.target < H.K):
        parser.error("invalid schedule, target, or umbrella factor")

    orbit, po, mi, mo, exponents, nodes, weights, exact = C.prepare()
    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    ip, iden, ivisit, iaccept = run_i(
        rng, args.chains, args.groups, args.burnin, args.steps, args.thin,
        args.target, H.ld(args.i_factor), orbit, po)
    jm, jden, jvisit, jaccept = run_j(
        rng, args.chains, args.groups, args.burnin, args.steps, args.thin,
        args.target, H.ld(args.j_factor), orbit, mi, mo, exponents,
        nodes, weights)
    envelope = exact["b_inner_eta2"] + exact["b11_full"]
    arr = exact["a11_full"] * ip
    b0r = envelope * jm["cross"]
    brr = envelope * jm["diagonal"]
    q = top_2d(exact["a00"], arr, exact["b00"], b0r, brr)
    ipool = np.sum(ip * iden) / np.sum(iden)
    jcross_pool = np.sum(jm["cross"] * jden) / np.sum(jden)
    jdiag_pool = np.sum(jm["diagonal"] * jden) / np.sum(jden)
    qpool = top_2d(
        exact["a00"], exact["a11_full"] * ipool, exact["b00"],
        envelope * jcross_pool, envelope * jdiag_pool)
    result = {
        "status": "HEURISTIC ONLY", "rigorous": False,
        "theorem_ready": False,
        "never_implies": ["an exact quotient", "Proposition 1", "H1<=236"],
        "parameters": vars(args) | {"output": None},
        "source_hashes": {
            str(BASE_PATH.relative_to(REPO)): H.sha256(BASE_PATH),
            str(H.UNCAPPED.relative_to(REPO)): H.sha256(H.UNCAPPED),
            str(M.INNER_ETA2.relative_to(REPO)): H.sha256(M.INNER_ETA2),
        },
        "group_I_capped_probability": [str(x) for x in ip],
        "group_J_cross_normalized": [str(x) for x in jm["cross"]],
        "group_J_diagonal_normalized": [str(x) for x in jm["diagonal"]],
        "group_top_quotient": [str(x) for x in q],
        "pooled_I_capped_probability": str(ipool),
        "pooled_J_cross_normalized": str(jcross_pool),
        "pooled_J_diagonal_normalized": str(jdiag_pool),
        "estimated_top_quotient": str(qpool),
        "group_quotient_standard_error": str(
            q.std(ddof=1) / np.sqrt(np.longdouble(args.groups))),
        "group_I_umbrella_visit_fraction": [str(x) for x in ivisit],
        "group_J_umbrella_visit_fraction": [str(x) for x in jvisit],
        "I_acceptance": iaccept, "J_acceptance": jaccept,
        "wall_seconds": time.monotonic() - started,
        "script_sha256_before_output": H.sha256(FILE),
    }
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            raise FileExistsError(args.output)
        args.output.write_text(payload)
        print(f"sha256 {hashlib.sha256(payload.encode()).hexdigest()}")
    print(json.dumps({key: result[key] for key in (
        "status", "estimated_top_quotient", "group_quotient_standard_error",
        "I_acceptance", "J_acceptance", "wall_seconds")}, indent=2))


if __name__ == "__main__":
    main()
