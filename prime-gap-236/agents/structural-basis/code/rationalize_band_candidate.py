#!/usr/bin/env python3
"""Emit a compact exact 272-label approximation to a band candidate.

The Rayleigh quotient is scale invariant.  We first expand the exact finite
Decimal compressed candidate, divide all coefficients by their maximum
absolute value, and round them to one common decimal grid.  Removing the
resulting integer vector's gcd changes only its irrelevant overall scale.  The
result is a portable fixed-polynomial input; it must be scalar-MP checked after
rationalization before use in a richer basis or an exact certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from fractions import Fraction
from math import gcd
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from band_operator import BandMap  # noqa: E402


PINNED_BAND_OPERATOR_SHA = \
    "e4fbf7a97d061d362c32b54bf0d49a89c4195b965e96d7ab89a2581bc907c073"
PINNED_SOURCE_SHA = \
    "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
PINNED_BANDS_SHA = \
    "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9"
PINNED_GROUPED_SHA = \
    "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
PINNED_INTEGRATOR_SHA = \
    "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
PINNED_RESULT_AUDITOR_SHA = \
    "5e704655aa6e2e91d76dab6463955f7d1bb3234cfc606af7012d55e9815f5059"
PINNED_QUADRATIC_POSTPROCESSOR_SHA = \
    "bbbce83623550d8d92467827e9c8535e172ed05dc237c93141737e04ae9e3468"
C10_PARAMETERS = {
    "alpha": "79247/300000", "delta": "1/100",
    "eta": "76247/300000", "beta1": "3/20",
    "beta2": "3/20", "beta3plus": "97/625",
}
DIRECT_KEYS = {
    "status", "rigorous", "fresh_scalar_reevaluation_required",
    "finite_form_value_claimed", "k", "parameters", "basis",
    "compressed_theta", "rational_vector", "trial", "provenance",
}
DIRECT_TRIAL_KEYS = {
    "name", "projective_pole_side", "exact_step_t", "exact_H12_gauge_scale",
    "normalization", "H12_coordinate",
    "raw_path_max_relative_coefficient_change",
    "raw_path_median_relative_coefficient_change",
    "normalized_max_relative_coefficient_change",
    "normalized_median_relative_coefficient_change",
    "normalized_max_relative_change_decimal",
    "normalized_median_relative_change_decimal",
    "compressed_max_relative_coordinate_change",
    "compressed_median_relative_coordinate_change",
    "compressed_max_relative_change_decimal",
    "compressed_median_relative_change_decimal",
    "normalized_trial_first_derivative_exact",
    "normalized_trial_first_derivative_decimal",
    "scaled_raw_path_first_derivative_exact",
    "scaled_raw_path_first_derivative_decimal", "note",
}
DIRECT_PROVENANCE_KEYS = {
    "raw_gradient_sha256", "recovery_artifact_sha256",
    "recovery_script_sha256", "trial_script_sha256",
    "line_search_dependency_sha256", "source_sha256", "bands_sha256",
    "no_finite_form_evaluation",
}
QUADRATIC_KEYS = {
    "status", "rigorous", "fresh_exact_reconstruction_required", "coordinate",
    "trial_sha256", "scalar_result_sha256", "i_stage_sha256",
    "recovery_artifact_sha256", "postprocessor_sha256", "auditor_sha256",
    "quadratic", "ranked_projective_candidates", "selected_candidate", "warning",
}
QUADRATIC_DATA_KEYS = {
    "D_coefficients", "N_coefficients", "stationary_polynomial_coefficients",
    "base_action_euler_D_error", "base_action_euler_N_error",
    "trial_displacement_first_derivative_exact",
}
RANKED_KEYS = {
    "name", "s", "denominator_exact", "numerator_exact", "quotient_exact",
    "quotient_decimal",
}
SELECTED_KEYS = {
    "status", "rigorous", "fresh_exact_reconstruction_required", "k",
    "parameters", "basis", "stationary_parameter_exact_decimal_rational",
    "compressed_theta", "rational_vector", "max_compressed_relative_change",
}


def file_sha(data_or_path):
    if isinstance(data_or_path, (bytes, bytearray)):
        data = bytes(data_or_path)
    else:
        data = Path(data_or_path).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json_loads(data):
    """Reject duplicate keys, nonfinite constants, floats, and oversized JSON."""
    if isinstance(data, str):
        encoded = data.encode("utf-8")
    else:
        encoded = bytes(data)
    if len(encoded) > 20_000_000:
        raise ValueError("candidate JSON exceeds 20 MB")

    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_float(text):
        raise ValueError(f"JSON float is not permitted: {text}")

    def reject_constant(text):
        raise ValueError(f"nonfinite JSON constant: {text}")

    return json.loads(encoded.decode("utf-8"), object_pairs_hook=pairs_hook,
                      parse_float=reject_float, parse_constant=reject_constant)


def exact_schema(mapping, expected, name):
    if not isinstance(mapping, dict) or set(mapping) != expected:
        raise ValueError(f"{name} exact schema")


def canonical_rational_vector(values, length, name):
    if not isinstance(values, list) or len(values) != length:
        raise ValueError(f"{name} length")
    result = []
    for index, text in enumerate(values):
        if type(text) is not str or not 1 <= len(text) <= 10_000:
            raise ValueError(f"{name}[{index}] bounded rational string")
        try:
            value = Fraction(text)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"{name}[{index}] rational parse") from exc
        if str(value) != text:
            raise ValueError(f"{name}[{index}] noncanonical rational")
        result.append(value)
    return result


def candidate_payload(candidate):
    """Select the exact compressed/expanded polynomial from known producers."""
    status = candidate.get("status")
    if status == "recovered-action-rational-band-trial":
        exact_schema(candidate, DIRECT_KEYS, "direct candidate")
        exact_schema(candidate.get("trial"), DIRECT_TRIAL_KEYS,
                     "direct trial diagnostics")
        exact_schema(candidate.get("provenance"), DIRECT_PROVENANCE_KEYS,
                     "direct trial provenance")
        payload = candidate
        theta_text = candidate.get("compressed_theta", [])
        if (candidate.get("rigorous") is not False or
                candidate.get("fresh_scalar_reevaluation_required") is not True or
                candidate.get("finite_form_value_claimed") is not False):
            raise ValueError("band trial discovery flags")
        if (set(candidate.get("parameters", {})) != set(C10_PARAMETERS) or
                any(Fraction(candidate["parameters"][key]) != Fraction(value)
                    for key, value in C10_PARAMETERS.items())):
            raise ValueError("band trial C10 parameters")
    elif status == "exact-rational-quadratic-from-mp100-discovery-forms":
        exact_schema(candidate, QUADRATIC_KEYS, "quadratic candidate")
        exact_schema(candidate.get("quadratic"), QUADRATIC_DATA_KEYS,
                     "quadratic data")
        ranked = candidate.get("ranked_projective_candidates")
        if not isinstance(ranked, list) or not ranked:
            raise ValueError("quadratic ranked candidates")
        for item in ranked:
            exact_schema(item, RANKED_KEYS, "ranked candidate")
        if (candidate.get("rigorous") is not False or
                candidate.get("fresh_exact_reconstruction_required") is not True or
                candidate.get("postprocessor_sha256") !=
                PINNED_QUADRATIC_POSTPROCESSOR_SHA or
                candidate.get("auditor_sha256") != PINNED_RESULT_AUDITOR_SHA):
            raise ValueError("quadratic candidate provenance/status")
        payload = candidate.get("selected_candidate")
        exact_schema(payload, SELECTED_KEYS, "quadratic selected candidate")
        if (not isinstance(payload, dict) or
                payload.get("status") !=
                "rational-stationary-band-trial-awaiting-exact-reconstruction" or
                payload.get("rigorous") is not False or
                payload.get("fresh_exact_reconstruction_required") is not True):
            raise ValueError("missing quadratic selected candidate")
        if (set(payload.get("parameters", {})) != set(C10_PARAMETERS) or
                any(Fraction(payload["parameters"][key]) != Fraction(value)
                    for key, value in C10_PARAMETERS.items())):
            raise ValueError("quadratic candidate C10 parameters")
        theta_text = payload.get("compressed_theta", [])
    else:
        raise ValueError("wrong candidate status")
    return payload, theta_text


def validate_and_expand(candidate, band_map, source):
    """Bind the compressed candidate to its explicit ordered polynomial."""
    payload, theta_text = candidate_payload(candidate)
    if payload.get("k") != 48 or source.get("k") != 48:
        raise ValueError("candidate/source k mismatch")
    if (source.get("degree") != 12 or source.get("basis_dimension") != 272 or
            band_map.dimension != 20 or len(band_map.labels) != 272):
        raise ValueError("pinned degree-band dimensions mismatch")
    expected_basis = [[a, list(lam)] for a, lam in band_map.labels]
    if source.get("basis") != expected_basis or payload.get("basis") != expected_basis:
        raise ValueError("candidate/source ordered basis mismatch")
    if len(theta_text) != 20:
        raise ValueError("candidate compressed dimension mismatch")
    theta = canonical_rational_vector(theta_text, 20, "compressed theta")
    expanded = [band_map.weight_q[i] * theta[band_map.owner[i]]
                for i in range(len(band_map.labels))]
    serialized = canonical_rational_vector(
        payload.get("rational_vector", []), 272, "expanded vector")
    if serialized != expanded:
        raise ValueError("candidate explicit expansion mismatch")
    return expanded


def require_distinct_output(output, trusted):
    resolved = [Path(path).resolve() for path in trusted]
    if len(set(resolved)) != len(resolved):
        raise ValueError("trusted rationalizer inputs alias")
    target = Path(output).resolve()
    if target in set(resolved):
        raise ValueError("rationalizer output aliases trusted input")
    if Path(output).exists():
        raise ValueError("rationalizer output already exists")


def rebind_expected(expected_hashes):
    changed = [str(path) for path, expected in expected_hashes.items()
               if file_sha(path) != expected]
    if changed:
        raise ValueError("trusted rationalizer byte changed: " + ", ".join(changed))


def reserve_output(path):
    """Atomically reserve a previously absent destination with O_EXCL."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(descriptor, b"reserved by rationalize_band_candidate\n")
    os.fsync(descriptor)
    stat = os.fstat(descriptor)
    return descriptor, (stat.st_dev, stat.st_ino)


