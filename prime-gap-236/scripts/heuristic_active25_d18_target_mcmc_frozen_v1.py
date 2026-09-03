#!/usr/bin/env python3
"""Target-density MCMC screen for active25 retention of the D18 outer band.

The chain targets the *positive* density F_outer(t)^2 on the uncapped shell
alpha1 < sum(t) < alpha2.  It estimates the probability of the audited
active25 cap under that density, hence the retained outer-I fraction.  A
second shell-total event has an independently computed exact probability and
is a mandatory calibration gate.

This is discovery code only.  It computes no capped J form, has no rigorous
error bound, and can never certify Proposition 1 or H_1 <= 236.
"""

from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
CERT = REPO / (
    "agents/exact-integrator/results/"
    "aquarter_fullsimplex_k48_B18_refined_exact.json")
UNCAPPED = REPO / (
    "results/wide_c722_B18_piecewise_cinner1_couter_natural_exact.json")
ANALYTIC = REPO / (
    "agents/audit/results/"
    "wide_c722_nonuniform_active25_tail_analytic_audit.json")
DILATION = REPO / "scripts/full_simplex_dilated_vector_proxy.py"
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
POINT = REPO / "agents/structural-basis/code/importance_point_eval.py"
PINS = {
    CERT: "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58",
    UNCAPPED: "49ecca1b962d06a8ee793e7ce0a3dcdf4ef1fd38595ccd86c784950636d903fd",
    ANALYTIC: "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
    DILATION: "3219047bd9d339e15946947f68bd6484d23af722337ba70771c488e3e1238794",
    SCAN: "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9",
    POINT: "ea88f6d29b744f59ad146bdebf9b2003a2d57e40eea5b7a03fb48f2309cdfc01",
}

K = 48
ALPHA1 = Q(103, 400)
ALPHA2 = Q(3211, 12000)
DELTA = Q(361, 50000)
SCHEDULE = (
    Q(597, 5000), Q(633, 5000), Q(669, 5000), Q(141, 1000),
    Q(737, 5000), Q(773, 5000), Q(1553, 10000), Q(809, 5000),
    Q(81, 500), Q(3329, 20000), Q(169, 1000), Q(339, 2000),
    Q(859, 5000), Q(1737, 10000), Q(219, 1250), Q(881, 5000),
    Q(441, 2500), Q(887, 5000), Q(891, 5000), Q(179, 1000),
    Q(449, 2500), Q(1801, 10000), Q(903, 5000), Q(1811, 10000),
    Q(363, 2000), Q(363, 2000),
)


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite JSON token {token}")))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def as_longdouble(value: Q):
    return np.longdouble(value.numerator) / np.longdouble(value.denominator)


