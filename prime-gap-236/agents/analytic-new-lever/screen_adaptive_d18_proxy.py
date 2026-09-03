#!/usr/bin/env python3
"""Common-chain natural-D18 outer-I proxy for adaptive cap schedules.

The target is the already audited naturally dilated D18 direction at the
baseline outer radius.  A normalized point ``y=t/alpha2`` represents the
same polynomial value after natural dilation to another radius.  Thus, for
candidate radii no larger than the baseline radius and with a no-smaller
normalized lower shell endpoint, the event average times
``(alpha2_new/alpha2_old)^48`` estimates capped outer-I mass relative to the
baseline *uncapped* shell mass.  This remains an MCMC proxy, not an integral,
projection energy, quotient, or theorem certificate.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
SOURCE = REPO / "scripts/heuristic_active25_d18_target_mcmc.py"
SOURCE_SHA256 = "28d6dacf8062f0dc6f5948d1fc3a1bd994ca4f39454931f9ce173bdb0aa84f8d"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if sha(SOURCE) != SOURCE_SHA256:
    raise RuntimeError("frozen D18 target sampler changed")
spec = importlib.util.spec_from_file_location("adaptive_d18_source", SOURCE)
if spec is None or spec.loader is None:
    raise ImportError(SOURCE)
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


SCHEDULES = {
    "audited-correlated-lift": (
        .119469, .126689, .133909, .141129, .148349, .155569,
        .155569, .162789, .1695, .1695, .1695, .1695, .1718,
        .1737, .1752, .1762, .1764, .1774, .1782, .1790, .1796,
        .1801, .1806, .1811, .1815, .1815),
    "d008": (
        .121028879, .129028879, .137028879, .145028879, .153028879,
        .161026489, .162277917, .169026137, .177025570, .180703209,
        .181335141, .182662183, .183788336, .184561037, .184847471,
        .185398460, .186005451, .186430198, .186766179, .187091117,
        .187370742, .187620191, .187872055, .191996026, .199996026,
        .207991647),
    "d010": (
        .125029322, .135029322, .145029322, .155028152, .161442307,
        .165029474, .175027084, .179306052, .181263809, .182802406,
        .183686639, .184585701, .185509476, .186175354, .186758845,
        .187235960, .187657930, .188037470, .189997700, .199997700,
        .209997700, .219997700, .229995050, .239995050, .249995050,
        .259995050),
    "d012": (
        .129029258, .141029258, .153026868, .160607690, .165029655,
        .176719798, .179137596, .181558953, .183299667, .184359566,
        .185429884, .186418672, .187156740, .187770091, .188314769,
        .191998557, .203998557, .215994023, .227994023, .239994023,
        .251994023, .263994023, .275994023, .287994023, .299994023,
        .311993726),
    "d014": (
        .133029229, .147029229, .159772569, .161028601, .174700442,
        .178498580, .181436642, .183088653, .184802990, .186140204,
        .187160624, .188031238, .188703410, .195998220, .209998220,
        .223998220, .237993073, .251993073, .265993073, .279993073,
        .293993073, .307992806, .321992806, .335992806, .349992806,
        .363992806),
    "d016": (
        .137029817, .153024986, .158942071, .169025822, .177264771,
        .180076510, .182894586, .184986673, .186519173, .187627000,
        .188653705, .191996783, .207996783, .223996783, .239992068,
        .255992068, .271992068, .287992068, .303992068, .319992068,
        .335991799, .351991799, .367991799, .383991799, .399991799,
        .415991013),
    "d1over60": (
        .138362442, .155023058, .158665131, .171691048, .177687929,
        .180591939, .183406411, .185490751, .187015407, .188225669,
        .189142062, .199996597, .216660746, .233324918, .249991531,
        .266658144, .283324756, .299991369, .316657982, .333324595,
        .349991207, .366657820, .383324433, .399991045, .416657658,
        .433324271),
}

DELTAS = {"audited-correlated-lift": .00722, "d008": .008,
          "d010": .010, "d012": .012, "d014": .014, "d016": .016}
DELTAS["d1over60"] = 1 / 60


def candidate_event(y, total, name, epsilon):
    delta = DELTAS[name]
    x = .010083333333333333 if name == "audited-correlated-lift" \
        else (.03747 - delta) / 3
    alpha1 = .25 + epsilon
    alpha2 = .25 + x + epsilon
    physical = y * np.longdouble(alpha2)
    large = physical > np.longdouble(delta)
    count = np.sum(large, axis=1)
    large_sum = np.sum(np.where(large, physical, 0), axis=1,
                       dtype=np.longdouble)
    schedule = np.asarray(SCHEDULES[name], dtype=np.longdouble)
    allowed = np.zeros(len(y), dtype=bool)
    allowed[count == 0] = True
    for r in range(1, len(schedule) + 1):
        selected = count == r
        allowed[selected] = large_sum[selected] <= schedule[r - 1]
    lower = np.longdouble(alpha1 / alpha2)
    allowed &= total > lower
    scale = float((alpha2 / float(M.ALPHA2)) ** 48)
    return allowed, count, scale, alpha1 / alpha2, alpha2


def run(seed, chains, burn, steps):
    _cert, _uncapped, basis, outer = M.load_target()
    polynomial = M.DecimalSievePolynomial(basis, outer, precision=80)
    rng = np.random.default_rng(seed)
    a1, a2 = M.as_longdouble(M.ALPHA1), M.as_longdouble(M.ALPHA2)
    z, logp = M.initialize_chains(rng, chains, polynomial, a1, a2)
    log_directional, log_radial = math.log(.22), math.log(.18)
    names = tuple(SCHEDULES)
    epsilons = (.0075, .0076)
    hits = {(name, epsilon): np.zeros(chains, dtype=np.int64)
            for name in names for epsilon in epsilons}
    hist = {(name, epsilon): [Counter() for _ in range(chains)]
            for name in names for epsilon in epsilons}
    accepted = proposed = 0
    started = time.monotonic()
    for iteration in range(burn + steps):
        radial = iteration % 4 == 0
        if radial:
            proposal = z + math.exp(log_radial) * rng.normal(size=chains)[:, None]
        else:
            noise = rng.normal(size=(chains, M.K))
            noise -= np.mean(noise, axis=1)[:, None]
            proposal = z + math.exp(log_directional) * noise
        proposal = np.asarray(proposal, dtype=np.longdouble)
        newlog, _, _ = M.log_target(proposal, polynomial, a1, a2)
        take = np.log(rng.random(chains)).astype(np.longdouble) < newlog - logp
        z[take], logp[take] = proposal[take], newlog[take]
        accepted += int(np.sum(take)); proposed += chains
        if iteration >= burn:
            points, _, _ = M.logistic_points(z, a2)
            y = points / a2
            total = np.sum(y, axis=1, dtype=np.longdouble)
            for name in names:
                for epsilon in epsilons:
                    event, count, *_ = candidate_event(y, total, name, epsilon)
                    hits[name, epsilon] += event
                    for chain in range(chains):
                        hist[name, epsilon][chain][int(count[chain])] += 1
        if (iteration + 1) % max(1, (burn + steps) // 4) == 0:
            print(f"step {iteration + 1}/{burn + steps}", flush=True)
    rows = []
    for name in names:
        for epsilon in epsilons:
            dummy_y = np.zeros((1, M.K), dtype=np.longdouble)
            _, _, scale, lower, alpha2 = candidate_event(
                dummy_y, np.ones(1), name, epsilon)
            rates = hits[name, epsilon] / steps
            rows.append({
                "name": name, "delta": DELTAS[name], "epsilon": epsilon,
                "alpha2": alpha2, "normalized_shell_lower": lower,
                "per_chain_event_rates": rates.tolist(),
                "event_rate": float(np.mean(rates)),
                "natural_dilation_scale48": scale,
                "relative_capped_outer_I_proxy": float(np.mean(rates) * scale),
                "count_histograms": [dict(sorted(row.items()))
                                     for row in hist[name, epsilon]],
            })
    return {"rows": rows, "acceptance": accepted / proposed,
            "wall_seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=2364901)
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--burn", type=int, default=800)
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.chains < 4 or min(args.burn, args.steps) < 1:
        parser.error("need at least four chains and positive lengths")
    result = run(args.seed, args.chains, args.burn, args.steps)
    result.update({
        "format": "adaptive-natural-d18-common-chain-proxy-v1",
        "status": "HEURISTIC ONLY", "rigorous": False,
        "theorem_ready": False,
        "source_sha256": SOURCE_SHA256,
        "script_sha256_before_output": sha(FILE),
        "sampling": {"seed": args.seed, "chains": args.chains,
                     "burn": args.burn, "steps": args.steps},
        "never_implies": ["an exact integral", "projection energy",
                          "a Rayleigh quotient", "Proposition 1", "H1<=236"],
    })
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise FileExistsError(args.output)
        args.output.write_text(payload)
    print(json.dumps({"acceptance": result["acceptance"],
                      "rows": [{k: row[k] for k in
                                ("name", "epsilon", "event_rate",
                                 "relative_capped_outer_I_proxy")}
                               for row in result["rows"]],
                      "wall_seconds": result["wall_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