def reject_owned_descriptor(descriptor):
    """Fail closed through the held inode without touching any pathname."""
    rejection = (b'{"status":"REJECTED-rationalizer-publication",'
                 b'"rigorous":false}\n')
    os.lseek(descriptor, 0, os.SEEK_SET)
    os.ftruncate(descriptor, 0)
    offset = 0
    while offset < len(rejection):
        written = os.write(descriptor, rejection[offset:])
        if written <= 0:
            raise OSError("short rationalizer rejection write")
        offset += written
    os.fsync(descriptor)


def publish_reserved(path, text, descriptor, identity, expected_hashes,
                     after_publish=None):
    """Publish through the owned O_EXCL inode, then audit everything again.

    Writing through the reservation descriptor cannot overwrite a path which a
    concurrent process created.  A crash can expose partial JSON, but the
    strict parser rejects it; this is preferable to a check/rename overwrite
    race.  This function always consumes and closes ``descriptor``.
    """
    target = Path(path)
    published = False
    expected_output_sha = file_sha(text.encode("utf-8"))

    def target_is_owned():
        try:
            observed = os.stat(target, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return (observed.st_dev, observed.st_ino) == identity

    try:
        rebind_expected(expected_hashes)
        encoded = text.encode("utf-8")
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.ftruncate(descriptor, 0)
        offset = 0
        while offset < len(encoded):
            written = os.write(descriptor, encoded[offset:])
            if written <= 0:
                raise OSError("short rationalizer output write")
            offset += written
        os.fsync(descriptor)
        published = True
        if after_publish is not None:
            after_publish(target)
        if not target_is_owned():
            raise ValueError("rationalizer output reservation was replaced")
        rebind_expected(expected_hashes)
        os.lseek(descriptor, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        while True:
            block = os.read(descriptor, 1 << 20)
            if not block:
                break
            digest.update(block)
        if (digest.hexdigest() != expected_output_sha or
                file_sha(target) != expected_output_sha or
                not target_is_owned()):
            raise ValueError("published rationalizer output bytes changed")
        return expected_output_sha
    except Exception:
        # Never rename or unlink a path after a separate inode check.  If a
        # foreign path replaced ours, this fd names only the now-unlinked owned
        # inode and the rejection vanishes on close; the foreign path is left
        # untouched.  If our inode is still linked, it becomes explicit
        # fail-closed rejection JSON.
        try:
            reject_owned_descriptor(descriptor)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)


def common_grid_quantize(normalized, denominator_digits):
    """Round to one decimal grid and remove the irrelevant common scale.

    Independent ``limit_denominator`` calls create 272 unrelated denominators,
    whose least common multiple makes later exact quadratic reconstruction
    needlessly expensive.  A common grid instead emits a primitive integer
    vector representing precisely the same rounded projective point.
    """
    limit = 10 ** denominator_digits
    grid_numerators = [round(x * limit) for x in normalized]
    common = 0
    for value in grid_numerators:
        common = gcd(common, abs(value))
    if common == 0:
        raise ValueError("quantization annihilated the polynomial")
    primitive = [value // common for value in grid_numerators]
    represented = [Fraction(value, limit) for value in grid_numerators]
    errors = [abs(x - y) for x, y in zip(normalized, represented)]
    return primitive, limit, common, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--bands", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--candidate-sha256", required=True)
    ap.add_argument("--denominator-digits", type=int, default=40)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    if not 10 <= args.denominator_digits <= 100:
        ap.error("denominator digits must lie in [10,100]")
    if (len(args.candidate_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in args.candidate_sha256)):
        ap.error("candidate SHA must be 64 lowercase hexadecimal characters")
    candidate_bytes = Path(args.candidate).read_bytes()
    if file_sha(candidate_bytes) != args.candidate_sha256:
        raise SystemExit("candidate byte pin mismatch")
    try:
        candidate = strict_json_loads(candidate_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"strict candidate JSON rejected: {exc}") from exc
    source_bytes, bands_bytes = (Path(args.source).read_bytes(),
                                 Path(args.bands).read_bytes())
    band_operator_sha = file_sha(Path(HERE) / "band_operator.py")
    if band_operator_sha != PINNED_BAND_OPERATOR_SHA:
        raise SystemExit("band expansion dependency SHA mismatch")
    if file_sha(source_bytes) != PINNED_SOURCE_SHA or \
            file_sha(bands_bytes) != PINNED_BANDS_SHA:
        raise SystemExit("source/bands byte pin mismatch")
    band_map = BandMap.from_source_and_bands(args.source, args.bands)
    # The source bytes are fixed by an external SHA and contain historical
    # floating discovery metadata; only the caller-selected candidate needs
    # the strict no-float parser.
    source = json.loads(source_bytes)
    try:
        expanded = validate_and_expand(candidate, band_map, source)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise SystemExit(f"candidate validation failed: {exc}") from exc
    scale = max(abs(x) for x in expanded)
    if not scale:
        raise SystemExit("zero polynomial")
    normalized = [x / scale for x in expanded]
    compact, limit, common, errors = common_grid_quantize(
        normalized, args.denominator_digits)
    script_sha = file_sha(__file__)
    exact_agent = Path(HERE).parents[1] / "exact-integrator"
    dependencies = [Path(HERE) / "band_operator.py", Path(__file__),
                    exact_agent / "grouped_fixed_vector.py",
                    exact_agent / "src" / "exact_integrator.py"]
    if (file_sha(dependencies[-2]) != PINNED_GROUPED_SHA or
            file_sha(dependencies[-1]) != PINNED_INTEGRATOR_SHA):
        raise SystemExit("transitive BandMap dependency SHA mismatch")
    if candidate.get("status") == \
            "exact-rational-quadratic-from-mp100-discovery-forms":
        dependencies.extend([Path(HERE) / "audit_band_trial_result.py",
                             Path(HERE) / "recover_band_quadratic.py"])
        if (file_sha(dependencies[-2]) != PINNED_RESULT_AUDITOR_SHA or
                file_sha(dependencies[-1]) != PINNED_QUADRATIC_POSTPROCESSOR_SHA):
            raise SystemExit("quadratic candidate dependency SHA mismatch")
    trusted = [Path(args.source), Path(args.bands), Path(args.candidate),
               *dependencies]
    try:
        require_distinct_output(args.output, trusted)
    except ValueError as exc:
        raise SystemExit(f"rationalizer output validation failed: {exc}") from exc
    result = {
        "status": "compact-rationalized-degree-band-candidate",
        "rigorous": False,
        "fresh_scalar_mp_recheck_required": True,
        "k": 48,
        "degree": 12,
        "basis_dimension": 272,
        "parameters": C10_PARAMETERS,
        "basis": source["basis"],
        "rational_vector": [str(x) for x in compact],
        "rationalization": {
            "rigorous_identity_to_candidate": False,
            "requires_scalar_mp_recheck": True,
            "method": "common-decimal-grid-then-primitive-integer-vector",
            "candidate_json": args.candidate,
            "candidate_sha256": args.candidate_sha256,
            "rationalizer_sha256": script_sha,
            "band_operator_sha256": band_operator_sha,
            "source_sha256": band_map.source_sha256,
            "bands_sha256": band_map.bands_sha256,
            "grouped_dependency_sha256": PINNED_GROUPED_SHA,
            "integrator_dependency_sha256": PINNED_INTEGRATOR_SHA,
            "normalization_scale_divisor": str(scale),
            "quantization_grid_denominator": str(limit),
            "integer_common_divisor_removed": str(common),
            "maximum_absolute_primitive_integer": str(max(abs(x) for x in compact)),
            "maximum_absolute_normalized_coefficient_error": str(max(errors)),
            "l1_absolute_normalized_coefficient_error": str(
                sum(errors, Fraction(0))),
            "uniform_error_bound": f"1/{2 * limit}",
            "zero_coefficients": sum(x == 0 for x in compact),
        },
    }
    expected_hashes = {
        Path(args.source).resolve(): PINNED_SOURCE_SHA,
        Path(args.bands).resolve(): PINNED_BANDS_SHA,
        Path(args.candidate).resolve(): args.candidate_sha256,
        (Path(HERE) / "band_operator.py").resolve(): PINNED_BAND_OPERATOR_SHA,
        Path(__file__).resolve(): script_sha,
        (exact_agent / "grouped_fixed_vector.py").resolve(): PINNED_GROUPED_SHA,
        (exact_agent / "src" / "exact_integrator.py").resolve():
            PINNED_INTEGRATOR_SHA,
    }
    if candidate.get("status") == \
            "exact-rational-quadratic-from-mp100-discovery-forms":
        expected_hashes[(Path(HERE) / "audit_band_trial_result.py").resolve()] = \
            PINNED_RESULT_AUDITOR_SHA
        expected_hashes[(Path(HERE) / "recover_band_quadratic.py").resolve()] = \
            PINNED_QUADRATIC_POSTPROCESSOR_SHA
    rendered = json.dumps(result, indent=2) + "\n"
    try:
        rebind_expected(expected_hashes)
        reservation = reserve_output(args.output)
        output_sha = publish_reserved(
            args.output, rendered, reservation[0], reservation[1],
            expected_hashes)
    except (FileExistsError, ValueError) as exc:
        raise SystemExit(f"rationalizer publication failed: {exc}") from exc
    summary = dict(result["rationalization"])
    summary["published_output_sha256"] = output_sha
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
