#!/usr/bin/env python3
"""Smooth count-umbrella variant of the single-count D16 search probe.

Unlike the binary umbrella, neighboring count strata differ by only one
moderate weight ratio.  This reduces (but does not rigorously control) the
observed count trapping.  Output remains heuristic discovery data only.
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
UMBRELLA_PATH = REPO / "scripts/heuristic_capped_single_count_umbrella_mcmc.py"
SPEC = importlib.util.spec_from_file_location("binary_umbrella", UMBRELLA_PATH)
U = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(U)
C, M, H = U.C, U.M, U.H


def peaked_weight(count, centers, base, radius):
    count = np.asarray(count)
    distance = np.minimum.reduce([np.abs(count - center)
                                  for center in centers])
    exponent = np.maximum(0, radius - distance)
    return np.asarray(base ** exponent, dtype=np.longdouble)


def run_j(rng, chains, groups, burnin, steps, thin, target, base, radius,
          orbit, inner_marginal, outer_marginal, exponents, nodes, weights):
    points, _ = H.simplex_dirichlet(
        rng, chains, H.K - 1, H.ld(H.ETA2), 1.0, 1.0)
    inner, small, large, full, count = C.outer_marginal_parts(
        points, orbit, inner_marginal, outer_marginal, exponents,
        nodes, weights)
    density = inner * inner + full * full
    umbrella = peaked_weight(count, (target - 1, target), base, radius)
    log_density = np.log(density) + np.log(umbrella)
    group = np.repeat(np.arange(groups), chains // groups)
    cross_num = np.zeros(groups, dtype=np.longdouble)
    diag_num = np.zeros(groups, dtype=np.longdouble)
    denominator = np.zeros(groups, dtype=np.longdouble)
    visits = np.zeros(groups, dtype=np.longdouble)
    transitions = np.zeros(groups, dtype=np.longdouble)
    records = accepted = proposed = 0
    total_steps = burnin + steps * thin
    for step in range(total_steps):
        old_count = count.copy()
        candidate = M.propose(points, H.ld(H.ETA2), rng)
        ci, cs, cl, cf, cc = C.outer_marginal_parts(
            candidate, orbit, inner_marginal, outer_marginal, exponents,
            nodes, weights)
        cdensity = ci * ci + cf * cf
        cumbrella = peaked_weight(cc, (target - 1, target), base, radius)
        clog = np.log(cdensity) + np.log(cumbrella)
        take = M.accept_log(log_density, clog, rng)
        points[take] = candidate[take]
        for current, proposed_values in (
                (inner, ci), (small, cs), (large, cl), (full, cf),
                (count, cc), (density, cdensity), (umbrella, cumbrella),
                (log_density, clog)):
            current[take] = proposed_values[take]
        accepted += int(take.sum())
        proposed += chains
        if step >= burnin and (step - burnin + 1) % thin == 0:
            selected = (small * (count == target) +
                        large * (count + 1 == target))
            inv = 1 / (density * umbrella)
            cross_num += U.group_sum(group, inner * selected * inv)
            diag_num += U.group_sum(group, selected * selected * inv)
            denominator += U.group_sum(group, 1 / umbrella)
            visits += U.group_sum(
                group, (count == target) | (count + 1 == target))
            transitions += U.group_sum(group, count != old_count)
            records += 1
        if (step + 1) % max(1, total_steps // 10) == 0:
            print(f"J smooth step {step + 1}/{total_steps}", flush=True)
    scale = records * (chains // groups)
    return ({"cross": cross_num / denominator,
             "diagonal": diag_num / denominator}, denominator,
            visits / scale, transitions / scale, accepted / proposed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chains", type=int, default=256)
    parser.add_argument("--groups", type=int, default=16)
    parser.add_argument("--burnin", type=int, default=600)
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--thin", type=int, default=2)
    parser.add_argument("--seed", type=int, default=2360487)
    parser.add_argument("--target", type=int, default=15)
    parser.add_argument("--i-base", type=str, default="1.5")
    parser.add_argument("--j-base", type=str, default="1.8")
    parser.add_argument("--radius", type=int, default=6)
    parser.add_argument("--schedule", choices=("volume-ramp", "count15-166"),
                        default="volume-ramp")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        ibase, jbase = np.longdouble(args.i_base), np.longdouble(args.j_base)
    except ValueError:
        parser.error("umbrella bases must be decimals")
    if (args.chains < args.groups or args.chains % args.groups or
            args.groups < 2 or min(args.burnin, args.steps, args.thin,
                                   args.radius) < 1 or
            not 1 <= args.target < H.K or
            not np.isfinite(ibase) or not np.isfinite(jbase) or
            not 1 < ibase <= 2 or not 1 < jbase <= 2):
        parser.error("invalid schedule, target, or smooth umbrella")

    if args.schedule == "count15-166":
        start, plateau = H.Q(1623, 25000), H.Q(83, 500)

        def selected_schedule(r):
            if r <= 0:
                raise ValueError("schedule is defined only at positive count")
            return min(start + (r - 1) * H.DELTA, plateau)

        H.schedule_q = selected_schedule

    orbit, po, mi, mo, exponents, nodes, weights, exact = C.prepare()
    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    # The binary module calls this global function on every current/candidate
    # I count.  Replace it only inside this isolated process.
    U.umbrella = lambda count, target, ignored: peaked_weight(
        count, (target,), ibase, args.radius)
    ip, iden, ivisit, iaccept = U.run_i(
        rng, args.chains, args.groups, args.burnin, args.steps, args.thin,
        args.target, ibase, orbit, po)
    jm, jden, jvisit, jtrans, jaccept = run_j(
        rng, args.chains, args.groups, args.burnin, args.steps, args.thin,
        args.target, jbase, args.radius, orbit, mi, mo, exponents,
        nodes, weights)
    envelope = exact["b_inner_eta2"] + exact["b11_full"]
    arr = exact["a11_full"] * ip
    b0r = envelope * jm["cross"]
    brr = envelope * jm["diagonal"]
    group_q = U.top_2d(exact["a00"], arr, exact["b00"], b0r, brr)
    ipool = np.sum(ip * iden) / np.sum(iden)
    jcross_pool = np.sum(jm["cross"] * jden) / np.sum(jden)
    jdiag_pool = np.sum(jm["diagonal"] * jden) / np.sum(jden)
    qpool = U.top_2d(
        exact["a00"], exact["a11_full"] * ipool, exact["b00"],
        envelope * jcross_pool, envelope * jdiag_pool)
    result = {
        "status": "HEURISTIC ONLY", "rigorous": False,
        "theorem_ready": False,
        "never_implies": ["an exact quotient", "Proposition 1", "H1<=236"],
        "parameters": vars(args) | {"output": None},
        "source_hashes": {
            str(UMBRELLA_PATH.relative_to(REPO)): H.sha256(UMBRELLA_PATH),
            str(U.BASE_PATH.relative_to(REPO)): H.sha256(U.BASE_PATH),
            str(H.UNCAPPED.relative_to(REPO)): H.sha256(H.UNCAPPED),
            str(M.INNER_ETA2.relative_to(REPO)): H.sha256(M.INNER_ETA2),
        },
        "group_I_capped_probability": [str(x) for x in ip],
        "group_J_cross_normalized": [str(x) for x in jm["cross"]],
        "group_J_diagonal_normalized": [str(x) for x in jm["diagonal"]],
        "group_top_quotient": [str(x) for x in group_q],
        "pooled_I_capped_probability": str(ipool),
        "pooled_J_cross_normalized": str(jcross_pool),
        "pooled_J_diagonal_normalized": str(jdiag_pool),
        "estimated_top_quotient": str(qpool),
        "group_quotient_standard_error": str(
            group_q.std(ddof=1) / np.sqrt(np.longdouble(args.groups))),
        "group_I_umbrella_visit_fraction": [str(x) for x in ivisit],
        "group_J_umbrella_visit_fraction": [str(x) for x in jvisit],
        "group_J_count_transition_fraction": [str(x) for x in jtrans],
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
