#!/usr/bin/env python3
"""Natural-D18 h^2 bridge for absolute and capped Riesz energy.

The chain targets the squared, naturally dilated D18 outer coordinate h^2 on
the full radial shell.  Its normalization A11 and cross moment B01 are exact.
Consequently

  I(G)/I(F) = (A11/A00) E_h2[(G/h)^2],
  B01/A11  = E_h2[G/h].

The second identity is a mandatory orientation/mixing calibration.  Samples
also give the G^2-weighted count and large-sum distribution by weighting each
h^2 draw with (G/h)^2.  This remains finite-chain discovery evidence, not a
rigorous bound or target launch.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time


os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
CORE = REPO / (
    "agents/structural-basis/code/active25_d18_cap_adapted_oracle_v1.py")
CORE_SHA256 = (
    "7258643c15d5ca26a1025ead96f8a6d2a6a9170e639913d2d272007b51e19840")
SUPPORT = REPO / "agents/analytic-new-lever/adaptive_support_v1_exact.json"
SUPPORT_SHA256 = (
    "b7070c2677815b22a86b5a55ce41b3a2477d593495062256356a5df2a37befa7")
CONTRACTION = REPO / (
    "agents/structural-basis/results/"
    "d1over60_d18_uncapped_pencil_exact_v1.json")
CONTRACTION_SHA256 = (
    "3bfaafb532da80a17bb40e4a2cfb94090beda8ca6df43acb07c4f531ce5be02f")
VERIFIED_WRAPPER = REPO / (
    "agents/structural-basis/code/active25_d18_verified_cap_oracle_v1.py")
VERIFIED_WRAPPER_SHA256 = (
    "d134832dbce0215e2e7b6d1fa70d71c4e855f7fdc1625b6a906182beef5f697e")
TWO_BAND_CHECKER = REPO / (
    "agents/analytic-new-lever/verify_two_outer_band_v1.py")
TWO_BAND_CHECKER_SHA256 = (
    "187a87f6c29532645100d9a91b94ce8038c38511dfff22326efe9722ea0f8001")
TWO_BAND_RESULT = REPO / (
    "agents/analytic-new-lever/two_outer_band_v1_exact.json")
TWO_BAND_RESULT_SHA256 = (
    "c74da6b53d351df7df00435709bde048d50ddd5d75ff42ad631b2b029627bdee")
TWO_BAND_GEOMETRY = "d1over60_two_band_verified"


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path, expected):
    if sha256(path) != expected:
        raise RuntimeError(f"pinned bridge dependency changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def configure(module, geometry):
    if geometry == "audited":
        module.configure_geometry("audited")
        return
    if geometry not in ("d1over60_verified", TWO_BAND_GEOMETRY):
        raise ValueError("bridge geometry lacks an exact natural contraction")
    wrapper = load("d18_verified_cap_bridge_geometry", VERIFIED_WRAPPER,
                   VERIFIED_WRAPPER_SHA256)
    module.GEOMETRIES[geometry] = wrapper.verified_geometry(module)
    module.configure_geometry(geometry)


def two_band_geometry(module):
    if (sha256(TWO_BAND_CHECKER) != TWO_BAND_CHECKER_SHA256 or
            sha256(TWO_BAND_RESULT) != TWO_BAND_RESULT_SHA256):
        raise RuntimeError("pinned two-band analytic support changed")
    data = module.strict_json(TWO_BAND_RESULT)
    parameters = data.get("parameters", {})
    lower = tuple(Q(value) for value in
                  parameters.get("lower_schedule_through_first_empty", ()))
    upper = tuple(Q(value) for value in
                  parameters.get("upper_schedule_through_first_empty", ()))
    expected_lower = tuple(Q(value, 1_000_000) for value in (
        139683, 156347, 157797, 173014, 180929, 183753,
        186776, 188864, 190396, 191607, 192583, 199985))
    expected_upper = tuple(Q(value, 1_000_000) for value in (
        138360, 155020, 158662, 171688, 177684, 180588,
        183402, 185486, 187011, 188221, 189137, 189137))
    if (data.get("status") !=
            "EXACT TWO-OUTER-BAND ANALYTIC SUPPORT PASS" or
            data.get("checker_sha256") != TWO_BAND_CHECKER_SHA256 or
            parameters.get("A") != [
                "-3/400", "1/4", "256241/1000000", "231241/900000"] or
            parameters.get("alpha") != [
                "103/400", "263741/1000000", "237991/900000"] or
            parameters.get("lower_width_fraction_of_outer") != "9/10" or
            lower != expected_lower or upper != expected_upper):
        raise ValueError("two-band support geometry mismatch")
    extend = lambda row: row + (row[-1],) * (26 - len(row))
    return {
        "boundary": Q(263741, 1_000_000),
        "lower_eta_sensitivity": Q(248741, 1_000_000),
        "lower_schedule": extend(lower),
        "upper_schedule": extend(upper),
        "result_sha256": TWO_BAND_RESULT_SHA256,
        "checker_sha256": TWO_BAND_CHECKER_SHA256,
    }


def exact_forms(module, geometry, cert, uncapped):
    if geometry == "audited":
        a00 = Q(cert["exact_denominator"])
        a11 = Q(uncapped["I_matrix"][1][1])
        b01 = Q(uncapped["kJ_matrix"][0][1])
        source = module.UNCAPPED
        source_sha = module.PINS[source]
    else:
        if sha256(CONTRACTION) != CONTRACTION_SHA256:
            raise RuntimeError("pinned exact d1over60 contraction changed")
        data = module.strict_json(CONTRACTION)
        expected = {
            "k": 48, "alpha1": "103/400",
            "alpha2": "237991/900000", "eta1": "97/400",
            "eta2": "224491/900000", "delta": "1/60",
            "outer_c": "231750/237991",
        }
        if (data.get("format") !=
                "parameterized-d18-uncapped-pencil-exact-v1" or
                data.get("rigorous_values") is not True or
                data.get("parameters") != expected):
            raise ValueError("exact d1over60 contraction geometry mismatch")
        a00 = Q(data["I_matrix"][0][0])
        a11 = Q(data["I_matrix"][1][1])
        b01 = Q(data["kJ_matrix"][0][1])
        if Q(data["natural_projection_over_inner_I"]) != (
                b01 ** 2 / (a11 * a00)):
            raise ArithmeticError("exact d1over60 projection mismatch")
        source, source_sha = CONTRACTION, CONTRACTION_SHA256
    if min(a00, a11, b01) <= 0:
        raise ArithmeticError("bridge requires positive exact forms")
    return {
        "A11_over_A00": a11 / a00,
        "B01_over_A00": b01 / a00,
        "B01_over_A11": b01 / a11,
        "projection_over_A00": b01 ** 2 / (a11 * a00),
        "source_path": str(source.relative_to(REPO)),
        "source_sha256": source_sha,
    }


def logistic_points(z, alpha2):
    z = np.asarray(z, dtype=np.longdouble)
    maximum = np.maximum(np.max(z, axis=1), np.longdouble(0))
    exponentials = np.exp(z - maximum[:, None])
    slack_numerator = np.exp(-maximum)
    denominator = slack_numerator + np.sum(
        exponentials, axis=1, dtype=np.longdouble)
    y = exponentials / denominator[:, None]
    slack = slack_numerator / denominator
    return np.longdouble(alpha2) * y, y, slack


def log_h2_target(z, natural, alpha1, alpha2):
    points, y, slack = logistic_points(z, alpha2)
    total = np.sum(points, axis=1, dtype=np.longdouble)
    h = natural.evaluate(points)
    valid = ((total > np.longdouble(alpha1)) &
             (total < np.longdouble(alpha2)) &
             (np.abs(h) > 0) & (slack > 0) & (y > 0).all(axis=1))
    answer = np.full(len(z), -np.inf, dtype=np.longdouble)
    if np.any(valid):
        answer[valid] = (2 * np.log(np.abs(h[valid])) +
                         np.sum(np.log(y[valid]), axis=1,
                                dtype=np.longdouble) +
                         np.log(slack[valid]))
    return answer, points


def initialize(rng, chains, natural, alpha1, alpha2, dimension):
    collected = []
    while sum(len(row) for row in collected) < chains:
        simplex = rng.dirichlet(np.ones(dimension + 1), size=chains * 4)
        points = simplex[:, :dimension] * float(alpha2)
        chosen = simplex[np.sum(points, axis=1) > float(alpha1)]
        if len(chosen):
            collected.append(chosen)
    rows = np.concatenate(collected)[:chains]
    z = np.log(rows[:, :dimension] / rows[:, dimension, None]).astype(
        np.longdouble)
    logp, _ = log_h2_target(z, natural, alpha1, alpha2)
    if not np.isfinite(logp).all():
        return initialize(rng, chains, natural, alpha1, alpha2, dimension)
    return z, logp


def radial_volume_draw(rng, samples, dimension, alpha1, alpha2):
    """Draw S with density proportional to S^(dimension-1) on the shell."""
    lower = np.longdouble(alpha1) ** dimension
    upper = np.longdouble(alpha2) ** dimension
    return (lower + rng.random(samples).astype(np.longdouble) *
            (upper - lower)) ** (np.longdouble(1) / dimension)


def split_rhat(values):
    values = np.asarray(values, dtype=np.longdouble)
    chains, draws = values.shape
    half = draws // 2
    split = np.concatenate((values[:, :half], values[:, -half:]), axis=0)
    within = np.mean(np.var(split, axis=1, ddof=1), dtype=np.longdouble)
    between = half * np.var(
        np.mean(split, axis=1, dtype=np.longdouble), ddof=1)
    variance = (half - 1) / half * within + between / half
    return float(np.sqrt(variance / within)) if within > 0 else math.inf


def weighted_quantiles(values, weights, probabilities):
    values = np.asarray(values, dtype=np.longdouble)
    weights = np.asarray(weights, dtype=np.longdouble)
    positive = weights > 0
    if not np.any(positive):
        return [None] * len(probabilities)
    order = np.argsort(values[positive])
    x = values[positive][order]
    cumulative = np.cumsum(weights[positive][order], dtype=np.longdouble)
    result = []
    for probability in probabilities:
        index = np.searchsorted(
            cumulative, np.longdouble(str(probability)) * cumulative[-1],
            side="left")
        result.append(float(x[min(int(index), len(x) - 1)]))
    return result


def schedule_membership(module, counts, large_sums, schedule):
    answer = counts == 0
    for count, bound in enumerate(schedule, start=1):
        if bound > count * module.DELTA:
            answer |= ((counts == count) &
                       (large_sums <= module.ld(bound)))
    return answer


def cap_membership(module, counts, large_sums, *, geometry, totals=None,
                   band_geometry=None):
    if geometry != TWO_BAND_GEOMETRY:
        return schedule_membership(
            module, counts, large_sums, module.SCHEDULE)
    if totals is None or band_geometry is None:
        raise ValueError("two-band membership needs radial totals")
    lower = totals <= module.ld(band_geometry["boundary"])
    return ((lower & schedule_membership(
                module, counts, large_sums,
                band_geometry["lower_schedule"])) |
            (~lower & schedule_membership(
                module, counts, large_sums,
                band_geometry["upper_schedule"])))


def chain_mean_se(values):
    chain_means = np.mean(values, axis=1, dtype=np.longdouble)
    return (float(np.mean(chain_means, dtype=np.longdouble)),
            float(np.std(chain_means, ddof=1) / np.sqrt(len(chain_means))),
            [float(value) for value in chain_means])


def read_cap(module, path, geometry, seed):
    data = module.strict_json(path)
    if geometry == "d1over60_verified":
        valid_source = (
            data.get("format") ==
            "active25-d18-verified-cap-bounded-oracle-v1" and
            data.get("source_sha256") == VERIFIED_WRAPPER_SHA256 and
            data.get("core_source_sha256") == CORE_SHA256)
    else:
        valid_source = (
            data.get("format") ==
            "active25-d18-cap-adapted-bounded-oracle-v1" and
            data.get("source_sha256") == CORE_SHA256)
    if (not valid_source or
            data.get("parameters", {}).get("geometry") != geometry or
            data.get("schedule", {}).get("seed") != seed or
            data.get("launch_authorized") is not False or
            data.get("exact_target_started") is not False):
        raise ValueError("cap result does not bind to bridge geometry/seed")
    screen = data["rayleigh_screen"]
    return data, float(screen["cap_riesz_norm_over_inner_I_estimate"]), float(
        screen["cap_riesz_norm_standard_error"])


def run(*, geometry, seed, chains, burn, draws, cap_result=None):
    if (type(seed) is not int or type(chains) is not int or
            type(burn) is not int or type(draws) is not int or
            not 4 <= chains <= 12 or not 200 <= burn <= 4000 or
            not 500 <= draws <= 8000 or chains * draws > 65536):
        raise ValueError("bridge schedule exceeds bounded envelope")
    module = load("d18_h2_bridge_core", CORE, CORE_SHA256)
    configure(module, geometry)
    band_geometry = (two_band_geometry(module)
                     if geometry == TWO_BAND_GEOMETRY else None)
    starts = {path: path.read_bytes() for path in (
        FILE, CORE, SUPPORT, CONTRACTION, VERIFIED_WRAPPER,
        TWO_BAND_CHECKER, TWO_BAND_RESULT)}
    cert, uncapped, _d0, basis, vector, outer = module.load_inputs()
    forms = exact_forms(module, geometry, cert, uncapped)
    inner = module.ResidualD18(
        basis, vector, center=module.ALPHA1, dilation=1)
    natural = module.ResidualD18(
        basis, vector, center=module.ALPHA2, dilation=module.OUTER_C)
    marginal = module.MarginalD18(basis, vector, inner.scale)
    point = module.point_consistency(
        inner, natural, basis, vector, outer, seed + 3000003)
    marginal_point = module.marginal_point_consistency(
        inner, marginal, seed + 3000033)
    cap_start = None
    cap_data = cap_s = cap_se = None
    if cap_result is not None:
        cap_result = Path(cap_result).resolve()
        cap_start = cap_result.read_bytes()
        cap_data, cap_s, cap_se = read_cap(
            module, cap_result, geometry, seed)

    rng = np.random.default_rng(seed)
    z, logp = initialize(
        rng, chains, natural, module.ld(module.ALPHA1),
        module.ld(module.ALPHA2), module.K)
    retained = np.empty((draws, chains, module.K), dtype=np.longdouble)
    accepted = 0
    proposed = 0
    radial_accepted = radial_proposed = 0
    shape_accepted = shape_proposed = 0
    started = time.monotonic()
    for iteration in range(burn + draws):
        if iteration % 4:
            noise = rng.normal(size=(chains, module.K))
            noise -= np.mean(noise, axis=1)[:, None]
            proposal = z + np.longdouble("0.42") * noise
            proposal = np.asarray(proposal, dtype=np.longdouble)
            newlog, _ = log_h2_target(
                proposal, natural, module.ld(module.ALPHA1),
                module.ld(module.ALPHA2))
            take = (np.log(rng.random(chains)).astype(np.longdouble) <
                    newlog - logp)
            shape_accepted += int(np.sum(take))
            shape_proposed += chains
        else:
            current, _, _ = logistic_points(z, module.ld(module.ALPHA2))
            current_total = np.sum(
                current, axis=1, dtype=np.longdouble)
            direction = current / current_total[:, None]
            new_total = radial_volume_draw(
                rng, chains, module.K, module.ld(module.ALPHA1),
                module.ld(module.ALPHA2))
            proposed_points = direction * new_total[:, None]
            proposed_y = proposed_points / module.ld(module.ALPHA2)
            proposed_slack = 1 - new_total / module.ld(module.ALPHA2)
            proposal = np.log(
                proposed_y / proposed_slack[:, None]).astype(np.longdouble)
            current_h = natural.evaluate(current)
            proposed_h = natural.evaluate(proposed_points)
            take = (np.log(rng.random(chains)).astype(np.longdouble) <
                    2 * (np.log(np.abs(proposed_h)) -
                         np.log(np.abs(current_h))))
            newlog, _ = log_h2_target(
                proposal, natural, module.ld(module.ALPHA1),
                module.ld(module.ALPHA2))
            radial_accepted += int(np.sum(take))
            radial_proposed += chains
        z[take], logp[take] = proposal[take], newlog[take]
        accepted += int(np.sum(take))
        proposed += chains
        if iteration >= burn:
            retained[iteration - burn] = logistic_points(
                z, module.ld(module.ALPHA2))[0]
        if (iteration + 1) % max(1, (burn + draws) // 4) == 0:
            print(f"h2 bridge step {iteration + 1}/{burn + draws}",
                  file=sys.stderr, flush=True)

    flat = retained.reshape(draws * chains, module.K)
    h = natural.evaluate(flat)
    g_top = marginal.riesz(flat)
    g = g_top
    flat_total = np.sum(flat, axis=1, dtype=np.longdouble)
    if band_geometry is not None:
        lower_flat = flat_total <= module.ld(band_geometry["boundary"])
        g = g_top.copy()
        top_eta = module.ETA2
        try:
            module.ETA2 = band_geometry["lower_eta_sensitivity"]
            g[lower_flat] = marginal.riesz(flat[lower_flat])
        finally:
            module.ETA2 = top_eta
    scale_ratio = module.ld(inner.scale / natural.scale)
    ratio = (g / h) * scale_ratio
    ratio = ratio.reshape(draws, chains).T
    ratio2 = ratio * ratio
    calibration_ratio = ((g_top / h) * scale_ratio).reshape(
        draws, chains).T
    exact_cross_mean = float(forms["B01_over_A11"])
    cross_mean, cross_se, cross_chains = chain_mean_se(calibration_ratio)
    second_mean, second_se, second_chains = chain_mean_se(ratio2)
    a11_over_a00 = float(forms["A11_over_A00"])
    s_mean = a11_over_a00 * second_mean
    s_se = a11_over_a00 * second_se
    cross_relative = abs(cross_mean - exact_cross_mean) / exact_cross_mean
    cross_z = ((cross_mean - exact_cross_mean) / cross_se
               if cross_se > 0 else math.inf)

    flat_points = flat.reshape(draws, chains, module.K).transpose(1, 0, 2)
    large = flat_points > module.ld(module.DELTA)
    counts = np.sum(large, axis=2)
    large_sums = np.sum(np.where(large, flat_points, 0), axis=2,
                        dtype=np.longdouble)
    totals = np.sum(flat_points, axis=2, dtype=np.longdouble)
    cap = cap_membership(
        module, counts, large_sums, geometry=geometry, totals=totals,
        band_geometry=band_geometry)
    cap_moment = ratio2 * cap
    cap_second_mean, cap_second_se, cap_second_chains = chain_mean_se(
        cap_moment)
    cap_bridge_mean = a11_over_a00 * cap_second_mean
    cap_bridge_se = a11_over_a00 * cap_second_se
    retention_chains = [
        float(np.sum(cap_moment[index], dtype=np.longdouble) /
              np.sum(ratio2[index], dtype=np.longdouble))
        for index in range(chains)]
    retention = float(np.mean(retention_chains))
    retention_se = float(np.std(retention_chains, ddof=1) /
                         math.sqrt(chains))
    band_screen = None
    if band_geometry is not None:
        lower_band = totals <= module.ld(band_geometry["boundary"])
        band_screen = {}
        for name, mask in (("lower_outer", lower_band),
                           ("upper_outer", ~lower_band)):
            band_moment = ratio2 * mask
            band_cap_moment = ratio2 * mask * cap
            band_mean, band_se, band_chains = chain_mean_se(band_moment)
            band_cap_mean, band_cap_se, band_cap_chains = chain_mean_se(
                band_cap_moment)
            energy = a11_over_a00 * band_mean
            energy_se = a11_over_a00 * band_se
            cap_energy = a11_over_a00 * band_cap_mean
            cap_energy_se = a11_over_a00 * band_cap_se
            band_screen[name] = {
                "eta_UV": str(
                    band_geometry["lower_eta_sensitivity"]
                    if name == "lower_outer" else module.ETA2),
                "G_norm_over_inner_I": energy,
                "G_norm_standard_error": energy_se,
                "capped_G_norm_over_inner_I": cap_energy,
                "capped_G_norm_standard_error": cap_energy_se,
                "cap_retention": cap_energy / energy if energy > 0 else None,
                "per_chain_second_moment": band_chains,
                "per_chain_capped_second_moment": band_cap_chains,
            }

    weights = ratio2.reshape(-1)
    counts_flat = counts.reshape(-1)
    sums_flat = large_sums.reshape(-1)
    total_weight = np.sum(weights, dtype=np.longdouble)
    probabilities = (0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)
    offsets = (Q(-1, 500), Q(-1, 1000), Q(0),
               Q(1, 1000), Q(1, 500))
    distribution = []
    for count in range(module.K + 1):
        selected = counts_flat == count
        local_weights = weights[selected]
        local_total = np.sum(local_weights, dtype=np.longdouble)
        share = float(local_total / total_weight) if total_weight > 0 else None
        bound = (module.SCHEDULE[count - 1]
                 if 1 <= count <= len(module.SCHEDULE) else None)
        cdf = []
        if bound is not None:
            for offset in offsets:
                threshold = bound + offset
                numerator = np.sum(
                    local_weights[sums_flat[selected] <= module.ld(threshold)],
                    dtype=np.longdouble)
                cdf.append({
                    "offset_from_current_bound": str(offset),
                    "threshold": str(threshold),
                    "G2_weighted_CDF": (float(numerator / local_total)
                                        if local_total > 0 else None),
                })
        distribution.append({
            "count": count, "draws": int(np.sum(selected)),
            "G2_energy_share": share,
            "G2_energy_over_inner_I": (s_mean * share
                                       if share is not None else None),
            "current_B_R": str(bound) if bound is not None else None,
            "current_cap_active_for_count": bool(
                count == 0 or
                (bound is not None and bound > count * module.DELTA)),
            "large_sum_weighted_quantiles": {
                str(p): q for p, q in zip(
                    probabilities,
                    weighted_quantiles(
                        sums_flat[selected], local_weights, probabilities))},
            "large_sum_CDF_near_current_B_R": cdf,
        })
    band_distributions = None
    if band_geometry is not None:
        band_distributions = {}
        for name, mask, schedule in (
                ("lower_outer", lower_band.reshape(-1),
                 band_geometry["lower_schedule"]),
                ("upper_outer", (~lower_band).reshape(-1),
                 band_geometry["upper_schedule"])):
            band_total = np.sum(weights[mask], dtype=np.longdouble)
            rows = []
            for count in range(module.K + 1):
                selected = mask & (counts_flat == count)
                local_weights = weights[selected]
                local_total = np.sum(local_weights, dtype=np.longdouble)
                bound = (schedule[count - 1]
                         if 1 <= count <= len(schedule) else None)
                cdf = []
                if bound is not None:
                    for offset in offsets:
                        threshold = bound + offset
                        numerator = np.sum(
                            local_weights[
                                sums_flat[selected] <= module.ld(threshold)],
                            dtype=np.longdouble)
                        cdf.append({
                            "offset_from_current_bound": str(offset),
                            "threshold": str(threshold),
                            "G2_weighted_CDF": (
                                float(numerator / local_total)
                                if local_total > 0 else None),
                        })
                rows.append({
                    "count": count, "draws": int(np.sum(selected)),
                    "G2_energy_share_of_total": (
                        float(local_total / total_weight)
                        if total_weight > 0 else None),
                    "G2_energy_share_within_band": (
                        float(local_total / band_total)
                        if band_total > 0 else None),
                    "G2_energy_over_inner_I": (
                        s_mean * float(local_total / total_weight)
                        if total_weight > 0 else None),
                    "current_B_R": str(bound) if bound is not None else None,
                    "large_sum_weighted_quantiles": {
                        str(p): q for p, q in zip(
                            probabilities,
                            weighted_quantiles(
                                sums_flat[selected], local_weights,
                                probabilities))},
                    "large_sum_CDF_near_current_B_R": cdf,
                })
            band_distributions[name] = rows

    acceptance = accepted / proposed
    shape_acceptance = shape_accepted / shape_proposed
    radial_acceptance = radial_accepted / radial_proposed
    rhat_ratio = split_rhat(ratio)
    rhat_ratio2 = split_rhat(ratio2)
    rhat_total = split_rhat(totals)
    radial_band_calibration = None
    radial_band_pass = True
    if band_geometry is not None:
        upper_indicator = (~lower_band).astype(np.longdouble)
        rhat_upper_indicator = split_rhat(upper_indicator)
        upper_fraction_by_chain = [
            float(value) for value in np.mean(
                upper_indicator, axis=1, dtype=np.longdouble)]
        every_chain_visits_both = all(
            0 < value < 1 for value in upper_fraction_by_chain)
        radial_band_pass = (
            rhat_upper_indicator <= 1.20 and every_chain_visits_both)
        radial_band_calibration = {
            "split_Rhat_upper_band_indicator": rhat_upper_indicator,
            "upper_band_fraction_by_chain": upper_fraction_by_chain,
            "every_chain_visits_both_bands": every_chain_visits_both,
            "pass": radial_band_pass,
        }
    mixing_pass = (0.10 <= shape_acceptance <= 0.70 and
                   0.01 <= radial_acceptance <= 0.99 and
                   rhat_total <= 1.20 and
                   rhat_ratio <= 1.20 and rhat_ratio2 <= 1.20 and
                   radial_band_pass)
    cross_pass = cross_relative <= 0.10 and abs(cross_z) <= 5
    status = ("H2-BRIDGE HEURISTIC CALIBRATED" if
              mixing_pass and cross_pass else
              "H2-BRIDGE CALIBRATION FAIL")
    if any(path.read_bytes() != payload for path, payload in starts.items()):
        raise RuntimeError("bridge source closure changed during run")
    if cap_result is not None and cap_result.read_bytes() != cap_start:
        raise RuntimeError("cap artifact changed during bridge run")
    elapsed = time.monotonic() - started
    cap_comparison = None
    if cap_data is not None:
        cap_comparison = {
            "path": str(cap_result.relative_to(REPO)),
            "sha256": sha256(cap_start), "direct_cap_s_over_I": cap_s,
            "direct_cap_standard_error": cap_se,
            "bridge_cap_s_over_I": cap_bridge_mean,
            "bridge_cap_standard_error": cap_bridge_se,
            "difference_over_independent_SE": (
                (cap_s - cap_bridge_mean) /
                math.sqrt(cap_se ** 2 + cap_bridge_se ** 2)
                if cap_se ** 2 + cap_bridge_se ** 2 > 0 else None),
        }
    return {
        "format": "active25-d18-h2-bridge-v1", "status": status,
        "rigorous": False, "theorem_ready": False,
        "launch_authorized": False, "exact_target_started": False,
        "resume_supported": False,
        "parameters": {
            "geometry": geometry, "k": module.K,
            "alpha1": str(module.ALPHA1), "alpha2": str(module.ALPHA2),
            "eta2": str(module.ETA2), "delta": str(module.DELTA),
            "eta_UV_cutoff_enforced_in_each_leave_one_out_term": True,
            "target_density": "natural_outer_D18(t)^2 on full radial shell",
            "two_band": ({
                "boundary": str(band_geometry["boundary"]),
                "lower_eta_UV": str(
                    band_geometry["lower_eta_sensitivity"]),
                "upper_eta_UV": str(module.ETA2),
                "lower_schedule": [str(x) for x in
                                   band_geometry["lower_schedule"]],
                "upper_schedule": [str(x) for x in
                                   band_geometry["upper_schedule"]],
            } if band_geometry is not None else None),
        },
        "schedule": {"seed": seed, "chains": chains, "burn": burn,
                     "draws_per_chain": draws, "workers": 1},
        "exact_bridge_forms": {key: str(value) for key, value in forms.items()},
        "formula": {
            "ratio": "r=G_F(t)/h(t) in the original polynomial scaling",
            "cross_calibration": (
                "E_h2[r_top_eta]=B01/A11; this calibrates the h^2 chain "
                "even when the lower band uses its smaller eta_UV"),
            "absolute_norm": "I(G)/I(F)=(A11/A00)E_h2[r^2]",
            "capped_norm":
                "I(G*1_cap)/I(F)=(A11/A00)E_h2[r^2*1_cap]",
        },
        "point_evaluator_calibration": point,
        "marginal_antiderivative_calibration": marginal_point,
        "mcmc_calibration": {
            "acceptance": acceptance,
            "shape_move_acceptance": shape_acceptance,
            "radial_independence_move_acceptance": radial_acceptance,
            "radial_proposal": (
                "hold t/sum(t) fixed and draw sum(t) with density "
                "proportional to sum(t)^(k-1); MH ratio h(new)^2/h(old)^2"),
            "split_Rhat_radial_total": rhat_total,
            "radial_band_calibration": radial_band_calibration,
            "split_Rhat_ratio": rhat_ratio,
            "split_Rhat_ratio_squared": rhat_ratio2,
            "mixing_pass": mixing_pass,
            "exact_cross_mean": exact_cross_mean,
            "estimated_cross_mean": cross_mean,
            "cross_mean_standard_error": cross_se,
            "cross_relative_error": cross_relative,
            "cross_z_score": cross_z, "cross_pass": cross_pass,
            "per_chain_cross_mean": cross_chains,
        },
        "screen": {
            "uncapped_G_norm_over_inner_I": s_mean,
            "uncapped_G_norm_standard_error": s_se,
            "uncapped_G_norm_lower_two_standard_errors": s_mean - 2 * s_se,
            "uncapped_G_norm_upper_two_standard_errors": s_mean + 2 * s_se,
            "per_chain_second_moment": second_chains,
            "capped_G_norm_over_inner_I": cap_bridge_mean,
            "capped_G_norm_standard_error": cap_bridge_se,
            "per_chain_capped_second_moment": cap_second_chains,
            "cap_retention": retention,
            "cap_retention_standard_error": retention_se,
            "per_chain_cap_retention": retention_chains,
            "by_radial_band": band_screen,
            "sufficient_threshold": 1 - float(Q(cert["exact_quotient"])),
        },
        "cap_result_comparison": cap_comparison,
        "G2_weighted_cap_geometry_diagnostics": {
            "large_sum_definition": "sum of t_i with t_i>delta",
            "nearby_rational_offsets": [str(value) for value in offsets],
            "by_large_coordinate_count": distribution,
            "by_radial_band_and_large_coordinate_count":
                band_distributions,
        },
        "wall_seconds": elapsed,
        "peak_rss_kib": int(resource.getrusage(
            resource.RUSAGE_SELF).ru_maxrss),
        "source_sha256": sha256(starts[FILE]),
        "source_hashes": {
            str(CORE.relative_to(REPO)): CORE_SHA256,
            str(SUPPORT.relative_to(REPO)): SUPPORT_SHA256,
            str(CONTRACTION.relative_to(REPO)): CONTRACTION_SHA256,
            str(VERIFIED_WRAPPER.relative_to(REPO)): VERIFIED_WRAPPER_SHA256,
            str(TWO_BAND_CHECKER.relative_to(REPO)):
                TWO_BAND_CHECKER_SHA256,
            str(TWO_BAND_RESULT.relative_to(REPO)): TWO_BAND_RESULT_SHA256,
        },
        "never_implies": ["independent samples", "a rigorous error bar",
                          "an exact Riesz norm", "a rigorous upper bound",
                          "Proposition 1", "H1<=236"],
    }


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def apply_limits():
    limit = 512 * 1024 * 1024
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    new_hard = hard if hard != resource.RLIM_INFINITY else limit
    resource.setrlimit(resource.RLIMIT_AS, (min(limit, new_hard), new_hard))
    signal.alarm(180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry", choices=(
        "audited", "d1over60_verified", TWO_BAND_GEOMETRY), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--chains", type=int, default=8)
    parser.add_argument("--burn", type=int, default=1000)
    parser.add_argument("--draws", type=int, default=3000)
    parser.add_argument("--cap-result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    apply_limits()
    result = run(geometry=args.geometry, seed=args.seed, chains=args.chains,
                 burn=args.burn, draws=args.draws,
                 cap_result=args.cap_result)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload), "status": result["status"],
        "uncapped_s_over_I": result["screen"][
            "uncapped_G_norm_over_inner_I"],
        "capped_s_over_I": result["screen"]["capped_G_norm_over_inner_I"],
        "retention": result["screen"]["cap_retention"],
        "wall_seconds": result["wall_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
