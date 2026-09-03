#!/usr/bin/env python3
"""Fail-closed diagnostics for stratified importance discovery.

All intervals and roots produced here are heuristic discovery diagnostics.
They are never mathematical error bounds and cannot enter a theorem checker.
"""

from __future__ import annotations

import math

import numpy as np


def _finite_array(values, name):
    array = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(array)):
        raise ArithmeticError(f"{name} contains a nonfinite value")
    return array


def split_rhat(batch_values):
    """Split-R-hat, treating each batch mean as one correlated-series draw."""
    values = _finite_array(batch_values, "batch values")
    if values.ndim < 2:
        raise ValueError("batch values need chain and batch axes")
    chains, batches = values.shape[:2]
    if chains < 2 or batches < 4 or batches % 2:
        raise ValueError("need >=2 chains and an even >=4 batch count")
    half = batches // 2
    split = np.concatenate((values[:, :half], values[:, half:]), axis=0)
    with np.errstate(over="ignore", invalid="ignore"):
        means = np.mean(split, axis=1)
        within_variances = np.var(split, axis=1, ddof=1)
        within = np.mean(within_variances, axis=0)
        between = half * np.var(means, axis=0, ddof=1)
        variance_hat = (half - 1) * within / half + between / half
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = np.sqrt(variance_hat / within)
    answer = np.where(within > 0, np.maximum(1.0, raw),
                      np.where(between == 0, 1.0, np.inf))
    # Overflow of finite inputs is a diagnostic failure, not a converged NaN.
    answer = np.where(np.isnan(answer), np.inf, answer)
    return answer


def batch_means_ess(raw_mean, raw_second_moment, batch_values, batch_size):
    """Conservative batch-means ESS diagnostic, capped at sample count."""
    if (isinstance(batch_size, bool) or not isinstance(batch_size, int) or
            batch_size <= 0):
        raise ValueError("batch_size must be a positive exact integer")
    mean = _finite_array(raw_mean, "raw mean")
    second = _finite_array(raw_second_moment, "raw second moment")
    batches = _finite_array(batch_values, "batch values")
    if mean.shape != second.shape or batches.shape[2:] != mean.shape:
        raise ValueError("ESS moment shapes do not agree")
    if batches.ndim < 2 or batches.shape[0] < 2 or batches.shape[1] < 4:
        raise ValueError("ESS needs at least two chains and four batches each")
    batch_mean = np.mean(batches, axis=(0, 1))
    if not np.allclose(mean, batch_mean, rtol=1e-12, atol=1e-15):
        raise ArithmeticError("raw and batched means are inconsistent")
    total_samples = batches.shape[0] * batches.shape[1] * batch_size
    raw_variance_unclipped = second - mean * mean
    variance_tolerance = 64 * np.finfo(float).eps * np.maximum(
        1.0, np.maximum(np.abs(second), mean * mean))
    if np.any(raw_variance_unclipped < -variance_tolerance):
        raise ArithmeticError("raw second moment is smaller than mean squared")
    raw_variance = np.maximum(0.0, raw_variance_unclipped)
    flattened = batches.reshape((-1,) + mean.shape)
    # Within every batch, mean(X^2) >= mean(X)^2.  This catches a malformed
    # raw second moment even when its raw mean happens to agree with the
    # signed average of inconsistent batch means.
    batch_mean_square = np.mean(flattened * flattened, axis=0)
    jensen_tolerance = 64 * np.finfo(float).eps * np.maximum(
        1.0, np.maximum(np.abs(second), batch_mean_square))
    if np.any(second < batch_mean_square - jensen_tolerance):
        raise ArithmeticError(
            "raw second moment violates the batch-mean Jensen bound")
    batch_variance = np.var(flattened, axis=0, ddof=1)
    spectral_variance = batch_size * batch_variance
    if (not np.all(np.isfinite(raw_variance)) or
            not np.all(np.isfinite(spectral_variance))):
        raise ArithmeticError("ESS variance calculation overflowed")
    with np.errstate(divide="ignore", invalid="ignore"):
        estimate = total_samples * raw_variance / spectral_variance
    if np.any((spectral_variance == 0) &
              (np.max(flattened, axis=0) != np.min(flattened, axis=0))):
        raise ArithmeticError("distinct batch means underflowed to zero variance")
    estimate = np.where(
        raw_variance == 0, float(total_samples),
        np.where(spectral_variance == 0, float(total_samples), estimate))
    return np.clip(estimate, 1.0, float(total_samples))


