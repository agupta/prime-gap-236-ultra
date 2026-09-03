#!/usr/bin/env python3
"""Fail-closed audit of the fresh C10 D12 near-20 scalar traversal.

This checker never integrates and never upgrades Decimal discovery data to a
certificate.  It byte-pins the selected rational input and both arithmetic
dependencies, reconstructs its 20-to-272 band expansion, and (when supplied)
recomputes every scalar identity in the grouped MP100 result and I checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXACT = ROOT / "agents" / "exact-integrator"
sys.path.insert(0, str(HERE))

from band_operator import BandMap  # noqa: E402


TRIAL_SHA = "88c1d26f6cf46bbdd12dc000eb802cac8efe91be0ad003d6827f2ccdc6c0ff47"
MANIFEST_SHA = "c16b960004b42e0c66fd2255fd6002eed1cbcf049167fe88f1f18c124e7686e5"
SOURCE_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
BANDS_SHA = "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9"
BAND_OPERATOR_SHA = "e4fbf7a97d061d362c32b54bf0d49a89c4195b965e96d7ab89a2581bc907c073"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
TRIAL_PRODUCER_SHA = "5e999a3727b9922aac986629e6b022b08614cfcd5ab38203b5f1a8e9e806a7bc"
RECOVERY_SHA = "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43"
RAW_SHA = "0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d"
PARAMETERS = {
    "alpha": "79247/300000", "delta": "1/100",
    "eta": "76247/300000", "beta1": "3/20",
    "beta2": "3/20", "beta3plus": "97/625",
}
COUNTS = {
    "i_orbit_groups": 1575, "i_faces": 312,
    "marginal_components": 695, "j_branch_integrals": 1200,
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


def sha(data_or_path):
    if isinstance(data_or_path, (bytes, bytearray)):
        data = bytes(data_or_path)
    else:
        data = Path(data_or_path).read_bytes()
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_parameters(observed):
    require(set(observed or {}) == set(PARAMETERS), "parameter key set")
    require(all(Fraction(observed[key]) == Fraction(value)
                for key, value in PARAMETERS.items()), "C10 parameters")


def validate_trial(trial_bytes, manifest_bytes, source_path, bands_path):
    """Reconstruct and return the selected exact rational band input."""
    require(sha(trial_bytes) == TRIAL_SHA, "near20 trial SHA")
    require(sha(manifest_bytes) == MANIFEST_SHA, "trial manifest SHA")
    require(sha(source_path) == SOURCE_SHA, "source SHA")
    require(sha(bands_path) == BANDS_SHA, "bands SHA")
    require(sha(HERE / "band_operator.py") == BAND_OPERATOR_SHA,
            "BandMap dependency SHA")
    require(sha(HERE / "propose_band_trials.py") == TRIAL_PRODUCER_SHA,
            "trial producer SHA")
    require(sha(EXACT / "grouped_fixed_vector.py") == GROUPED_SHA,
            "grouped evaluator SHA")
    require(sha(EXACT / "src" / "exact_integrator.py") == INTEGRATOR_SHA,
            "integrator SHA")
    trial = json.loads(trial_bytes)
    manifest = json.loads(manifest_bytes)
    require(trial.get("status") == "recovered-action-rational-band-trial",
            "trial status")
    require(trial.get("rigorous") is False and
            trial.get("fresh_scalar_reevaluation_required") is True and
            trial.get("finite_form_value_claimed") is False,
            "trial discovery flags")
    require(trial.get("k") == 48, "trial k")
    validate_parameters(trial.get("parameters"))
    detail = trial.get("trial", {})
    require(detail.get("name") == "h12_near_20pct" and
            detail.get("projective_pole_side") == "near" and
            Fraction(detail.get("normalized_max_relative_coefficient_change")) ==
            Fraction(1, 5), "selected trial identity")
    provenance = trial.get("provenance", {})
    expected_provenance = {
        "raw_gradient_sha256": RAW_SHA,
        "recovery_artifact_sha256": RECOVERY_SHA,
        "recovery_script_sha256":
            "9342fa3f6d8157a4d9b8603a20bb0527b7f47087a5aa3c9d39aebef892f9fee5",
        "trial_script_sha256": TRIAL_PRODUCER_SHA,
        "line_search_dependency_sha256":
            "f5acf5f3b5a0c87f65175b724acafaf805dee40f43039e5b9300d2b0b6758f09",
        "source_sha256": SOURCE_SHA, "bands_sha256": BANDS_SHA,
        "no_finite_form_evaluation": True,
    }
    require(provenance == expected_provenance, "trial provenance")
    require(manifest.get("status") ==
            "three-rational-band-trials-awaiting-scalar-selection" and
            manifest.get("rigorous") is False and
            manifest.get("fresh_scalar_reevaluation_required") is True and
            manifest.get("trial_count") == 3, "manifest status")
    entries = {item.get("name"): item for item in manifest.get("trials", [])}
    require(set(entries) == {"h12_near_5pct", "h12_near_10pct",
                             "h12_near_20pct"}, "manifest trial names")
    require(entries["h12_near_20pct"].get("sha256") == TRIAL_SHA,
            "manifest near20 binding")

    band_map = BandMap.from_source_and_bands(source_path, bands_path)
    require(band_map.dimension == 20 and len(band_map.labels) == 272,
            "band dimensions")
    basis = [[a, list(lam)] for a, lam in band_map.labels]
    require(trial.get("basis") == basis, "ordered trial basis")
    theta = [Fraction(x) for x in trial.get("compressed_theta", [])]
    vector = [Fraction(x) for x in trial.get("rational_vector", [])]
    require(len(theta) == 20 and len(vector) == 272, "trial vector lengths")
    require(theta[19] == 1, "H12 gauge")
    require(vector == list(band_map.expand(theta)), "exact band expansion")
    forbidden = {"denominator", "numerator", "quotient", "j_value", "margin"}

    def keys(value):
        if isinstance(value, dict):
            for key, item in value.items():
                yield key
                yield from keys(item)
        elif isinstance(value, list):
            for item in value:
                yield from keys(item)

    require(not (forbidden & set(keys(trial))), "trial contains finite form fields")
    return trial, band_map, theta, vector


def parse_finite(mapping, names):
    values = {name: Decimal(mapping[name]) for name in names}
    require(all(value.is_finite() for value in values.values()),
            "non-finite scalar result")
    return values


def validate_result(result_bytes, stage_bytes, trial_path):
    """Recompute all MP100 result/checkpoint scalar identities."""
    result = json.loads(result_bytes)
    stage = json.loads(stage_bytes)
    require(set(result) == RESULT_KEYS, "result exact schema")
    require(set(stage) == STAGE_KEYS, "I-stage exact schema")
    require(result.get("status") ==
            "multiprecision-grouped-fixed-vector-discovery" and
            result.get("rigorous") is False and result.get("decimal_dps") == 100,
            "result arithmetic/status")
    require(result.get("input_sha256") == TRIAL_SHA and result.get("k") == 48 and
            result.get("basis_dimension") == 272 and result.get("workers") == 2,
            "result input/dimensions")
    validate_parameters(result.get("parameters"))
    require(result.get("script_sha256") == GROUPED_SHA and
            result.get("integrator_sha256") == INTEGRATOR_SHA,
            "result dependency SHAs")
    require(all(result.get(key) == value for key, value in COUNTS.items()),
            "result traversal counts")
    require(Path(result.get("input_json", "")).resolve() == Path(trial_path).resolve(),
            "result input path")

    with localcontext() as context:
        context.prec = 100
        values = parse_finite(result, (
            "denominator", "j_value", "numerator", "quotient", "margin"))
        denominator = values["denominator"]
        j_value = values["j_value"]
        numerator = values["numerator"]
        quotient = values["quotient"]
        margin = values["margin"]
        require(denominator > 0 and result.get("denominator_positive") is True,
                "positive denominator")
        require(numerator == Decimal(48) * j_value, "N=48J")
        require(quotient == numerator / denominator, "quotient recomputation")
        require(margin == numerator - denominator, "margin recomputation")
        require(result.get("margin_positive") is (margin > 0),
                "margin sign flag")
        display = float(result.get("quotient_decimal_display"))
        require(math.isfinite(display) and
                abs(display - float(quotient)) <= 4 * math.ulp(float(quotient)),
                "quotient display")

    require(stage.get("status") == "grouped-fixed-vector-I-stage" and
            stage.get("i_complete") is True and stage.get("rigorous") is False and
            stage.get("decimal_dps") == 100, "I-stage arithmetic/status")
    require(stage.get("input_sha256") == TRIAL_SHA and
            stage.get("script_sha256") == GROUPED_SHA and
            stage.get("integrator_sha256") == INTEGRATOR_SHA,
            "I-stage provenance")
    require(Path(stage.get("input_json", "")).resolve() == Path(trial_path).resolve(),
            "I-stage input path")
    validate_parameters(stage.get("parameters"))
    require(stage.get("i_orbit_groups") == 1575 and stage.get("i_faces") == 312,
            "I-stage counts")
    require(Decimal(stage.get("denominator")) == denominator and
            stage.get("denominator_positive") is True,
            "I-stage denominator")
    i_seconds = float(result.get("i_seconds", 0))
    j_seconds = float(result.get("j_seconds", 0))
    total_seconds = float(result.get("total_seconds", 0))
    require(float(stage.get("i_seconds", 0)) > 0 and
            i_seconds == float(stage["i_seconds"]) and j_seconds > 0 and
            total_seconds > 0 and
            abs(total_seconds - (i_seconds + j_seconds)) <=
            1e-12 * max(total_seconds, 1),
            "runtime metadata")
    require(all(int(mapping.get(key, 0)) > 0
                for mapping in (stage, result)
                for key in ("peak_rss_kib", "child_peak_rss_kib")),
            "resource metadata")
    return result, stage, values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--bands", required=True)
    parser.add_argument("--result")
    parser.add_argument("--i-stage")
    args = parser.parse_args()
    trial_bytes = Path(args.trial).read_bytes()
    manifest_bytes = Path(args.manifest).read_bytes()
    validate_trial(trial_bytes, manifest_bytes, args.source, args.bands)
    output = {"status": "BAND TRIAL PREFLIGHT PASS", "trial_sha256": TRIAL_SHA,
              "finite_form_evaluated": False}
    if bool(args.result) != bool(args.i_stage):
        raise SystemExit("--result and --i-stage must be supplied together")
    if args.result:
        result_bytes = Path(args.result).read_bytes()
        stage_bytes = Path(args.i_stage).read_bytes()
        result, _, values = validate_result(result_bytes, stage_bytes, args.trial)
        # Rebind all current bytes after semantic validation.
        validate_trial(Path(args.trial).read_bytes(),
                       Path(args.manifest).read_bytes(), args.source, args.bands)
        require(sha(result_bytes) == sha(args.result) and
                sha(stage_bytes) == sha(args.i_stage),
                "result bytes changed during audit")
        output = {
            "status": "BAND TRIAL SCALAR RESULT AUDIT PASS",
            "rigorous": False, "trial_sha256": TRIAL_SHA,
            "result_sha256": sha(result_bytes), "i_stage_sha256": sha(stage_bytes),
            "denominator": str(values["denominator"]),
            "numerator": str(values["numerator"]),
            "quotient": str(values["quotient"]),
            "margin": str(values["margin"]),
            "fresh_exact_reconstruction_required": True,
        }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
