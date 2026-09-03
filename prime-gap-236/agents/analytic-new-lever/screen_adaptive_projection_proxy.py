#!/usr/bin/env python3
"""MCMC screen for the retained D18 representer energy int_V G_F^2.

For the fixed inner D18 polynomial F at alpha=103/400, put

    G_F(t) = sum_i int F(t_1,...,t_{i-1},s,t_{i+1},...) ds.

The chain targets G_F^2 on the uncapped baseline outer shell.  Event rates
therefore estimate the fraction of that common representer energy retained
by each candidate cap.  This is a calibrated ranking proxy only: floating
point and finite-chain output is not an exact integral or quotient.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
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
TARGET_SOURCE = REPO / "scripts/heuristic_active25_d18_target_mcmc.py"
TARGET_SHA = "28d6dacf8062f0dc6f5948d1fc3a1bd994ca4f39454931f9ce173bdb0aa84f8d"
SCAN_SOURCE = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
SCAN_SHA = "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9"
CERT = REPO / (
    "agents/exact-integrator/results/aquarter_fullsimplex_k48_B18_refined_exact.json")
CERT_SHA = "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58"
SCHEDULE_SOURCE = FILE.with_name("screen_adaptive_d18_proxy.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


for path, expected in ((TARGET_SOURCE, TARGET_SHA), (SCAN_SOURCE, SCAN_SHA),
                       (CERT, CERT_SHA)):
    if sha(path) != expected:
        raise RuntimeError(f"projection proxy dependency changed: {path}")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("projection_proxy_target", TARGET_SOURCE)
S = load("projection_proxy_scan", SCAN_SOURCE)
C = load("projection_proxy_schedules", SCHEDULE_SOURCE)
K = 48
ALPHA1 = Q(103, 400)
ALPHA2 = Q(3211, 12000)


class MarginalSum:
    def __init__(self):
        cert = json.loads(CERT.read_text())
        basis = [(int(a), tuple(int(x) for x in lam))
                 for a, lam in cert["basis"]]
        vector = [Q(x) for x in cert["rational_vector"]]
        self.terms = S.marginal_polynomial(basis, vector, K, ALPHA1)
        self.orbits = M.PowerSumOrbitEvaluator(
            [lam for _, lam in self.terms])
        self.max_residual = max(power for power, _ in self.terms)
        self.scale = max(abs(value) for value in self.terms.values())
        matrix = np.zeros((len(self.orbits.partitions),
                           self.max_residual + 1), dtype=np.longdouble)
        for (power, lam), value in self.terms.items():
            scaled = value / self.scale
            matrix[self.orbits.index[lam], power] += (
                np.longdouble(scaled.numerator) /
                np.longdouble(scaled.denominator))
        self.matrix = matrix

    def evaluate(self, points):
        points = np.asarray(points, dtype=np.longdouble)
        n = len(points)
        deleted = np.repeat(points, K, axis=0)
        deleted[np.arange(n * K), np.tile(np.arange(K), n)] = 0
        orbit = self.orbits.evaluate(deleted)
        residual = (np.longdouble(ALPHA1.numerator) /
                    np.longdouble(ALPHA1.denominator) -
                    np.sum(deleted, axis=1, dtype=np.longdouble))
        powers = np.ones((n * K, self.max_residual + 1),
                         dtype=np.longdouble)
        for power in range(1, self.max_residual + 1):
            powers[:, power] = powers[:, power - 1] * residual
        values = np.einsum("pq,pn,nq->n", self.matrix, orbit, powers,
                           optimize=True)
        values[residual <= 0] = 0
        return np.sum(values.reshape(n, K), axis=1, dtype=np.longdouble)

    def decimal_one(self, point):
        """Independent 70-digit recurrence for the startup spot checks."""
        with localcontext() as context:
            context.prec = 70
            alpha = Decimal(ALPHA1.numerator) / Decimal(ALPHA1.denominator)
            scale = Decimal(self.scale.numerator) / Decimal(self.scale.denominator)
            coefficients = {
                key: Decimal(value.numerator) / Decimal(value.denominator) / scale
                for key, value in self.terms.items()
            }
            answer = Decimal(0)
            for omitted in range(K):
                coordinates = [Decimal(str(value)) for i, value in enumerate(point)
                               if i != omitted]
                residual = alpha - sum(coordinates, Decimal(0))
                if residual <= 0:
                    continue
                power_sums = [Decimal(0)] * (self.orbits.max_power + 1)
                for coordinate in coordinates:
                    value = Decimal(1)
                    for exponent in range(1, len(power_sums)):
                        value *= coordinate
                        power_sums[exponent] += value
                orbit = [Decimal(0)] * len(self.orbits.partitions)
                orbit[self.orbits.index[()]] = Decimal(1)
                for index, recurrence in enumerate(self.orbits.recurrences):
                    if recurrence is None:
                        continue
                    exponent, base, divisor, merges = recurrence
                    value = power_sums[exponent] * orbit[base]
                    for merged, multiplicity in merges:
                        value -= multiplicity * orbit[merged]
                    orbit[index] = value / divisor
                rp = Decimal(1)
                for power in range(self.max_residual + 1):
                    for (p, lam), coefficient in coefficients.items():
                        if p == power:
                            answer += coefficient * orbit[
                                self.orbits.index[lam]] * rp
                    rp *= residual
            return +answer


def log_target(z, evaluator):
    a2 = np.longdouble(ALPHA2.numerator) / np.longdouble(ALPHA2.denominator)
    points, y, slack = M.logistic_points(z, a2)
    sums = np.sum(points, axis=1, dtype=np.longdouble)
    values = evaluator.evaluate(points)
    a1 = np.longdouble(ALPHA1.numerator) / np.longdouble(ALPHA1.denominator)
    valid = ((sums > a1) & (sums < a2) & (np.abs(values) > 0) &
             (slack > 0) & (y > 0).all(axis=1))
    result = np.full(len(z), -np.inf, dtype=np.longdouble)
    if np.any(valid):
        result[valid] = (2 * np.log(np.abs(values[valid])) +
                         np.sum(np.log(y[valid]), axis=1,
                                dtype=np.longdouble) +
                         np.log(slack[valid]))
    return result, points


def initialize(rng, chains, evaluator):
    a2 = float(ALPHA2)
    while True:
        y = rng.dirichlet(np.ones(K + 1), size=chains * 3)
        points = y[:, :K] * a2
        mask = np.sum(points, axis=1) > float(ALPHA1)
        rows = y[mask][:chains]
        if len(rows) < chains:
            continue
        z = np.log(rows[:, :K] / rows[:, K, None]).astype(np.longdouble)
        logp, _ = log_target(z, evaluator)
        if np.isfinite(logp).all():
            return z, logp


def event(points, name):
    delta = C.DELTAS[name]
    x = .010083333333333333 if name == "audited-correlated-lift" \
        else (.03747 - delta) / 3
    alpha2 = .25 + x + .0075
    large = points > np.longdouble(delta)
    count = np.sum(large, axis=1)
    large_sum = np.sum(np.where(large, points, 0), axis=1,
                       dtype=np.longdouble)
    schedule = np.asarray(C.SCHEDULES[name], dtype=np.longdouble)
    result = ((np.sum(points, axis=1, dtype=np.longdouble) < alpha2) &
              (np.sum(points, axis=1, dtype=np.longdouble) > float(ALPHA1)))
    cap = count == 0
    for r in range(1, len(schedule) + 1):
        selected = count == r
        cap |= selected & (large_sum <= schedule[r - 1])
    return result & cap, count


def run(seed, chains, burn, steps):
    evaluator = MarginalSum()
    # Deterministic cancellation check in the shell.
    rng = np.random.default_rng(seed + 1)
    y = rng.dirichlet(np.ones(K + 1), size=2)
    points = y[:, :K] * float(ALPHA2)
    # Radially push both points into the outer shell.
    points *= np.array([.99, .98])[:, None] / np.sum(points, axis=1)[:, None]
    points *= np.array([float(ALPHA2), float(ALPHA2)])[:, None]
    fast = evaluator.evaluate(points)
    exact = [evaluator.decimal_one(row) for row in points]
    relative = max(float(abs(Decimal(str(a)) - b) /
                         max(abs(b), Decimal("1e-100")))
                   for a, b in zip(fast, exact))
    if relative > 1e-7:
        raise ArithmeticError("marginal-sum long-double spot oracle failed")

    rng = np.random.default_rng(seed)
    z, logp = initialize(rng, chains, evaluator)
    names = tuple(C.SCHEDULES)
    hits = {name: np.zeros(chains, dtype=np.int64) for name in names}
    by_count = {name: [dict() for _ in range(chains)] for name in names}
    accepted = proposed = 0
    started = time.monotonic()
    for iteration in range(burn + steps):
        if iteration % 4:
            noise = rng.normal(size=(chains, K))
            noise -= np.mean(noise, axis=1)[:, None]
            proposal = z + .42 * noise
        else:
            proposal = z + .18 * rng.normal(size=chains)[:, None]
        proposal = np.asarray(proposal, dtype=np.longdouble)
        newlog, newpoints = log_target(proposal, evaluator)
        take = np.log(rng.random(chains)).astype(np.longdouble) < newlog - logp
        z[take], logp[take] = proposal[take], newlog[take]
        accepted += int(np.sum(take)); proposed += chains
        if iteration >= burn:
            a2 = np.longdouble(ALPHA2.numerator) / np.longdouble(ALPHA2.denominator)
            points, _, _ = M.logistic_points(z, a2)
            for name in names:
                chosen, count = event(points, name)
                hits[name] += chosen
                for chain in range(chains):
                    key = int(count[chain])
                    row = by_count[name][chain]
                    row[key] = row.get(key, 0) + int(chosen[chain])
        if (iteration + 1) % max(1, (burn + steps) // 4) == 0:
            print(f"step {iteration + 1}/{burn + steps}", flush=True)
    rows = []
    for name in names:
        rates = hits[name] / steps
        rows.append({"name": name, "delta": C.DELTAS[name],
                     "per_chain_energy_retention": rates.tolist(),
                     "energy_retention": float(np.mean(rates)),
                     "retained_hits_by_count": by_count[name]})
    return {"rows": rows, "acceptance": accepted / proposed,
            "spot_oracle_max_relative": relative,
            "wall_seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=2364902)
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--burn", type=int, default=600)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.seed, args.chains, args.burn, args.steps)
    result.update({
        "format": "adaptive-d18-representer-energy-mcmc-proxy-v1",
        "status": "HEURISTIC ONLY", "rigorous": False,
        "theorem_ready": False,
        "criterion": "rank candidates by retained int_V G_F(t)^2 dt",
        "source_hashes": {str(TARGET_SOURCE.relative_to(REPO)): TARGET_SHA,
                          str(SCAN_SOURCE.relative_to(REPO)): SCAN_SHA,
                          str(CERT.relative_to(REPO)): CERT_SHA},
        "sampling": {"seed": args.seed, "chains": args.chains,
                     "burn": args.burn, "steps": args.steps},
        "script_sha256_before_output": sha(FILE),
        "never_implies": ["an exact integral", "a projection lower bound",
                          "a Rayleigh quotient", "Proposition 1", "H1<=236"],
    })
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise FileExistsError(args.output)
        args.output.write_text(payload)
    print(json.dumps({"acceptance": result["acceptance"],
                      "spot_oracle_max_relative": result["spot_oracle_max_relative"],
                      "rows": [{"name": row["name"],
                                "energy_retention": row["energy_retention"],
                                "per_chain": row["per_chain_energy_retention"]}
                               for row in result["rows"]],
                      "wall_seconds": result["wall_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
