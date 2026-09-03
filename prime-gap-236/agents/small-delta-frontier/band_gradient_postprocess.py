#!/usr/bin/env python3
"""Fail-closed consumer for the frozen C10 D12 20-band gradient artifact.

This program deliberately does *not* turn a Decimal gradient into a theorem or
an improved Rayleigh quotient.  It checks the complete discovery-artifact
identity and, when the serialized residual is large enough to be useful,
emits one exact rational perturbation which must be evaluated from scratch.
Otherwise it emits an explicit no-claim record.

The emitted ``rational_vector`` is the finite-step trial polynomial, so it can
be passed to an independent scalar evaluator.  No form value for that trial is
predicted or asserted here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
STRUCTURAL = PROJECT / "agents" / "structural-basis"
EXACT_AGENT = PROJECT / "agents" / "exact-integrator"
CODE = STRUCTURAL / "code"
EXACT_SRC = EXACT_AGENT / "src"
sys.path[:0] = [str(CODE), str(EXACT_AGENT), str(EXACT_SRC)]

import exact_integrator as ei  # noqa: E402
from band_operator import BandMap  # noqa: E402


PINNED = {
    "source": "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
    "bands": "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9",
    "sparse": "e1545435f0c7ad22a17115ac46c291436c1ead5101fd3de6d2a80ab65bc9c257",
    "band": "e4fbf7a97d061d362c32b54bf0d49a89c4195b965e96d7ab89a2581bc907c073",
    "grouped": "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator": "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "baseline": "02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9",
}

PARAMETERS = {
    "alpha": Fraction(79247, 300000),
    "delta": Fraction(1, 100),
    "eta": Fraction(76247, 300000),
    "beta1": Fraction(3, 20),
    "beta2": Fraction(3, 20),
    "beta3plus": Fraction(97, 625),
}

EXPECTED_GATES = {
    "decimal_dps_at_least_90",
    "source_sha_pinned",
    "bands_sha_pinned",
    "operator_unchanged_during_run",
    "band_dependency_sha_pinned_and_unchanged",
    "grouped_sha_pinned_and_unchanged",
    "integrator_sha_pinned_and_unchanged",
    "source_k48_dim272_banddim20",
    "parameters_exact_c10",
    "all_vectors_length20",
    "all_numbers_finite",
    "gradient_halves_match",
    "denominator_positive",
    "quotient_recomputed",
    "euler_relative_below_1e50",
    "complete_traversal_counts",
    "stratum_buckets_sum",
    "baseline_artifact_sha_pinned",
    "baseline_dependencies_match",
    "baseline_forms_50_digits",
}

EXPECTED_GRADIENT_KEYS = {
    "status", "implementation", "rigorous", "complete", "decimal_dps",
    "workers", "source_json", "source_sha256", "bands_json",
    "bands_sha256", "operator_sha256", "band_operator_dependency_sha256",
    "integrator_sha256", "grouped_evaluator_sha256", "baseline_json",
    "baseline_sha256", "parameters", "theta", "denominator", "numerator",
    "quotient", "a_theta", "b_theta", "grad_denominator",
    "grad_numerator", "euler_denominator_error", "euler_numerator_error",
    "i_orbit_groups", "i_faces", "marginal_components",
    "j_branch_integrals", "i_seconds", "j_seconds", "total_seconds",
    "i_value_by_r", "j_value_by_r", "peak_rss_kib",
    "child_peak_rss_kib", "gates_passed", "gates",
    "euler_denominator_relative", "euler_numerator_relative",
    "baseline_relative_tolerance",
}

HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class ValidationError(ValueError):
    """A fail-closed artifact or provenance rejection."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha256_bytes(Path(path).read_bytes())


def _reject_constant(value):
    raise ValidationError(f"non-finite JSON constant {value!r}")


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValidationError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def strict_load_bytes(data, description):
    try:
        value = json.loads(
            data, object_pairs_hook=_unique_object,
            parse_constant=_reject_constant)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        raise ValidationError(f"malformed {description}: {exc}") from exc
    require(isinstance(value, dict), f"{description} must be a JSON object")
    return value


