#!/usr/bin/env python3
"""Independent exact comparator for the two frozen wide k=30 proxy outputs."""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
GATE_REL = (
    "agents/structural-basis/results/"
    "wide_hybrid_outer_constant_proxy_launch_gate.json")
RESULTS = {
    "high_plateau": (
        "agents/structural-basis/results/"
        "wide_hybrid_outer_constant_D4_k30_high_plateau.json"),
    "volume_ramp": (
        "agents/structural-basis/results/"
        "wide_hybrid_outer_constant_D4_k30_volume_ramp.json"),
}
PINNED = {
    "agents/structural-basis/code/wide_hybrid_outer_constant_proxy.py":
        "21b9b384d0ec502cbfd83bacb2da1d7e7529a1131a8a959e28eaa948f568ba16",
    GATE_REL:
        "718d8bba2e4df460583cac6f9c27f9da682de43e31fd86e2ce0ba04f599e058b",
    "agents/audit/verify_wide_hybrid_outer_constant_proxy_gate.py":
        "8edc74b1f9a67745dbf3470c150644a5652f45ed85b2d4227495d0e9950cfcdf",
    "agents/audit/results/wide_hybrid_outer_constant_proxy_prelaunch_audit.json":
        "201b928df3840ddc714747dd40426e487bda78ad771f5a1d6afff3f24cbfe3d7",
    RESULTS["high_plateau"]:
        "aed2641e604c050a96c572b08ad1f84d6ded59b12e3b05b714be6a0301a79798",
    RESULTS["volume_ramp"]:
        "ff9d05d610f3960fa898bbf22f3fdc367232e22621a64ed350d5da7a19684acb",
}

