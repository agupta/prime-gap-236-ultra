#!/usr/bin/env python3
"""Audit completed MP100 sparse-coordinate self forms and rebuild each pencil."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


MANIFEST_SHA = "967a004ed5f02dc08d07bd9ab8f5af1050b345427327935b96d0979ae531787f"
PREFLIGHT_SHA = "38a5963fa24827fbe83593fc1dd663666cf9cc43363e74704969c138be588c25"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
PARAMETERS = {"alpha": "79247/300000", "delta": "1/100",
              "eta": "76247/300000", "beta1": "3/20",
              "beta2": "3/20", "beta3plus": "97/625"}
RESULT_KEYS = {
    "status", "rigorous", "decimal_dps", "input_json", "k", "parameters",
    "basis_dimension", "workers", "i_orbit_groups", "i_faces",
    "marginal_components", "j_branch_integrals", "input_sha256",
    "i_seconds", "j_seconds", "total_seconds", "peak_rss_kib",
    "child_peak_rss_kib", "peak_rss_note", "denominator_positive",
    "margin_positive", "denominator", "j_value", "numerator", "quotient",
    "quotient_decimal_display", "margin", "script_sha256",
    "integrator_sha256",
}
STAGE_KEYS = {
    "status", "i_complete", "rigorous", "decimal_dps", "input_json",
    "input_sha256", "script_sha256", "integrator_sha256", "parameters",
    "i_orbit_groups", "i_faces", "i_seconds", "denominator_positive",
    "denominator", "peak_rss_kib", "child_peak_rss_kib",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, what):
    def pairs(items):
        out = {}
        for key, value in items:
            require(type(key) is str and key not in out,
                    f"{what}: duplicate/non-string key")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"{what}: nonfinite {token}")))


def fraction(value, what):
    require(type(value) is str and value == value.strip() and value,
            f"{what}: rational string")
    try:
        return Fraction(value)
    except Exception as exc:
        raise ValueError(f"{what}: malformed rational") from exc


def decimal160(value):
    value = fraction(value, "decimal160 input")
    return Decimal(value.numerator)/Decimal(value.denominator)


def pencil(direction, result):
    cross = direction["cross_action"]
    with localcontext() as context:
        context.prec = 170
        D, N, a, b, A, B = map(decimal160, (
            cross["denominator_D0"], cross["numerator_N0"],
            cross["A_cross_a01"], cross["B48_cross_b01"],
            result["denominator"], result["numerator"]))
        gram = D*A-a*a
        require(gram > 0, "pencil denominator Gram determinant")
        c1 = -(N*A+D*B)+2*a*b
        c0 = N*B-b*b
        discriminant = c1*c1-4*gram*c0
        require(discriminant > 0, "pencil discriminant")
        roots = ((-c1-discriminant.sqrt())/(2*gram),
                 (-c1+discriminant.sqrt())/(2*gram))
        qmax = max(roots)
        denominator = B-qmax*A
        require(denominator != 0, "finite maximizing chart")
        s = -(b-qmax*a)/denominator
        qcheck = (N+2*s*b+s*s*B)/(D+2*s*a+s*s*A)
        require(abs(qcheck-qmax) < Decimal("1e-150"), "pencil substitution")
        base = N/D
        threshold_B = A+(b-a)*(b-a)/(N-D)
        return {
            "base_quotient": str(base), "self_quotient": str(B/A),
            "crossing_threshold_self_quotient": str(threshold_B/A),
            "line_maximum": str(qmax), "line_parameter": str(s),
            "line_gain": str(qmax-base), "line_shortfall": str(1-qmax),
            "denominator_gram_determinant": str(gram),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--coordinates", required=True,
                        help="comma-separated coordinate indices")
    parser.add_argument("--expected-workers", type=int, default=1)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest_path = Path(args.manifest).resolve()
    preflight_path = Path(args.preflight).resolve()
    manifest_raw, preflight_raw = manifest_path.read_bytes(), preflight_path.read_bytes()
    require(sha(manifest_raw) == MANIFEST_SHA, "manifest SHA")
    require(sha(preflight_raw) == PREFLIGHT_SHA, "preflight SHA")
    manifest = strict_json(manifest_raw, "manifest")
    preflight = strict_json(preflight_raw, "preflight")
    require(preflight.get("status") == "AUDIT PASS" and
            preflight.get("directions_checked") == 19 and
            preflight.get("manifest_sha256") == MANIFEST_SHA,
            "preflight verdict")
    entries = {item["coordinate"]: item for item in manifest["full_ranking"]}
    coordinates = [int(x) for x in args.coordinates.split(",")]
    require(coordinates and len(coordinates) == len(set(coordinates)) and
            all(x in entries for x in coordinates), "coordinate list")
    results_dir = Path(args.results_dir).resolve()
    trusted = {manifest_path: manifest_raw, preflight_path: preflight_raw}
    records = []
    for coordinate in coordinates:
        entry = entries[coordinate]
        input_path = Path(entry["path"]).resolve()
        input_raw = input_path.read_bytes()
        require(sha(input_raw) == entry["sha256"], f"c{coordinate}: input SHA")
        direction = strict_json(input_raw, f"c{coordinate} direction")
        stage_path = results_dir/f"c10_D12_sparse_c{coordinate:02d}_self_mp100.I-stage.json"
        result_path = results_dir/f"c10_D12_sparse_c{coordinate:02d}_self_mp100.json"
        stage_raw, result_raw = stage_path.read_bytes(), result_path.read_bytes()
        stage, result = strict_json(stage_raw, f"c{coordinate} stage"), strict_json(
            result_raw, f"c{coordinate} result")
        trusted.update({input_path: input_raw, stage_path: stage_raw, result_path: result_raw})
        require(set(stage) == STAGE_KEYS and set(result) == RESULT_KEYS,
                f"c{coordinate}: exact output schemas")
        counts = entry["expected_grouped_counts"]
        common = (stage["input_sha256"] == result["input_sha256"] == entry["sha256"] and
                  stage["script_sha256"] == result["script_sha256"] == GROUPED_SHA and
                  stage["integrator_sha256"] == result["integrator_sha256"] == INTEGRATOR_SHA and
                  stage["parameters"] == result["parameters"] == PARAMETERS and
                  stage["decimal_dps"] == result["decimal_dps"] == 100 and
                  stage["rigorous"] is result["rigorous"] is False and
                  stage["i_orbit_groups"] == result["i_orbit_groups"] == counts["i_orbit_groups"] and
                  stage["i_faces"] == result["i_faces"] == counts["i_faces"] and
                  result["marginal_components"] == counts["marginal_components"] and
                  result["j_branch_integrals"] == counts["j_branch_integrals"] and
                  result["basis_dimension"] == entry["basis_dimension"] and
                  result["workers"] == args.expected_workers)
        require(common, f"c{coordinate}: provenance/count gate")
        require(stage["status"] == "grouped-fixed-vector-I-stage" and
                stage["i_complete"] is True and
                result["status"] == "multiprecision-grouped-fixed-vector-discovery" and
                stage["denominator_positive"] is result["denominator_positive"] is True and
                stage["denominator"] == result["denominator"],
                f"c{coordinate}: status/denominator gate")
        with localcontext() as context:
            context.prec = 100
            D = Decimal(result["denominator"])
            J = Decimal(result["j_value"])
            N = Decimal(48)*J
            q = N/D
            margin = N-D
            require(str(N) == result["numerator"] and str(q) == result["quotient"] and
                    str(margin) == result["margin"],
                    f"c{coordinate}: Decimal100 operation replay")
            require(result["margin_positive"] is (margin > 0) and
                    result["quotient_decimal_display"] == float(q),
                    f"c{coordinate}: sign/display gate")
        records.append({
            "coordinate": coordinate, "coordinate_name": entry["name"],
            "input_sha256": entry["sha256"], "stage_sha256": sha(stage_raw),
            "result_sha256": sha(result_raw), "i_seconds": result["i_seconds"],
            "j_seconds": result["j_seconds"], "total_seconds": result["total_seconds"],
            "peak_rss_kib": result["peak_rss_kib"],
            "child_peak_rss_kib": result["child_peak_rss_kib"],
            **pencil(direction, result),
        })
    answer = {
        "status": "AUDIT PASS", "rigorous": False,
        "scope": "MP100 serialized self forms and 2x2 discovery pencils",
        "manifest_sha256": MANIFEST_SHA, "preflight_sha256": PREFLIGHT_SHA,
        "records": records,
    }
    rendered = (json.dumps(answer, indent=2)+"\n").encode()
    output = Path(args.output).resolve()
    require(output not in trusted and not output.exists(), "output collision")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, rendered); os.fsync(fd)
        require(os.fstat(fd).st_size == len(rendered), "short output")
        for path, raw in trusted.items():
            require(path.read_bytes() == raw, f"trusted file changed: {path}")
    finally:
        os.close(fd)
    print(json.dumps({"status": "AUDIT PASS", "output_sha256": sha(rendered),
                      "records": records}, indent=2))


if __name__ == "__main__":
    main()
