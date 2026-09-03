#!/usr/bin/env python3
"""Build a production-disabled gate for the wide-C722 schedule proxy."""

from __future__ import annotations

import argparse
import json
import math
from fractions import Fraction as Q
from pathlib import Path

import wide_hybrid_outer_constant_proxy as proxy


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SOURCE_RELATIVE = (
    "agents/structural-basis/code/wide_hybrid_outer_constant_proxy.py")
TEST_RELATIVE = (
    "agents/structural-basis/tests/"
    "test_wide_hybrid_outer_constant_proxy.py")
GATE_TEST_RELATIVE = (
    "agents/structural-basis/tests/"
    "test_wide_hybrid_outer_constant_proxy_gate.py")
SPEC_RELATIVE = (
    "agents/structural-basis/WIDE-HYBRID-OUTER-CONSTANT-PROXY.md")
COST_PROBE_RELATIVE = (
    "agents/structural-basis/results/"
    "wide_hybrid_outer_constant_D4_k30_cost_probe_v2.json")
PROXY_OUTPUTS = {
    "high_plateau": (
        "agents/structural-basis/results/"
        "wide_hybrid_outer_constant_D4_k30_high_plateau.json"),
    "volume_ramp": (
        "agents/structural-basis/results/"
        "wide_hybrid_outer_constant_D4_k30_volume_ramp.json"),
}


def canonical_sha(value):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError("expected self hash is not canonical SHA-256")
    return value


def strict_json(path):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key: {key}")
            answer[key] = value
        return answer

    value = json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(
                           ValueError(f"nonfinite JSON token: {token}")))
    return value


def validate_analytic_audits():
    paths = {
        "high_plateau":
            REPO / "agents/audit/results/wide_c722_p172_analytic_audit.json",
        "volume_ramp":
            REPO / "agents/audit/results/"
                   "wide_c722_volume_ramp_analytic_audit.json",
    }
    answer = {}
    for name, path in paths.items():
        artifact = strict_json(path)
        expected_active = list(proxy.active_counts(proxy.SCHEDULES[name]))
        parameters = artifact.get("parameters")
        if (artifact.get("status") != "AUDIT PASS" or
                artifact.get("c1") != "0" or artifact.get("c2") != "0" or
                artifact.get("beta") != "1/2" or
                not isinstance(parameters, dict) or
                parameters.get("k") != proxy.TARGET_K or
                parameters.get("delta") != str(proxy.DELTA) or
                parameters.get("epsilon") != "3/400" or
                parameters.get("A") != [
                    "-3/400", "1/4", "3121/12000"] or
                parameters.get("outer_active") != expected_active):
            raise ValueError(f"{name} analytic audit payload changed")
        answer[name] = {
            "status": "AUDIT PASS", "c1": "0", "c2": "0",
            "beta": "1/2", "artifact_sha256": proxy.sha256(path),
        }
    return answer


def validate_cost_probe(path):
    path = Path(path).resolve()
    artifact = strict_json(path)
    if (artifact.get("status") !=
            "wide-hybrid-D4-k30-cost-probe-complete" or
            artifact.get("rigorous") is not False or
            artifact.get("theorem_ready") is not False or
            artifact.get("target_k48_integration_run") is not False or
            artifact.get("proxy_quotient_run") is not False or
            artifact.get("script_sha256") != proxy.sha256(proxy.FILE) or
            artifact.get("source_hashes") != proxy.validate_sources() or
            artifact.get("low_k_signed_literal") !=
            proxy.low_k_signed_literal_tests() or
            artifact.get("full_proxy_geometry") !=
            proxy.proxy_geometry_estimate()):
        raise ValueError("cost probe is not the frozen no-quotient calibration")
    block = artifact.get("probe")
    if (not isinstance(block, dict) or block.get("k") != proxy.PROXY_K or
            block.get("radial_degree") != 4 or
            block.get("schedule") != "high_plateau" or
            block.get("cross_tag") != "rr" or
            block.get("branch_calls") != 7008 or
            block.get("nonzero_common_strata") != 24 or
            Q(block.get("exact_value")) <= 0 or
            isinstance(block.get("peak_rss_kib"), bool) or
            not isinstance(block.get("peak_rss_kib"), int) or
            block["peak_rss_kib"] <= 0 or
            isinstance(block.get("contraction_seconds"), bool) or
            not isinstance(block.get("contraction_seconds"), (int, float)) or
            not math.isfinite(block["contraction_seconds"]) or
            block["contraction_seconds"] <= 0):
        raise ValueError("cost probe datum changed")
    return artifact


