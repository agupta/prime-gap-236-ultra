#!/usr/bin/env python3
"""Independent fail-closed prelaunch checker for the frozen wide k=30 proxy.

No producer module is imported and no expensive quotient is evaluated.  The
checker pins every frozen package byte, strictly parses the gate, reconstructs
the two rational schedules and resource arithmetic, and refuses to pass once
either planned output exists.
"""

from __future__ import annotations

import argparse
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
COST_REL = (
    "agents/structural-basis/results/"
    "wide_hybrid_outer_constant_D4_k30_cost_probe_v2.json")

PINNED = {
    "agents/structural-basis/code/wide_hybrid_outer_constant_proxy.py":
        "21b9b384d0ec502cbfd83bacb2da1d7e7529a1131a8a959e28eaa948f568ba16",
    "agents/structural-basis/code/build_wide_hybrid_outer_constant_proxy_gate.py":
        "e69ba4595645c60ea9f044abd58586386261b082292e01a7f0a45634033dfa55",
    "agents/structural-basis/WIDE-HYBRID-OUTER-CONSTANT-PROXY.md":
        "df9a930df0b4e75e641ab70e8c088e93ce779cd352ababd77908c414b872e5db",
    GATE_REL:
        "718d8bba2e4df460583cac6f9c27f9da682de43e31fd86e2ce0ba04f599e058b",
    COST_REL:
        "710f31e9be1c616b159e2f0db7fa12a9695c7fcce8a648d26ae70f5b85c9d483",
    "agents/structural-basis/tests/test_wide_hybrid_outer_constant_proxy.py":
        "b77729b123bc601a728f81da93265b28bd162675ef9ca0c18341a7a11c973de4",
    "agents/structural-basis/tests/test_wide_hybrid_outer_constant_proxy_gate.py":
        "a82510f9d96b012b92164536d06c3fe14f6ce34dd9367e94d531698ec8e81f33",
}

OUTPUTS = {
    "high_plateau": (
        "agents/structural-basis/results/"
        "wide_hybrid_outer_constant_D4_k30_high_plateau.json"),
    "volume_ramp": (
        "agents/structural-basis/results/"
        "wide_hybrid_outer_constant_D4_k30_volume_ramp.json"),
}

COMMANDS = {
    name: (
        "python3 agents/structural-basis/code/"
        "wide_hybrid_outer_constant_proxy.py --schedule " + name +
        " --output " + output)
    for name, output in OUTPUTS.items()
}

DELTA = Q(361, 50000)


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


def rational(value) -> Q:
    require(isinstance(value, str), "expected rational string")
    return Q(value)


def active_counts(schedule):
    # Definition 1 has an open large-coordinate threshold.  None of the
    # audited nodes is an equality, but use the strict feasibility test here.
    return [0] + [m for m, cap in enumerate(schedule, 1)
                  if m * DELTA < cap]


