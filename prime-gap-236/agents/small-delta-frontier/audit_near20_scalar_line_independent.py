#!/usr/bin/env python3
"""Independent audit/reconstruction of the C10 D12 near-20 band trial.

This program performs no integration.  It treats every serialized MP100
number as the exact rational represented by its decimal string, checks the
fresh scalar result and I-stage identities, and reconstructs the quadratic
Rayleigh line from the independently recovered base action.  Its output is
discovery data, never a rigorous integral or sieve certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


TRIAL_SHA = "88c1d26f6cf46bbdd12dc000eb802cac8efe91be0ad003d6827f2ccdc6c0ff47"
RECOVERY_SHA = "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
SOURCE_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
BANDS_SHA = "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9"
RAW_SHA = "0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d"

PARAMETERS = {
    "alpha": Fraction(79247, 300000),
    "delta": Fraction(1, 100),
    "eta": Fraction(76247, 300000),
    "beta1": Fraction(3, 20),
    "beta2": Fraction(3, 20),
    "beta3plus": Fraction(97, 625),
}
COUNTS = {
    "i_orbit_groups": 1575,
    "i_faces": 312,
    "marginal_components": 695,
    "j_branch_integrals": 1200,
}
RESULT_KEYS = {
    "status", "rigorous", "decimal_dps", "input_json", "k", "parameters",
    "basis_dimension", "workers", "i_orbit_groups", "i_faces",
    "marginal_components", "j_branch_integrals", "input_sha256", "i_seconds",
    "j_seconds", "total_seconds", "peak_rss_kib", "child_peak_rss_kib",
    "peak_rss_note", "denominator_positive", "margin_positive", "denominator",
    "j_value", "numerator", "quotient", "quotient_decimal_display", "margin",
    "script_sha256", "integrator_sha256",
}
STAGE_KEYS = {
    "status", "i_complete", "rigorous", "decimal_dps", "input_json",
    "input_sha256", "script_sha256", "integrator_sha256", "parameters",
    "i_orbit_groups", "i_faces", "i_seconds", "denominator_positive",
    "denominator", "peak_rss_kib", "child_peak_rss_kib",
}
TRIAL_KEYS = {
    "status", "rigorous", "fresh_scalar_reevaluation_required",
    "finite_form_value_claimed", "k", "parameters", "basis",
    "compressed_theta", "rational_vector", "trial", "provenance",
}
RECOVERY_KEYS = {
    "status", "complete", "rigorous", "decimal_dps", "parameters",
    "source_json", "source_sha256", "bands_json", "bands_sha256",
    "raw_json", "raw_sha256", "recovery_script_sha256",
    "recovery_statement", "recorded_half_mismatch_evidence",
    "validation_gates", "theta", "grad_denominator", "grad_numerator",
    "a_theta_exact_fraction_half", "b_theta_exact_fraction_half",
    "denominator", "numerator", "no_projected_trial_emitted",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def strict_json(data: bytes, label: str):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"{label}: duplicate JSON key {key!r}")
            out[key] = value
        return out

    def bad_constant(value):
        raise ValueError(f"{label}: nonstandard JSON number {value}")

    try:
        return json.loads(data, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label}: malformed JSON") from exc


def exact_int(value, label: str) -> int:
    require(type(value) is int, f"{label}: expected integer")
    return value


def exact_bool(value, label: str) -> bool:
    require(type(value) is bool, f"{label}: expected Boolean")
    return value


def fraction(value, label: str) -> Fraction:
    require(type(value) is str and value.strip() == value and value,
            f"{label}: expected canonical nonempty string")
    try:
        answer = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{label}: invalid exact rational") from exc
    return answer


def decimal(value, label: str) -> Decimal:
    require(type(value) is str and value.strip() == value and value,
            f"{label}: expected decimal string")
    try:
        answer = Decimal(value)
    except Exception as exc:
        raise ValueError(f"{label}: invalid Decimal") from exc
    require(answer.is_finite(), f"{label}: non-finite Decimal")
    return answer


def check_parameters(mapping, label: str) -> None:
    require(type(mapping) is dict and set(mapping) == set(PARAMETERS),
            f"{label}: parameter key set")
    for key, expected in PARAMETERS.items():
        require(fraction(mapping[key], f"{label}.{key}") == expected,
                f"{label}: parameter {key}")


def dot(left, right) -> Fraction:
    require(len(left) == len(right), "dot dimension")
    return sum((x * y for x, y in zip(left, right)), Fraction(0))


def decimal_of(value: Fraction, precision: int) -> Decimal:
    with localcontext() as context:
        context.prec = precision
        return +(Decimal(value.numerator) / Decimal(value.denominator))


def eval_form(coefficients, x: Fraction) -> Fraction:
    a0, a1, a2 = coefficients
    return a0 + 2 * a1 * x + a2 * x * x


def stationary_roots(coefficients, precision: int):
    c0, c1, c2 = coefficients
    with localcontext() as context:
        context.prec = precision
        d0, d1, d2 = (decimal_of(value, precision) for value in (c0, c1, c2))
        if d2 == 0:
            if d1 == 0:
                return []
            return [+(-d0 / d1)]
        discriminant = d1 * d1 - Decimal(4) * d2 * d0
        require(discriminant >= 0, "stationary polynomial has no real roots")
        square_root = discriminant.sqrt()
        return [ +((-d1 - square_root) / (Decimal(2) * d2)),
                 +((-d1 + square_root) / (Decimal(2) * d2)) ]


def publish_new(path: Path, text: str, closure: dict[Path, bytes]) -> str:
    """Publish through a newly reserved inode and rebind the full closure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    identity = os.fstat(descriptor)
    expected_inode = (identity.st_dev, identity.st_ino)
    encoded = text.encode("utf-8")
    expected_sha = sha_bytes(encoded)
    try:
        offset = 0
        while offset < len(encoded):
            written = os.write(descriptor, encoded[offset:])
            if written <= 0:
                raise OSError("short independent-audit output write")
            offset += written
        os.fsync(descriptor)
        for trusted_path, expected_bytes in closure.items():
            require(trusted_path.read_bytes() == expected_bytes,
                    f"trusted byte changed during publication: {trusted_path}")
        observed = os.stat(path, follow_symlinks=False)
        require((observed.st_dev, observed.st_ino) == expected_inode,
                "independent-audit output inode replaced")
        os.lseek(descriptor, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        while True:
            block = os.read(descriptor, 1 << 20)
            if not block:
                break
            digest.update(block)
        require(digest.hexdigest() == expected_sha and
                sha_path(path) == expected_sha,
                "independent-audit output bytes changed")
        observed = os.stat(path, follow_symlinks=False)
        require((observed.st_dev, observed.st_ino) == expected_inode,
                "independent-audit output inode replaced at final gate")
        return expected_sha
    except Exception:
        # Rewrite only the held inode.  If a foreign pathname replaced it,
        # the foreign inode is untouched and this rejection vanishes on close.
        rejection = (b'{"status":"REJECTED-independent-near20-audit",'
                     b'"rigorous":false}\n')
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            offset = 0
            while offset < len(rejection):
                written = os.write(descriptor, rejection[offset:])
                if written <= 0:
                    break
                offset += written
            os.fsync(descriptor)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--i-stage", required=True)
    parser.add_argument("--grouped-source", required=True)
    parser.add_argument("--integrator-source", required=True)
    parser.add_argument("--expect-result-sha256", required=True)
    parser.add_argument("--expect-stage-sha256", required=True)
    parser.add_argument("--root-precision", type=int, default=230)
    parser.add_argument("--output")
    args = parser.parse_args()

    require(type(args.root_precision) is int and 180 <= args.root_precision <= 1000,
            "root precision outside [180,1000]")
    paths = {name: Path(value).resolve() for name, value in {
        "trial": args.trial, "recovery": args.recovery,
        "result": args.result, "stage": args.i_stage,
        "grouped": args.grouped_source, "integrator": args.integrator_source,
        "self": __file__,
    }.items()}
    require(len(set(paths.values())) == len(paths), "trusted path alias")
    output_path = Path(args.output).resolve() if args.output else None
    if output_path is not None:
        require(output_path not in set(paths.values()), "output aliases trusted input")
        require(not output_path.exists(), "output already exists")

    start_bytes = {name: path.read_bytes() for name, path in paths.items()}
    expected_hashes = {
        "trial": TRIAL_SHA, "recovery": RECOVERY_SHA,
        "result": args.expect_result_sha256,
        "stage": args.expect_stage_sha256,
        "grouped": GROUPED_SHA, "integrator": INTEGRATOR_SHA,
        "self": sha_bytes(start_bytes["self"]),
    }
    require(all(len(value) == 64 and
                all(character in "0123456789abcdef" for character in value)
                for value in expected_hashes.values()), "malformed expected SHA256")
    for name, expected in expected_hashes.items():
        require(sha_bytes(start_bytes[name]) == expected, f"{name} byte SHA")

    trial = strict_json(start_bytes["trial"], "trial")
    recovery = strict_json(start_bytes["recovery"], "recovery")
    result = strict_json(start_bytes["result"], "result")
    stage = strict_json(start_bytes["stage"], "stage")

    require(type(trial) is dict and set(trial) == TRIAL_KEYS, "trial exact schema")
    require(trial["status"] == "recovered-action-rational-band-trial" and
            exact_bool(trial["rigorous"], "trial.rigorous") is False and
            exact_bool(trial["fresh_scalar_reevaluation_required"],
                       "trial.fresh_scalar_reevaluation_required") is True and
            exact_bool(trial["finite_form_value_claimed"],
                       "trial.finite_form_value_claimed") is False,
            "trial discovery status")
    require(exact_int(trial["k"], "trial.k") == 48, "trial k=48")
    check_parameters(trial["parameters"], "trial")
    require(type(trial["basis"]) is list and len(trial["basis"]) == 272,
            "trial ordered basis length")
    theta_y = [fraction(value, f"trial.compressed_theta[{index}]")
               for index, value in enumerate(trial["compressed_theta"])]
    vector_y = [fraction(value, f"trial.rational_vector[{index}]")
                for index, value in enumerate(trial["rational_vector"])]
    require(len(theta_y) == 20 and len(vector_y) == 272,
            "trial coefficient lengths")
    detail = trial["trial"]
    require(type(detail) is dict and detail.get("name") == "h12_near_20pct" and
            detail.get("projective_pole_side") == "near" and
            detail.get("H12_coordinate") == "1", "near20 trial identity")
    t = fraction(detail["exact_step_t"], "trial.exact_step_t")
    scale = fraction(detail["exact_H12_gauge_scale"],
                     "trial.exact_H12_gauge_scale")
    require(t != 0 and scale != 0 and theta_y[19] == 1,
            "nonzero line/gauge and H12 endpoint")
    provenance = trial["provenance"]
    require(provenance.get("recovery_artifact_sha256") == RECOVERY_SHA and
            provenance.get("source_sha256") == SOURCE_SHA and
            provenance.get("bands_sha256") == BANDS_SHA and
            provenance.get("raw_gradient_sha256") == RAW_SHA and
            provenance.get("no_finite_form_evaluation") is True,
            "trial provenance")

    require(type(recovery) is dict and set(recovery) == RECOVERY_KEYS,
            "recovery exact schema")
    require(recovery["status"] ==
            "byte-pinned-recovered-degree-band-gradient-discovery" and
            exact_bool(recovery["complete"], "recovery.complete") is True and
            exact_bool(recovery["rigorous"], "recovery.rigorous") is False and
            exact_int(recovery["decimal_dps"], "recovery.decimal_dps") == 100,
            "recovery status")
    check_parameters(recovery["parameters"], "recovery")
    require(recovery["source_sha256"] == SOURCE_SHA and
            recovery["bands_sha256"] == BANDS_SHA and
            recovery["raw_sha256"] == RAW_SHA and
            recovery["no_projected_trial_emitted"] is True,
            "recovery provenance/flags")
    theta = [fraction(value, f"recovery.theta[{index}]")
             for index, value in enumerate(recovery["theta"])]
    grad_d = [fraction(value, f"recovery.grad_denominator[{index}]")
              for index, value in enumerate(recovery["grad_denominator"])]
    grad_n = [fraction(value, f"recovery.grad_numerator[{index}]")
              for index, value in enumerate(recovery["grad_numerator"])]
    a_theta = [fraction(value, f"recovery.a_theta[{index}]")
               for index, value in enumerate(recovery["a_theta_exact_fraction_half"])]
    b_theta = [fraction(value, f"recovery.b_theta[{index}]")
               for index, value in enumerate(recovery["b_theta_exact_fraction_half"])]
    require(all(len(values) == 20 for values in
                (theta, grad_d, grad_n, a_theta, b_theta)),
            "recovery vector dimensions")
    require(all(2 * a == g for a, g in zip(a_theta, grad_d)) and
            all(2 * b == g for b, g in zip(b_theta, grad_n)),
            "recovered actions are exact serialized gradient halves")
    require(theta[19] == 1, "base H12 gauge")

    require(type(result) is dict and set(result) == RESULT_KEYS,
            "result exact schema")
    require(result["status"] == "multiprecision-grouped-fixed-vector-discovery" and
            exact_bool(result["rigorous"], "result.rigorous") is False and
            exact_int(result["decimal_dps"], "result.decimal_dps") == 100,
            "result discovery status")
    require(exact_int(result["k"], "result.k") == 48 and
            exact_int(result["basis_dimension"], "result.basis_dimension") == 272 and
            exact_int(result["workers"], "result.workers") == 2,
            "result k/dimension/workers")
    check_parameters(result["parameters"], "result")
    require(result["input_sha256"] == TRIAL_SHA and
            result["script_sha256"] == GROUPED_SHA and
            result["integrator_sha256"] == INTEGRATOR_SHA,
            "result provenance")
    require(Path(result["input_json"]).resolve() == paths["trial"],
            "result input path")
    for key, expected in COUNTS.items():
        require(exact_int(result[key], f"result.{key}") == expected,
                f"result count {key}")

    require(type(stage) is dict and set(stage) == STAGE_KEYS,
            "I-stage exact schema")
    require(stage["status"] == "grouped-fixed-vector-I-stage" and
            exact_bool(stage["i_complete"], "stage.i_complete") is True and
            exact_bool(stage["rigorous"], "stage.rigorous") is False and
            exact_int(stage["decimal_dps"], "stage.decimal_dps") == 100,
            "I-stage status")
    check_parameters(stage["parameters"], "stage")
    require(stage["input_sha256"] == TRIAL_SHA and
            stage["script_sha256"] == GROUPED_SHA and
            stage["integrator_sha256"] == INTEGRATOR_SHA and
            Path(stage["input_json"]).resolve() == paths["trial"],
            "I-stage provenance")
    require(exact_int(stage["i_orbit_groups"], "stage.i_orbit_groups") == 1575 and
            exact_int(stage["i_faces"], "stage.i_faces") == 312,
            "I-stage counts")

    with localcontext() as context:
        context.prec = 100
        denominator = decimal(result["denominator"], "result.denominator")
        j_value = decimal(result["j_value"], "result.j_value")
        numerator = decimal(result["numerator"], "result.numerator")
        quotient = decimal(result["quotient"], "result.quotient")
        margin = decimal(result["margin"], "result.margin")
        require(denominator > 0 and
                exact_bool(result["denominator_positive"],
                           "result.denominator_positive") is True,
                "result positive denominator")
        require(numerator == Decimal(48) * j_value, "Decimal100 numerator=48J")
        require(quotient == numerator / denominator,
                "Decimal100 quotient identity")
        require(margin == numerator - denominator,
                "Decimal100 margin identity")
        require(exact_bool(result["margin_positive"],
                           "result.margin_positive") is (margin > 0),
                "result margin sign flag")
        display = float(result["quotient_decimal_display"])
        require(math.isfinite(display) and
                abs(display - float(quotient)) <= 4 * math.ulp(float(quotient)),
                "quotient display")
        stage_denominator = decimal(stage["denominator"], "stage.denominator")
        require(stage_denominator == denominator and
                exact_bool(stage["denominator_positive"],
                           "stage.denominator_positive") is True,
                "I-stage/result denominator identity")

    for mapping, prefix in ((result, "result"), (stage, "stage")):
        for key in ("peak_rss_kib", "child_peak_rss_kib"):
            require(exact_int(mapping[key], f"{prefix}.{key}") > 0,
                    f"{prefix} resource metadata")
    for key in ("i_seconds", "j_seconds", "total_seconds"):
        require(type(result[key]) in (int, float) and type(result[key]) is not bool and
                math.isfinite(float(result[key])) and float(result[key]) > 0,
                f"result {key}")
    require(type(stage["i_seconds"]) in (int, float) and
            type(stage["i_seconds"]) is not bool and
            float(stage["i_seconds"]) == float(result["i_seconds"]),
            "I-stage/runtime identity")
    require(abs(float(result["total_seconds"]) -
                (float(result["i_seconds"]) + float(result["j_seconds"]))) <=
            1e-12 * max(float(result["total_seconds"]), 1.0),
            "total runtime identity")

    # Reconstruct the raw projective direction from y=s*(theta+t*d).
    direction = [(y / scale - x) / t for x, y in zip(theta, theta_y)]
    require(all(y == scale * (x + t * d)
                for x, d, y in zip(theta, direction, theta_y)),
            "exact projective endpoint identity")

    a00 = fraction(recovery["denominator"], "recovery.denominator")
    b00 = fraction(recovery["numerator"], "recovery.numerator")
    ay = Fraction(result["denominator"])
    by = Fraction(result["numerator"])
    require(a00 > 0 and ay > 0, "positive serialized endpoint denominators")
    a01 = dot(direction, a_theta)
    b01 = dot(direction, b_theta)
    a11 = (ay / (scale * scale) - a00 - 2 * t * a01) / (t * t)
    b11 = (by / (scale * scale) - b00 - 2 * t * b01) / (t * t)
    d_coefficients = (a00, a01, a11)
    n_coefficients = (b00, b01, b11)
    require(scale * scale * eval_form(d_coefficients, t) == ay and
            scale * scale * eval_form(n_coefficients, t) == by,
            "exact endpoint form reconstruction")

    euler_d = dot(theta, a_theta) - a00
    euler_n = dot(theta, b_theta) - b00
    require(abs(euler_d) <= abs(a00) / 10**50 and
            abs(euler_n) <= abs(b00) / 10**50,
            "serialized base-action Euler residual")
    positive_definite = (a11 > 0 and a00 * a11 - a01 * a01 > 0)
    require(positive_definite, "reconstructed D line is not positive definite")

    stationary = (
        b01 * a00 - a01 * b00,
        b11 * a00 - a11 * b00,
        b11 * a01 - a11 * b01,
    )
    roots = stationary_roots(stationary, args.root_precision)
    root_records = []
    for root in roots:
        u = Fraction(str(root))
        d_at_root = eval_form(d_coefficients, u)
        n_at_root = eval_form(n_coefficients, u)
        require(d_at_root > 0, "stationary root has nonpositive D")
        root_records.append({
            "u_decimal": str(root),
            "u_over_trial_t_decimal": str(decimal_of(u / t, 100)),
            "D_decimal": str(decimal_of(d_at_root, 100)),
            "N_decimal": str(decimal_of(n_at_root, 100)),
            "quotient_decimal": str(decimal_of(n_at_root / d_at_root, 100)),
        })

    # The stored derivative is for h=y-theta and is reconstructed directly
    # from the serialized action.  The separately rounded base form and
    # action obey Euler only to about 60 relative digits, not identically, so
    # scale*t times the raw derivative is recorded as a consistency proxy and
    # must not be required to equal the stored derivative exactly.
    raw_q_derivative = 2 * stationary[0] / (a00 * a00)
    displacement = [y - x for x, y in zip(theta, theta_y)]
    normalized_q_derivative = 2 * (
        dot(displacement, b_theta) * a00 -
        dot(displacement, a_theta) * b00) / (a00 * a00)
    recorded_q_derivative = fraction(
        detail["normalized_trial_first_derivative_exact"],
        "trial.normalized_trial_first_derivative_exact")
    require(normalized_q_derivative == recorded_q_derivative,
        "trial first derivative/action identity")
    raw_projective_derivative_proxy = scale * t * raw_q_derivative
    homogeneity_derivative_defect = (
        raw_projective_derivative_proxy - normalized_q_derivative)
    require(abs(homogeneity_derivative_defect) <=
            max(abs(normalized_q_derivative), Fraction(1)) / 10**50,
            "serialized action/base homogeneity defect")

    direction_serial = json.dumps([str(value) for value in direction],
                                  separators=(",", ":")).encode()
    output = {
        "status": "INDEPENDENT NEAR20 SCALAR/LINE AUDIT PASS",
        "rigorous": False,
        "claim_scope": "Decimal100 discovery output only; no exact integral or sieve claim",
        "bindings": {
            "trial_sha256": TRIAL_SHA,
            "recovery_sha256": RECOVERY_SHA,
            "result_sha256": expected_hashes["result"],
            "i_stage_sha256": expected_hashes["stage"],
            "grouped_source_sha256": GROUPED_SHA,
            "integrator_source_sha256": INTEGRATOR_SHA,
            "independent_auditor_sha256": expected_hashes["self"],
        },
        "counts": COUNTS | {"basis_dimension": 272, "compressed_dimension": 20},
        "decimal100_forms": {
            "denominator": str(denominator), "j_value": str(j_value),
            "numerator_48J": str(numerator), "quotient": str(quotient),
            "margin": str(margin),
        },
        "projective_identity": {
            "formula": "y=scale*(theta+t*direction)",
            "t": str(t), "scale": str(scale),
            "direction_sha256": sha_bytes(direction_serial),
            "direction": [str(value) for value in direction],
        },
        "raw_line_forms": {
            "D_formula": "A00+2*A01*u+A11*u^2",
            "N_formula": "B00+2*B01*u+B11*u^2",
            "A00_A01_A11": [str(value) for value in d_coefficients],
            "B00_B01_B11": [str(value) for value in n_coefficients],
            "D_positive_definite": positive_definite,
            "D_determinant": str(a00 * a11 - a01 * a01),
            "base_euler_D_error": str(euler_d),
            "base_euler_N_error": str(euler_n),
        },
        "stationary": {
            "polynomial_formula": "c0+c1*u+c2*u^2",
            "coefficients": [str(value) for value in stationary],
            "finite_real_roots_with_D_positive": root_records,
            "projective_infinity_quotient_decimal":
                str(decimal_of(b11 / a11, 100)),
        },
        "trial_first_derivative_exact": str(normalized_q_derivative),
        "raw_projective_derivative_proxy":
            str(raw_projective_derivative_proxy),
        "serialized_homogeneity_derivative_defect":
            str(homogeneity_derivative_defect),
    }

    # End gates bind every trusted byte after all arithmetic and before write.
    for name, path in paths.items():
        require(path.read_bytes() == start_bytes[name], f"{name} changed during audit")
    serialized = json.dumps(output, indent=2) + "\n"
    if output_path is not None:
        closure = {path: start_bytes[name] for name, path in paths.items()}
        output_sha = publish_new(output_path, serialized, closure)
        print(json.dumps({
            "status": output["status"], "rigorous": False,
            "output_sha256": output_sha,
            "result_sha256": expected_hashes["result"],
            "quotient": str(quotient), "margin": str(margin),
            "root_count": len(root_records),
        }, indent=2))
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
