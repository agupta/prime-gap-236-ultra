#!/usr/bin/env python3
"""Propose three rational C10 degree-band trials from the recovered action.

No capped form is evaluated here.  The trials take three controlled near-side
steps along the full-simplex-I-preconditioned first-derivative direction and
carry only base-point derivative diagnostics.  A trial has no quotient claim
until a fresh scalar grouped traversal evaluates that explicit rational vector.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXACT_AGENT = HERE.parents[1] / "exact-integrator"
sys.path[:0] = [str(HERE), str(EXACT_AGENT), str(EXACT_AGENT / "src")]

from band_line_search import (BandMap, direction_from_gradient,  # noqa: E402
                              file_sha)
from recover_band_gradient import (BASELINE_SHA, PINNED, RAW_SHA,  # noqa: E402
                                   atomic_write, dependency_paths,
                                   require_distinct_output, sha,
                                   trusted_input_paths,
                                   validate_rejected)


RECOVERY_SCRIPT_SHA = \
    "9342fa3f6d8157a4d9b8603a20bb0527b7f47087a5aa3c9d39aebef892f9fee5"
RECOVERY_ARTIFACT_SHA = \
    "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43"
LINE_SEARCH_SHA = \
    "f5acf5f3b5a0c87f65175b724acafaf805dee40f43039e5b9300d2b0b6758f09"


def exact_median(values):
    values = sorted(values)
    n = len(values)
    if not n:
        raise ValueError("median of empty data")
    return values[n // 2] if n % 2 else \
        (values[n // 2 - 1] + values[n // 2]) / 2


def fraction_decimal(value, digits=60):
    with __import__("decimal").localcontext() as context:
        context.prec = digits
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def projective_steps(ratios, reference, target):
    """Exact near/far steps with a prescribed post-gauge max change."""
    reference_ratio = ratios[reference]
    if reference_ratio >= 0:
        raise ValueError("the pinned H12 reference ratio must be negative")
    c = -reference_ratio
    spread = max(abs(value - reference_ratio) for value in ratios)
    if not 0 < target or not spread < target * c:
        raise ValueError("target does not straddle the projective pole")
    near = target / (spread + target * c)
    pole = Fraction(1, 1) / c
    far = target / (target * c - spread)
    if not 0 < near < pole < far:
        raise ArithmeticError("projective step ordering failure")
    return near, pole, far, spread, c


def recursive_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from recursive_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from recursive_keys(item)


def rebind_trusted(expected_hashes):
    """Fail closed if any byte-pinned input changed before an output write."""
    changed = [str(path) for path, expected in expected_hashes.items()
               if sha(path) != expected]
    if changed:
        raise RuntimeError("trusted trial input changed: " + ", ".join(changed))


def bind_written_trials(written, expected_hashes):
    """Add freshly written trials to the final manifest's byte closure."""
    for item in written:
        path = Path(item["path"]).resolve()
        expected = item["sha256"]
        if path in expected_hashes and expected_hashes[path] != expected:
            raise RuntimeError(f"written trial aliases a trusted byte: {path}")
        expected_hashes[path] = expected
    rebind_trusted(expected_hashes)


def validate_recovery(recovery_bytes, raw_bytes, source_path, bands_path):
    if sha(recovery_bytes) != RECOVERY_ARTIFACT_SHA:
        raise ValueError("recovery artifact SHA")
    if sha(HERE / "recover_band_gradient.py") != RECOVERY_SCRIPT_SHA:
        raise ValueError("recovery script SHA")
    if sha(HERE / "band_line_search.py") != LINE_SEARCH_SHA:
        raise ValueError("line-search dependency SHA")
    raw, recovered, evidence = validate_rejected(
        raw_bytes, source_path, bands_path)
    recovery = json.loads(recovery_bytes)
    expected_scalars = {
        "status": "byte-pinned-recovered-degree-band-gradient-discovery",
        "rigorous": False, "complete": True,
        "no_projected_trial_emitted": True,
        "raw_sha256": RAW_SHA,
        "recovery_script_sha256": RECOVERY_SCRIPT_SHA,
        "source_sha256": PINNED["source"], "bands_sha256": PINNED["bands"],
        "decimal_dps": 100,
    }
    for key, value in expected_scalars.items():
        if recovery.get(key) != value:
            raise ValueError(f"recovery field {key}")
    exact_fields = {
        "parameters": raw["parameters"], "theta": raw["theta"],
        "denominator": raw["denominator"], "numerator": raw["numerator"],
        "grad_denominator": raw["grad_denominator"],
        "grad_numerator": raw["grad_numerator"],
        "a_theta_exact_fraction_half": recovered["a_theta"],
        "b_theta_exact_fraction_half": recovered["b_theta"],
        "recorded_half_mismatch_evidence": evidence,
    }
    for key, value in exact_fields.items():
        if recovery.get(key) != value:
            raise ValueError(f"recovery payload {key}")
    expected_gates = {
        "raw_bytes_sha_pinned", "sole_raw_failure_is_redundant_halves",
        "substantive_producer_invariants_recomputed",
        "dependencies_and_parameters_pinned",
        "exact_half_mismatch_below_1e98_relative",
        "no_projected_trial_or_quotient_emitted",
    }
    gates = recovery.get("validation_gates", {})
    if set(gates) != expected_gates or not all(gates.values()):
        raise ValueError("recovery validation gates")
    return raw, recovered