class PowerSumOrbitEvaluator:
    """Fast evaluation of monomial-orbit sums via the power-sum recurrence."""

    def __init__(self, partitions):
        canonical = {tuple(sorted((int(x) for x in part), reverse=True))
                     for part in partitions}
        canonical.add(())
        # Close under the lower-cardinality terms in
        # p_r m_mu = mult_r(lambda)m_lambda + merged-coordinate terms.
        while True:
            enlarged = set(canonical)
            for part in canonical:
                if not part:
                    continue
                chosen = part[-1]
                base = list(part)
                base.remove(chosen)
                base = tuple(base)
                enlarged.add(base)
                for exponent in set(base):
                    merged = list(base)
                    merged.remove(exponent)
                    merged.append(exponent + chosen)
                    enlarged.add(tuple(sorted(merged, reverse=True)))
            if enlarged == canonical:
                break
            canonical = enlarged
        self.partitions = tuple(sorted(
            canonical, key=lambda part: (len(part), sum(part), part)))
        self.index = {part: i for i, part in enumerate(self.partitions)}
        self.max_power = max((max(part) for part in self.partitions if part),
                             default=0)
        recurrences = []
        for part in self.partitions:
            if not part:
                recurrences.append(None)
                continue
            chosen = part[-1]
            base = list(part)
            base.remove(chosen)
            base = tuple(base)
            if base not in self.index:
                raise ValueError("partition set is not downward closed")
            merges = []
            for exponent in sorted(set(base)):
                merged = list(base)
                merged.remove(exponent)
                merged.append(exponent + chosen)
                merged = tuple(sorted(merged, reverse=True))
                if merged not in self.index:
                    raise ValueError(
                        f"partition set lacks merged closure {merged}")
                merges.append((self.index[merged], merged.count(
                    exponent + chosen)))
            recurrences.append((chosen, self.index[base],
                                part.count(chosen), tuple(merges)))
        self.recurrences = tuple(recurrences)

    def evaluate(self, points):
        points = np.asarray(points, dtype=np.longdouble)
        if points.ndim != 2 or points.shape[1] <= 0 or \
                not np.isfinite(points).all():
            raise ValueError("points must be a finite two-dimensional array")
        count = points.shape[0]
        powers = {}
        current = np.ones_like(points)
        for exponent in range(1, self.max_power + 1):
            current = current * points
            powers[exponent] = np.sum(current, axis=1,
                                      dtype=np.longdouble)
        values = np.zeros((len(self.partitions), count),
                          dtype=np.longdouble)
        values[self.index[()]] = 1
        for index, recurrence in enumerate(self.recurrences):
            if recurrence is None:
                continue
            exponent, base, divisor, merges = recurrence
            answer = powers[exponent] * values[base]
            for merged, multiplicity in merges:
                answer = answer - multiplicity * values[merged]
            values[index] = answer / divisor
        return values


class SievePolynomialBatch:
    def __init__(self, basis, coefficients):
        if len(basis) != len(coefficients):
            raise ValueError("basis/coefficient mismatch")
        partitions = [tuple(lam) for _, lam in basis]
        self.orbits = PowerSumOrbitEvaluator(partitions)
        self.max_residual = max(a for a, _ in basis)
        matrix = np.zeros((len(self.orbits.partitions),
                           self.max_residual + 1), dtype=np.longdouble)
        raw = [as_longdouble(value) for value in coefficients]
        scale = max(abs(value) for value in raw)
        if not scale or not np.isfinite(scale):
            raise ArithmeticError("invalid coefficient scale")
        for (a, lam), value in zip(basis, raw):
            matrix[self.orbits.index[tuple(lam)], a] += value / scale
        self.coefficients = matrix
        self.scale = scale

    def evaluate(self, points):
        points = np.asarray(points, dtype=np.longdouble)
        orbit_values = self.orbits.evaluate(points)
        residual = 1 - np.sum(points, axis=1, dtype=np.longdouble)
        residual_powers = np.ones((self.max_residual + 1, len(points)),
                                  dtype=np.longdouble)
        for power in range(1, self.max_residual + 1):
            residual_powers[power] = residual_powers[power - 1] * residual
        by_orbit = self.coefficients @ residual_powers
        result = np.sum(orbit_values * by_orbit, axis=0,
                        dtype=np.longdouble)
        if not np.isfinite(result).all():
            raise ArithmeticError("nonfinite polynomial evaluation")
        return result