def decimal_token(value, name):
    require(isinstance(value, str) and value.strip() == value,
            f"{name} must be a whitespace-free Decimal string")
    try:
        result = Decimal(value)
    except Exception as exc:
        raise ValidationError(f"invalid Decimal token for {name}") from exc
    require(result.is_finite(), f"{name} is non-finite")
    return result


def fraction_token(value, name):
    require(isinstance(value, str) and value.strip() == value,
            f"{name} must be a whitespace-free rational string")
    try:
        return Fraction(value)
    except Exception as exc:
        raise ValidationError(f"invalid rational token for {name}") from exc


def parse_label(value, name):
    require(isinstance(value, list) and len(value) == 2,
            f"{name} is not [a,lambda]")
    a, lam = value
    require(type(a) is int and a >= 0 and isinstance(lam, list) and
            all(type(x) is int and x >= 2 for x in lam),
            f"invalid no-ones label {name}")
    label = (a, tuple(lam))
    require(tuple(sorted(label[1], reverse=True)) == label[1],
            f"partition is not ordered at {name}")
    return label


def validate_source_and_bands(source, bands, band_map):
    require(source.get("k") == 48 and source.get("degree") == 12 and
            source.get("basis_dimension") == 272 and
            source.get("rigorous") is True,
            "source is not the exact k=48 no-ones D12 artifact")
    raw_basis = source.get("basis")
    raw_vector = source.get("rational_vector")
    require(isinstance(raw_basis, list) and isinstance(raw_vector, list) and
            len(raw_basis) == len(raw_vector) == 272,
            "source basis/vector dimension")
    labels = tuple(parse_label(x, f"source basis[{i}]")
                   for i, x in enumerate(raw_basis))
    require(len(set(labels)) == 272, "duplicate source label")
    expected_basis = tuple(ei.no_ones_basis(12, 48))
    require(labels == expected_basis,
            "source basis is not the complete ordered no-ones D12 basis")
    coefficients = tuple(fraction_token(x, f"source coefficient[{i}]")
                         for i, x in enumerate(raw_vector))
    require(all(x != 0 for x in coefficients),
            "source contains a zero coefficient (band ownership ambiguity)")
    require(source.get("integrator_sha256") == PINNED["integrator"],
            "source integrator SHA")
    require(all(Fraction(source.get("parameters", {}).get(key, "NaN")) == value
                for key, value in {
                    "alpha": Fraction(79247, 300000),
                    "delta": Fraction(1, 100),
                    "eta": Fraction(76247, 300000),
                    "beta1": Fraction(79247, 300000),
                    "beta2": Fraction(79247, 300000),
                    "beta3plus": Fraction(79247, 300000),
                }.items()), "source full-simplex parameters")

    require(bands.get("status") == "exact-rational-degree-band-decomposition" and
            bands.get("source_sha256") == PINNED["source"] and
            bands.get("compressed_basis_dimension") == 20 and
            bands.get("expanded_term_count") == 272 and
            bands.get("core_degree") == 4 and
            bands.get("total_degree") == "a+sum(lambda)",
            "band decomposition metadata")
    core = bands.get("core")
    blocks = bands.get("bands")
    require(isinstance(core, list) and len(core) == 12 and
            isinstance(blocks, dict) and set(blocks) ==
            {str(x) for x in range(5, 13)}, "band block shape")

    source_by_label = dict(zip(labels, coefficients))
    seen = []
    for i, item in enumerate(core):
        require(isinstance(item, dict) and set(item) == {"label", "coefficient"},
                f"core[{i}] fields")
        label = parse_label(item["label"], f"core[{i}]")
        coefficient = fraction_token(item["coefficient"],
                                     f"core[{i}] coefficient")
        require(label[0] + sum(label[1]) <= 4 and
                source_by_label.get(label) == coefficient,
                f"core[{i}] identity")
        seen.append(label)
    for degree in range(5, 13):
        block = blocks[str(degree)]
        require(isinstance(block, list), f"band {degree} is not a list")
        for i, item in enumerate(block):
            require(isinstance(item, dict) and
                    set(item) == {"label", "coefficient"},
                    f"band {degree}[{i}] fields")
            label = parse_label(item["label"], f"band {degree}[{i}]")
            coefficient = fraction_token(
                item["coefficient"], f"band {degree}[{i}] coefficient")
            require(label[0] + sum(label[1]) == degree and
                    source_by_label.get(label) == coefficient,
                    f"band {degree}[{i}] identity")
            seen.append(label)
    require(tuple(seen) == labels,
            "core/bands do not reproduce the complete ordered source basis")
    require(tuple(band_map.labels) == labels and
            tuple(band_map.expand(band_map.theta0_q)) == coefficients and
            band_map.dimension == 20,
            "BandMap reconstruction")
    require(tuple(band_map.owner[:12]) == tuple(range(12)) and
            all(band_map.owner[i] == 12 + labels[i][0] +
                sum(labels[i][1]) - 5 for i in range(12, 272)),
            "actual core/degree channel ownership")
    return labels, coefficients


