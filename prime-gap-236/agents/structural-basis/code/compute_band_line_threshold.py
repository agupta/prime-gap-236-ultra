#!/usr/bin/env python3
"""Exact discovery gate for the near20 line after its MP100 I stage.

No trial numerator is used.  The output states the exact endpoint quotient
threshold above which the reconstructed two-dimensional line has a point with
quotient greater than one, conditional on the serialized Decimal action and
fresh endpoint forms belonging to one quadratic pair.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from audit_band_trial_result import (BANDS_SHA, BAND_OPERATOR_SHA,  # noqa: E402
                                     GROUPED_SHA, INTEGRATOR_SHA, MANIFEST_SHA,
                                     PARAMETERS, SOURCE_SHA, STAGE_KEYS,
                                     TRIAL_PRODUCER_SHA, TRIAL_SHA, sha,
                                     validate_parameters, validate_trial)
from recover_band_quadratic import (AUDITOR_SHA, RECOVERY_SHA,  # noqa: E402
                                    load_recovery)


STAGE_SHA = "db9caca00ecd24ab36bdfcaeb5839af69d0a668d3c546e62af498052a983c5bb"
POSTPROCESSOR_SHA = \
    "bbbce83623550d8d92467827e9c8535e172ed05dc237c93141737e04ae9e3468"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def threshold_from_endpoint_denominator(d0, n0, d1, n1, endpoint_d):
    """Return endpoint q threshold and associated exact margin data."""
    base_margin = n0 - d0
    linear_margin = n1 - d1
    require(d0 > 0 and endpoint_d > 0 and base_margin < 0,
            "threshold endpoint signs")
    quadratic_margin_threshold = linear_margin * linear_margin / (4 * base_margin)
    endpoint_margin_threshold = (base_margin + linear_margin +
                                 quadratic_margin_threshold)
    endpoint_numerator_threshold = endpoint_d + endpoint_margin_threshold
    quotient_threshold = endpoint_numerator_threshold / endpoint_d
    return {
        "base_margin": base_margin,
        "linear_margin": linear_margin,
        "quadratic_margin_threshold": quadratic_margin_threshold,
        "endpoint_margin_threshold": endpoint_margin_threshold,
        "endpoint_numerator_threshold": endpoint_numerator_threshold,
        "endpoint_quotient_threshold": quotient_threshold,
    }


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--bands", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--i-stage", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = HERE.parents[2]
    exact = root / "agents" / "exact-integrator"
    closure = [HERE / "band_operator.py", HERE / "propose_band_trials.py",
               exact / "grouped_fixed_vector.py",
               exact / "src" / "exact_integrator.py"]
    trusted = [Path(value).resolve() for value in
               (args.trial, args.manifest, args.source, args.bands,
                args.recovery, args.i_stage, __file__,
                HERE / "audit_band_trial_result.py",
                HERE / "recover_band_quadratic.py", *closure)]
    require(len(set(trusted)) == len(trusted), "threshold trusted inputs alias")
    require(Path(args.output).resolve() not in set(trusted) and
            not Path(args.output).exists(), "threshold output path")
    require(sha(HERE / "audit_band_trial_result.py") == AUDITOR_SHA and
            sha(HERE / "recover_band_quadratic.py") == POSTPROCESSOR_SHA,
            "threshold dependency SHAs")
    trial_bytes = Path(args.trial).read_bytes()
    manifest_bytes = Path(args.manifest).read_bytes()
    recovery_bytes = Path(args.recovery).read_bytes()
    stage_bytes = Path(args.i_stage).read_bytes()
    trial, _, theta1, _ = validate_trial(
        trial_bytes, manifest_bytes, args.source, args.bands)
    recovery, theta0, a_theta, b_theta = load_recovery(recovery_bytes)
    require(sha(stage_bytes) == STAGE_SHA, "I-stage SHA")
    stage = json.loads(stage_bytes)
    require(set(stage) == STAGE_KEYS, "I-stage schema")
    require(stage.get("status") == "grouped-fixed-vector-I-stage" and
            stage.get("i_complete") is True and stage.get("rigorous") is False and
            stage.get("decimal_dps") == 100 and
            stage.get("input_sha256") == TRIAL_SHA and
            stage.get("script_sha256") == GROUPED_SHA and
            stage.get("integrator_sha256") == INTEGRATOR_SHA,
            "I-stage provenance/status")
    validate_parameters(stage.get("parameters"))
    require(stage.get("parameters") == PARAMETERS and
            stage.get("i_orbit_groups") == 1575 and stage.get("i_faces") == 312 and
            stage.get("denominator_positive") is True,
            "I-stage parameters/counts")
    displacement = [y - x for x, y in zip(theta0, theta1)]
    d0, n0 = Fraction(recovery["denominator"]), Fraction(recovery["numerator"])
    endpoint_d = Fraction(stage["denominator"])
    d1 = 2 * sum((x * y for x, y in zip(displacement, a_theta)), Fraction(0))
    n1 = 2 * sum((x * y for x, y in zip(displacement, b_theta)), Fraction(0))
    d2 = endpoint_d - d0 - d1
    gram4 = 4 * d0 * d2 - d1 * d1
    require(d2 > 0 and gram4 > 0, "positive-definite line denominator")
    threshold = threshold_from_endpoint_denominator(
        d0, n0, d1, n1, endpoint_d)

    def dec(value, precision=80):
        with localcontext() as context:
            context.prec = precision
            return str(Decimal(value.numerator) / Decimal(value.denominator))

    result = {
        "status": "near20-line-threshold-from-I-stage-discovery",
        "rigorous": False,
        "trial_numerator_used": False,
        "no_projected_sign_inferred": True,
        "conditional_statement": (
            "If the fresh endpoint numerator and the serialized base action/forms "
            "are treated as one quadratic pair, projected max > 1 iff endpoint "
            "quotient is strictly greater than endpoint_quotient_threshold."
        ),
        "trial_sha256": TRIAL_SHA, "recovery_sha256": RECOVERY_SHA,
        "i_stage_sha256": STAGE_SHA,
        "script_sha256": sha(__file__),
        "endpoint_denominator_exact": str(endpoint_d),
        "endpoint_denominator_decimal": dec(endpoint_d),
        "D_linear_coefficient_exact": str(d1),
        "D_quadratic_coefficient_exact": str(d2),
        "D_gram_determinant_times_four_exact": str(gram4),
        **{key + "_exact": str(value) for key, value in threshold.items()},
        "endpoint_quotient_threshold_decimal": dec(
            threshold["endpoint_quotient_threshold"]),
    }
    expected = {
        Path(args.trial).resolve(): TRIAL_SHA,
        Path(args.manifest).resolve(): MANIFEST_SHA,
        Path(args.source).resolve(): SOURCE_SHA,
        Path(args.bands).resolve(): BANDS_SHA,
        Path(args.recovery).resolve(): RECOVERY_SHA,
        Path(args.i_stage).resolve(): STAGE_SHA,
        Path(__file__).resolve(): result["script_sha256"],
        (HERE / "audit_band_trial_result.py").resolve(): AUDITOR_SHA,
        (HERE / "recover_band_quadratic.py").resolve(): POSTPROCESSOR_SHA,
        (HERE / "band_operator.py").resolve(): BAND_OPERATOR_SHA,
        (HERE / "propose_band_trials.py").resolve(): TRIAL_PRODUCER_SHA,
        (exact / "grouped_fixed_vector.py").resolve(): GROUPED_SHA,
        (exact / "src" / "exact_integrator.py").resolve(): INTEGRATOR_SHA,
    }
    validate_trial(Path(args.trial).read_bytes(), Path(args.manifest).read_bytes(),
                   args.source, args.bands)
    load_recovery(Path(args.recovery).read_bytes())
    require(all(sha(path) == digest for path, digest in expected.items()),
            "threshold trusted byte changed before output")
    atomic_write(args.output, json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "status": result["status"],
        "output_sha256": sha(args.output),
        "endpoint_quotient_threshold_decimal":
            result["endpoint_quotient_threshold_decimal"],
        "trial_numerator_used": False,
    }, indent=2))


if __name__ == "__main__":
    main()