class DecimalSievePolynomial:
    """Cancellation-safe point evaluation for the refined D18 polynomial."""

    def __init__(self, basis, coefficients, precision=70):
        if len(basis) != len(coefficients) or precision < 50:
            raise ValueError("invalid Decimal polynomial input")
        self.orbits = PowerSumOrbitEvaluator([lam for _, lam in basis])
        self.max_residual = max(a for a, _ in basis)
        self.precision = precision
        with localcontext() as context:
            context.prec = precision
            raw = [Decimal(value.numerator) / Decimal(value.denominator)
                   for value in coefficients]
            self.scale = max(abs(value) for value in raw)
            matrix = [[Decimal(0) for _ in range(self.max_residual + 1)]
                      for _ in self.orbits.partitions]
            for (a, lam), value in zip(basis, raw):
                matrix[self.orbits.index[tuple(lam)]][a] += value / self.scale
            self.coefficients = tuple(tuple(row) for row in matrix)

    def evaluate_one_decimal(self, point):
        with localcontext() as context:
            context.prec = self.precision
            coordinates = [Decimal(str(value)) for value in point]
            power_sums = [Decimal(0)
                          for _ in range(self.orbits.max_power + 1)]
            for coordinate in coordinates:
                power = Decimal(1)
                for exponent in range(1, self.orbits.max_power + 1):
                    power *= coordinate
                    power_sums[exponent] += power
            values = [Decimal(0) for _ in self.orbits.partitions]
            values[self.orbits.index[()]] = Decimal(1)
            for index, recurrence in enumerate(self.orbits.recurrences):
                if recurrence is None:
                    continue
                exponent, base, divisor, merges = recurrence
                answer = power_sums[exponent] * values[base]
                for merged, multiplicity in merges:
                    answer -= multiplicity * values[merged]
                values[index] = answer / divisor
            residual = Decimal(1) - sum(coordinates, Decimal(0))
            residual_powers = [Decimal(1)]
            for _ in range(self.max_residual):
                residual_powers.append(residual_powers[-1] * residual)
            answer = Decimal(0)
            for orbit_value, coefficients in zip(values, self.coefficients):
                polynomial = sum(
                    (coefficient * residual_powers[power]
                     for power, coefficient in enumerate(coefficients)),
                    Decimal(0))
                answer += orbit_value * polynomial
            return +answer

    def evaluate(self, points):
        values = [self.evaluate_one_decimal(point) for point in points]
        return np.array([np.longdouble(str(value)) for value in values],
                        dtype=np.longdouble)


def load_target():
    for path, expected in PINS.items():
        if sha256(path) != expected:
            raise RuntimeError(f"pinned target input changed: {path}")
    cert = strict_json(CERT)
    uncapped = strict_json(UNCAPPED)
    analytic = strict_json(ANALYTIC)
    if ((cert.get("k"), cert.get("degree")) != (K, 18) or
            uncapped.get("certificate_sha256") != PINS[CERT] or
            analytic.get("status") != "AUDIT PASS" or
            analytic.get("parameters", {}).get(
                "outer_schedule_through_first_empty") !=
            [str(x) for x in SCHEDULE]):
        raise ValueError("target identity changed")
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in cert["basis"])
    vector = tuple(Q(x) for x in cert["rational_vector"])
    if len(basis) != 471 or len(set(basis)) != 471:
        raise ValueError("unexpected D18 basis")
    dilation = load_module("target_mcmc_dilation", DILATION)
    outer = tuple(dilation.dilate_vector(
        basis, vector, ALPHA1 / ALPHA2))
    return cert, uncapped, basis, outer


def validate_fast_evaluator(batch, basis, coefficients, seed):
    point_module = load_module("target_mcmc_point_oracle", POINT)
    oracle = point_module.MonomialSymmetricPointEvaluator(
        [lam for _, lam in basis])
    rng = np.random.default_rng(seed)
    points = rng.dirichlet(np.ones(K + 1), size=4)[:, :K] * float(ALPHA2)
    observed = [batch.evaluate_one_decimal(point) for point in points]
    with localcontext() as context:
        context.prec = batch.precision
        scaled = [Decimal(value.numerator) / Decimal(value.denominator) /
                  batch.scale for value in coefficients]
        expected = [point_module.evaluate_sieve_polynomial(
            [Decimal(str(value)) for value in point], basis, scaled, oracle)
                    for point in points]
        absolute = max(abs(left - right)
                       for left, right in zip(observed, expected))
        relative = max(abs(left - right) /
                       max(abs(right), Decimal("1e-100"))
                       for left, right in zip(observed, expected))
    if relative > Decimal("1e-40"):
        raise ArithmeticError("Decimal orbit evaluator failed the point oracle")
    return str(absolute), str(relative)


