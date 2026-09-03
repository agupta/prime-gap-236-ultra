#!/usr/bin/env python3
"""Recover the exact rational line quadratic after one fresh scalar trial.

All displayed coefficients are exact Fractions of the serialized MP100 base
action and fresh MP100 trial forms.  Consequently this is a discovery
postprocessor, not an exact integral or a theorem certificate.  The affine
coordinate is ``theta(s)=theta0+s*(theta_trial-theta0)``; H12 stays exactly 1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXACT = ROOT / "agents" / "exact-integrator"
sys.path.insert(0, str(HERE))

from audit_band_trial_result import (BANDS_SHA, BAND_OPERATOR_SHA,  # noqa: E402
                                     GROUPED_SHA, INTEGRATOR_SHA,
                                     MANIFEST_SHA, RECOVERY_SHA, SOURCE_SHA,
                                     TRIAL_PRODUCER_SHA, TRIAL_SHA, sha,
                                     validate_result, validate_trial)


AUDITOR_SHA = "5e704655aa6e2e91d76dab6463955f7d1bb3234cfc606af7012d55e9815f5059"
RECOVERY_SCRIPT_SHA = \
    "9342fa3f6d8157a4d9b8603a20bb0527b7f47087a5aa3c9d39aebef892f9fee5"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rebind_expected(expected_hashes):
    changed = [str(path) for path, expected in expected_hashes.items()
               if sha(path) != expected]
    require(not changed, "quadratic trusted byte changed: " + ", ".join(changed))


def exact_quadratic(theta0, a_theta, b_theta, denominator0, numerator0,
                    theta1, denominator1, numerator1):
    """Recover D(s),N(s) exactly from the base action and endpoint forms."""
    vectors = (theta0, a_theta, b_theta, theta1)
    require(len(theta0) == 20 and all(len(vector) == 20 for vector in vectors),
            "quadratic vector dimensions")
    require(denominator0 > 0 and denominator1 > 0,
            "quadratic endpoint denominators")
    displacement = [y - x for x, y in zip(theta0, theta1)]
    d0, n0 = denominator0, numerator0
    d1 = 2 * sum((h * a for h, a in zip(displacement, a_theta)), Fraction(0))
    n1 = 2 * sum((h * b for h, b in zip(displacement, b_theta)), Fraction(0))
    d2 = denominator1 - d0 - d1
    n2 = numerator1 - n0 - n1
    require(d0 + d1 + d2 == denominator1 and
            n0 + n1 + n2 == numerator1, "endpoint reconstruction")
    stationary = (
        n1 * d0 - n0 * d1,
        2 * (n2 * d0 - n0 * d2),
            n2 * d1 - n1 * d2,
    )
    require(d2 > 0 and 4 * d0 * d2 - d1 * d1 > 0,
            "line denominator is not positive definite")
    return {
        "displacement": displacement,
        "D": (d0, d1, d2), "N": (n0, n1, n2),
        "stationary": stationary,
    }


def evaluate_quadratic(coefficients, s):
    return coefficients[0] + s * coefficients[1] + s * s * coefficients[2]


def decimal_fraction(value, precision):
    with localcontext() as context:
        context.prec = precision
        return Decimal(value.numerator) / Decimal(value.denominator)


def stationary_roots(stationary, precision):
    """Return high-precision real roots of c0+c1*s+c2*s^2."""
    c0, c1, c2 = [decimal_fraction(value, precision) for value in stationary]
    with localcontext() as context:
        context.prec = precision
        if c2 == 0:
            if c1 == 0:
                return []
            return [+(-c0 / c1)]
        discriminant = c1 * c1 - Decimal(4) * c2 * c0
        require(discriminant >= 0, "negative stationary discriminant")
        root = discriminant.sqrt()
        return [+( (-c1 - root) / (Decimal(2) * c2)),
                +( (-c1 + root) / (Decimal(2) * c2))]


def rank_candidates(quadratic, roots, precision):
    """Rank finite stationary points and the projective point at infinity."""
    candidates = []
    for index, root in enumerate(roots):
        s = Fraction(str(root))
        denominator = evaluate_quadratic(quadratic["D"], s)
        numerator = evaluate_quadratic(quadratic["N"], s)
        if denominator > 0:
            candidates.append((numerator / denominator,
                               f"stationary_{index}", s, denominator, numerator))
    if quadratic["D"][2] > 0:
        candidates.append((quadratic["N"][2] / quadratic["D"][2],
                           "infinity", None, quadratic["D"][2],
                           quadratic["N"][2]))
    require(candidates, "no positive-denominator projective candidate")
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates


def atomic_write(path, text):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=target.parent,
                prefix=target.name + ".tmp.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def load_recovery(recovery_bytes):
    require(sha(recovery_bytes) == RECOVERY_SHA, "recovery artifact SHA")
    recovery = json.loads(recovery_bytes)
    require(recovery.get("status") ==
            "byte-pinned-recovered-degree-band-gradient-discovery" and
            recovery.get("rigorous") is False and recovery.get("complete") is True,
            "recovery status")
    require(recovery.get("recovery_script_sha256") == RECOVERY_SCRIPT_SHA,
            "recovery producer binding")
    theta = [Fraction(x) for x in recovery.get("theta", [])]
    a_theta = [Fraction(x) for x in
               recovery.get("a_theta_exact_fraction_half", [])]
    b_theta = [Fraction(x) for x in
               recovery.get("b_theta_exact_fraction_half", [])]
    grad_d = [Fraction(x) for x in recovery.get("grad_denominator", [])]
    grad_n = [Fraction(x) for x in recovery.get("grad_numerator", [])]
    require(len(theta) == len(a_theta) == len(b_theta) ==
            len(grad_d) == len(grad_n) == 20, "recovery vector dimensions")
    require(all(2 * value == gradient for value, gradient in zip(a_theta, grad_d)) and
            all(2 * value == gradient for value, gradient in zip(b_theta, grad_n)),
            "exact recovery halves")
    return recovery, theta, a_theta, b_theta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--bands", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--i-stage", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--precision", type=int, default=230)
    args = parser.parse_args()
    require(args.precision >= 200, "root precision below 200")
    dependency_paths = [HERE / "band_operator.py", HERE / "propose_band_trials.py",
                        EXACT / "grouped_fixed_vector.py",
                        EXACT / "src" / "exact_integrator.py"]
    paths = [Path(value).resolve() for value in
             (args.trial, args.manifest, args.source, args.bands, args.recovery,
              args.result, args.i_stage, __file__,
              HERE / "audit_band_trial_result.py",
              HERE / "recover_band_gradient.py", *dependency_paths)]
    require(len(set(paths)) == len(paths), "trusted quadratic inputs alias")
    require(Path(args.output).resolve() not in set(paths),
            "quadratic output aliases trusted input")
    require(not Path(args.output).exists(), "quadratic output already exists")
    require(sha(HERE / "audit_band_trial_result.py") == AUDITOR_SHA,
            "result auditor SHA")
    require(sha(HERE / "recover_band_gradient.py") == RECOVERY_SCRIPT_SHA,
            "recovery script SHA")

    trial_bytes, manifest_bytes = (Path(args.trial).read_bytes(),
                                   Path(args.manifest).read_bytes())
    recovery_bytes = Path(args.recovery).read_bytes()
    result_bytes, stage_bytes = (Path(args.result).read_bytes(),
                                 Path(args.i_stage).read_bytes())
    trial, band_map, theta1, _ = validate_trial(
        trial_bytes, manifest_bytes, args.source, args.bands)
    result, _, _ = validate_result(result_bytes, stage_bytes, args.trial)
    recovery, theta0, a_theta, b_theta = load_recovery(recovery_bytes)
    require(theta1[19] == theta0[19] == 1, "line does not preserve H12 gauge")
    quadratic = exact_quadratic(
        theta0, a_theta, b_theta,
        Fraction(recovery["denominator"]), Fraction(recovery["numerator"]),
        theta1, Fraction(result["denominator"]), Fraction(result["numerator"]))
    d0, d1, _ = quadratic["D"]
    n0, n1, _ = quadratic["N"]
    actual_first_derivative = (n1 * d0 - n0 * d1) / (d0 * d0)
    require(actual_first_derivative == Fraction(
        trial["trial"]["normalized_trial_first_derivative_exact"]),
        "trial first derivative does not match recovered line")
    euler_d = sum((x * y for x, y in zip(theta0, a_theta)), Fraction(0)) - \
        Fraction(recovery["denominator"])
    euler_n = sum((x * y for x, y in zip(theta0, b_theta)), Fraction(0)) - \
        Fraction(recovery["numerator"])
    require(abs(euler_d) <= abs(Fraction(recovery["denominator"])) / 10**50 and
            abs(euler_n) <= abs(Fraction(recovery["numerator"])) / 10**50,
            "base action Euler gate")
    roots = stationary_roots(quadratic["stationary"], args.precision)
    ranked = rank_candidates(quadratic, roots, args.precision)
    best_q, best_name, best_s, best_d, best_n = ranked[0]
    candidate = None
    if best_s is not None:
        theta_best = [x + best_s * h for x, h in
                      zip(theta0, quadratic["displacement"])]
        vector_best = list(band_map.expand(theta_best))
        require(theta_best[19] == 1, "recovered candidate H12 gauge")
        changes = [abs((x - y) / y) for x, y in zip(theta_best, theta0)]
        candidate = {
            "status": "rational-stationary-band-trial-awaiting-exact-reconstruction",
            "rigorous": False, "fresh_exact_reconstruction_required": True,
            "k": 48, "parameters": trial["parameters"],
            "basis": trial["basis"],
            "stationary_parameter_exact_decimal_rational": str(best_s),
            "compressed_theta": [str(x) for x in theta_best],
            "rational_vector": [str(x) for x in vector_best],
            "max_compressed_relative_change": str(max(changes)),
        }

    def describe(item):
        quotient, name, s, denominator, numerator = item
        return {
            "name": name, "s": None if s is None else str(s),
            "denominator_exact": str(denominator),
            "numerator_exact": str(numerator),
            "quotient_exact": str(quotient),
            "quotient_decimal": str(decimal_fraction(quotient, 80)),
        }

    result_out = {
        "status": "exact-rational-quadratic-from-mp100-discovery-forms",
        "rigorous": False,
        "fresh_exact_reconstruction_required": True,
        "coordinate": "theta(s)=theta0+s*(theta_trial-theta0)",
        "trial_sha256": TRIAL_SHA,
        "scalar_result_sha256": sha(result_bytes),
        "i_stage_sha256": sha(stage_bytes),
        "recovery_artifact_sha256": RECOVERY_SHA,
        "postprocessor_sha256": sha(__file__),
        "auditor_sha256": AUDITOR_SHA,
        "quadratic": {
            "D_coefficients": [str(x) for x in quadratic["D"]],
            "N_coefficients": [str(x) for x in quadratic["N"]],
            "stationary_polynomial_coefficients":
                [str(x) for x in quadratic["stationary"]],
            "base_action_euler_D_error": str(
                euler_d),
            "base_action_euler_N_error": str(
                euler_n),
            "trial_displacement_first_derivative_exact": str(
                actual_first_derivative),
        },
        "ranked_projective_candidates": [describe(item) for item in ranked],
        "selected_candidate": candidate,
        "warning": "All exact fractions are exact only relative to serialized Decimal discovery actions/forms; they are not exact capped integrals.",
    }
    expected_hashes = {
        Path(args.trial).resolve(): TRIAL_SHA,
        Path(args.manifest).resolve(): MANIFEST_SHA,
        Path(args.source).resolve(): SOURCE_SHA,
        Path(args.bands).resolve(): BANDS_SHA,
        Path(args.recovery).resolve(): RECOVERY_SHA,
        Path(args.result).resolve(): sha(result_bytes),
        Path(args.i_stage).resolve(): sha(stage_bytes),
        Path(__file__).resolve(): result_out["postprocessor_sha256"],
        (HERE / "audit_band_trial_result.py").resolve(): AUDITOR_SHA,
        (HERE / "recover_band_gradient.py").resolve(): RECOVERY_SCRIPT_SHA,
        (HERE / "band_operator.py").resolve(): BAND_OPERATOR_SHA,
        (HERE / "propose_band_trials.py").resolve(): TRIAL_PRODUCER_SHA,
        (EXACT / "grouped_fixed_vector.py").resolve(): GROUPED_SHA,
        (EXACT / "src" / "exact_integrator.py").resolve(): INTEGRATOR_SHA,
    }
    # Re-run the semantic validators on fresh bytes so their entire dependency
    # closure (source, bands, BandMap, producer, evaluator, integrator) is also
    # rebound at the final write boundary.
    validate_trial(Path(args.trial).read_bytes(), Path(args.manifest).read_bytes(),
                   args.source, args.bands)
    validate_result(Path(args.result).read_bytes(), Path(args.i_stage).read_bytes(),
                    args.trial)
    load_recovery(Path(args.recovery).read_bytes())
    rebind_expected(expected_hashes)
    atomic_write(args.output, json.dumps(result_out, indent=2) + "\n")
    print(json.dumps({
        "status": result_out["status"], "rigorous": False,
        "output_sha256": sha(args.output), "selected": best_name,
        "predicted_quotient_decimal": str(decimal_fraction(best_q, 80)),
        "fresh_exact_reconstruction_required": True,
    }, indent=2))


if __name__ == "__main__":
    main()