def build_gate(expected_self_sha256):
    expected_self_sha256 = canonical_sha(expected_self_sha256)
    if proxy.sha256(HERE) != expected_self_sha256:
        raise ValueError("executed gate builder differs from trust root")
    existing_outputs = [relative for relative in PROXY_OUTPUTS.values()
                        if (REPO / relative).exists()]
    if existing_outputs:
        raise FileExistsError(
            "proxy output must be fresh at gate freeze: " +
            ", ".join(existing_outputs))
    sources = proxy.validate_sources()
    if not proxy.validate_schedules():
        raise ArithmeticError("schedule validation failed")
    low_k = proxy.low_k_signed_literal_tests()
    shell_masses = proxy.exact_target_shell_masses()
    coordinate_cost = proxy.outer_coordinate_complexity()
    cost_path = REPO / COST_PROBE_RELATIVE
    cost_probe = validate_cost_probe(cost_path)
    proxy_resources = proxy.parallel_proxy_resource_estimate(cost_probe)
    proxy_geometry = proxy.proxy_geometry_estimate()

    target_geometry = {
        name: proxy.target_geometry_estimate(schedule)
        for name, schedule in proxy.SCHEDULES.items()
    }
    target_resources = {
        name: proxy.resource_estimate(target_geometry[name])
        for name in proxy.SCHEDULES
    }
    if (any(Q(block["estimated_wall_seconds"]) <=
            proxy.MAX_ESTIMATED_TARGET_WALL_SECONDS
            for block in target_resources.values()) or
            proxy_resources["resource_gate_pass"] is not True):
        raise ArithmeticError("predeclared proxy/target resource split changed")
    analytic = validate_analytic_audits()
    radial = proxy.load_radial_base()

    local_hashes = {
        str(HERE.relative_to(REPO)): expected_self_sha256,
        SOURCE_RELATIVE: proxy.sha256(REPO / SOURCE_RELATIVE),
        TEST_RELATIVE: proxy.sha256(REPO / TEST_RELATIVE),
        GATE_TEST_RELATIVE: proxy.sha256(REPO / GATE_TEST_RELATIVE),
        SPEC_RELATIVE: proxy.sha256(REPO / SPEC_RELATIVE),
        COST_PROBE_RELATIVE: proxy.sha256(cost_path),
    }
    source_hashes = dict(sorted({**sources, **local_hashes}.items()))
    commands = {
        name: (
            "python3 agents/structural-basis/code/"
            "wide_hybrid_outer_constant_proxy.py --schedule " + name +
            " --output " + output)
        for name, output in PROXY_OUTPUTS.items()
    }
    return {
        "status": "wide-C722-hybrid-outer-constant-proxy-prelaunch-gate",
        "rigorous": False,
        "theorem_ready": False,
        "proxy_launch_authorized": False,
        "target_k48_launch_authorized": False,
        "scope": (
            "Source-bound exact k=2 algebra and k=30 radial-D4 schedule "
            "sensitivity plan. No k=30 quotient and no k=48 target form has "
            "been evaluated."),
        "source_hashes": source_hashes,
        "parameters": {
            "target_k": proxy.TARGET_K, "proxy_k": proxy.PROXY_K,
            "delta": str(proxy.DELTA), "alpha1": str(proxy.ALPHA1),
            "eta1": str(proxy.ETA1), "alpha2": str(proxy.ALPHA2),
            "eta2": str(proxy.ETA2),
        },
        "schedules": {
            name: {"caps": [str(value) for value in schedule],
                   "active_counts": list(proxy.active_counts(schedule))}
            for name, schedule in proxy.SCHEDULES.items()},
        "analytic_hypotheses": analytic,
        "low_k_signed_literal": low_k,
        "exact_target_constant_shell_I": {
            name: str(value) for name, value in shell_masses.items()},
        "certified_radial_base": {
            "degree": 16, "basis_dimension": 307,
            "denominator": str(radial["denominator"]),
            "numerator": str(radial["numerator"]),
            "quotient": str(radial["quotient"]),
            "amplitudes": [str(value) for value in radial["amplitudes"]],
        },
        "outer_coordinate_cost_assessment": coordinate_cost,
        "proxy_geometry": proxy_geometry,
        "proxy_resource_estimate": proxy_resources,
        "target_geometry_upper": target_geometry,
        "target_resource_estimates": target_resources,
        "planned_proxy_outputs": PROXY_OUTPUTS,
        "planned_proxy_commands": commands,
        "continuation_gate": {
            "minimum_best_exact_proxy_gain": str(proxy.MIN_PROXY_GAIN),
            "minimum_best_minus_other_exact_quotient":
                str(proxy.MIN_PROXY_SCHEDULE_SEPARATION),
            "maximum_parallel_proxy_wall_seconds":
                str(proxy.MAX_ESTIMATED_PROXY_WALL_SECONDS),
            "maximum_proxy_peak_rss_kib_per_process":
                proxy.MAX_PROXY_PEAK_RSS_KIB,
            "maximum_proxy_aggregate_rss_kib":
                proxy.MAX_PROXY_AGGREGATE_RSS_KIB,
            "proxy_resource_gate_pass":
                proxy_resources["resource_gate_pass"],
            "both_fresh_results_and_exact_comparator_required": True,
            "independent_gate_audit_required": True,
            "session_11209_must_be_finished": True,
            "separate_root_authorization_required": True,
            "target_k48_resource_gate_pass": False,
            "same_bv_d16_outer_coordinate_deferred_as_not_cheap": True,
            "proxy_launch_authorized": False,
            "target_k48_launch_authorized": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = build_gate(args.expected_self_sha256)
    digest = proxy.publish_new(args.output, payload)
    print(digest)


if __name__ == "__main__":
    main()
