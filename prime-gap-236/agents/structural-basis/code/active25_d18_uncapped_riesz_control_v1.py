#!/usr/bin/env python3
"""Bounded uncapped control for the cap-adapted D18 Riesz oracle.

This companion estimates integral_shell G_F^2 on the complete radial shell
alpha1<sum(t)<alpha2 with the same geometry-specific eta_UV cutoff used by the
capped oracle.  It intentionally removes the active25 count/cap indicators.
The result separates radial-shell/cutoff effects from cap retention.  It is a
floating discovery control, never an exact integral or launch authorization.
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
ORACLE = REPO / (
    "agents/structural-basis/code/active25_d18_cap_adapted_oracle_v1.py")
ORACLE_SHA256 = (
    "7258643c15d5ca26a1025ead96f8a6d2a6a9170e639913d2d272007b51e19840")
D1_EXACT = REPO / (
    "agents/structural-basis/results/"
    "d1over60_d18_uncapped_pencil_exact_v1.json")
D1_EXACT_SHA256 = (
    "3bfaafb532da80a17bb40e4a2cfb94090beda8ca6df43acb07c4f531ce5be02f")
SUPPORT = REPO / "agents/analytic-new-lever/adaptive_support_v1_exact.json"
SUPPORT_SHA256 = (
    "b7070c2677815b22a86b5a55ce41b3a2477d593495062256356a5df2a37befa7")
VERIFIED_GEOMETRY = "d1over60_verified"
VERIFIED_WRAPPER = REPO / (
    "agents/structural-basis/code/active25_d18_verified_cap_oracle_v1.py")
VERIFIED_WRAPPER_SHA256 = (
    "d134832dbce0215e2e7b6d1fa70d71c4e855f7fdc1625b6a906182beef5f697e")


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_oracle_module():
    if sha256(ORACLE) != ORACLE_SHA256:
        raise RuntimeError("pinned capped-oracle source changed")
    spec = importlib.util.spec_from_file_location(
        "active25_d18_cap_adapted_oracle_v1_frozen", ORACLE)
    if spec is None or spec.loader is None:
        raise ImportError(ORACLE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def install_verified_geometry(module):
    if sha256(SUPPORT) != SUPPORT_SHA256:
        raise RuntimeError("pinned analytic support certificate changed")
    data = module.strict_json(SUPPORT)
    parameters = data.get("candidate", {}).get("parameters", {})
    prefix = tuple(Q(value) for value in
                   parameters.get("outer_schedule_through_first_empty", ()))
    expected = tuple(Q(value, 1_000_000) for value in (
        138360, 155020, 158662, 171688, 177684, 180588,
        183402, 185486, 187011, 188221, 189137, 189137))
    if (data.get("status") != "EXACT ADAPTIVE ANALYTIC SUPPORT PASS" or
            data.get("checker_sha256") !=
            "b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d" or
            prefix != expected or parameters.get("alpha") !=
            ["103/400", "237991/900000"] or
            parameters.get("delta") != "1/60"):
        raise ValueError("verified support geometry mismatch")
    module.GEOMETRIES[VERIFIED_GEOMETRY] = {
        "approved": True, "delta": Q(1, 60),
        "alpha2": Q(237991, 900000), "eta2": Q(224491, 900000),
        "schedule": prefix + (prefix[-1],) * (26 - len(prefix)),
        "source": "exact adaptive analytic support pass b7070c26",
    }


def full_simplex_shell_sample(module, rng, samples):
    """Uniform alpha2-simplex proposal with a constant Lebesgue weight."""
    simplex = rng.dirichlet(np.ones(module.K + 1), size=samples)
    points = (simplex[:, :module.K].astype(np.longdouble) *
              module.ld(module.ALPHA2))
    total = np.sum(points, axis=1, dtype=np.longdouble)
    shell = ((total > module.ld(module.ALPHA1)) &
             (total < module.ld(module.ALPHA2) +
              np.longdouble("1e-18")))
    measure = (module.ld(module.ALPHA2) ** module.K /
               math.factorial(module.K))
    return points, measure, shell


def exact_full_shell_volume(module):
    return ((module.ALPHA2 ** module.K -
             module.ALPHA1 ** module.K) / math.factorial(module.K))


def mean_se(values):
    rows = np.asarray(values, dtype=np.longdouble)
    return (np.mean(rows, axis=0, dtype=np.longdouble),
            np.std(rows, axis=0, ddof=1) / np.sqrt(len(rows)))


def weighted_quantiles(values, weights, probabilities):
    values = np.asarray(values, dtype=np.longdouble)
    weights = np.asarray(weights, dtype=np.longdouble)
    positive = weights > 0
    if not np.any(positive):
        return [None for _ in probabilities]
    values = values[positive]
    weights = weights[positive]
    order = np.argsort(values)
    values = values[order]
    cumulative = np.cumsum(weights[order], dtype=np.longdouble)
    total = cumulative[-1]
    result = []
    for probability in probabilities:
        index = int(np.searchsorted(
            cumulative, np.longdouble(str(probability)) * total,
            side="left"))
        result.append(float(values[min(index, len(values) - 1)]))
    return result


def cap_membership(module, counts, large_sums):
    """Apply only the active25 count-specific large-sum schedule."""
    selected = counts == 0
    for count, bound in enumerate(module.SCHEDULE, start=1):
        if bound > count * module.DELTA:
            selected |= ((counts == count) &
                         (large_sums <= module.ld(bound)))
    return selected


def read_cap_result(module, path, geometry, seed):
    data = module.strict_json(path)
    if geometry == VERIFIED_GEOMETRY:
        source_match = (
            sha256(VERIFIED_WRAPPER) == VERIFIED_WRAPPER_SHA256 and
            data.get("format") ==
            "active25-d18-verified-cap-bounded-oracle-v1" and
            data.get("source_sha256") == VERIFIED_WRAPPER_SHA256 and
            data.get("core_source_sha256") == ORACLE_SHA256)
    else:
        source_match = (
            data.get("format") ==
            "active25-d18-cap-adapted-bounded-oracle-v1" and
            data.get("source_sha256") == ORACLE_SHA256)
    if (not source_match or
            data.get("parameters", {}).get("geometry") != geometry or
            data.get("schedule", {}).get("seed") != seed or
            data.get("exact_target_started") is not False or
            data.get("launch_authorized") is not False):
        raise ValueError("cap-result binding mismatch")
    screen = data.get("rayleigh_screen", {})
    cap_s = float(screen["cap_riesz_norm_over_inner_I_estimate"])
    cap_se = float(screen["cap_riesz_norm_standard_error"])
    if cap_s < 0 or cap_se < 0:
        raise ValueError("invalid cap-result estimate")
    return data, cap_s, cap_se


def natural_projection_anchor(module, geometry, cert, uncapped):
    """Return an exact natural-direction Riesz projection when pinned."""
    if geometry == "audited":
        inner_i = Q(cert["exact_denominator"])
        outer_i = Q(uncapped["I_matrix"][1][1])
        cross = Q(uncapped["kJ_matrix"][0][1])
        return {
            "value": cross ** 2 / (outer_i * inner_i),
            "source_path": str(module.UNCAPPED.relative_to(REPO)),
            "source_sha256": module.PINS[module.UNCAPPED],
            "formula": "B01^2/(A11*A00)",
            "geometry_parameters_checked": True,
        }
    if geometry in ("d1over60", VERIFIED_GEOMETRY):
        if sha256(D1_EXACT) != D1_EXACT_SHA256:
            raise RuntimeError("pinned d1over60 exact contraction changed")
        data = module.strict_json(D1_EXACT)
        expected_parameters = {
            "k": module.K, "alpha1": str(module.ALPHA1),
            "alpha2": str(module.ALPHA2), "eta1": str(module.ETA1),
            "eta2": str(module.ETA2), "delta": str(module.DELTA),
            "outer_c": str(module.OUTER_C),
        }
        if (data.get("format") !=
                "parameterized-d18-uncapped-pencil-exact-v1" or
                data.get("rigorous_values") is not True or
                data.get("parameters") != expected_parameters):
            raise ValueError("d1over60 exact contraction geometry mismatch")
        value = Q(data["natural_projection_over_inner_I"])
        a00, a11 = map(Q, (data["I_matrix"][0][0],
                           data["I_matrix"][1][1]))
        b01 = Q(data["kJ_matrix"][0][1])
        if value != b01 ** 2 / (a11 * a00):
            raise ArithmeticError("d1over60 natural projection mismatch")
        return {
            "value": value,
            "source_path": str(D1_EXACT.relative_to(REPO)),
            "source_sha256": D1_EXACT_SHA256,
            "formula": "B01^2/(A11*A00)",
            "geometry_parameters_checked": True,
            "A11_over_A00": str(a11 / a00),
            "B01_over_A00": str(b01 / a00),
        }
    return None


def run_control(*, geometry, seed, batches, samples_per_batch,
                cap_result=None):
    if (type(seed) is not int or type(batches) is not int or
            type(samples_per_batch) is not int or
            not 2 <= batches <= 8 or
            not 512 <= samples_per_batch <= 16384 or
            batches * samples_per_batch > 65536):
        raise ValueError("control schedule exceeds bounded envelope")
    module = load_oracle_module()
    if geometry == VERIFIED_GEOMETRY:
        install_verified_geometry(module)
    module.configure_geometry(geometry)
    own_start = FILE.read_bytes()
    oracle_start = ORACLE.read_bytes()
    cert, uncapped, _d0, basis, vector, outer = module.load_inputs()
    anchor = natural_projection_anchor(module, geometry, cert, uncapped)
    anchor_value = float(anchor["value"]) if anchor is not None else None
    anchor_start = (D1_EXACT.read_bytes()
                    if geometry in ("d1over60", VERIFIED_GEOMETRY) else None)
    support_start = (SUPPORT.read_bytes()
                     if geometry == VERIFIED_GEOMETRY else None)
    wrapper_start = (VERIFIED_WRAPPER.read_bytes()
                     if geometry == VERIFIED_GEOMETRY else None)
    inner = module.ResidualD18(
        basis, vector, center=module.ALPHA1, dilation=1)
    natural = module.ResidualD18(
        basis, vector, center=module.ALPHA2, dilation=module.OUTER_C)
    marginal = module.MarginalD18(basis, vector, inner.scale)
    point = module.point_consistency(
        inner, natural, basis, vector, outer, seed + 2000003)
    marginal_point = module.marginal_point_consistency(
        inner, marginal, seed + 2000033)
    cap_data = None
    cap_s = cap_se = None
    cap_start = None
    if cap_result is not None:
        cap_result = Path(cap_result).resolve()
        cap_start = cap_result.read_bytes()
        cap_data, cap_s, cap_se = read_cap_result(
            module, cap_result, geometry, seed)

    exact_inner_i = module.ld(
        Q(cert["exact_denominator"]) / inner.scale ** 2)
    rng = np.random.default_rng(seed)
    matrix_batches = []
    volume_batches = []
    s_batches = []
    projection_batches = []
    cap_from_shell_batches = []
    all_counts = []
    all_large_sums = []
    all_g2 = []
    started = time.monotonic()
    for batch_index in range(batches):
        points, measure, shell = full_simplex_shell_sample(
            module, rng, samples_per_batch)
        evaluation_points = points.copy()
        evaluation_points[~shell] = 0
        g = marginal.riesz(evaluation_points)
        h = natural.evaluate(evaluation_points)
        values = np.column_stack((g, h))
        values[~shell] = 0
        matrix = measure * (values.T @ values) / samples_per_batch
        matrix_batches.append(matrix)
        volume_batches.append(measure * np.mean(
            shell, dtype=np.longdouble))
        s = float(matrix[0, 0] / exact_inner_i)
        projection = (float(matrix[0, 1] ** 2 /
                            (matrix[1, 1] * exact_inner_i))
                      if matrix[1, 1] > 0 else 0.0)
        s_batches.append(s)
        projection_batches.append(projection)
        large = points > module.ld(module.DELTA)
        counts = np.sum(large, axis=1)
        large_sums = np.sum(
            np.where(large, points, np.longdouble(0)),
            axis=1, dtype=np.longdouble)
        g2 = g * g
        cap_mask = shell & cap_membership(module, counts, large_sums)
        cap_from_shell_batches.append(float(
            measure * np.sum(g2[cap_mask], dtype=np.longdouble) /
            samples_per_batch / exact_inner_i))
        all_counts.append(counts)
        all_large_sums.append(large_sums)
        all_g2.append(np.where(shell, g2, np.longdouble(0)))
        print(f"uncapped Riesz control batch {batch_index + 1}/{batches}: "
              f"s/I={s:.9g}, natural_projection/I={projection:.9g}",
              file=sys.stderr, flush=True)

    matrix_mean, matrix_se = mean_se(matrix_batches)
    s_mean = float(np.mean(s_batches))
    s_se = float(np.std(s_batches, ddof=1) / math.sqrt(batches))
    projection_mean = float(np.mean(projection_batches))
    projection_se = float(
        np.std(projection_batches, ddof=1) / math.sqrt(batches))
    cap_from_shell_mean = float(np.mean(cap_from_shell_batches))
    cap_from_shell_se = float(
        np.std(cap_from_shell_batches, ddof=1) / math.sqrt(batches))
    inflation_batches = [
        s / projection if projection > 0 else math.inf
        for s, projection in zip(s_batches, projection_batches)]
    anchored_s_batches = ([anchor_value * value
                           for value in inflation_batches]
                          if anchor_value is not None else None)
    anchored_s_mean = (float(np.mean(anchored_s_batches))
                       if anchored_s_batches is not None else None)
    anchored_s_se = (float(np.std(anchored_s_batches, ddof=1) /
                           math.sqrt(batches))
                     if anchored_s_batches is not None else None)
    anchored_cap_batches = ([
        anchor_value * cap_value / projection
        if projection > 0 else math.inf
        for cap_value, projection in zip(
            cap_from_shell_batches, projection_batches)]
        if anchor_value is not None else None)
    anchored_cap_mean = (float(np.mean(anchored_cap_batches))
                         if anchored_cap_batches is not None else None)
    anchored_cap_se = (float(np.std(anchored_cap_batches, ddof=1) /
                             math.sqrt(batches))
                       if anchored_cap_batches is not None else None)
    exact_volume = module.ld(exact_full_shell_volume(module))
    volume_mean = np.mean(volume_batches, dtype=np.longdouble)
    measure = module.ld(module.ALPHA2) ** module.K / math.factorial(module.K)
    probability = volume_mean / measure
    volume_se = measure * np.sqrt(
        probability * (1 - probability) /
        (batches * samples_per_batch))
    volume_relative_error = float(abs(volume_mean - exact_volume) /
                                  exact_volume)
    volume_z = float((volume_mean - exact_volume) / volume_se)
    volume_pass = volume_relative_error <= 0.02 and abs(volume_z) <= 5

    exact_natural_projection = anchor_value
    exact_natural_relative_error = (
        abs(projection_mean - anchor_value) / anchor_value
        if anchor_value is not None else None)

    cap_comparison = None
    if cap_data is not None:
        cap_comparison = {
            "cap_result_path": str(cap_result.relative_to(REPO)),
            "cap_result_sha256": sha256(cap_start),
            "cap_s_over_I": cap_s,
            "cap_s_standard_error": cap_se,
            "cap_over_uncapped_point_ratio": (
                cap_s / anchored_s_mean
                if anchored_s_mean is not None and anchored_s_mean > 0
                else None),
            "uncapped_sample_reapplied_cap_s_over_I": cap_from_shell_mean,
            "uncapped_sample_reapplied_cap_standard_error":
                cap_from_shell_se,
            "anchored_uncapped_sample_reapplied_cap_s_over_I":
                anchored_cap_mean,
            "anchored_uncapped_sample_reapplied_cap_standard_error":
                anchored_cap_se,
            "interpretation": (
                "point retention only; numerator and denominator are noisy "
                "discovery estimates, not a confidence bound"),
        }


    counts = np.concatenate(all_counts)
    large_sums = np.concatenate(all_large_sums)
    g2 = np.concatenate(all_g2)
    total_g2 = np.sum(g2, dtype=np.longdouble)
    total_samples = batches * samples_per_batch
    offsets = (Q(-1, 500), Q(-1, 1000), Q(0),
               Q(1, 1000), Q(1, 500))
    quantile_probabilities = (0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)
    count_distribution = []
    for count in range(module.K + 1):
        selected = counts == count
        weights = g2[selected]
        count_g2 = np.sum(weights, dtype=np.longdouble)
        current_bound = (module.SCHEDULE[count - 1]
                         if 1 <= count <= len(module.SCHEDULE) else None)
        cdf_rows = []
        if current_bound is not None:
            for offset in offsets:
                threshold_value = current_bound + offset
                numerator = np.sum(
                    weights[large_sums[selected] <= module.ld(threshold_value)],
                    dtype=np.longdouble)
                cdf_rows.append({
                    "offset_from_current_bound": str(offset),
                    "threshold": str(threshold_value),
                    "G2_weighted_CDF": (float(numerator / count_g2)
                                        if count_g2 > 0 else None),
                })
        count_distribution.append({
            "count": count,
            "sample_points": int(np.sum(selected)),
            "G2_energy_over_inner_I": float(
                measure * count_g2 / total_samples / exact_inner_i),
            "anchored_G2_energy_over_inner_I": (
                anchored_s_mean * float(count_g2 / total_g2)
                if anchored_s_mean is not None and total_g2 > 0 else None),
            "G2_energy_share": (float(count_g2 / total_g2)
                                if total_g2 > 0 else None),
            "current_B_R": (str(current_bound)
                            if current_bound is not None else None),
            "current_cap_active_for_count": bool(
                count == 0 or
                (current_bound is not None and
                 current_bound > count * module.DELTA)),
            "large_sum_weighted_quantiles": {
                str(probability): value
                for probability, value in zip(
                    quantile_probabilities,
                    weighted_quantiles(
                        large_sums[selected], weights,
                        quantile_probabilities))},
            "large_sum_CDF_near_current_B_R": cdf_rows,
        })

    if (FILE.read_bytes() != own_start or ORACLE.read_bytes() != oracle_start or
            (anchor_start is not None and
             D1_EXACT.read_bytes() != anchor_start) or
            (support_start is not None and
             SUPPORT.read_bytes() != support_start) or
            (wrapper_start is not None and
             VERIFIED_WRAPPER.read_bytes() != wrapper_start) or
            (cap_result is not None and cap_result.read_bytes() != cap_start)):
        raise RuntimeError("control source closure changed during run")
    elapsed = time.monotonic() - started
    threshold = 1 - float(Q(cert["exact_quotient"]))
    if not volume_pass:
        status = "HEURISTIC VOLUME CALIBRATION FAIL"
    elif anchor is None:
        status = "UNANCHORED INTEGRAND CALIBRATION FAIL"
    else:
        status = "ANCHORED HEURISTIC CALIBRATED"
    return {
        "format": "active25-d18-uncapped-riesz-control-v1",
        "status": status,
        "rigorous": False,
        "theorem_ready": False,
        "launch_authorized": False,
        "exact_target_started": False,
        "resume_supported": False,
        "parameters": {
            "geometry": geometry,
            "geometry_analytically_approved": module.GEOMETRIES[
                geometry]["approved"],
            "k": module.K, "alpha1": str(module.ALPHA1),
            "alpha2": str(module.ALPHA2), "eta2": str(module.ETA2),
            "eta_UV_cutoff_enforced_in_each_leave_one_out_term": True,
            "cap_indicators_applied": False,
        },
        "proposal": {
            "law": "Dirichlet_49(1,...,1)*alpha2",
            "measure": "alpha2^48/48!",
            "indicator": "sum(t)>alpha1",
            "constant_weight": True,
        },
        "schedule": {"seed": seed, "batches": batches,
                     "samples_per_batch": samples_per_batch, "workers": 1},
        "point_evaluator_calibration": point,
        "marginal_antiderivative_calibration": marginal_point,
        "exact_volume_calibration": {
            "estimate": str(volume_mean), "standard_error": str(volume_se),
            "exact": str(exact_volume),
            "relative_error": volume_relative_error, "z_score": volume_z,
            "acceptance_rule": "relative error <=0.02 and |z|<=5",
            "pass": volume_pass,
        },
        "uncapped_screen": {
            "raw_uniform_G_norm_over_inner_I_estimate": s_mean,
            "raw_uniform_G_norm_standard_error": s_se,
            "batch_raw_uniform_G_norm": s_batches,
            "raw_uniform_natural_projection_over_inner_I_estimate":
                projection_mean,
            "raw_uniform_natural_projection_standard_error": projection_se,
            "batch_raw_uniform_natural_projection": projection_batches,
            "raw_uniform_normalization_is_absolute": False,
            "exact_natural_projection_anchor_over_inner_I":
                exact_natural_projection,
            "exact_natural_projection_anchor": (
                {key: (str(value) if key == "value" else value)
                 for key, value in anchor.items()}
                if anchor is not None else None),
            "raw_projection_relative_error_against_anchor":
                exact_natural_relative_error,
            "Riesz_inflation_over_natural_projection_batches":
                inflation_batches,
            "anchored_G_norm_over_inner_I_estimate": anchored_s_mean,
            "anchored_G_norm_standard_error": anchored_s_se,
            "anchored_G_norm_lower_two_standard_errors": (
                anchored_s_mean - 2 * anchored_s_se
                if anchored_s_mean is not None else None),
            "anchored_G_norm_upper_two_standard_errors": (
                anchored_s_mean + 2 * anchored_s_se
                if anchored_s_mean is not None else None),
            "batch_anchored_G_norm": anchored_s_batches,
            "anchor_method": (
                "exact natural projection times Monte Carlo estimate of "
                "I(G)I(h)/I(G,h)^2" if anchor is not None else None),
            "sample_matrix_PSD_check": bool(
                matrix_mean[0, 0] * matrix_mean[1, 1] +
                np.longdouble("1e-300") >= matrix_mean[0, 1] ** 2),
            "sufficient_threshold": threshold,
            "anchored_lower_two_SE_exceeds_threshold": (
                anchored_s_mean - 2 * anchored_s_se > threshold
                if anchored_s_mean is not None else None),
            "raw_cap_reapplied_within_uncapped_sample_over_inner_I":
                cap_from_shell_mean,
            "raw_cap_reapplied_standard_error": cap_from_shell_se,
            "anchored_cap_reapplied_over_inner_I": anchored_cap_mean,
            "anchored_cap_reapplied_standard_error": anchored_cap_se,
            "anchored_cap_reapplied_over_uncapped_point_ratio": (
                anchored_cap_mean / anchored_s_mean
                if (anchored_cap_mean is not None and
                    anchored_s_mean is not None and anchored_s_mean > 0)
                else None),
            "raw_cap_reapplied_over_uncapped_point_ratio": (
                cap_from_shell_mean / s_mean if s_mean > 0 else None),
        },
        "G2_weighted_cap_geometry_diagnostics": {
            "large_sum_definition": "sum of coordinates t_i with t_i>delta",
            "quantile_convention":
                "left-continuous empirical G^2-weighted quantile",
            "nearby_rational_offsets": [str(value) for value in offsets],
            "by_large_coordinate_count": count_distribution,
        },
        "cap_comparison": cap_comparison,
        "matrix": [[str(x) for x in row] for row in matrix_mean],
        "matrix_standard_error": [
            [str(x) for x in row] for row in matrix_se],
        "wall_seconds": elapsed,
        "peak_rss_kib": int(resource.getrusage(
            resource.RUSAGE_SELF).ru_maxrss),
        "source_sha256": sha256(own_start),
        "pinned_capped_oracle_sha256": ORACLE_SHA256,
        "never_implies": ["an exact Riesz norm", "a rigorous upper bound",
                          "approved adaptive support", "Proposition 1",
                          "H1<=236"],
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
        "audited", "d014", "d1over60", VERIFIED_GEOMETRY),
                        required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--batches", type=int, default=4)
    parser.add_argument("--samples-per-batch", type=int, default=4096)
    parser.add_argument("--cap-result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    apply_limits()
    result = run_control(
        geometry=args.geometry, seed=args.seed, batches=args.batches,
        samples_per_batch=args.samples_per_batch, cap_result=args.cap_result)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload), "status": result["status"],
        "s_over_I": result["uncapped_screen"][
            "anchored_G_norm_over_inner_I_estimate"],
        "wall_seconds": result["wall_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