def validate_baseline(baseline):
    require(baseline.get("status") ==
            "multiprecision-grouped-fixed-vector-discovery" and
            baseline.get("rigorous") is False and
            baseline.get("decimal_dps") == 100 and
            baseline.get("k") == 48 and
            baseline.get("basis_dimension") == 272 and
            baseline.get("input_sha256") == PINNED["source"] and
            baseline.get("script_sha256") == PINNED["grouped"] and
            baseline.get("integrator_sha256") == PINNED["integrator"],
            "baseline identity/dependencies")
    require((baseline.get("i_orbit_groups"), baseline.get("i_faces"),
             baseline.get("marginal_components"),
             baseline.get("j_branch_integrals")) == (1575, 312, 695, 1200),
            "baseline traversal counts")
    require(all(Fraction(baseline.get("parameters", {}).get(key, "NaN")) == value
                for key, value in PARAMETERS.items()), "baseline parameters")
    values = {key: decimal_token(baseline.get(key), f"baseline {key}")
              for key in ("denominator", "numerator", "quotient")}
    require(values["denominator"] > 0, "baseline denominator")
    return values


def validate_gradient(gradient, source, bands, baseline, band_map):
    require(set(gradient) == EXPECTED_GRADIENT_KEYS,
            f"gradient key set mismatch: missing={sorted(EXPECTED_GRADIENT_KEYS-set(gradient))}, "
            f"extra={sorted(set(gradient)-EXPECTED_GRADIENT_KEYS)}")
    require(gradient.get("status") ==
            "multiprecision-degree-band-gradient-discovery" and
            gradient.get("implementation") == "sparse-structure-of-arrays" and
            gradient.get("rigorous") is False and
            gradient.get("complete") is True,
            "gradient status")
    require(type(gradient.get("decimal_dps")) is int and
            gradient["decimal_dps"] >= 90 and
            type(gradient.get("workers")) is int and
            gradient["workers"] in (1, 2), "precision/workers")
    dps = gradient["decimal_dps"]
    require(gradient.get("gates_passed") is True and
            isinstance(gradient.get("gates"), dict) and
            set(gradient["gates"]) == EXPECTED_GATES and
            all(value is True for value in gradient["gates"].values()),
            "producer gate record")
    require(gradient.get("source_sha256") == PINNED["source"] ==
            band_map.source_sha256 and
            gradient.get("bands_sha256") == PINNED["bands"] ==
            band_map.bands_sha256 and
            gradient.get("operator_sha256") == PINNED["sparse"] and
            gradient.get("band_operator_dependency_sha256") == PINNED["band"] and
            gradient.get("grouped_evaluator_sha256") == PINNED["grouped"] and
            gradient.get("integrator_sha256") == PINNED["integrator"] and
            gradient.get("baseline_sha256") == PINNED["baseline"],
            "gradient pinned hashes")
    require(all(Fraction(gradient.get("parameters", {}).get(key, "NaN")) == value
                for key, value in PARAMETERS.items()), "gradient parameters")
    require((gradient.get("i_orbit_groups"), gradient.get("i_faces"),
             gradient.get("marginal_components"),
             gradient.get("j_branch_integrals")) == (1575, 312, 695, 1200),
            "gradient traversal counts")
    require(gradient.get("baseline_relative_tolerance") == "1E-50",
            "baseline tolerance token")
    for key in ("i_seconds", "j_seconds", "total_seconds"):
        value = gradient.get(key)
        require(type(value) in (int, float) and not isinstance(value, bool) and
                math.isfinite(value) and value >= 0, f"invalid {key}")
    require(gradient["total_seconds"] + 1e-9 >=
            gradient["i_seconds"] + gradient["j_seconds"],
            "phase timing inconsistency")
    for key in ("peak_rss_kib", "child_peak_rss_kib"):
        require(type(gradient.get(key)) is int and gradient[key] >= 0,
                f"invalid {key}")

    baseline_values = validate_baseline(baseline)
    vector_keys = ("theta", "a_theta", "b_theta", "grad_denominator",
                   "grad_numerator")
    require(all(isinstance(gradient.get(key), list) and
                len(gradient[key]) == 20 for key in vector_keys),
            "gradient vector dimensions")
    require(isinstance(gradient.get("i_value_by_r"), list) and
            isinstance(gradient.get("j_value_by_r"), list) and
            len(gradient["i_value_by_r"]) ==
            len(gradient["j_value_by_r"]) == 16,
            "stratum bucket dimensions")

    with localcontext() as ctx:
        ctx.prec = dps
        theta = [decimal_token(x, f"theta[{i}]")
                 for i, x in enumerate(gradient["theta"])]
        expected_theta = [Decimal(q.numerator) / Decimal(q.denominator)
                          for q in band_map.theta0_q]
        require(theta == expected_theta, "theta does not equal exact theta0")
        a = [decimal_token(x, f"a_theta[{i}]")
             for i, x in enumerate(gradient["a_theta"])]
        b = [decimal_token(x, f"b_theta[{i}]")
             for i, x in enumerate(gradient["b_theta"])]
        grad_d = [decimal_token(x, f"grad_denominator[{i}]")
                  for i, x in enumerate(gradient["grad_denominator"])]
        grad_n = [decimal_token(x, f"grad_numerator[{i}]")
                  for i, x in enumerate(gradient["grad_numerator"])]
        require(all(Decimal(2) * x == y for x, y in zip(a, grad_d)) and
                all(Decimal(2) * x == y for x, y in zip(b, grad_n)),
                "gradient halves")
        denominator = decimal_token(gradient["denominator"], "denominator")
        numerator = decimal_token(gradient["numerator"], "numerator")
        quotient = decimal_token(gradient["quotient"], "quotient")
        require(denominator > 0 and quotient == numerator / denominator,
                "denominator or quotient recomputation")
        euler_d = sum((x * y for x, y in zip(theta, grad_d)), Decimal(0)) - \
            Decimal(2) * denominator
        euler_n = sum((x * y for x, y in zip(theta, grad_n)), Decimal(0)) - \
            Decimal(2) * numerator
        serialized_euler_d = decimal_token(
            gradient["euler_denominator_error"], "Euler D")
        serialized_euler_n = decimal_token(
            gradient["euler_numerator_error"], "Euler N")
        require(euler_d == serialized_euler_d and euler_n == serialized_euler_n,
                "Euler values do not reconstruct")
        tolerance = Decimal("1e-50")
        rel_d = abs(euler_d) / abs(denominator)
        rel_n = abs(euler_n) / abs(numerator)
        require(rel_d <= tolerance and rel_n <= tolerance and
                decimal_token(gradient["euler_denominator_relative"],
                              "Euler D relative") == rel_d and
                decimal_token(gradient["euler_numerator_relative"],
                              "Euler N relative") == rel_n,
                "Euler relative gate")
        i_buckets = [decimal_token(x, f"I bucket[{i}]")
                     for i, x in enumerate(gradient["i_value_by_r"])]
        j_buckets = [decimal_token(x, f"J bucket[{i}]")
                     for i, x in enumerate(gradient["j_value_by_r"])]
        require(sum(i_buckets, Decimal(0)) == denominator and
                Decimal(48) * sum(j_buckets, Decimal(0)) == numerator,
                "stratum buckets do not reconstruct I and 48J")
        for key, observed in (("denominator", denominator),
                              ("numerator", numerator),
                              ("quotient", quotient)):
            reference = baseline_values[key]
            require(abs(observed - reference) <= tolerance * abs(reference),
                    f"gradient {key} does not match scalar baseline")

        residual = [+(y - quotient * x) for x, y in zip(a, b)]
    return {
        "dps": dps,
        "theta": theta,
        "a": a,
        "b": b,
        "denominator": denominator,
        "numerator": numerator,
        "quotient": quotient,
        "residual": residual,
    }