MIN_GAIN = Q(1, 100000)
MIN_SEPARATION = Q(1, 10000000)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(relative: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {relative}: {key}")
            result[key] = value
        return result

    return json.loads(
        (REPO / relative).read_bytes(), object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {relative}: {token}")))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def q(value) -> Q:
    require(isinstance(value, str), "exact value must be a rational string")
    return Q(value)


def decimal(value: Q, precision: int = 40) -> str:
    with localcontext() as context:
        context.prec = precision
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def build() -> dict[str, object]:
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"frozen proxy/result byte changed: {relative}")
    gate = strict_json(GATE_REL)
    require(isinstance(gate, dict), "gate must be an object")

    quotients = {}
    gains = {}
    summaries = {}
    common_base = None
    for name, relative in RESULTS.items():
        result = strict_json(relative)
        require(isinstance(result, dict), f"{name} result must be an object")
        require(result.get("status") ==
                "wide-hybrid-outer-constant-one-schedule-proxy-complete" and
                result.get("rigorous") is False and
                result.get("theorem_ready") is False and
                result.get("target_k48_integration_run") is False and
                result.get("target_launch_authorized") is False,
                f"{name} scope/target flags changed")
        require(result.get("script_sha256") == PINNED[
            "agents/structural-basis/code/wide_hybrid_outer_constant_proxy.py"],
            f"{name} driver provenance changed")
        require(result.get("parameters") == {
            "delta": "361/50000", "alpha1": "103/400",
            "eta1": "97/400", "alpha2": "3211/12000",
            "eta2": "3031/12000"}, f"{name} parameters changed")
        schedule = gate["schedules"][name]
        require(result.get("schedule") == name and
                result.get("caps") == schedule["caps"] and
                result.get("active_counts") == schedule["active_counts"],
                f"{name} schedule binding changed")
        require(result.get("low_k_signed_literal") ==
                gate["low_k_signed_literal"] and
                result.get("exact_target_constant_shell_I") ==
                gate["exact_target_constant_shell_I"][name],
                f"{name} low-k/shell binding changed")
        for dependency, expected in result.get("source_hashes", {}).items():
            require(sha(REPO / dependency) == expected,
                    f"{name} transitive dependency changed: {dependency}")

        proxy = result.get("proxy")
        require(isinstance(proxy, dict) and proxy.get("k") == 30 and
                proxy.get("radial_degree") == 4,
                f"{name} is not the declared k30 D4 proxy")
        base_i, base_b = q(proxy["base_denominator"]), q(
            proxy["base_numerator"])
        require(base_i > 0, f"{name} base denominator is nonpositive")
        if common_base is None:
            common_base = (base_i, base_b)
        require(common_base == (base_i, base_b),
                "two result files use different base forms")

        row = proxy.get("schedule_result")
        require(isinstance(row, dict) and row.get("name") == name and
                row.get("schedule_prefix") == schedule["caps"],
                f"{name} result row/schedule changed")
        matrix_i = [[q(x) for x in line] for line in row["I_matrix"]]
        matrix_b = [[q(x) for x in line] for line in row["kJ_matrix"]]
        require(len(matrix_i) == len(matrix_b) == 2 and
                all(len(line) == 2 for line in matrix_i + matrix_b) and
                matrix_i[0][0] == base_i and matrix_i[0][1] == 0 and
                matrix_i[1][0] == 0 and matrix_i[1][1] > 0 and
                matrix_b[0][0] == base_b and
                matrix_b[0][1] == matrix_b[1][0] and matrix_b[1][1] > 0,
                f"{name} 2x2 matrix structure changed")
        vector = [q(x) for x in row["rational_vector"]]
        require(len(vector) == 2 and vector[0] == 1,
                f"{name} rational vector changed shape")
        exact_i = sum(vector[i] * matrix_i[i][j] * vector[j]
                      for i in range(2) for j in range(2))
        exact_b = sum(vector[i] * matrix_b[i][j] * vector[j]
                      for i in range(2) for j in range(2))
        quotient = exact_b / exact_i
        gain = quotient - base_b / base_i
        require(exact_i == q(row["exact_denominator"]) and
                exact_b == q(row["exact_numerator"]) and
                quotient == q(row["exact_quotient"]) and
                gain == q(row["exact_gain"]),
                f"{name} exact vector contraction mismatch")
        expected_calls = gate["proxy_geometry"]["schedules"][name]
        require(row.get("integral_calls") == {
            tag: block["branch_pair_upper"]
            for tag, block in expected_calls.items()},
            f"{name} branch-call inventory changed")
        require(result.get("exact_quotient_for_comparison") ==
                row["exact_quotient"] and
                result.get("individual_gain_gate_pass") is False and
                result.get("fresh_other_schedule_and_comparator_required")
                is True and gain < MIN_GAIN,
                f"{name} continuation gate inconsistency")
        require(0 < float(result["wall_seconds"]) < 900 and
                0 < int(result["peak_rss_kib"]) < 131072,
                f"{name} observed resource record out of bounds")
        quotients[name] = quotient
        gains[name] = gain
        summaries[name] = {
            "quotient_decimal_40": decimal(quotient),
            "gain": str(gain),
            "gain_decimal_40": decimal(gain),
            "gain_gate_shortfall": str(MIN_GAIN - gain),
        }

    require(quotients["volume_ramp"] > quotients["high_plateau"],
            "schedule ranking changed")
    separation = (quotients["volume_ramp"] -
                  quotients["high_plateau"])
    require(0 < separation < MIN_SEPARATION,
            "predeclared schedule-separation verdict changed")
    require(max(gains.values()) < MIN_GAIN,
            "predeclared individual-gain verdict changed")

    return {
        "status": "AUDIT PASS -- PROXY GATE FAIL",
        "scope": "frozen wide-C722 k30 constant-shell two-schedule proxy",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "results": summaries,
        "ranking": ["volume_ramp", "high_plateau"],
        "exact_separation": str(separation),
        "separation_decimal_40": decimal(separation),
        "separation_gate_shortfall": str(MIN_SEPARATION - separation),
        "decision": (
            "retire the constant-shell k30 proxy mechanism: both 1e-5 gain "
            "gates and the 1e-7 separation gate fail; no k48 launch"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