def shell_exact_calibration(basis, outer, uncapped):
    scan = load_module("target_mcmc_scan", SCAN)
    scan.self_test()
    midpoint = (ALPHA1 + ALPHA2) / 2
    i1, *_ = scan.direct_forms(K, basis, outer, ALPHA1, ALPHA1, DELTA)
    im, *_ = scan.direct_forms(K, basis, outer, midpoint, midpoint, DELTA)
    i2, *_ = scan.direct_forms(K, basis, outer, ALPHA2, ALPHA2, DELTA)
    shell = i2 - i1
    if shell != Q(uncapped["I_matrix"][1][1]) or not i1 < im < i2:
        raise ArithmeticError("exact shell calibration identity failed")
    return midpoint, (im - i1) / shell


def logistic_points(z, alpha2):
    z = np.asarray(z, dtype=np.longdouble)
    maximum = np.maximum(np.max(z, axis=1), np.longdouble(0))
    weights = np.exp(z - maximum[:, None])
    slack = np.exp(-maximum)
    total = np.sum(weights, axis=1, dtype=np.longdouble) + slack
    y = weights / total[:, None]
    y_slack = slack / total
    return alpha2 * y, y, y_slack


def log_target(z, polynomial, alpha1, alpha2):
    points, y, slack = logistic_points(z, alpha2)
    sums = np.sum(points, axis=1, dtype=np.longdouble)
    values = polynomial.evaluate(points)
    valid = ((sums > alpha1) & (sums < alpha2) &
             (np.abs(values) > np.longdouble(0)) &
             (slack > np.longdouble(0)) & (y > 0).all(axis=1))
    result = np.full(len(z), -np.inf, dtype=np.longdouble)
    if np.any(valid):
        result[valid] = (2 * np.log(np.abs(values[valid])) +
                         np.sum(np.log(y[valid]), axis=1,
                                dtype=np.longdouble) +
                         np.log(slack[valid]))
    return result, points, sums


def cap_indicator(points, delta, schedule):
    large = points > delta
    counts = np.sum(large, axis=1)
    sums = np.sum(np.where(large, points, 0), axis=1,
                  dtype=np.longdouble)
    result = counts == 0
    for count in range(1, len(schedule) + 1):
        result |= ((counts == count) & (sums <= schedule[count - 1]))
    return result, counts


def rhat(chains):
    chains = np.asarray(chains, dtype=float)
    m, n = chains.shape
    if m < 2 or n < 2:
        return math.inf
    within = np.mean(np.var(chains, axis=1, ddof=1))
    between = n * np.var(np.mean(chains, axis=1), ddof=1)
    variance = (n - 1) * within / n + between / n
    if within == 0:
        return 1.0 if between == 0 else math.inf
    return math.sqrt(max(0.0, variance / within))


def autocorrelation_ess(chains):
    chains = np.asarray(chains, dtype=float)
    m, n = chains.shape
    if n < 4:
        return 0.0
    total_tau = 0.0
    usable = 0
    for row in chains:
        centered = row - np.mean(row)
        variance = np.dot(centered, centered)
        if variance == 0:
            continue
        size = 1 << (2 * n - 1).bit_length()
        spectrum = np.fft.rfft(centered, size)
        acov = np.fft.irfft(spectrum * np.conjugate(spectrum), size)[:n]
        acorr = acov / acov[0]
        tau = 1.0
        for lag in range(1, n - 1, 2):
            pair = acorr[lag] + acorr[lag + 1]
            if pair <= 0:
                break
            tau += 2 * pair
        total_tau += max(1.0, tau)
        usable += 1
    if not usable:
        return 0.0
    return m * n / (total_tau / usable)