def ratio_matrix_delta(batch_numerators, batch_denominators):
    """Ratio-of-means matrix and joint batch-means delta standard error."""
    numerators = _finite_array(batch_numerators, "ratio numerators")
    denominators = _finite_array(batch_denominators, "ratio denominators")
    if numerators.ndim < 4 or denominators.shape != numerators.shape[:2]:
        raise ValueError("ratio batches need [chain,batch,d,d] and [chain,batch]")
    if numerators.shape[-1] != numerators.shape[-2]:
        raise ValueError("ratio numerator matrices must be square")
    count = numerators.shape[0] * numerators.shape[1]
    if count < 2:
        raise ValueError("at least two ratio batches are required")
    z_tolerance = 64 * np.finfo(float).eps
    if np.any(denominators < 0) or np.any(denominators > 2 + z_tolerance):
        raise ArithmeticError("envelope z batches must lie in [0,2]")
    if not np.array_equal(numerators, np.swapaxes(numerators, -1, -2)):
        raise ArithmeticError("envelope numerator batches must be symmetric")
    diagonal = np.diagonal(numerators, axis1=-2, axis2=-1)
    if np.any(diagonal < 0) or np.any(diagonal > 1 + z_tolerance):
        raise ArithmeticError("envelope diagonal batches must lie in [0,1]")
    off_diagonal = numerators.copy()
    diagonal_indices = np.arange(numerators.shape[-1])
    off_diagonal[..., diagonal_indices, diagonal_indices] = 0
    if np.any(np.abs(off_diagonal) > 0.5 + z_tolerance):
        raise ArithmeticError("envelope off-diagonal batch exceeds 1/2")
    mean_numerator = np.mean(numerators, axis=(0, 1))
    mean_denominator = float(np.mean(denominators))
    if not math.isfinite(mean_denominator) or mean_denominator <= 0:
        raise ArithmeticError("ratio denominator mean must be positive")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        ratio = mean_numerator / mean_denominator
        residuals = numerators - (
            denominators[..., np.newaxis, np.newaxis] * ratio)
        flattened = residuals.reshape((-1,) + ratio.shape)
        standard_error = np.std(flattened, axis=0, ddof=1) / (
            mean_denominator * math.sqrt(count))
    if not np.all(np.isfinite(ratio)) or not np.all(np.isfinite(standard_error)):
        raise ArithmeticError("ratio estimate or standard error is nonfinite")
    return {
        "ratio": ratio,
        "standard_error": standard_error,
        "mean_numerator": mean_numerator,
        "mean_denominator": mean_denominator,
        "batch_count": count,
    }


