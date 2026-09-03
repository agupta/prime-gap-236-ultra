#!/usr/bin/env python3
"""Fail-closed static audit of the completed affine Decimal discovery output.

This does not rerun any integral.  It hashes and strictly parses the result,
recontracts its pinned I-stage, and recomputes all serialized Decimal scalar
relations at precision 100.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
PG = HERE.parents[1]
EI = PG / "agents/exact-integrator"

INPUT = EI / "results/hb_c10_fullsimplex_noones_D12_integer_scaled.json"
MULTIPLIER = EI / "results/c10_stratum_linear_cappedopt_D4_exact.json"
STAGE = EI / "results/c10_D12_stratum_linear_decimal100_cut11.json.I-stage.json"

EXPECTED = {
    "input": "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93",
    "multiplier": "ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158",
    "stage": "96c9b89bc3ca56f7bb12ac931692790e4e621d1aad34817eb456bd00994cb22d",
}
DEPENDENCIES = {
    "driver": "91d1b4ad0c675ccfe36100166bee20bb4007af49e1d0cfe618c8c82c8857f354",
    "stratum_amplitude": "d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887",
    "stratum_linear": "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
    "grouped": "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator": "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "robust_solver": "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e",
}
STAGE_DEPENDENCIES = {
    "driver": "ba3ff83b186e7784634a97bf82f13ae3abdd4a4e753b226f0eaed23d659dfbc0",
    "stratum_linear": DEPENDENCIES["stratum_linear"],
    "grouped": DEPENDENCIES["grouped"],
    "integrator": DEPENDENCIES["integrator"],
    "robust_solver": DEPENDENCIES["robust_solver"],
}
DEPENDENCY_PATHS = {
    "driver": EI / "stratum_linear_transfer_decimal.py",
    "stratum_amplitude": EI / "stratum_amplitude.py",
    "stratum_linear": EI / "stratum_linear.py",
    "grouped": EI / "grouped_fixed_vector.py",
    "integrator": EI / "src/exact_integrator.py",
    "robust_solver": EI / "robust_generalized_solve.py",
}
PARAMETERS = {
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
    "beta1": "3/20",
    "beta2": "3/20",
    "beta3plus": "97/625",
}
FROZEN_DENOMINATOR = Decimal(
    "9.404805046184364933993801445964141570663344888014190056715425272135294022457997898153502271689941759E+311"
)
DECIMAL_TOKEN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:E[+-]?[0-9]+)?$")
TOP_KEYS = {
    "status", "rigorous", "complete", "space_note", "theorem_ready",
    "historical_transitive_provenance_limitation", "decimal_dps",
    "linear_cutoff", "input_json", "input_sha256", "multiplier_json",
    "multiplier_sha256", "i_stage_json", "i_stage_sha256", "parameters",
    "dependency_hashes", "fixed_basis_dimension", "multiplier_dimension",
    "transferred_vector", "denominator", "numerator", "quotient", "margin",
    "denominator_positive", "margin_positive", "marginal_components",
    "j_branch_domains", "i_by_r", "j_by_common_r", "j_seconds",
    "peak_rss_kib", "gates", "gates_passed",
}
GATE_KEYS = {
    "dependencies_unchanged", "i_stage_unchanged",
    "input_and_multiplier_pinned", "i_stage_complete",
    "denominator_positive", "j_counts_complete", "finite",
}


def fail(message: str) -> None:
    raise SystemExit(f"AUDIT FAIL: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def strict_bool(value: object, expected: bool, name: str) -> None:
    require(type(value) is bool and value is expected, f"{name} is not {expected}")


def strict_int(value: object, expected: int, name: str) -> None:
    require(type(value) is int and value == expected, f"{name}!={expected}")


def dec(value: object, name: str) -> Decimal:
    require(isinstance(value, str) and DECIMAL_TOKEN.fullmatch(value) is not None,
            f"malformed Decimal token {name}")
    answer = Decimal(value)
    require(answer.is_finite(), f"nonfinite Decimal {name}")
    return answer


def parse_stage_key(token: object) -> tuple[tuple[int, int], tuple[int, int]]:
    require(isinstance(token, str), "non-string stage key")
    try:
        value = ast.literal_eval(token)
    except (SyntaxError, ValueError) as exc:
        fail(f"malformed stage key: {exc}")
    require(
        isinstance(value, tuple) and len(value) == 2
        and all(isinstance(x, tuple) and len(x) == 2 for x in value)
        and all(type(y) is int for x in value for y in x),
        "stage key does not consist of two integer pairs",
    )
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result")
    parser.add_argument("--expect-sha256", required=True)
    args = parser.parse_args()
    result_path = Path(args.result).resolve()

    result_bytes = result_path.read_bytes()
    result_sha = sha(result_bytes)
    require(result_sha == args.expect_sha256, "result byte SHA mismatch")
    try:
        out = json.loads(result_bytes)
    except json.JSONDecodeError as exc:
        fail(f"malformed result JSON: {exc}")
    require(type(out) is dict and set(out) == TOP_KEYS, "result schema mismatch")

    # Pin all three arithmetic inputs and all source dependencies independently
    # of the producer's own claims.
    for name, path in (("input", INPUT), ("multiplier", MULTIPLIER), ("stage", STAGE)):
        require(file_sha(path) == EXPECTED[name], f"current {name} SHA mismatch")
    for name, path in DEPENDENCY_PATHS.items():
        require(file_sha(path) == DEPENDENCIES[name], f"dependency changed: {name}")

    source = json.loads(INPUT.read_bytes())
    multiplier = json.loads(MULTIPLIER.read_bytes())
    stage = json.loads(STAGE.read_bytes())
    strict_int(source.get("k"), 48, "input k")
    require(len(source.get("basis", [])) == len(source.get("rational_vector", [])) == 272,
            "input is not the 272-coordinate source")
    strict_int(multiplier.get("k"), 48, "multiplier k")
    require(multiplier.get("status") == "exact-stratum-linear-rational-vector",
            "wrong multiplier status")
    strict_bool(multiplier.get("rigorous_forms"), True, "multiplier rigorous_forms")
    strict_bool(multiplier.get("block_direct_bitwise_equal"), True,
                "multiplier block/direct gate")

    require(stage.get("status") == "multiprecision-stratum-linear-I-stage",
            "wrong I-stage status")
    strict_bool(stage.get("rigorous"), False, "stage rigorous")
    strict_bool(stage.get("complete"), True, "stage complete")
    strict_int(stage.get("decimal_dps"), 100, "stage decimal_dps")
    strict_int(stage.get("linear_cutoff"), 11, "stage cutoff")
    strict_int(stage.get("nominal_dimension"), 40, "stage nominal dimension")
    strict_int(stage.get("i_orbit_groups"), 1575, "stage orbit groups")
    strict_int(stage.get("i_faces"), 312, "stage I faces")
    require(stage.get("input_sha256") == EXPECTED["input"], "stage input SHA")
    require(stage.get("parameters") == PARAMETERS, "stage parameter mismatch")
    require(stage.get("dependency_hashes") == STAGE_DEPENDENCIES,
            "stage dependency closure mismatch")

    require(out["status"] == "multiprecision-transferred-affine-candidate",
            "result status is not accepted candidate")
    strict_bool(out["rigorous"], False, "result rigorous")
    strict_bool(out["complete"], True, "result complete")
    strict_bool(out["theorem_ready"], False, "result theorem_ready")
    strict_int(out["decimal_dps"], 100, "result decimal_dps")
    strict_int(out["linear_cutoff"], 11, "result cutoff")
    strict_int(out["fixed_basis_dimension"], 272, "fixed basis dimension")
    strict_int(out["multiplier_dimension"], 48, "multiplier dimension")
    strict_int(out["marginal_components"], 695, "marginal component count")
    strict_int(out["j_branch_domains"], 1200, "J domain count")
    require(out["parameters"] == PARAMETERS, "result parameters mismatch")
    require(out["dependency_hashes"] == DEPENDENCIES, "result dependencies mismatch")
    require(out["input_sha256"] == EXPECTED["input"], "result input SHA")
    require(out["multiplier_sha256"] == EXPECTED["multiplier"],
            "result multiplier SHA")
    require(out["i_stage_sha256"] == EXPECTED["stage"], "result stage SHA")
    require(Path(out["input_json"]).name == INPUT.name, "wrong result input path")
    require(Path(out["multiplier_json"]).name == MULTIPLIER.name,
            "wrong result multiplier path")
    require(Path(out["i_stage_json"]).name == STAGE.name, "wrong result stage path")

    require(type(out["gates"]) is dict and set(out["gates"]) == GATE_KEYS,
            "gate schema mismatch")
    for name in sorted(GATE_KEYS):
        strict_bool(out["gates"][name], True, f"gate {name}")
    strict_bool(out["gates_passed"], True, "gates_passed")
    strict_bool(out["denominator_positive"], True, "denominator_positive")

    # Rebuild the 48 cutoff-applied multiplier coefficients exactly as the
    # Decimal100 transfer does, directly from the rational multiplier file.
    labels = [(int(r), ("1", "L", "Z").index(channel))
              for r, channel in multiplier.get("linear_labels", [])]
    require(labels == [(r, p) for r in range(16) for p in range(3)],
            "multiplier label order mismatch")
    rationals = [Fraction(x) for x in multiplier.get("rational_vector", [])]
    require(len(rationals) == 48, "multiplier vector length")
    with localcontext() as ctx:
        ctx.prec = 100
        coefficients = {
            label: (Decimal(value.numerator) / Decimal(value.denominator)
                    if label[1] == 0 or label[0] <= 11 else Decimal(0))
            for label, value in zip(labels, rationals)
        }
        expected_vector = [str(coefficients[label]) for label in labels]
        require(out["transferred_vector"] == expected_vector,
                "serialized transferred vector mismatch")

        raw_entries = stage.get("i_entries")
        require(type(raw_entries) is dict, "stage entries are not an object")
        entries = [(parse_stage_key(key), dec(value, f"stage[{key}]") )
                   for key, value in raw_entries.items()]
        expected_keys = {
            ((r, p), (r, q))
            for r in range(16)
            for p in ((0, 1, 2) if r <= 11 else (0,))
            for q in ((0, 1, 2) if r <= 11 else (0,))
            if q <= p
        }
        require({key for key, _ in entries} == expected_keys and len(entries) == 76,
                "I-stage key set mismatch")

        i_rebuilt = []
        for r in range(16):
            total = Decimal(0)
            for (left, right), value in entries:
                if left[0] != r:
                    continue
                term = coefficients.get(left, Decimal(0)) * coefficients.get(right, Decimal(0)) * value
                total += term * (1 if left == right else 2)
            i_rebuilt.append(total)

        require(type(out["i_by_r"]) is list and len(out["i_by_r"]) == 16,
                "i_by_r length")
        i_serialized = [dec(x, f"i_by_r[{i}]") for i, x in enumerate(out["i_by_r"])]
        require(i_serialized == i_rebuilt, "I-stage contraction mismatch")
        denominator = sum(i_rebuilt, Decimal(0))
        require(denominator == dec(out["denominator"], "denominator"),
                "denominator field mismatch")
        require(denominator == FROZEN_DENOMINATOR,
                "denominator differs from frozen transfer value")

        require(type(out["j_by_common_r"]) is list and len(out["j_by_common_r"]) == 16,
                "j_by_common_r length")
        j_values = [dec(x, f"j_by_common_r[{i}]")
                    for i, x in enumerate(out["j_by_common_r"])]
        numerator = Decimal(48) * sum(j_values, Decimal(0))
        quotient = numerator / denominator
        margin = numerator - denominator
        require(numerator == dec(out["numerator"], "numerator"),
                "numerator field mismatch")
        require(quotient == dec(out["quotient"], "quotient"),
                "quotient field mismatch")
        require(margin == dec(out["margin"], "margin"), "margin field mismatch")
        strict_bool(out["margin_positive"], margin > 0, "margin_positive")
        require(denominator > 0, "recomputed denominator is nonpositive")

    require(type(out["j_seconds"]) in (int, float) and not isinstance(out["j_seconds"], bool)
            and math.isfinite(out["j_seconds"]) and out["j_seconds"] >= 0,
            "invalid J time")
    require(type(out["peak_rss_kib"]) is int and not isinstance(out["peak_rss_kib"], bool)
            and out["peak_rss_kib"] > 0, "invalid peak RSS")
    require(file_sha(result_path) == result_sha, "result mutated during audit")
    for name, path in (("input", INPUT), ("multiplier", MULTIPLIER), ("stage", STAGE)):
        require(file_sha(path) == EXPECTED[name], f"{name} mutated during audit")
    for name, path in DEPENDENCY_PATHS.items():
        require(file_sha(path) == DEPENDENCIES[name], f"dependency mutated: {name}")

    print("DISCOVERY-OUTPUT AUDIT PASS (not rigorous integration)")
    print(f"result_sha256={result_sha}")
    print(f"denominator={denominator}")
    print(f"numerator={numerator}")
    print(f"quotient={quotient}")
    print(f"margin={margin}")
    print(f"margin_positive={margin > 0}")
    print("rigorous=false")
    print("theorem_ready=false")


if __name__ == "__main__":
    main()
