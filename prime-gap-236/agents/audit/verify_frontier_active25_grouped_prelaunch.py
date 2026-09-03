#!/usr/bin/env python3
"""Independent audit of the active-25 grouped-domain arithmetic preflight.

This checker never launches the complete k=48 cross traversal.  It verifies
the frozen core, exact representative artifacts, an ungrouped oracle,
low-dimensional literal/grouped identities, Definition-5 factors/signs, and
the arithmetic of the disabled resource envelope.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
CORE = REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py"
TESTS = REPO / "agents/small-delta-frontier/test_frontier_active25_inner_d16_tagged_shell.py"
RESULTS = REPO / "agents/small-delta-frontier/results"
ANALYTIC = REPO / "agents/audit/results/wide_c722_nonuniform_active25_tail_analytic_audit.json"
RADIAL = REPO / "agents/small-delta-frontier/bv_D16_radial_two_amplitudes_exact.json"
GATE = RESULTS / "frontier_active25_innerD16_tagged_shell_prelaunch_gate.json"
GATE_CHECKER = REPO / "agents/small-delta-frontier/verify_frontier_active25_prelaunch_gate.py"
STAGED = REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_staged_v2.py"
STAGED_TESTS = REPO / "agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v2.py"
STAGED_SPEC = REPO / "agents/small-delta-frontier/FRONTIER-ACTIVE25-INNER-D16-TAGGED-SHELL-PRELAUNCH-V2.md"
ORACLE = RESULTS / "frontier_active25_innerD16_shell_cross_r10_h10_ungrouped_oracle.json"
DIRECT = RESULTS / "frontier_active25_innerD16_shell_cross_r10_h10_direct_v2.json"
BENCHMARKS = {
    (0, 17): RESULTS / "frontier_active25_innerD16_shell_cross_r00_h17_direct_v2.json",
    (5, 15): RESULTS / "frontier_active25_innerD16_shell_cross_r05_h15_direct_v2.json",
    (10, 10): DIRECT,
    (15, 10): RESULTS / "frontier_active25_innerD16_shell_cross_r15_h10_direct_v2.json",
    (22, 6): RESULTS / "frontier_active25_innerD16_shell_cross_r22_h06_direct_v2.json",
    (25, 5): RESULTS / "frontier_active25_innerD16_shell_cross_r25_h05_direct_v2.json",
}

PINS = {
    CORE: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    TESTS: "a9c822357bb2cb9225030b0df46f11bca225ec05158e48ee0d57ff2394f7071f",
    ANALYTIC: "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
    RADIAL: "33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca",
    GATE: "1642a5efcc4e2b304271fe3b785d439ce9b1ddb405855f56a7e62a1b4e61e6ac",
    GATE_CHECKER: "552e6e92916c62179f56262f33fddfeda46d65463c7a13edb165892f0c15020b",
    STAGED: "bb00675f722a843c0d87ef36e382aea812d6622c79da517e238b0146af9592dd",
    STAGED_TESTS: "27fabdfa8e4f73820ca70af6189751d2e30acd7f699b580b9cd2cfdb625f10ed",
    STAGED_SPEC: "1a39e72a2d69ab0e64570ed05a9b0ea762b7f4223a4d88205d7a1f525230c721",
    ORACLE: "f97e16231e47d028406a88702631457fb110fe1cf00fcb9a2a4ba71557dbc21c",
    DIRECT: "37b0d249a0fd17e823f154277bfabe162c3b80c72c344c97686312c7fac7e393",
    BENCHMARKS[(0, 17)]: "73f351f24defafc0cb6c0a293d258bac33d504e457771ea11362ff5d67bd9107",
    BENCHMARKS[(5, 15)]: "5603845bf7514a4f6dcb4831ed3854b1915189d39424d9d1b47f2bc6f2cd1901",
    BENCHMARKS[(15, 10)]: "5f4d88417ed0b84d26c52512ddf710b35bd9e7d55e9df4a68ad2114dc3602d29",
    BENCHMARKS[(22, 6)]: "8e023686703d353bb63faad3be541238920bc8b7640a4ba3202b924d0385ace9",
    BENCHMARKS[(25, 5)]: "9c13277024543c51b2c945743ce74c5ebfc5b1d2eb3e21d264740bcf0e35e6df",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def strict_json(path: Path):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate key in {path}: {key}")
            answer[key] = value
        return answer

    return json.loads(
        path.read_bytes(), object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")))


def load_core():
    spec = importlib.util.spec_from_file_location(
        "independent_active25_grouped_core", CORE)
    if spec is None or spec.loader is None:
        raise ImportError(CORE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_staged():
    spec = importlib.util.spec_from_file_location(
        "independent_active25_staged_v2", STAGED)
    if spec is None or spec.loader is None:
        raise ImportError(STAGED)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == STAGED.resolve(),
            "wrong staged wrapper imported")
    return module


def verify_artifacts(core):
    oracle, direct = strict_json(ORACLE), strict_json(DIRECT)
    common = {
        "status": "frontier-inner-D16-tagged-shell-exact-cost-probe",
        "rigorous_values": True,
        "theorem_ready": False,
        "complete_cross": False,
        "script_sha256": PINS[CORE],
        "common_r": 10,
        "selected_h": 10,
    }
    for artifact in (oracle, direct):
        for key, value in common.items():
            require(artifact.get(key) == value,
                    f"representative artifact field changed: {key}")
        require(artifact.get("parameters") == core.parameter_record(),
                "representative parameters changed")
    require(oracle.get("evaluation_mode") ==
            "ungrouped-four-branch-oracle" and
            direct.get("evaluation_mode") == "direct-full-grouped",
            "representative modes changed")
    require(oracle.get("radial_cross_by_target_R") ==
            direct.get("radial_cross_by_target_R"),
            "ungrouped/direct representative values disagree")
    raw = oracle.get("raw_cross_by_pair_and_target_R")
    require(isinstance(raw, dict) and set(raw) == set(core.PAIR_NAMES) and
            all(len(row) == core.K + 1 for row in raw.values()),
            "ungrouped raw pair tables malformed")
    radial = strict_json(RADIAL)
    inner_amp, outer_amp = (Q(x) for x in radial["rational_amplitudes"])
    tables = {tag: [Q(x) for x in row] for tag, row in raw.items()}
    independently_contracted = [
        outer_amp * (tables["rh"][r] - tables["rl"][r]) +
        (inner_amp - outer_amp) *
        (tables["vh"][r] - tables["vl"][r])
        for r in range(core.K + 1)]
    require([str(x) for x in independently_contracted] ==
            oracle["radial_cross_by_target_R"],
            "independent radial pair contraction failed")
    require(sum(x != 0 for x in independently_contracted) == 2,
            "representative target-count support changed")
    return {
        "oracle_direct_exact_equal": True,
        "independent_signed_pair_contraction": True,
        "nonzero_target_entries": 2,
        "ungrouped_domain_products": sum(oracle["domain_counts"].values()),
        "direct_domain_products": sum(direct["domain_counts"].values()),
    }


def verify_low_k(core):
    """Compare ungrouped, grouped, direct, and tagged canonical recurrences."""
    cases = 0
    tag_rows = 0
    for k in (1, 2, 3, 4):
        delta, eta = Q(1, 10), Q(7, 20)
        alpha_r, alpha_v, alpha_h, alpha_l = (
            Q(2, 5), Q(3, 10), Q(9, 20), Q(2, 5))
        schedule = tuple(min(Q(6, 25) + i * Q(7, 100), Q(19, 50))
                         for i in range(k))
        r_support = core.ei.OneStratumSupport(
            k, alpha_r, delta, eta,
            alpha_r, alpha_r, alpha_r)
        v_support = core.ei.OneStratumSupport(
            k, alpha_v, delta, eta,
            alpha_v, alpha_v, alpha_v)
        high = core.shell.ScheduledStratumSupport.make(
            k, alpha_h, eta, delta, schedule)
        low = core.shell.ScheduledStratumSupport.make(
            k, alpha_l, eta, delta, schedule)
        labels = ((0, ()), (1, ()), (0, (1,)), (0, (2,)))
        coefficients = (Q(3, 2), Q(-5, 3), Q(7, 5), Q(-11, 7))
        components = core.outer_core.components(labels, coefficients, k)
        one = (((), 0, 0, Q(1)),)
        named = {"R": (r_support, components),
                 "V": (v_support, components),
                 "H": (high, one), "L": (low, one)}
        catalog = (("rh", "R", "H"), ("rl", "R", "L"),
                   ("vh", "V", "H"), ("vl", "V", "L"))
        weights = {"rh": Q(7, 11), "rl": Q(-7, 11),
                   "vh": Q(-5, 13), "vl": Q(5, 13)}
        literal, counts, faces = core.tagged_cross_catalog(
            named, catalog, eta)
        expected = [sum(weights[tag] * literal[tag][target]
                        for tag in weights)
                    for target in range(k + 1)]
        grouped, grouped_counts, _, _, grouped_faces = \
            core.grouped_weighted_cross(
                named, catalog, weights, eta)
        direct, _, _, _, direct_faces = core.grouped_weighted_cross(
            named, catalog, weights, eta,
            direct_full_left=("R", "V"))
        require(grouped == direct == expected and counts == grouped_counts and
                faces == grouped_faces == direct_faces,
                f"low-k grouped identity failed at k={k}")

        # A separate canonical stratum recurrence checks right-hand target
        # ownership, not merely the aggregate J value.
        same_named = {"P": (high, components), "C": (high, one)}
        tagged, _, _ = core.tagged_cross_catalog(
            same_named, (("pc", "P", "C"),), eta)
        for target in range(k + 1):
            canonical = sum(
                coefficient * sum(
                    high.basis_j_in_strata(
                        left_target, label, target, (0, ()))
                    for left_target in range(k + 1))
                for coefficient, label in zip(coefficients, labels))
            require(tagged["pc"][target] == canonical,
                    f"right-target ownership failed at k={k}, R={target}")
            tag_rows += 1
        cases += 1
    return {"dimensions": [1, 2, 3, 4], "cases": cases,
            "canonical_target_rows": tag_rows,
            "all_exact_equal": True}


def verify_definition5_and_shell(core):
    require(core.ALPHA1 == core.A1 + core.EPSILON and
            core.ETA1 == core.A1 - core.EPSILON and
            core.ALPHA2 == core.A2 + core.EPSILON and
            core.ETA2 == core.A2 - core.EPSILON,
            "Definition-5 band endpoints changed")
    _, _, _, inner_i, inner_kj = core.production_cross_inputs()
    require(inner_i > 0 and inner_kj > 0,
            "inner exact forms are not positive")

    # Capture the three low-level exact tables used by the shell assembler,
    # then reconstruct every sign and the factor k independently.
    captured = []
    original = core.shell.cross_constant_stratum_table

    def recording(left, right, common_eta):
        value = original(left, right, common_eta)
        captured.append(value)
        return value

    core.shell.cross_constant_stratum_table = recording
    try:
        active, masses, k_j, counts = core.shell_i_and_j()
    finally:
        core.shell.cross_constant_stratum_table = original
    require(active == list(range(26)) and len(masses) >= 26 and
            all(masses[r] > 0 for r in active),
            "active shell mass inventory changed")
    require(len(captured) == 3, "shell low-level traversal count changed")
    hh, hl, ll = (item[0] for item in captured)
    for i in range(len(k_j)):
        for j in range(len(k_j)):
            expected = core.K * (hh[i][j] - hl[i][j] - hl[j][i] + ll[i][j])
            require(k_j[i][j] == expected,
                    f"shell Definition-5 sign/factor failed at {i},{j}")
            require(k_j[i][j] == k_j[j][i],
                    "shell numerator is not symmetric")
            if i in active and j in active and abs(i - j) > 1:
                require(k_j[i][j] == 0,
                        "shell numerator is not tridiagonal")
    return {
        "inner_inner_cutoff": str(core.ETA1),
        "mixed_and_shell_cutoff": str(core.ETA2),
        "inner_block_already_kJ": True,
        "inner_shell_cross_is_raw_J_and_requires_one_future_factor_k": True,
        "shell_formula": "k*(HH-HL-HL^T+LL)",
        "k": core.K,
        "active_shell_counts": active,
        "shell_nonzero_entries": sum(x != 0 for row in k_j for x in row),
        "low_level_domain_counts": counts,
    }


def verify_gate(core):
    gate = strict_json(GATE)
    analytic = strict_json(ANALYTIC)
    preflight = core.preflight()
    require(gate.get("format") ==
            "frontier-active25-inner-D16-tagged-shell-prelaunch-gate-v1" and
            gate.get("status") ==
            "PRELAUNCH DISABLED PENDING INDEPENDENT IMPLEMENTATION AUDIT" and
            gate.get("launch_authorized") is False,
            "gate is not fail-closed")
    require(gate.get("arithmetic_core_sha256") == PINS[CORE] and
            gate.get("arithmetic_test_sha256") == PINS[TESTS] and
            gate.get("analytic_audit_sha256") == PINS[ANALYTIC] and
            gate.get("schedule_canonical_sha256") ==
            analytic["parameters"]["outer_schedule_canonical_sha256"],
            "gate provenance changed")
    require(gate.get("oracle_artifact_sha256") == PINS[ORACLE] and
            gate.get("oracle_direct_exact_equal") is True,
            "gate oracle binding changed")
    for field in ("dimension", "cross_face_count",
                  "grouped_geometric_domain_upper"):
        require(gate.get(field) == preflight.get(field),
                f"gate/preflight mismatch: {field}")
    require(gate.get("literal_branch_product_upper") ==
            preflight["cross_domain_count_total"] and
            gate.get("active_outer_counts") == list(range(26)) and
            gate.get("stage_common_r") == list(range(26)),
            "gate count/stage inventory changed")

    rows = gate.get("benchmark_artifacts")
    require(isinstance(rows, list) and len(rows) == len(BENCHMARKS),
            "benchmark gate inventory changed")
    observed_wall, observed_rss = [], []
    for row in rows:
        key = (row.get("common_r"), row.get("h"))
        require(key in BENCHMARKS and row.get("sha256") == PINS[BENCHMARKS[key]],
                "benchmark hash/key changed")
        artifact = strict_json(BENCHMARKS[key])
        require(artifact.get("script_sha256") == PINS[CORE] and
                artifact.get("evaluation_mode") == "direct-full-grouped" and
                artifact.get("common_r") == key[0] and
                artifact.get("selected_h") == key[1] and
                artifact.get("complete_cross") is False and
                artifact.get("parameters") == core.parameter_record(),
                "benchmark artifact schema/provenance changed")
        require(Decimal(str(artifact["wall_seconds"])) ==
                Decimal(row["wall_seconds"]) and
                artifact["peak_rss_kib"] == row["peak_rss_kib"],
                "benchmark measurement transcription changed")
        observed_wall.append(Decimal(row["wall_seconds"]))
        observed_rss.append(row["peak_rss_kib"])
    max_wall, max_rss = max(observed_wall), max(observed_rss)
    projected = max_wall * Decimal(gate["cross_face_count"])
    envelope = projected * Decimal(gate["resource_gate"]["wall_safety_factor"])
    require(Decimal(gate["max_observed_face_wall_seconds"]) == max_wall and
            gate["max_observed_peak_rss_kib"] == max_rss and
            Decimal(gate["projected_one_worker_seconds"]) == projected and
            Decimal(gate["wall_envelope_seconds"]) == envelope and
            gate["rss_envelope_kib"] ==
            max_rss * gate["resource_gate"]["rss_safety_factor"] and
            envelope <= Decimal(gate["resource_gate"]["max_total_wall_seconds"]),
            "resource envelope arithmetic changed")
    require(gate["resource_gate"] == {
        "max_total_wall_seconds": 14400,
        "minimum_mem_available_kib_each_reading": 1400000,
        "required_stable_mem_readings": 2,
        "rss_safety_factor": 4,
        "wall_safety_factor": 3,
        "workers": 1,
    }, "resource policy changed")
    return {
        "face_inventory": gate["cross_face_count"],
        "grouped_domain_upper": gate["grouped_geometric_domain_upper"],
        "wall_envelope_seconds": gate["wall_envelope_seconds"],
        "rss_envelope_kib": gate["rss_envelope_kib"],
        "gate_arithmetic_pass": True,
        "launch_authorized": False,
        "remaining_gate": (
            "a frozen exact-common-r wrapper/validator must enforce the two "
            "live memory readings, one-worker staging, immutable hashes, "
            "complete count set, and exclusive publication"),
    }


def verify_disabled_staged_wrapper(core):
    """Audit the new immutable v2 wrapper without running a target shard."""
    staged = load_staged()
    require(staged.CORE_PATH.resolve() == CORE.resolve() and
            staged.GATE_PATH.resolve() == GATE.resolve() and
            staged.GATE_CHECKER.resolve() == GATE_CHECKER.resolve(),
            "staged dependency paths changed")
    require(staged.PINNED == {
        staged.CORE_PATH: PINS[CORE],
        staged.GATE_PATH: PINS[GATE],
        staged.GATE_CHECKER: PINS[GATE_CHECKER]},
            "staged dependency pins changed")
    require(staged.snapshots() and staged.load_gate()["launch_authorized"] is False,
            "staged wrapper is not pinned to disabled gate")
    try:
        staged.require_authorized()
    except RuntimeError as error:
        require("disabled" in str(error), "unexpected authorization failure")
    else:
        raise ArithmeticError("disabled staged wrapper authorized a target run")
    preflight = staged.preflight()
    require(preflight.get("launch_authorized") is False and
            preflight.get("target_started") is False and
            preflight.get("active_common_r") == list(range(26)) and
            preflight.get("dimension") == 27 and
            preflight.get("driver_sha256") == PINS[STAGED] and
            preflight.get("gate_sha256") == PINS[GATE] and
            preflight.get("arithmetic_core_sha256") == PINS[CORE],
            "staged preflight identity changed")

    def fake(r, value=Q(1)):
        vector = [Q(0)] * (core.K + 1)
        vector[r] = value
        vector[r + 1] = -value / 2
        return {
            "common_r": r, "complete_common_r": True,
            "domain_counts": {tag: 1 for tag in ("rh", "rl", "vh", "vl")},
            "faces": 1, "geometric_group_count": 1,
            "inner_48J": "7/5", "inner_I": "3/2",
            "inner_basis_dimension": 307, "nonzero_group_count": 1,
            "raw_J_cross_by_target_R": [str(x) for x in vector]}

    shards = [fake(r, Q(r + 1)) for r in range(26)]
    forward, identity = staged.merge_exact_shards(shards)
    reverse, reverse_identity = staged.merge_exact_shards(reversed(shards))
    expected = [Q(0)] * (core.K + 1)
    for r in range(26):
        expected[r] += r + 1
        expected[r + 1] -= Q(r + 1, 2)
    require(forward == reverse == expected and identity == reverse_identity ==
            (Q(3, 2), Q(7, 5), 307),
            "deterministic exact shard merge failed")

    hostile = []
    hostile.append(shards[:-1])
    hostile.append(shards + [fake(0)])
    bad = [dict(x) for x in shards]
    escaped = list(bad[3]["raw_J_cross_by_target_R"])
    escaped[10] = "1"
    bad[3]["raw_J_cross_by_target_R"] = escaped
    hostile.append(bad)
    bad = [dict(x) for x in shards]
    bad[4]["inner_I"] = "4/3"
    hostile.append(bad)
    rejected = 0
    for case in hostile:
        try:
            staged.merge_exact_shards(case)
        except ValueError:
            rejected += 1
    require(rejected == len(hostile), "hostile shard mutation was accepted")
    require(sha(STAGED) == PINS[STAGED] and sha(GATE) == PINS[GATE],
            "staged wrapper or gate moved during audit")
    return {
        "v2_wrapper_frozen": True,
        "launch_authorized": False,
        "target_execution_rejected_before_arithmetic": True,
        "active_common_r": list(range(26)),
        "dimension": 27,
        "deterministic_fraction_merge": True,
        "hostile_merge_mutations_rejected": rejected,
        "next_required_revision": (
            "a new versioned authorized gate plus a new wrapper revision "
            "pinning it; both need an independent delta audit, live memory "
            "checks, one-worker enforcement, and an envelope-aware strict "
            "post-run consumer before any shard or quotient is trusted"),
    }


def build():
    observed = {}
    for path, expected in PINS.items():
        actual = sha(path)
        require(actual == expected, f"frozen input changed: {path}: {actual}")
        observed[str(path.relative_to(REPO))] = actual
    core = load_core()
    require(core.require_pins() and core.validate_analytic(),
            "core dependency/analytic closure failed")
    result = {
        "status": "PRELAUNCH PASS FOR FROZEN DISABLED V2; LAUNCH DISABLED",
        "scope": (
            "grouped-domain arithmetic, exact representative oracle, "
            "Definition-5 assembly, and disabled resource-envelope arithmetic; "
            "no full k=48 cross traversal or quotient"),
        "checker_sha256": sha(FILE),
        "pinned": dict(sorted(observed.items())),
        "artifact_checks": verify_artifacts(core),
        "low_k_literal_grouped_checks": verify_low_k(core),
        "definition5_and_shell_checks": verify_definition5_and_shell(core),
        "resource_gate_checks": verify_gate(core),
        "disabled_staged_wrapper_checks": verify_disabled_staged_wrapper(core),
        "decision": (
            "the frozen arithmetic core, resource arithmetic, and disabled "
            "v2 staging scaffold pass; no production is authorized because "
            "the byte-pinned gate is deliberately false"),
    }
    require(sha(CORE) == PINS[CORE] and sha(GATE) == PINS[GATE],
            "core or gate changed during audit")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
