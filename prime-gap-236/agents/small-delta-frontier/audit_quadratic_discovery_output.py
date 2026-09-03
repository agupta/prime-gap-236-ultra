#!/usr/bin/env python3
"""Fail-closed static audit of a D12 quadratic-transfer discovery output.

No integration is performed.  The checker pins both result and internal
I-stage bytes, validates the complete provenance/schema, and recomputes every
serialized Decimal100 scalar identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from decimal import Decimal, localcontext
from pathlib import Path


HERE = Path(__file__).resolve().parent
PG = HERE.parents[1]
EI = PG / "agents/exact-integrator"
INPUT = EI / "results/hb_c10_fullsimplex_noones_D12_integer_scaled.json"
MULTIPLIER = EI / "results/c10_stratum_quadratic_cappedopt_D4_exact.json"

EXPECTED_INPUT_SHA = "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93"
EXPECTED_MULTIPLIER_SHA = "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86"
DEPENDENCIES = {
    "driver": "cd1232cb448fbda9003fab366e9095ffd36913d83ddaeba9e9521d886057b07f",
    "quadratic": "62dad8c96005bdb06945552a36b6dc35cecea6633daa5f3cf06e514a6aa77234",
    "stratum_amplitude": "d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887",
    "stratum_linear": "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
    "grouped": "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator": "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "robust_solver": "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e",
    "scheduled_basis": "06f79a13dbf172f40716d603ae8d824b5f65d2d69ed08dee59bd5c091821c4d0",
    "scheduled_verifier": "97f36696712f9cbe0cc0fff1fab6c4dc5ec4850220c12ebcc63f9c794aff1a1a",
}
DEPENDENCY_PATHS = {
    "driver": EI / "stratum_quadratic_transfer_decimal.py",
    "quadratic": EI / "stratum_quadratic.py",
    "stratum_amplitude": EI / "stratum_amplitude.py",
    "stratum_linear": EI / "stratum_linear.py",
    "grouped": EI / "grouped_fixed_vector.py",
    "integrator": EI / "src/exact_integrator.py",
    "robust_solver": EI / "robust_generalized_solve.py",
    "scheduled_basis": EI / "run_scheduled_basis.py",
    "scheduled_verifier": EI / "verify_scheduled_fixed_vector.py",
}
PARAMETERS = {
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
    "beta1": "3/20",
    "beta2": "3/20",
    "beta3plus": "97/625",
}
CHANNELS = ("1", "L", "Z", "L^2", "LZ", "Z^2")
DECIMAL_TOKEN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:E[+-]?[0-9]+)?$")
TOP_KEYS = {
    "status", "rigorous", "complete", "space_note", "theorem_ready",
    "decimal_dps", "input_json", "input_sha256", "multiplier_json",
    "multiplier_sha256", "parameters", "dependency_hashes",
    "fixed_basis_dimension", "multiplier_dimension", "i_stage_json",
    "i_stage_sha256", "i_by_r", "j_by_common_r", "denominator",
    "numerator", "quotient", "margin", "margin_positive",
    "i_orbit_groups", "i_faces", "marginal_components",
    "j_branch_domains", "i_seconds", "j_seconds", "total_seconds",
    "peak_rss_kib", "gates", "gates_passed",
}
STAGE_KEYS = {
    "status", "rigorous", "complete", "decimal_dps", "input_sha256",
    "multiplier_sha256", "parameters", "dependency_hashes",
    "i_orbit_groups", "i_faces", "i_by_r", "denominator", "i_seconds",
}
GATE_KEYS = {
    "dependencies_unchanged", "input_unchanged", "multiplier_unchanged",
    "i_stage_unchanged", "inputs_pinned", "counts_complete",
    "denominator_positive", "finite",
}


def fail(message: str) -> None:
    raise SystemExit(f"AUDIT FAIL: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_duplicate_pairs(pairs):
    answer = {}
    for key, value in pairs:
        require(key not in answer, f"duplicate JSON key {key!r}")
        answer[key] = value
    return answer


def reject_constant(token):
    fail(f"nonfinite JSON constant {token}")


def strict_loads(raw: bytes, description: str):
    try:
        return json.loads(raw, object_pairs_hook=reject_duplicate_pairs,
                          parse_constant=reject_constant)
    except (json.JSONDecodeError, UnicodeError) as exc:
        fail(f"malformed {description} JSON: {exc}")


def file_sha(path: Path) -> str:
    return digest(path.read_bytes())


def strict_bool(value: object, expected: bool, name: str) -> None:
    require(type(value) is bool and value is expected, f"{name} is not {expected}")


def strict_int(value: object, expected: int, name: str) -> None:
    require(type(value) is int and value == expected, f"{name}!={expected}")


def dec(value: object, name: str) -> Decimal:
    require(isinstance(value, str) and DECIMAL_TOKEN.fullmatch(value) is not None,
            f"malformed Decimal {name}")
    answer = Decimal(value)
    require(answer.is_finite(), f"nonfinite Decimal {name}")
    return answer


def finite_nonnegative_number(value: object, name: str) -> None:
    require(type(value) in (int, float) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0, f"invalid {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result")
    parser.add_argument("--expect-sha256", required=True)
    parser.add_argument("--expect-stage-sha256", required=True)
    args = parser.parse_args()
    result_path = Path(args.result).resolve()
    stage_path = Path(str(result_path) + ".I-stage.json")

    result_bytes = result_path.read_bytes()
    stage_bytes = stage_path.read_bytes()
    result_sha = digest(result_bytes)
    stage_sha = digest(stage_bytes)
    require(result_sha == args.expect_sha256, "result SHA mismatch")
    require(stage_sha == args.expect_stage_sha256, "I-stage SHA mismatch")
    out = strict_loads(result_bytes, "result")
    stage = strict_loads(stage_bytes, "stage")
    require(type(out) is dict and set(out) == TOP_KEYS, "result schema mismatch")
    require(type(stage) is dict and set(stage) == STAGE_KEYS, "stage schema mismatch")

    require(file_sha(INPUT) == EXPECTED_INPUT_SHA, "input bytes changed")
    require(file_sha(MULTIPLIER) == EXPECTED_MULTIPLIER_SHA,
            "multiplier bytes changed")
    for name, path in DEPENDENCY_PATHS.items():
        require(file_sha(path) == DEPENDENCIES[name], f"dependency changed: {name}")

    source = strict_loads(INPUT.read_bytes(), "input")
    multiplier = strict_loads(MULTIPLIER.read_bytes(), "multiplier")
    strict_int(source.get("k"), 48, "input k")
    require(len(source.get("basis", [])) == len(source.get("rational_vector", [])) == 272,
            "input dimension mismatch")
    strict_int(multiplier.get("k"), 48, "multiplier k")
    require(multiplier.get("status") == "exact-stratum-quadratic-rational-vector",
            "multiplier status mismatch")
    strict_bool(multiplier.get("rigorous_forms"), True, "multiplier rigorous_forms")
    strict_bool(multiplier.get("block_direct_bitwise_equal"), True,
                "multiplier block/direct gate")
    require(multiplier.get("parameters") == PARAMETERS, "multiplier parameters")
    labels = [(int(r), channel) for r, channel in multiplier.get("quadratic_labels", [])]
    require(labels == [(r, channel) for r in range(16) for channel in CHANNELS],
            "quadratic coordinate order mismatch")
    require(len(multiplier.get("rational_vector", [])) == 96,
            "quadratic multiplier vector length")

    require(stage["status"] == "multiprecision-quadratic-transfer-I-stage",
            "stage status mismatch")
    strict_bool(stage["rigorous"], False, "stage rigorous")
    strict_bool(stage["complete"], True, "stage complete")
    strict_int(stage["decimal_dps"], 100, "stage decimal_dps")
    require(stage["input_sha256"] == EXPECTED_INPUT_SHA, "stage input SHA")
    require(stage["multiplier_sha256"] == EXPECTED_MULTIPLIER_SHA,
            "stage multiplier SHA")
    require(stage["parameters"] == PARAMETERS, "stage parameters")
    require(stage["dependency_hashes"] == DEPENDENCIES, "stage dependencies")
    strict_int(stage["i_orbit_groups"], 1575, "stage orbit groups")
    strict_int(stage["i_faces"], 312, "stage I faces")

    require(out["status"] == "multiprecision-transferred-quadratic-candidate",
            "result status mismatch")
    require(out["space_note"] ==
            "one transferred exact-D4 rational D2 multiplier; not a D12 multiplier-space optimum",
            "result space-note mismatch")
    strict_bool(out["rigorous"], False, "result rigorous")
    strict_bool(out["complete"], True, "result complete")
    strict_bool(out["theorem_ready"], False, "result theorem_ready")
    strict_int(out["decimal_dps"], 100, "result decimal_dps")
    require(out["input_sha256"] == EXPECTED_INPUT_SHA, "result input SHA")
    require(out["multiplier_sha256"] == EXPECTED_MULTIPLIER_SHA,
            "result multiplier SHA")
    require(out["parameters"] == PARAMETERS, "result parameters")
    require(out["dependency_hashes"] == DEPENDENCIES, "result dependencies")
    strict_int(out["fixed_basis_dimension"], 272, "fixed basis dimension")
    strict_int(out["multiplier_dimension"], 96, "multiplier dimension")
    strict_int(out["i_orbit_groups"], 1575, "result orbit groups")
    strict_int(out["i_faces"], 312, "result I faces")
    strict_int(out["marginal_components"], 695, "marginal components")
    strict_int(out["j_branch_domains"], 1200, "J domains")
    require(Path(out["input_json"]).name == INPUT.name, "result input path")
    require(Path(out["multiplier_json"]).name == MULTIPLIER.name,
            "result multiplier path")
    require(Path(out["i_stage_json"]).name == stage_path.name,
            "result stage path")
    require(out["i_stage_sha256"] == stage_sha, "result stage SHA")

    require(type(out["gates"]) is dict and set(out["gates"]) == GATE_KEYS,
            "gate schema mismatch")
    for name in sorted(GATE_KEYS):
        strict_bool(out["gates"][name], True, f"gate {name}")
    strict_bool(out["gates_passed"], True, "gates_passed")

    with localcontext() as ctx:
        ctx.prec = 100
        require(type(stage["i_by_r"]) is list and len(stage["i_by_r"]) == 16,
                "stage i_by_r length")
        require(out["i_by_r"] == stage["i_by_r"], "result/stage I list mismatch")
        i_values = [dec(x, f"i_by_r[{i}]") for i, x in enumerate(stage["i_by_r"])]
        denominator = sum(i_values, Decimal(0))
        require(denominator == dec(stage["denominator"], "stage denominator"),
                "stage denominator mismatch")
        require(denominator == dec(out["denominator"], "result denominator"),
                "result denominator mismatch")
        require(denominator > 0, "denominator nonpositive")

        require(type(out["j_by_common_r"]) is list and len(out["j_by_common_r"]) == 16,
                "J list length")
        j_values = [dec(x, f"j_by_common_r[{i}]")
                    for i, x in enumerate(out["j_by_common_r"])]
        numerator = Decimal(48) * sum(j_values, Decimal(0))
        quotient = numerator / denominator
        margin = numerator - denominator
        require(numerator == dec(out["numerator"], "numerator"),
                "numerator mismatch")
        require(quotient == dec(out["quotient"], "quotient"),
                "quotient mismatch")
        require(margin == dec(out["margin"], "margin"), "margin mismatch")
        strict_bool(out["margin_positive"], margin > 0, "margin_positive")

    for name in ("i_seconds", "j_seconds", "total_seconds"):
        finite_nonnegative_number(out[name], name)
    finite_nonnegative_number(stage["i_seconds"], "stage i_seconds")
    require(out["i_seconds"] == stage["i_seconds"], "stage/result I time mismatch")
    require(type(out["peak_rss_kib"]) is int and not isinstance(out["peak_rss_kib"], bool)
            and out["peak_rss_kib"] > 0, "invalid peak RSS")

    require(file_sha(result_path) == result_sha, "result mutated during audit")
    require(file_sha(stage_path) == stage_sha, "stage mutated during audit")
    require(file_sha(INPUT) == EXPECTED_INPUT_SHA, "input mutated during audit")
    require(file_sha(MULTIPLIER) == EXPECTED_MULTIPLIER_SHA,
            "multiplier mutated during audit")
    for name, path in DEPENDENCY_PATHS.items():
        require(file_sha(path) == DEPENDENCIES[name], f"dependency mutated: {name}")

    print("DISCOVERY-OUTPUT AUDIT PASS (not rigorous integration)")
    print(f"result_sha256={result_sha}")
    print(f"stage_sha256={stage_sha}")
    print(f"denominator={denominator}")
    print(f"numerator={numerator}")
    print(f"quotient={quotient}")
    print(f"margin={margin}")
    print(f"margin_positive={margin > 0}")
    print("rigorous=false")
    print("theorem_ready=false")


if __name__ == "__main__":
    main()