def largest_generalized_root(a_matrix, b_matrix, base_quotient=1.0,
                             relative_rank_tolerance=1e-12,
                             active_indices=None):
    """Largest root after diagonal equilibration and PSD whitening.

    ``active_indices`` must be supplied when the finite basis has exact null
    coordinates.  Statistical near-zeros are never used to guess the active
    subspace.  Diagonal equilibration is mandatory because positive rare-
    stratum masses can be far below a global numerical rank threshold.
    """
    a = _finite_array(a_matrix, "denominator matrix")
    b = _finite_array(b_matrix, "numerator matrix")
    if a.ndim != 2 or a.shape[0] != a.shape[1] or b.shape != a.shape:
        raise ValueError("generalized matrices must be same-size square arrays")
    if not math.isfinite(float(base_quotient)) or base_quotient <= 0:
        raise ValueError("base quotient must be finite and positive")
    if (not math.isfinite(float(relative_rank_tolerance)) or
            not 0 < relative_rank_tolerance < 1):
        raise ValueError("rank tolerance must lie strictly between zero and one")
    antisymmetry_a = float(np.max(np.abs(a - a.T), initial=0.0))
    antisymmetry_b = float(np.max(np.abs(b - b.T), initial=0.0))
    a_symmetric = (a + a.T) / 2
    b_symmetric = (b + b.T) / 2
    dimension = a.shape[0]
    if active_indices is None:
        active = np.arange(dimension, dtype=int)
    else:
        active = np.asarray(active_indices)
        if (active.ndim != 1 or active.size == 0 or
                not np.issubdtype(active.dtype, np.integer)):
            raise ValueError("active_indices must be a nonempty integer list")
        active = active.astype(int)
        if (np.any(active < 0) or np.any(active >= dimension) or
                len(set(int(x) for x in active)) != len(active)):
            raise ValueError("active_indices are duplicate or outside range")
        inactive_mask = np.ones(dimension, dtype=bool)
        inactive_mask[active] = False
        inactive = np.flatnonzero(inactive_mask)
        if inactive.size:
            # For the tagged D4 calibration, inactive coordinates are exact
            # zero functions selected by the byte-pinned oracle.  Do not let
            # a malformed active list discard a positive A mass or a B-only
            # direction silently.
            if (np.any(a[inactive, :] != 0) or
                    np.any(a[:, inactive] != 0) or
                    np.any(b[inactive, :] != 0) or
                    np.any(b[:, inactive] != 0)):
                raise ArithmeticError(
                    "inactive coordinate has a nonzero realized matrix row")
    a_active = a_symmetric[np.ix_(active, active)]
    b_active = b_symmetric[np.ix_(active, active)]
    diagonal = np.diag(a_active)
    if np.any(diagonal <= 0):
        raise ArithmeticError(
            "active denominator coordinates must have positive realized mass")
    diagonal_scale = 1 / np.sqrt(diagonal)
    a_equilibrated = diagonal_scale[:, None] * a_active * diagonal_scale[None, :]
    b_equilibrated = diagonal_scale[:, None] * b_active * diagonal_scale[None, :]
    eigenvalues, eigenvectors = np.linalg.eigh(a_equilibrated)
    scale = max(float(np.max(np.abs(eigenvalues), initial=0.0)), 1.0)
    if float(eigenvalues[0]) < -relative_rank_tolerance * scale:
        raise ArithmeticError("realized denominator matrix is materially indefinite")
    retained = eigenvalues > relative_rank_tolerance * scale
    if not np.any(retained):
        raise ArithmeticError("realized denominator matrix has zero numerical rank")
    if int(np.sum(retained)) != len(active):
        raise ArithmeticError(
            "active denominator matrix is numerically rank deficient")
    whitening = eigenvectors[:, retained] / np.sqrt(eigenvalues[retained])
    reduced = whitening.T @ b_equilibrated @ whitening
    roots, vectors = np.linalg.eigh((reduced + reduced.T) / 2)
    index = int(np.argmax(roots))
    root = float(roots[index]) * float(base_quotient)
    reduced_vector = vectors[:, index]
    active_vector = diagonal_scale * (whitening @ reduced_vector)
    vector = np.zeros(dimension)
    vector[active] = active_vector
    denominator = float(vector @ a_symmetric @ vector)
    numerator = float(vector @ b_symmetric @ vector) * float(base_quotient)
    if denominator <= 0 or not math.isfinite(root):
        raise ArithmeticError("generalized root has invalid realized denominator")
    return {
        "root": root,
        "rank": int(np.sum(retained)),
        "vector": vector,
        "rayleigh": numerator / denominator,
        "antisymmetry_a": antisymmetry_a,
        "antisymmetry_b": antisymmetry_b,
        "smallest_equilibrated_a_eigenvalue": float(eigenvalues[0]),
        "largest_equilibrated_a_eigenvalue": float(eigenvalues[-1]),
    }


def simultaneous_coverage(estimate, standard_error, exact, mask,
                          multiplier):
    estimate = _finite_array(estimate, "coverage estimate")
    standard_error = _finite_array(standard_error, "coverage standard error")
    exact = _finite_array(exact, "coverage oracle")
    mask = np.asarray(mask, dtype=bool)
    if not (estimate.shape == standard_error.shape == exact.shape == mask.shape):
        raise ValueError("coverage arrays must have identical shapes")
    if np.any(standard_error < 0):
        raise ValueError("standard errors cannot be negative")
    if not math.isfinite(float(multiplier)) or multiplier <= 0:
        raise ValueError("coverage multiplier must be finite and positive")
    discrepancy = np.abs(estimate - exact)
    radius = float(multiplier) * standard_error
    passed = np.logical_or(~mask, discrepancy <= radius)
    failed_indices = [tuple(int(x) for x in index)
                      for index in np.argwhere(~passed)]
    with np.errstate(divide="ignore", invalid="ignore"):
        standardized = np.where(
            standard_error > 0, discrepancy / standard_error,
            np.where(discrepancy == 0, 0.0, np.inf))
    return {
        "pass": not failed_indices,
        "failed_indices": failed_indices,
        "max_standardized_discrepancy": float(
            np.max(standardized[mask], initial=0.0)),
        "checked_entries": int(np.sum(mask)),
    }