def build() -> dict[str, object]:
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"pinned package byte changed: {relative}")

    gate = strict_json(GATE_REL)
    cost = strict_json(COST_REL)
    require(isinstance(gate, dict) and isinstance(cost, dict),
            "gate/cost top level must be objects")

    # The frozen gate binds a wider dependency closure than this checker's
    # own top-level package pins.  Rehash every member of that closure.
    source_hashes = gate.get("source_hashes")
    require(isinstance(source_hashes, dict) and source_hashes,
            "missing gate source-hash closure")
    for relative, expected in source_hashes.items():
        require(isinstance(relative, str) and isinstance(expected, str) and
                len(expected) == 64,
                "malformed gate source-hash entry")
        require(sha(REPO / relative) == expected,
                f"gate dependency changed: {relative}")

    require(gate.get("status") ==
            "wide-C722-hybrid-outer-constant-proxy-prelaunch-gate" and
            gate.get("rigorous") is False and
            gate.get("theorem_ready") is False,
            "gate status/scope changed")
    require(gate.get("proxy_launch_authorized") is False and
            gate.get("target_k48_launch_authorized") is False,
            "frozen producer gate must remain production-disabled")
    require(gate.get("parameters") == {
        "target_k": 48, "proxy_k": 30, "delta": "361/50000",
        "alpha1": "103/400", "eta1": "97/400",
        "alpha2": "3211/12000", "eta2": "3031/12000"},
        "parameter block changed")

    expected_schedules = {
        "high_plateau": [
            min(Q(11, 200) + (m - 1) * DELTA, Q(43, 250))
            for m in range(1, 25)],
        "volume_ramp": [
            min(Q(49, 625) + (m - 1) * DELTA, Q(1599, 10000))
            for m in range(1, 24)],
    }
    schedules = gate.get("schedules")
    require(isinstance(schedules, dict) and
            set(schedules) == set(expected_schedules),
            "schedule inventory changed")
    for name, expected in expected_schedules.items():
        block = schedules[name]
        recorded = [rational(value) for value in block.get("caps", ())]
        require(recorded == expected, f"{name} rational schedule changed")
        require(all(left <= right <= left + DELTA
                    for left, right in zip(recorded, recorded[1:])),
                f"{name} violates Definition-1 schedule increments")
        require(block.get("active_counts") == active_counts(recorded),
                f"{name} active-count inventory changed")
        require(len(recorded) * DELTA > recorded[-1],
                f"{name} schedule does not stop at first empty count")

    analytic = gate.get("analytic_hypotheses")
    require(isinstance(analytic, dict) and set(analytic) == set(OUTPUTS),
            "analytic-audit inventory changed")
    audit_paths = {
        "high_plateau":
            "agents/audit/results/wide_c722_p172_analytic_audit.json",
        "volume_ramp":
            "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json",
    }
    for name, relative in audit_paths.items():
        block = analytic[name]
        artifact = strict_json(relative)
        require(block == {"status": "AUDIT PASS", "c1": "0", "c2": "0",
                          "beta": "1/2", "artifact_sha256": sha(REPO / relative)},
                f"{name} gate analytic binding changed")
        params = artifact.get("parameters")
        require(artifact.get("status") == "AUDIT PASS" and
                artifact.get("c1") == "0" and artifact.get("c2") == "0" and
                artifact.get("beta") == "1/2" and
                isinstance(params, dict) and params.get("k") == 48 and
                params.get("delta") == "361/50000" and
                params.get("epsilon") == "3/400" and
                params.get("A") == ["-3/400", "1/4", "3121/12000"] and
                params.get("outer_active") == active_counts(
                    expected_schedules[name]),
                f"{name} analytic artifact schema changed")

    require(gate.get("low_k_signed_literal") == {
        "literal_cross": "7079/3000000",
        "signed_self": "94927012783/126000000000000",
        "shell_j": "1/12500", "k2_shell_numerator": "1/6250"},
        "low-k literal/polarization regression changed")
    shell = gate.get("exact_target_constant_shell_I")
    require(isinstance(shell, dict) and
            all(rational(shell[name]) > 0 for name in OUTPUTS),
            "target shell mass is not exactly positive")
    radial = gate.get("certified_radial_base")
    require(isinstance(radial, dict) and radial.get("degree") == 16 and
            radial.get("basis_dimension") == 307 and
            rational(radial["denominator"]) > 0 and
            rational(radial["numerator"]) /
            rational(radial["denominator"]) == rational(radial["quotient"]),
            "radial-base contraction record inconsistent")

    require(gate.get("planned_proxy_outputs") == OUTPUTS and
            gate.get("planned_proxy_commands") == COMMANDS,
            "planned proxy output/command changed")
    present = [relative for relative in OUTPUTS.values()
               if (REPO / relative).exists()]
    require(not present, "planned result is not fresh: " + ", ".join(present))

    require(cost.get("status") ==
            "wide-hybrid-D4-k30-cost-probe-complete" and
            cost.get("rigorous") is False and
            cost.get("theorem_ready") is False and
            cost.get("target_k48_integration_run") is False and
            cost.get("proxy_quotient_run") is False,
            "cost probe scope changed")
    probe = cost.get("probe")
    require(isinstance(probe, dict) and probe.get("k") == 30 and
            probe.get("radial_degree") == 4 and
            probe.get("branch_calls") == 7008 and
            probe.get("peak_rss_kib") == 35320,
            "cost calibration datum changed")
    rate = Q(str(probe["contraction_seconds"])) / 7008
    geometry = gate.get("proxy_geometry")
    require(isinstance(geometry, dict) and
            geometry.get("total_branch_pair_upper") == 119610 and
            cost.get("full_proxy_geometry") == geometry,
            "proxy geometry no longer matches cost probe")
    base_calls = sum(int(item["branch_pair_upper"])
                     for item in geometry["base"].values())
    calls = {
        name: base_calls + sum(int(item["branch_pair_upper"])
                               for item in geometry["schedules"][name].values())
        for name in OUTPUTS
    }
    require(calls == {"high_plateau": 71034, "volume_ramp": 70266},
            "per-process branch-call arithmetic changed")
    walls = {name: rate * count * Q(3, 2)
             for name, count in calls.items()}
    resource = gate.get("proxy_resource_estimate")
    require(isinstance(resource, dict) and
            resource.get("branch_calls_per_process") == calls and
            {name: rational(value) for name, value in
             resource.get("estimated_wall_seconds_per_process", {}).items()}
            == walls and
            rational(resource["estimated_parallel_wall_seconds"]) ==
            max(walls.values()) and max(walls.values()) < 900 and
            resource.get("measured_peak_rss_kib_per_process") == 35320 and
            resource.get("estimated_aggregate_peak_rss_kib") == 70640 and
            35320 < 131072 and 70640 < 262144 and
            resource.get("resource_gate_pass") is True,
            "parallel proxy resource gate arithmetic changed")

    continuation = gate.get("continuation_gate")
    require(isinstance(continuation, dict) and
            continuation.get("proxy_resource_gate_pass") is True and
            continuation.get("independent_gate_audit_required") is True and
            continuation.get("session_11209_must_be_finished") is True and
            continuation.get("separate_root_authorization_required") is True and
            continuation.get("both_fresh_results_and_exact_comparator_required")
            is True and continuation.get("proxy_launch_authorized") is False and
            continuation.get("target_k48_launch_authorized") is False and
            continuation.get("target_k48_resource_gate_pass") is False,
            "continuation policy weakened")
    require(all(rational(block["estimated_wall_seconds"]) > 14400
                for block in gate.get("target_resource_estimates", {}).values()),
            "k=48 target resource split changed")

    return {
        "status": "AUDIT PASS",
        "scope": "frozen wide-C722 k=30 two-schedule discovery proxy prelaunch",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "prelaunch": {
            "planned_outputs_absent": True,
            "driver_source_bound": True,
            "normal_and_optimized_safe": True,
            "branch_calls_per_process": calls,
            "estimated_parallel_wall_seconds": str(max(walls.values())),
            "wall_margin_seconds": str(Q(900) - max(walls.values())),
            "estimated_aggregate_rss_kib": 70640,
            "aggregate_rss_margin_kib": 262144 - 70640,
            "commands": COMMANDS,
        },
        "authorization": (
            "root may launch only these two k=30 discovery proxies, after "
            "this checker passes immediately before launch and session 11209 "
            "is confirmed finished; no k=48 launch is authorized"),
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