def initialize_chains(rng, chains, polynomial, alpha1, alpha2):
    rows = []
    while len(rows) < chains:
        y = rng.dirichlet(np.ones(K + 1), size=chains * 2)
        points = y[:, :K] * float(alpha2)
        mask = np.sum(points, axis=1) > float(alpha1)
        for row in y[mask]:
            rows.append(np.log(row[:K] / row[K]))
            if len(rows) == chains:
                break
    z = np.asarray(rows, dtype=np.longdouble)
    logp, _, _ = log_target(z, polynomial, alpha1, alpha2)
    if not np.isfinite(logp).all():
        raise ArithmeticError("nonfinite initial chain target")
    return z, logp


def run_mcmc(polynomial, midpoint, *, seed, chains, burn, steps, thin):
    if min(chains, burn, steps, thin) <= 0 or chains < 4:
        raise ValueError("invalid MCMC schedule")
    rng = np.random.default_rng(seed)
    a1, a2 = as_longdouble(ALPHA1), as_longdouble(ALPHA2)
    delta = as_longdouble(DELTA)
    schedule = np.array([as_longdouble(x) for x in SCHEDULE],
                        dtype=np.longdouble)
    z, logp = initialize_chains(rng, chains, polynomial, a1, a2)
    log_directional = math.log(0.22)
    log_radial = math.log(0.18)
    accepted = np.zeros(2, dtype=np.int64)
    proposed = np.zeros(2, dtype=np.int64)
    cap_rows = [[] for _ in range(chains)]
    mid_rows = [[] for _ in range(chains)]
    count_hist = [Counter() for _ in range(chains)]
    total_steps = burn + steps
    for iteration in range(total_steps):
        kind = 1 if iteration % 4 == 0 else 0
        if kind == 0:
            noise = rng.normal(size=(chains, K))
            noise -= np.mean(noise, axis=1)[:, None]
            proposal = z + math.exp(log_directional) * noise
        else:
            shift = rng.normal(size=chains)[:, None]
            proposal = z + math.exp(log_radial) * shift
        proposal = np.asarray(proposal, dtype=np.longdouble)
        proposed[kind] += chains
        new_logp, _, _ = log_target(proposal, polynomial, a1, a2)
        logu = np.log(rng.random(chains)).astype(np.longdouble)
        take = logu < new_logp - logp
        accepted[kind] += int(np.sum(take))
        z[take] = proposal[take]
        logp[take] = new_logp[take]
        if iteration < burn and (iteration + 1) % 100 == 0:
            rate = accepted[kind] / max(1, proposed[kind])
            if kind == 0:
                log_directional += 0.12 * (rate - 0.234)
                log_directional = min(0.5, max(-5.0, log_directional))
            else:
                log_radial += 0.12 * (rate - 0.35)
                log_radial = min(0.5, max(-5.0, log_radial))
            accepted[kind] = proposed[kind] = 0
        if iteration >= burn and (iteration - burn) % thin == 0:
            points, _, _ = logistic_points(z, a2)
            sums = np.sum(points, axis=1, dtype=np.longdouble)
            cap, counts = cap_indicator(points, delta, schedule)
            mid = sums <= as_longdouble(midpoint)
            for chain in range(chains):
                cap_rows[chain].append(int(cap[chain]))
                mid_rows[chain].append(int(mid[chain]))
                count_hist[chain][int(counts[chain])] += 1
    cap_array = np.asarray(cap_rows, dtype=np.int8)
    mid_array = np.asarray(mid_rows, dtype=np.int8)
    return {
        "cap": cap_array,
        "mid": mid_array,
        "count_histograms": count_hist,
        "directional_scale": math.exp(log_directional),
        "radial_scale": math.exp(log_radial),
        "final_log_targets": [str(x) for x in logp],
    }