def rational_sign(value):
    return 1 if value > 0 else -1 if value < 0 else 0


def build_trial(validated, band_map, step, minimum_relative_signal):
    """Build an L-infinity-relative ascent direction, with no quotient claim."""
    theta_q = tuple(band_map.theta0_q)
    residual = validated["residual"]
    direction_q = tuple(Fraction(rational_sign(r)) * abs(t)
                        for r, t in zip(residual, theta_q))
    with localcontext() as ctx:
        ctx.prec = validated["dps"]
        direction_decimal = [Decimal(x.numerator) / Decimal(x.denominator)
                             for x in direction_q]
        residual_pairing = sum((x * y for x, y in
                                zip(direction_decimal, residual)), Decimal(0))
        scale = max(abs(validated["numerator"]),
                    abs(validated["quotient"] * validated["denominator"]))
        relative_signal = (residual_pairing / scale if scale else Decimal(0))
    if not any(direction_q) or residual_pairing <= 0 or \
            relative_signal < minimum_relative_signal:
        return None, residual_pairing, relative_signal
    trial_theta = tuple(x + step * y for x, y in zip(theta_q, direction_q))
    direction_vector = tuple(band_map.expand(direction_q))
    trial_vector = tuple(band_map.expand(trial_theta))
    require(len(direction_vector) == len(trial_vector) == 272,
            "internal expanded trial dimension")
    return {
        "direction_theta": direction_q,
        "direction_vector": direction_vector,
        "trial_theta": trial_theta,
        "trial_vector": trial_vector,
    }, residual_pairing, relative_signal