def build_trials(raw, recovered, band_map, precision=230):
    """Return manifest diagnostics and three exact rational input objects."""
    numerator, denominator = Fraction(raw["numerator"]), Fraction(raw["denominator"])
    base_ratio = numerator / denominator
    gradient_view = {
        "theta": raw["theta"],
        "a_theta": recovered["a_theta"],
        "b_theta": recovered["b_theta"],
        "quotient": str(base_ratio),
        "parameters": raw["parameters"],
    }
    getcontext().prec = precision
    first = direction_from_gradient(gradient_view, band_map, precision)
    second = direction_from_gradient(gradient_view, band_map, precision + 40)
    theta_decimal, a_decimal, b_decimal, direction_decimal, residual_decimal, diagnostics = first
    direction_stability = max(abs(x - y) for x, y in zip(
        direction_decimal, second[3])) / max(
            max(abs(x) for x in second[3]), Decimal(1))
    normalized_orthogonality = abs(diagnostics["theta_p_direction"]) / \
        diagnostics["theta_p_norm"].sqrt()
    if (direction_stability > Decimal("1e-80") or
            diagnostics["raw_solve_relative_infinity_error"] > Decimal("1e-180") or
            normalized_orthogonality > Decimal("1e-180") or
            abs(diagnostics["direction_p_norm_error"]) > Decimal("1e-180")):
        raise ArithmeticError("direction stability/orthogonality gate")

    direction = [Fraction(str(x)) for x in direction_decimal]
    action_theta = [Fraction(x) for x in raw["theta"]]
    # The gradient channels are actions at the serialized Decimal theta, not
    # at the longer source rationals from which Decimal theta was rounded.
    # Build every trial from that exact serialized action base.
    theta_base = action_theta
    if theta_base[19] != 1:
        raise ArithmeticError("serialized H12 base coordinate is not one")
    a_theta = [Fraction(x) for x in recovered["a_theta"]]
    b_theta = [Fraction(x) for x in recovered["b_theta"]]
    residual = [b - base_ratio * a for a, b in zip(a_theta, b_theta)]
    residual_pairing = sum((d * r for d, r in zip(direction, residual)), Fraction(0))
    if residual_pairing <= 0:
        raise ArithmeticError("direction is not oriented by positive derivative")
    d_prime = 2 * sum((d * a for d, a in zip(direction, a_theta)), Fraction(0))
    n_prime = 2 * sum((d * b for d, b in zip(direction, b_theta)), Fraction(0))
    rayleigh_prime = (n_prime * denominator - numerator * d_prime) / \
        (denominator * denominator)
    if rayleigh_prime <= 0:
        raise ArithmeticError("nonpositive Rayleigh first derivative")
    euler_residual = sum((t * r for t, r in zip(action_theta, residual)), Fraction(0))

    relative_ratios = [direction[i] / theta_base[i]
                       for i in range(band_map.dimension)]
    near5, _, _, _, _ = projective_steps(
        relative_ratios, 19, Fraction(1, 20))
    near10, _, _, _, _ = projective_steps(
        relative_ratios, 19, Fraction(1, 10))
    near20, pole, _, spread, c = projective_steps(
        relative_ratios, 19, Fraction(1, 5))
    specifications = (
        ("h12_near_5pct", near5, Fraction(1, 20), "near"),
        ("h12_near_10pct", near10, Fraction(1, 10), "near"),
        ("h12_near_20pct", near20, Fraction(1, 5), "near"),
    )
    base_expanded = band_map.expand(theta_base)
    if any(not x for x in base_expanded):
        raise ArithmeticError("zero base coefficient prevents relative audit")
    trials = []
    for name, step, target, side in specifications:
        unscaled = [theta_base[i] + step * direction[i]
                    for i in range(band_map.dimension)]
        if not unscaled[19]:
            raise ArithmeticError("trial hit H12 projective pole")
        scale = Fraction(1, 1) / unscaled[19]
        theta_trial = [scale * value for value in unscaled]
        if theta_trial[19] != 1:
            raise ArithmeticError("H12 gauge normalization failure")
        expanded = band_map.expand(theta_trial)
        compressed_changes = [abs((theta_trial[i] - theta_base[i]) /
                                  theta_base[i])
                              for i in range(band_map.dimension)]
        raw_changes = [abs((unscaled[band_map.owner[i]] -
                            theta_base[band_map.owner[i]]) /
                           theta_base[band_map.owner[i]])
                       for i in range(len(band_map.labels))]
        normalized_changes = [abs((expanded[i] - base_expanded[i]) /
                                  base_expanded[i])
                              for i in range(len(expanded))]
        if max(normalized_changes) != target:
            raise ArithmeticError("prescribed projective perturbation not attained")
        displacement = [x - y for x, y in zip(theta_trial, theta_base)]
        trial_first_derivative = 2 * sum(
            (x * r for x, r in zip(displacement, residual)), Fraction(0)) / \
            denominator
        scaled_raw_first_derivative = scale * step * rayleigh_prime
        if trial_first_derivative <= 0:
            raise ArithmeticError("nonpositive normalized-trial first derivative")
        trial = {
            "status": "recovered-action-rational-band-trial",
            "rigorous": False,
            "fresh_scalar_reevaluation_required": True,
            "finite_form_value_claimed": False,
            "k": 48,
            "parameters": raw["parameters"],
            "basis": [[a, list(lam)] for a, lam in band_map.labels],
            "compressed_theta": [str(x) for x in theta_trial],
            "rational_vector": [str(x) for x in expanded],
            "trial": {
                "name": name,
                "projective_pole_side": side,
                "exact_step_t": str(step),
                "exact_H12_gauge_scale": str(scale),
                "normalization": "multiply theta0+t*d so compressed H12 coordinate equals 1",
                "H12_coordinate": "1",
                "raw_path_max_relative_coefficient_change": str(max(raw_changes)),
                "raw_path_median_relative_coefficient_change": str(
                    exact_median(raw_changes)),
                "normalized_max_relative_coefficient_change": str(
                    max(normalized_changes)),
                "normalized_median_relative_coefficient_change": str(
                    exact_median(normalized_changes)),
                "normalized_max_relative_change_decimal": fraction_decimal(
                    max(normalized_changes)),
                "normalized_median_relative_change_decimal": fraction_decimal(
                    exact_median(normalized_changes)),
                "compressed_max_relative_coordinate_change": str(
                    max(compressed_changes)),
                "compressed_median_relative_coordinate_change": str(
                    exact_median(compressed_changes)),
                "compressed_max_relative_change_decimal": fraction_decimal(
                    max(compressed_changes)),
                "compressed_median_relative_change_decimal": fraction_decimal(
                    exact_median(compressed_changes)),
                "normalized_trial_first_derivative_exact": str(
                    trial_first_derivative),
                "normalized_trial_first_derivative_decimal": fraction_decimal(
                    trial_first_derivative),
                "scaled_raw_path_first_derivative_exact": str(
                    scaled_raw_first_derivative),
                "scaled_raw_path_first_derivative_decimal": fraction_decimal(
                    scaled_raw_first_derivative),
                "note": "The derivative fields are first-order changes at the serialized action base, not finite-step form evaluations.",
            },
        }
        trials.append(trial)
    diagnostics_out = {
        "precision": precision,
        "second_precision": precision + 40,
        "direction_stability_relative": str(direction_stability),
        "P_theta_dot_direction": str(diagnostics["theta_p_direction"]),
        "normalized_P_orthogonality": str(normalized_orthogonality),
        "direction_P_norm_error": str(diagnostics["direction_p_norm_error"]),
        "raw_solve_relative_infinity_error": str(
            diagnostics["raw_solve_relative_infinity_error"]),
        "theta_dot_rayleigh_residual_exact": str(euler_residual),
        "theta_dot_residual_relative_to_numerator": str(
            abs(euler_residual / numerator)),
        "direction_dot_residual_exact": str(residual_pairing),
        "denominator_first_derivative_exact": str(d_prime),
        "numerator_first_derivative_exact": str(n_prime),
        "rayleigh_first_derivative_exact": str(rayleigh_prime),
        "rayleigh_first_derivative_decimal": fraction_decimal(rayleigh_prime),
        "H12_projective_pole_step": str(pole),
        "relative_direction_spread": str(spread),
        "negative_H12_relative_direction": str(c),
        "direction": [str(x) for x in direction],
    }
    return diagnostics_out, trials


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--recovery", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--bands", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--precision", type=int, default=230)
    args = ap.parse_args()
    if args.precision < 220:
        raise SystemExit("precision must be at least 220")
    raw_bytes = Path(args.raw).read_bytes()
    recovery_bytes = Path(args.recovery).read_bytes()
    try:
        raw, recovered = validate_recovery(
            recovery_bytes, raw_bytes, args.source, args.bands)
    except Exception as exc:
        raise SystemExit(f"recovery consumer validation failed: {exc}") from exc
    band_map = BandMap.from_source_and_bands(args.source, args.bands)
    diagnostics, trials = build_trials(raw, recovered, band_map, args.precision)
    output_dir = Path(args.output_dir)
    trial_paths = [output_dir / f"c10_D12_{item['trial']['name']}_v3.json"
                   for item in trials]
    manifest_path = Path(args.manifest)
    trusted = [*trusted_input_paths(args.raw, args.source, args.bands),
               Path(args.recovery), HERE / "band_line_search.py", Path(__file__)]
    destinations = [*trial_paths, manifest_path]
    if len({path.resolve() for path in destinations}) != len(destinations):
        raise SystemExit("trial destination paths alias")
    try:
        for path in destinations:
            require_distinct_output(path, trusted)
    except ValueError as exc:
        raise SystemExit(f"trial output validation failed: {exc}") from exc
    self_sha = file_sha(__file__)
    expected_hashes = {
        Path(args.raw).resolve(): RAW_SHA,
        Path(args.recovery).resolve(): RECOVERY_ARTIFACT_SHA,
        Path(args.source).resolve(): PINNED["source"],
        Path(args.bands).resolve(): PINNED["bands"],
        (HERE / "recover_band_gradient.py").resolve(): RECOVERY_SCRIPT_SHA,
        (HERE / "band_line_search.py").resolve(): LINE_SEARCH_SHA,
        Path(__file__).resolve(): self_sha,
    }
    for path in trusted_input_paths(args.raw, args.source, args.bands):
        resolved = Path(path).resolve()
        if resolved not in expected_hashes:
            if resolved.name == "c10_capped_fullD12_vector_grouped_mp100.json":
                expected_hashes[resolved] = BASELINE_SHA
            else:
                dependency_name = next(
                    (key for key, value in dependency_paths().items()
                     if value.resolve() == resolved), None)
                if dependency_name is None:
                    raise SystemExit(f"unclassified trusted input {resolved}")
                expected_hashes[resolved] = PINNED[dependency_name]
    common_provenance = {
        "raw_gradient_sha256": RAW_SHA,
        "recovery_artifact_sha256": RECOVERY_ARTIFACT_SHA,
        "recovery_script_sha256": RECOVERY_SCRIPT_SHA,
        "trial_script_sha256": self_sha,
        "line_search_dependency_sha256": LINE_SEARCH_SHA,
        "source_sha256": PINNED["source"],
        "bands_sha256": PINNED["bands"],
        "no_finite_form_evaluation": True,
    }
    written = []
    for path, trial in zip(trial_paths, trials):
        trial["provenance"] = common_provenance
        rendered = json.dumps(trial, indent=2) + "\n"
        rebind_trusted(expected_hashes)
        atomic_write(path, rendered)
        written.append({"name": trial["trial"]["name"], "path": str(path),
                        "sha256": sha(path)})
    manifest = {
        "status": "three-rational-band-trials-awaiting-scalar-selection",
        "rigorous": False,
        "fresh_scalar_reevaluation_required": True,
        "trial_count": len(trials),
        "provenance": common_provenance,
        "base_action_diagnostics": diagnostics,
        "trials": written,
        "statement": "No finite-step denominator, numerator, or Rayleigh value has been computed for these trials.",
    }
    # Bind the just-written trial bytes too, then rebind the complete closure
    # immediately before the final manifest write.
    bind_written_trials(written, expected_hashes)
    atomic_write(manifest_path, json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "status": manifest["status"],
        "manifest_sha256": sha(manifest_path),
        "trials": written,
        "rayleigh_first_derivative_decimal": diagnostics[
            "rayleigh_first_derivative_decimal"],
        "no_finite_form_evaluation": True,
    }, indent=2))


if __name__ == "__main__":
    main()