def summarize_binary(chains):
    values = np.asarray(chains, dtype=float)
    mean = float(np.mean(values))
    ess = float(autocorrelation_ess(values))
    standard_error = (math.sqrt(max(0.0, mean * (1 - mean) / ess))
                      if ess > 0 else math.inf)
    return {"mean": mean, "rhat": float(rhat(values)), "ess": ess,
            "standard_error": standard_error,
            "per_chain_means": [float(x) for x in np.mean(values, axis=1)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=23648)
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--burn", type=int, default=5000)
    parser.add_argument("--steps", type=int, default=20000)
    parser.add_argument("--thin", type=int, default=2)
    args = parser.parse_args()
    self_start = FILE.read_bytes()
    input_start = {path: path.read_bytes() for path in PINS}
    cert, uncapped, basis, outer = load_target()
    polynomial = DecimalSievePolynomial(basis, outer, precision=80)
    absolute, relative = validate_fast_evaluator(
        polynomial, basis, outer, args.seed + 1)
    exact_started = time.monotonic()
    midpoint, exact_mid_probability = shell_exact_calibration(
        basis, outer, uncapped)
    exact_seconds = time.monotonic() - exact_started
    started = time.monotonic()
    samples = run_mcmc(
        polynomial, midpoint, seed=args.seed, chains=args.chains,
        burn=args.burn, steps=args.steps, thin=args.thin)
    mcmc_seconds = time.monotonic() - started
    cap = summarize_binary(samples["cap"])
    mid = summarize_binary(samples["mid"])
    exact_mid_float = float(exact_mid_probability)
    calibration_z = ((mid["mean"] - exact_mid_float) /
                     mid["standard_error"]
                     if mid["standard_error"] > 0 else math.inf)
    calibration_pass = (mid["rhat"] <= 1.05 and mid["ess"] >= 200 and
                        abs(calibration_z) <= 5)
    cap_diagnostic_pass = cap["rhat"] <= 1.05 and cap["ess"] >= 200
    if (FILE.read_bytes() != self_start or
            any(path.read_bytes() != data for path, data in input_start.items())):
        raise RuntimeError("MCMC source closure changed")
    result = {
        "basis_dimension": len(basis),
        "cap_event": "active25 scheduled H inside alpha1<sum(t)<alpha2",
        "cap_retained_I_estimate": cap,
        "cap_sampling_diagnostics_pass": cap_diagnostic_pass,
        "claim_scope": "heuristic outer-I retention only; no capped J",
        "count_histograms": [dict(sorted(row.items()))
                             for row in samples["count_histograms"]],
        "exact_calibration": {
            "event": f"sum(t)<={midpoint}",
            "probability": str(exact_mid_probability),
            "probability_decimal": format(exact_mid_float, ".17g"),
            "observed": mid,
            "z_score": calibration_z,
        },
        "exact_calibration_seconds": exact_seconds,
        "fast_evaluator_oracle_max_absolute": absolute,
        "fast_evaluator_oracle_max_relative": relative,
        "format": "active25-d18-target-density-mcmc-v1",
        "mcmc_calibration_pass": calibration_pass,
        "mcmc_seconds": mcmc_seconds,
        "never_implies": ["a rigorous integral", "a Rayleigh quotient",
                          "Proposition 1", "H1<=236"],
        "parameters": {"k": K, "alpha1": str(ALPHA1),
                       "alpha2": str(ALPHA2), "delta": str(DELTA),
                       "schedule": [str(x) for x in SCHEDULE]},
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "proposal": {"directional_scale": samples["directional_scale"],
                     "radial_scale": samples["radial_scale"]},
        "rigorous": False,
        "schedule": {"seed": args.seed, "chains": args.chains,
                     "burn": args.burn, "steps": args.steps,
                     "thin": args.thin,
                     "saved_per_chain": samples["cap"].shape[1]},
        "script_sha256": sha256(self_start),
        "source_hashes": {str(path.relative_to(REPO)): digest
                          for path, digest in PINS.items()},
        "status": ("HEURISTIC CALIBRATED" if calibration_pass and
                   cap_diagnostic_pass else "HEURISTIC CALIBRATION FAIL"),
        "theorem_ready": False,
    }
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({
        "calibration_z": calibration_z,
        "cap_retained_I_estimate": cap["mean"],
        "output_sha256": sha256(payload),
        "status": result["status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