def _resolved(path):
    return Path(path).resolve(strict=False)


def process(gradient_path, expected_gradient_sha, source_path, bands_path,
            output_path, step=Fraction(1, 4096),
            minimum_relative_signal=Decimal("1e-60")):
    require(isinstance(expected_gradient_sha, str) and
            HEX64.fullmatch(expected_gradient_sha) is not None,
            "--gradient-sha256 must be 64 lowercase hex characters")
    require(step > 0 and step <= Fraction(1, 16),
            "trial step must lie in (0,1/16]")
    require(minimum_relative_signal.is_finite() and
            minimum_relative_signal >= 0,
            "invalid minimum relative signal")

    paths = {
        "postprocessor": Path(__file__),
        "gradient": Path(gradient_path),
        "source": Path(source_path),
        "bands": Path(bands_path),
        "sparse": CODE / "band_operator_sparse.py",
        "band": CODE / "band_operator.py",
        "grouped": EXACT_AGENT / "grouped_fixed_vector.py",
        "integrator": EXACT_SRC / "exact_integrator.py",
        "baseline": EXACT_AGENT / "results" /
                    "c10_capped_fullD12_vector_grouped_mp100.json",
    }
    output = Path(output_path)
    protected = {_resolved(path) for path in paths.values()}
    require(_resolved(output) not in protected,
            "output path collides with an input or arithmetic dependency")
    require(not output.exists(), "refusing to overwrite an existing output")
    require(len(protected) == len(paths), "two protected inputs alias each other")

    raw = {name: path.read_bytes() for name, path in paths.items()}
    hashes = {name: sha256_bytes(data) for name, data in raw.items()}
    require(hashes["gradient"] == expected_gradient_sha,
            "gradient byte SHA mismatch")
    for name in ("source", "bands", "sparse", "band", "grouped",
                 "integrator", "baseline"):
        require(hashes[name] == PINNED[name], f"pinned {name} SHA mismatch")

    source = strict_load_bytes(raw["source"], "source")
    bands = strict_load_bytes(raw["bands"], "bands")
    gradient = strict_load_bytes(raw["gradient"], "gradient")
    baseline = strict_load_bytes(raw["baseline"], "baseline")
    band_map = BandMap.from_source_and_bands(str(paths["source"]),
                                             str(paths["bands"]))
    labels, _ = validate_source_and_bands(source, bands, band_map)
    validated = validate_gradient(gradient, source, bands, baseline, band_map)
    trial, pairing, relative_signal = build_trial(
        validated, band_map, step, minimum_relative_signal)

    common = {
        "rigorous": False,
        "theorem_ready": False,
        "proves_improvement": False,
        "gradient_sha256": hashes["gradient"],
        "source_sha256": hashes["source"],
        "bands_sha256": hashes["bands"],
        "baseline_sha256": hashes["baseline"],
        "producer_sha256": hashes["sparse"],
        "postprocessor_sha256": hashes["postprocessor"],
        "dependency_sha256": {
            key: hashes[key] for key in ("band", "grouped", "integrator")
        },
        "k": 48,
        "compressed_dimension": 20,
        "basis_dimension": 272,
        "parameters": {key: str(value) for key, value in PARAMETERS.items()},
        "serialized_base_quotient_discovery_only": str(validated["quotient"]),
        "serialized_residual_pairing_discovery_only": str(pairing),
        "serialized_relative_signal_discovery_only": str(relative_signal),
        "minimum_relative_signal": str(minimum_relative_signal),
        "inference_limit": (
            "one action (A*theta,B*theta) does not determine either quadratic "
            "form away from theta; no finite-step quotient is inferred"),
    }
    if trial is None:
        result = {
            "status": "no-claim-band-gradient-postprocess",
            **common,
            "reason": "serialized residual signal is zero, nonpositive, or below gate",
            "next_required_step": "obtain a stronger independently checked action",
        }
    else:
        result = {
            "status": "rational-band-trial-needs-independent-reevaluation",
            **common,
            "basis": [[a, list(lam)] for a, lam in labels],
            "base_theta_rational": [str(x) for x in band_map.theta0_q],
            "direction_theta_rational": [str(x) for x in
                                         trial["direction_theta"]],
            "direction_rational_vector": [str(x) for x in
                                          trial["direction_vector"]],
            "trial_step": str(step),
            "trial_theta_rational": [str(x) for x in trial["trial_theta"]],
            "rational_vector": [str(x) for x in trial["trial_vector"]],
            "next_required_step": (
                "recompute I and 48J for rational_vector from the pinned support "
                "with an independent scalar exact or outward-interval evaluator"),
        }

    # Detect every mid-run mutation, including source/bands and the consumer.
    require(all(path.read_bytes() == raw[name] for name, path in paths.items()),
            "an input or dependency changed during postprocessing")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gradient", required=True)
    parser.add_argument("--gradient-sha256", required=True,
                        help="caller-supplied byte SHA of the completed gradient")
    parser.add_argument("--source", required=True)
    parser.add_argument("--bands", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--step", default="1/4096")
    parser.add_argument("--minimum-relative-signal", default="1e-60")
    args = parser.parse_args()
    try:
        step = Fraction(args.step)
        signal = Decimal(args.minimum_relative_signal)
        result = process(args.gradient, args.gradient_sha256, args.source,
                         args.bands, args.output, step, signal)
    except (ValidationError, OSError, ValueError, ArithmeticError) as exc:
        raise SystemExit(f"NO CLAIM: {exc}") from exc
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
