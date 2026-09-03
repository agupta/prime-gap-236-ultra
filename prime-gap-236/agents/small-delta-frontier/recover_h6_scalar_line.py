#!/usr/bin/env python3
"""Fail-closed algebraic consumer for the sparse H6 scalar line.

Modes:

* ``threshold`` consumes only a candidate I-stage and gives the exact endpoint
  quotient threshold equivalent to a line maximum above one.
* ``self`` consumes the direct 11-label H6 self-form result and reconstructs
  the complete quadratic pencil from the stored cross action.

Neither mode evaluates an integral.  Decimal producer values are manipulated
as their exact serialized rational numbers and remain discovery-only.
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


GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
PARAMETERS = {"alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
              "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
              "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, description):
    def pairs(items):
        answer = {}
        for key, value in items:
            require(type(key) is str and key not in answer,
                    f"{description}: duplicate/non-string key")
            answer[key] = value
        return answer

    def constant(value):
        raise ValueError(f"{description}: nonfinite {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def load_bound(path_text, expected_sha, description):
    require(type(expected_sha) is str and len(expected_sha) == 64 and
            all(x in "0123456789abcdef" for x in expected_sha),
            f"{description}: malformed expected SHA")
    path = Path(path_text).resolve()
    raw = path.read_bytes()
    require(digest(raw) == expected_sha, f"{description}: SHA mismatch")
    return path, raw, strict_json(raw, description)


def q(value, description):
    require(type(value) is str and value and value == value.strip(),
            f"{description}: rational string")
    try:
        return Fraction(value)
    except Exception as exc:
        raise ValueError(f"{description}: malformed rational") from exc


def decimal(value, digits=80):
    with localcontext() as context:
        context.prec = digits
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def decimal_value(value):
    """Convert a Fraction to the active Decimal context."""
    return Decimal(value.numerator) / Decimal(value.denominator)


def quadratic_roots_decimal(a, b, c, digits=100):
    """Stable Decimal roots of a*x^2+b*x+c, for discovery output only."""
    require(a != 0 or b != 0, "constant stationary polynomial")
    discriminant = b*b - 4*a*c
    require(discriminant >= 0, "quadratic has no real projective roots")
    with localcontext() as context:
        context.prec = digits + 20
        aa, bb, cc = map(decimal_value, (a, b, c))
        if aa == 0:
            roots = [-cc/bb]
        else:
            root_disc = decimal_value(discriminant).sqrt()
            if root_disc == 0:
                roots = [-bb/(2*aa)]
            else:
                # This form avoids cancellation at the very small stationary root.
                qvalue = -(bb + (root_disc if bb >= 0 else -root_disc))/2
                roots = [qvalue/aa, cc/qvalue]
        roots.sort()
        context.prec = digits
        return discriminant, [+(x) for x in roots]


def validate_parameters(value, description):
    require(type(value) is dict and set(value) == set(PARAMETERS) and
            all(q(value[key], f"{description}.{key}") == expected
                for key, expected in PARAMETERS.items()),
            f"{description}: C10 parameters")


def manifest_action(manifest):
    require(manifest.get("status") == "h6-sparse-scalar-line-package" and
            manifest.get("rigorous") is False and
            manifest.get("fresh_scalar_reevaluation_required") is True and
            manifest.get("finite_form_value_claimed") is False and
            manifest.get("k") == 48, "manifest status")
    validate_parameters(manifest.get("parameters"), "manifest parameters")
    provenance = manifest.get("provenance")
    require(type(provenance) is dict and
            provenance.get("grouped_self_form_evaluator_sha256") == GROUPED_SHA and
            provenance.get("exact_integrator_sha256") == INTEGRATOR_SHA,
            "manifest arithmetic provenance")
    action = manifest.get("base_action")
    require(type(action) is dict, "manifest base action")
    D0 = q(action.get("denominator_D0"), "D0")
    N0 = q(action.get("numerator_N0"), "N0")
    a01 = q(action.get("A_cross_a01"), "a01")
    b01 = q(action.get("B48_cross_b01"), "b01")
    R = q(action.get("ascent_residual_R"), "R")
    derivative = q(action.get("quotient_first_derivative"), "derivative")
    require(D0 > 0 and 0 < N0 < D0 and
            R == D0 * b01 - N0 * a01 > 0 and
            derivative == 2 * R / D0**2, "manifest line action identities")
    return D0, N0, a01, b01


def find_artifact(manifest, artifact_sha, kind):
    matches = [x for x in manifest.get("artifacts", [])
               if type(x) is dict and x.get("sha256") == artifact_sha and
               x.get("kind") == kind]
    require(len(matches) == 1, f"manifest binding for {kind}")
    return matches[0]


def validate_candidate(candidate, candidate_sha, manifest):
    find_artifact(manifest, candidate_sha, "h6-sparse-rational-band-trial")
    require(candidate.get("status") == "h6-sparse-rational-band-trial" and
            candidate.get("rigorous") is False and
            candidate.get("finite_form_value_claimed") is False and
            candidate.get("k") == 48 and candidate.get("basis_dimension") == 272 and
            len(candidate.get("basis", [])) == 272 and
            len(candidate.get("rational_vector", [])) == 272,
            "candidate status/dimension")
    validate_parameters(candidate.get("parameters"), "candidate parameters")
    trial = candidate.get("trial")
    require(type(trial) is dict and trial.get("finite_projective_pole") is False and
            trial.get("first_order_only") is True and
            trial.get("changed_expanded_coordinate_count") == 11,
            "candidate trial fields")
    tau = q(trial.get("exact_step_tau"), "candidate tau")
    require(tau in {Fraction(1, 20), Fraction(1, 10), Fraction(1, 5)} and
            q(trial.get("exact_max_expanded_relative_change"),
              "candidate max change") == tau, "candidate normalization")
    return tau


def validate_stage(stage, input_sha, expected_groups):
    require(stage.get("status") == "grouped-fixed-vector-I-stage" and
            stage.get("i_complete") is True and stage.get("rigorous") is False and
            stage.get("decimal_dps") == 100 and
            stage.get("input_sha256") == input_sha and
            stage.get("script_sha256") == GROUPED_SHA and
            stage.get("integrator_sha256") == INTEGRATOR_SHA and
            stage.get("i_orbit_groups") == expected_groups and
            stage.get("i_faces") == 312 and
            stage.get("denominator_positive") is True,
            "I-stage status/provenance/counts")
    validate_parameters(stage.get("parameters"), "stage parameters")
    D = q(stage.get("denominator"), "stage denominator")
    require(D > 0, "stage denominator sign")
    return D


def recover_A11(D0, a01, tau, Dtau):
    require(tau != 0, "zero endpoint step")
    return (Dtau - D0 - 2 * tau * a01) / tau**2


def endpoint_threshold(D0, N0, a01, b01, tau, Dtau):
    A11 = recover_A11(D0, a01, tau, Dtau)
    determinant = D0 * A11 - a01**2
    require(determinant > 0,
            "I-line is not proved positive definite by the endpoint stage")
    h0, h1 = N0 - D0, b01 - a01
    require(h0 < 0, "base quotient is not below one")
    threshold = 1 + (h0 + tau * h1)**2 / (h0 * Dtau)
    return A11, determinant, threshold


def validate_self_result(result, direction_sha):
    require(result.get("status") == "multiprecision-grouped-fixed-vector-discovery" and
            result.get("rigorous") is False and result.get("decimal_dps") == 100 and
            result.get("k") == 48 and result.get("basis_dimension") == 11 and
            result.get("workers") == 2 and result.get("input_sha256") == direction_sha and
            result.get("script_sha256") == GROUPED_SHA and
            result.get("integrator_sha256") == INTEGRATOR_SHA and
            result.get("i_orbit_groups") == 77 and result.get("i_faces") == 312 and
            result.get("marginal_components") == 23 and
            result.get("j_branch_integrals") == 1200 and
            result.get("denominator_positive") is True,
            "self result status/provenance/counts")
    validate_parameters(result.get("parameters"), "self result parameters")
    # Replay the producer's actual Decimal100 operation order.  Converting the
    # four independently rounded strings to Fraction and demanding algebraic
    # equality is wrong by a possible final Decimal ulp.  This gate remains
    # exact: each serialized Decimal must equal the result of the specified
    # operation under a fresh precision-100 context.
    texts = {}
    for key in ("denominator", "j_value", "numerator", "quotient", "margin"):
        value = result.get(key)
        require(type(value) is str and value and value == value.strip(),
                f"self result {key} string")
        try:
            texts[key] = Decimal(value)
        except Exception as exc:
            raise ValueError(f"self result {key} Decimal") from exc
        require(texts[key].is_finite(), f"self result {key} finite")
    with localcontext() as context:
        context.prec = 100
        expected_numerator = Decimal(48) * texts["j_value"]
        expected_quotient = texts["numerator"] / texts["denominator"]
        expected_margin = texts["numerator"] - texts["denominator"]
    require(texts["denominator"] > 0 and
            texts["numerator"] == expected_numerator and
            texts["quotient"] == expected_quotient and
            texts["margin"] == expected_margin,
            "self result Decimal100 identities/factor 48")
    A11 = q(result["denominator"], "A11")
    B11 = q(result["numerator"], "B11")
    return A11, B11


def line_reconstruction(D0, N0, a01, b01, A11, B11):
    determinant = D0 * A11 - a01**2
    require(determinant > 0, "reconstructed I line is not positive definite")
    c0 = D0 * b01 - N0 * a01
    c1 = D0 * B11 - N0 * A11
    c2 = B11 * a01 - A11 * b01
    h0, h1, h2 = N0 - D0, b01 - a01, B11 - A11
    threshold_curvature = h1**2 / h0
    crosses_one = h2 > threshold_curvature
    stationary_discriminant, stationary_roots = quadratic_roots_decimal(
        c2, c1, c0)

    # The extrema over the real projective line are the two generalized
    # eigenvalues of the exact 2x2 pencil B-lambda*A.  Recording the exact
    # polynomial avoids pretending that the displayed Decimal roots are exact.
    lambda2 = determinant
    lambda1 = -N0*A11 - D0*B11 + 2*a01*b01
    lambda0 = N0*B11 - b01**2
    lambda_discriminant, lambda_roots = quadratic_roots_decimal(
        lambda2, lambda1, lambda0)
    require(len(lambda_roots) == 2, "degenerate projective eigenvalues")
    projective_min, projective_max = lambda_roots
    with localcontext() as context:
        context.prec = 100
        infinity_q = decimal_value(B11) / decimal_value(A11)
        stationary_values = []
        for root in stationary_roots:
            denominator = (decimal_value(D0) + 2*root*decimal_value(a01) +
                           root*root*decimal_value(A11))
            numerator = (decimal_value(N0) + 2*root*decimal_value(b01) +
                         root*root*decimal_value(B11))
            stationary_values.append(+(numerator/denominator))
    trials = {}
    for name, tau in (("h6_5pct", Fraction(1, 20)),
                      ("h6_10pct", Fraction(1, 10)),
                      ("h6_20pct", Fraction(1, 5))):
        D = D0 + 2 * tau * a01 + tau**2 * A11
        N = N0 + 2 * tau * b01 + tau**2 * B11
        require(D > 0, f"{name}: denominator")
        trials[name] = {"tau": str(tau), "D": str(D), "N": str(N),
                        "q": str(N / D), "q_decimal": decimal(N / D)}
    return {
        "A11": str(A11), "B11": str(B11),
        "I_line_determinant": str(determinant),
        "stationary_polynomial_coefficients":
            {"c0": str(c0), "c1": str(c1), "c2": str(c2)},
        "stationary_polynomial_discriminant": str(stationary_discriminant),
        "stationary_roots_decimal100": [str(x) for x in stationary_roots],
        "stationary_quotients_decimal100": [str(x) for x in stationary_values],
        "projective_generalized_eigen_polynomial": {
            "lambda2": str(lambda2), "lambda1": str(lambda1),
            "lambda0": str(lambda0),
            "discriminant": str(lambda_discriminant),
        },
        "projective_minimum_decimal100": str(projective_min),
        "projective_maximum_decimal100": str(projective_max),
        "projective_infinity_quotient_decimal100": str(+infinity_q),
        "one_crossing_curvature_threshold": str(threshold_curvature),
        "N_minus_D_quadratic_coefficient": str(h2),
        "line_max_strictly_above_one": crosses_one,
        "trial_values": trials,
        "line_formula": (
            "q(s)=(N0+2*s*b01+s^2*B11)/(D0+2*s*a01+s^2*A11)"
        ),
    }


def publish(path_text, output, trusted):
    if path_text is None:
        print(json.dumps(output, indent=2))
        return
    path = Path(path_text).resolve()
    require(path not in trusted, "output aliases trusted input")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(output, indent=2) + "\n").encode()
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
        fd_stat, path_stat = os.fstat(descriptor), os.stat(path, follow_symlinks=False)
        require((fd_stat.st_dev, fd_stat.st_ino) ==
                (path_stat.st_dev, path_stat.st_ino), "output inode changed")
        require(path.read_bytes() == payload, "output bytes changed")
        for trusted_path, raw in trusted.items():
            require(trusted_path.read_bytes() == raw, f"trusted byte changed {trusted_path}")
    except Exception as exc:
        rejection = (json.dumps({"status": "REJECTED", "error": str(exc)}) + "\n").encode()
        os.ftruncate(descriptor, 0)
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.write(descriptor, rejection)
        os.fsync(descriptor)
        raise
    finally:
        os.close(descriptor)
    print(json.dumps({"status": output["status"],
                      "output_sha256": digest(payload)}, indent=2))


def common_files(args):
    manifest_path, manifest_raw, manifest = load_bound(
        args.manifest, args.expect_manifest_sha256, "manifest")
    D0, N0, a01, b01 = manifest_action(manifest)
    return manifest_path, manifest_raw, manifest, D0, N0, a01, b01


def threshold_mode(args):
    mp, mr, manifest, D0, N0, a01, b01 = common_files(args)
    cp, cr, candidate = load_bound(
        args.candidate, args.expect_candidate_sha256, "candidate")
    tau = validate_candidate(candidate, args.expect_candidate_sha256, manifest)
    sp, sr, stage = load_bound(args.i_stage, args.expect_stage_sha256, "I stage")
    Dtau = validate_stage(stage, args.expect_candidate_sha256, 1575)
    A11, determinant, threshold = endpoint_threshold(
        D0, N0, a01, b01, tau, Dtau)
    output = {
        "status": "h6-endpoint-I-stage-threshold-discovery",
        "rigorous": False, "finite_endpoint_numerator_present": False,
        "candidate_sha256": args.expect_candidate_sha256,
        "i_stage_sha256": args.expect_stage_sha256, "tau": str(tau),
        "D_tau": str(Dtau), "recovered_A11": str(A11),
        "I_line_determinant": str(determinant),
        "strict_endpoint_q_threshold": str(threshold),
        "strict_endpoint_q_threshold_decimal": decimal(threshold),
        "criterion": (
            "with this positive-definite I line, max_s q(s)>1 iff "
            "the endpoint quotient q_tau is strictly greater than the threshold"
        ),
        "no_sign_without_endpoint_numerator": True,
    }
    publish(args.output, output, {mp: mr, cp: cr, sp: sr,
                                  Path(__file__).resolve(): Path(__file__).read_bytes()})


def self_mode(args):
    mp, mr, manifest, D0, N0, a01, b01 = common_files(args)
    dp, dr, direction = load_bound(
        args.direction, args.expect_direction_sha256, "direction")
    find_artifact(manifest, args.expect_direction_sha256,
                  "h6-sparse-self-form-direction")
    require(direction.get("status") == "h6-sparse-self-form-direction" and
            direction.get("basis_dimension") == 11 and
            len(direction.get("basis", [])) == 11 and
            len(direction.get("rational_vector", [])) == 11 and
            direction.get("k") == 48, "direction schema")
    rp, rr, result = load_bound(
        args.self_result, args.expect_self_result_sha256, "self result")
    A11, B11 = validate_self_result(result, args.expect_direction_sha256)
    output = {
        "status": "h6-complete-scalar-line-reconstruction-discovery",
        "rigorous": False, "self_result_sha256": args.expect_self_result_sha256,
        **line_reconstruction(D0, N0, a01, b01, A11, B11),
    }
    publish(args.output, output, {mp: mr, dp: dr, rp: rr,
                                  Path(__file__).resolve(): Path(__file__).read_bytes()})


def add_common(parser):
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expect-manifest-sha256", required=True)
    parser.add_argument("--output")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    threshold = sub.add_parser("threshold")
    add_common(threshold)
    threshold.add_argument("--candidate", required=True)
    threshold.add_argument("--expect-candidate-sha256", required=True)
    threshold.add_argument("--i-stage", required=True)
    threshold.add_argument("--expect-stage-sha256", required=True)
    threshold.set_defaults(function=threshold_mode)
    self_parser = sub.add_parser("self")
    add_common(self_parser)
    self_parser.add_argument("--direction", required=True)
    self_parser.add_argument("--expect-direction-sha256", required=True)
    self_parser.add_argument("--self-result", required=True)
    self_parser.add_argument("--expect-self-result-sha256", required=True)
    self_parser.set_defaults(function=self_mode)
    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
