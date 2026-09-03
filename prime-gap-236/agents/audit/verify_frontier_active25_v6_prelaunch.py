#!/usr/bin/env python3
"""Independent prelaunch audit of the frozen active25 D16 v6 workflow.

This checker never calls ``exact_common_r_shard``, ``child_payload``, the
conditional assembler's ``build_result``, or either production run entry.
All state-machine exercises use explicitly tagged synthetic shards in fresh
temporary directories.  The isolated CLI is invoked only in preflight mode.
"""

from __future__ import annotations

import argparse
import copy
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
HERE = REPO / "agents/small-delta-frontier"
DRIVER = HERE / "frontier_active25_inner_d16_staged_v6.py"
DRIVER_TEST = HERE / "test_frontier_active25_inner_d16_staged_v6.py"
ASSEMBLER = HERE / "assemble_frontier_active25_inner_d16_v6.py"
ASSEMBLER_TEST = HERE / "test_assemble_frontier_active25_inner_d16_v6.py"
GATE = HERE / (
    "results/frontier_active25_innerD16_tagged_shell_authorized_gate_v6.json")
SPEC = HERE / "FRONTIER-ACTIVE25-INNER-D16-STAGED-V6-PRELAUNCH.md"

PINS = {
    DRIVER: "cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e",
    DRIVER_TEST:
        "c5e45fe4a929fba55f29ae96f6e127bd8a680d8fa0ca01ca17dfa70f2b56d6ff",
    ASSEMBLER:
        "4b834f1a87b995a73a86d4e02505ddea599191467eccd69d43eed1d8f85b1356",
    ASSEMBLER_TEST:
        "e6ad2423ce9545e7a3f890b30f4e230bc49f4a15bfea04ed6f8d4340cdeb80ff",
    GATE: "7b37c89dd84b03301e3937c981b7c67ea6ce17e21bfd07a76199430bcfb16b80",
    SPEC: "ed9fd5aacc27308f3dd2827d6517044be18057e937cdb99942420c3a3a1e308a",
}

PREFLIGHT_SHA256 = \
    "be576a376b884a2a821c4feef4c29167aede6772f0f549f0f3206dc7ae57de4b"
INTENDED_PATHS = (
    HERE / "results/frontier_active25_innerD16_v6_attempt_001",
    HERE / (
        "results/frontier_active25_innerD16_v6_attempt_001."
        "root-authorization.json"),
    HERE / "results/frontier_active25_innerD16_v6_conditional_pencil.json",
)
BOOT = "12345678-1234-1234-1234-123456789abc"


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json_bytes(data, name):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key in {name}: {key}")
            result[key] = value
        return result

    return json.loads(
        data, object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            AuditFailure(f"nonfinite JSON in {name}: {token}")))


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    require(specification is not None and specification.loader is not None,
            f"cannot load {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(),
            f"wrong local module loaded for {path}")
    return module


def expect_rejection(function, message):
    try:
        function()
    except Exception:
        return True
    raise AuditFailure(message)


def fake_shard(module, common_r):
    vector = [Q(0)] * (module.v5.v2.core.K + 1)
    vector[common_r] = Q(common_r + 1, 17)
    if common_r + 1 < 26:
        vector[common_r + 1] = -Q(common_r + 1, 31)
    return {
        "common_r": common_r,
        "complete_common_r": True,
        "domain_counts": {tag: 1 for tag in ("rh", "rl", "vh", "vl")},
        "faces": 1,
        "geometric_group_count": 1,
        "inner_48J": "7/5",
        "inner_I": "3/2",
        "inner_basis_dimension": 307,
        "nonzero_group_count": 1,
        "raw_J_cross_by_target_R": [str(value) for value in vector],
    }


class FakeRuntime:
    def __init__(self, module, *, mutation=None, fail_r=None,
                 now=1_000_000_000_000, boot=BOOT,
                 child_nanoseconds=1_000_000_000, memory=1_500_000):
        self.module = module
        self.mutation = mutation
        self.fail_r = fail_r
        self.now = now
        self.boot = boot
        self.child_nanoseconds = child_nanoseconds
        self.memory = memory
        self.children = []

    def monotonic_ns(self):
        return self.now

    def boot_id(self):
        return self.boot

    def mem_available_kib(self):
        return self.memory

    def sleep(self, seconds):
        self.now += int(seconds * 10**9)

    def run_child(self, common_r, timeout_seconds, ledger_row,
                  authorization_row):
        self.children.append((common_r, timeout_seconds))
        self.now += self.child_nanoseconds
        if self.fail_r == common_r:
            raise RuntimeError("synthetic child interruption")
        shard = fake_shard(self.module, common_r)
        if self.mutation is not None:
            self.mutation(shard, common_r)
        child = {
            "arithmetic_core_sha256":
                self.module.v5.v2.PINNED[self.module.v5.v2.CORE_PATH],
            "authorization_binding": authorization_row,
            "dependency_sha256": self.module.dependency_record(),
            "driver_sha256": self.module._SELF["sha256"],
            "format": self.module.runtime_format(
                "frontier-active25-inner-D16-child-arithmetic-v6",
                "synthetic-test"),
            "gate_sha256": self.module.SYNTHETIC_GATE_SHA256,
            "ledger_binding": ledger_row,
            "parameters": self.module.v5.v2.core.parameter_record(),
            "shard": shard,
            "status": "complete",
            "theorem_ready": False,
        }
        return self.module.canonical_json(child)


def verify_static_tuple(driver, assembler):
    for path, expected in PINS.items():
        observed = path.stat()
        require(stat.S_ISREG(observed.st_mode) and observed.st_nlink == 1,
                f"frozen tuple member is not singly linked regular: {path}")
        require(sha256(path) == expected, f"frozen tuple changed: {path}")
    require(driver._SELF["sha256"] == PINS[DRIVER] and
            driver.bind_startup_self(PINS[DRIVER]) == DRIVER.read_bytes(),
            "producer startup source binding failed")
    require(assembler._SELF["sha256"] == PINS[ASSEMBLER] and
            assembler.bind_startup_self(PINS[ASSEMBLER]) ==
            ASSEMBLER.read_bytes(), "assembler startup source binding failed")
    require(assembler.PINNED[assembler.STAGED] == PINS[DRIVER] and
            assembler.PINNED[assembler.STAGED_TEST] == PINS[DRIVER_TEST] and
            assembler.PINNED[assembler.GATE] == PINS[GATE],
            "assembler does not pin the frozen producer tuple")

    dependency_record = driver.dependency_record()
    require(len(dependency_record) == 46,
            "complete transitive dependency inventory is not 46 files")
    for relative, expected in dependency_record.items():
        path = REPO / relative
        require(path.is_file() and sha256(path) == expected,
                f"transitive dependency changed: {relative}")
    transitive = driver.transitive_snapshots()
    require(set(transitive) == {"v5", "v2", "core", "shell"} and
            transitive == driver.transitive_snapshots(),
            "transitive source/data snapshots are incomplete or unstable")
    closure = assembler.closure_snapshot(PINS[ASSEMBLER])
    require(set(closure) == {
                "assembler_self", "assembler_dependencies", "producer_self",
                "producer_dependencies", "transitive_dependencies"} and
            closure["transitive_dependencies"] == transitive and
            closure == assembler.closure_snapshot(PINS[ASSEMBLER]),
            "conditional assembler closure is incomplete or unstable")

    gate = driver.load_gate()
    preflight = driver.preflight()
    require(gate["status"] == "PRELAUNCH_CANDIDATE" and
            gate["launch_authorized"] is False and
            gate["active_outer_counts"] == list(range(26)) and
            gate["stage_common_r"] == list(range(26)) and
            gate["dimension"] == 27 and
            preflight == {
                "abandon_after_interruption": True,
                "active_outer_counts": list(range(26)),
                "dimension": 27,
                "driver_sha256": PINS[DRIVER],
                "gate_sha256": PINS[GATE],
                "launch_authorized_by_gate": False,
                "one_shot_no_resume": True,
                "resource_gate": gate["resource_gate"],
                "status": "frontier-active25-v6-one-shot-preflight",
                "target_started": False,
            }, "disabled gate/preflight identity changed")
    require(gate["resource_gate"] == {
                "max_single_shard_seconds": 600,
                "max_total_wall_seconds": 14400,
                "minimum_mem_available_kib_each_reading": 1400000,
                "minimum_seconds_between_mem_readings": 5,
                "required_stable_mem_readings": 2,
                "rss_safety_factor": 4,
                "wall_safety_factor": 3,
                "workers": 1,
            }, "resource envelope changed")
    require(all(not path.exists() for path in INTENDED_PATHS),
            "an intended v6 target path exists before audit")
    return len(dependency_record)


def run_regressions():
    counts = {}
    targets = (("producer", DRIVER_TEST), ("assembler", ASSEMBLER_TEST))
    for optimized, flags in ((False, []), (True, ["-O"])):
        for label, path in targets:
            relative = str(path.relative_to(REPO))
            completed = subprocess.run(
                [sys.executable, *flags, "-m", "unittest", relative],
                cwd=REPO, capture_output=True, text=True, timeout=30)
            require(completed.returncode == 0 and
                    completed.stdout == "" and
                    completed.stderr.rstrip().endswith("OK"),
                    f"{label} regression failed, optimized={optimized}: "
                    f"{completed.stdout[-500:]}{completed.stderr[-1000:]}")
            match = re.search(r"Ran (\d+) tests?", completed.stderr)
            require(match is not None, "cannot inventory regression count")
            counts[(label, optimized)] = int(match.group(1))
    require(counts == {
                ("producer", False): 14, ("producer", True): 14,
                ("assembler", False): 9, ("assembler", True): 9,
            }, "normal/optimized regression inventory changed")

    outputs = []
    for flags in ([], ["-O"]):
        completed = subprocess.run(
            [sys.executable, *flags, "-I", str(DRIVER), "--preflight-only"],
            cwd=REPO, capture_output=True, timeout=30)
        require(completed.returncode == 0 and completed.stderr == b"",
                "isolated preflight failed")
        outputs.append(completed.stdout)
    require(outputs[0] == outputs[1] and
            hashlib.sha256(outputs[0]).hexdigest() == PREFLIGHT_SHA256,
            "normal/optimized preflight bytes differ")
    return {"producer_each_mode": 14, "assembler_each_mode": 9,
            "preflight_sha256": PREFLIGHT_SHA256}


def validate_complete_synthetic(driver):
    with tempfile.TemporaryDirectory(prefix="active25-v6-audit-complete-") as raw:
        record = Path(raw)
        runtime = FakeRuntime(driver)
        ledger_created = driver._initialize_test_only(record, runtime)
        result = driver._run_test_only(
            record, runtime, driver.ledger_binding(ledger_created))
        require(result["one_shot_complete"] is True and
                [row[0] for row in runtime.children] == list(range(26)) and
                set(os.listdir(record)) == set(driver.ALLOWED_LEAVES),
                "synthetic one-shot did not publish the exact inventory")

        handle = driver.v5.open_record_dir(record)
        try:
            ledger_snap = driver.v5.read_leaf(handle, driver.LEDGER_LEAF)
            ledger = driver._parse_ledger(
                handle, ledger_snap, "synthetic-test", driver._SELF["sha256"],
                driver.SYNTHETIC_AUTHORIZATION)
            manifest_snap = driver.v5.read_leaf(handle, driver.MANIFEST_LEAF)
            manifest = strict_json_bytes(manifest_snap["data"], "manifest")
            driver.strict_manifest(
                manifest, handle, ledger, ledger_snap, "synthetic-test",
                driver._SELF["sha256"], driver.SYNTHETIC_AUTHORIZATION,
                runtime.now)
            require(len(manifest["stages"]) == 26 and
                    [row["common_r"] for row in manifest["stages"]] ==
                    list(range(26)) and
                    [row["leaf"] for row in manifest["stages"]] ==
                    list(driver.STAGE_LEAVES),
                    "manifest does not inventory common counts 0 through 25")
            snapshots = [ledger_snap]
            previous_end = ledger["start_monotonic_ns"]
            cumulative = 0
            for common_r, row in enumerate(manifest["stages"]):
                snap = driver.v5.read_leaf(handle, row["leaf"])
                stage = driver.parse_stage_bytes(
                    snap["data"], common_r, ledger,
                    driver.ledger_binding(ledger_snap), "synthetic-test",
                    driver._SELF["sha256"],
                    driver.SYNTHETIC_AUTHORIZATION, runtime.now)
                resource = stage["resource_observation"]
                interval = stage["supervised_child_interval"]
                require(previous_end <=
                        resource["first"]["before_monotonic_ns"] <=
                        resource["first"]["after_monotonic_ns"] <=
                        resource["second"]["before_monotonic_ns"] <=
                        resource["second"]["after_monotonic_ns"] <=
                        interval["start_monotonic_ns"] <
                        interval["end_monotonic_ns"] <=
                        manifest["final_monotonic_ns"] <= runtime.now and
                        resource["second"]["before_monotonic_ns"] -
                        resource["first"]["after_monotonic_ns"] >=
                        5 * 10**9 and
                        all(resource[key]["mem_available_kib"] >= 1_400_000
                            for key in ("first", "second")),
                        "global resource/child timeline is not monotone")
                cumulative += stage["supervised_child_nanoseconds"]
                previous_end = interval["end_monotonic_ns"]
                snapshots.append(snap)
            snapshots.append(manifest_snap)
            require(cumulative ==
                    manifest["cumulative_supervised_child_nanoseconds"] and
                    manifest["elapsed_monotonic_nanoseconds"] ==
                    manifest["final_monotonic_ns"] -
                    ledger["start_monotonic_ns"] and
                    len({(row["device"], row["inode"])
                         for row in snapshots}) == 28,
                    "time accounting or 28-inode inventory failed")

            future = copy.deepcopy(manifest)
            future["final_monotonic_ns"] = runtime.now + 1
            future["elapsed_monotonic_nanoseconds"] = (
                future["final_monotonic_ns"] - ledger["start_monotonic_ns"])
            expect_rejection(
                lambda: driver.strict_manifest(
                    future, handle, ledger, ledger_snap, "synthetic-test",
                    driver._SELF["sha256"],
                    driver.SYNTHETIC_AUTHORIZATION, runtime.now),
                "future-dated manifest was accepted")
            bad_merge = copy.deepcopy(manifest)
            bad_merge["merged_raw_J_cross_by_target_R"][0] = "999"
            expect_rejection(
                lambda: driver.strict_manifest(
                    bad_merge, handle, ledger, ledger_snap, "synthetic-test",
                    driver._SELF["sha256"],
                    driver.SYNTHETIC_AUTHORIZATION, runtime.now),
                "false exact merged vector was accepted")
        finally:
            driver.v5.close_record_dir(handle)

        before = len(runtime.children)
        expect_rejection(
            lambda: driver._run_test_only(
                record, runtime, driver.ledger_binding(ledger_created)),
            "completed attempt was resumable")
        require(len(runtime.children) == before,
                "resume rejection occurred after arithmetic dispatch")
    return True


def verify_abandonment_and_anchors(driver):
    with tempfile.TemporaryDirectory(prefix="active25-v6-audit-nonempty-") as raw:
        record = Path(raw)
        (record / "intruder").write_text("x")
        runtime = FakeRuntime(driver)
        expect_rejection(
            lambda: driver._initialize_test_only(record, runtime),
            "nonempty attempt directory initialized")
        require(runtime.children == [] and
                not (record / driver.LEDGER_LEAF).exists(),
                "nonempty-directory rejection changed state")

    with tempfile.TemporaryDirectory(prefix="active25-v6-audit-prefix-") as raw:
        record = Path(raw)
        runtime = FakeRuntime(driver)
        ledger = driver._initialize_test_only(record, runtime)
        (record / driver.STAGE_LEAVES[0]).write_text("{}\n")
        expect_rejection(
            lambda: driver._run_test_only(
                record, runtime, driver.ledger_binding(ledger)),
            "fabricated stage prefix was accepted")
        require(runtime.children == [],
                "fabricated-prefix rejection dispatched arithmetic")

    with tempfile.TemporaryDirectory(prefix="active25-v6-audit-interrupt-") as raw:
        record = Path(raw)
        runtime = FakeRuntime(driver, fail_r=1)
        ledger = driver._initialize_test_only(record, runtime)
        expect_rejection(
            lambda: driver._run_test_only(
                record, runtime, driver.ledger_binding(ledger)),
            "synthetic interruption was accepted")
        require(set(os.listdir(record)) == {
                    driver.LEDGER_LEAF, driver.STAGE_LEAVES[0]} and
                not (record / driver.MANIFEST_LEAF).exists(),
                "interruption published a wrong prefix or manifest")
        runtime.fail_r = None
        before = len(runtime.children)
        expect_rejection(
            lambda: driver._run_test_only(
                record, runtime, driver.ledger_binding(ledger)),
            "interrupted attempt resumed")
        require(len(runtime.children) == before,
                "abandoned-attempt rejection dispatched arithmetic")

    with tempfile.TemporaryDirectory(prefix="active25-v6-audit-anchor-") as raw:
        record = Path(raw)
        runtime = FakeRuntime(driver)
        ledger = driver._initialize_test_only(record, runtime)
        wrong = driver.ledger_binding(ledger)
        wrong["sha256"] = "f" * 64
        expect_rejection(
            lambda: driver._run_test_only(record, runtime, wrong),
            "wrong external ledger SHA was accepted")
        require(runtime.children == [],
                "wrong-ledger rejection dispatched arithmetic")
        external = record.parent / (record.name + ".ledger-hardlink")
        os.link(record / driver.LEDGER_LEAF, external)
        expect_rejection(
            lambda: driver._run_test_only(
                record, runtime, driver.ledger_binding(ledger)),
            "hardlinked ledger was accepted")

    with tempfile.TemporaryDirectory(prefix="active25-v6-audit-clock-") as raw:
        runtime = FakeRuntime(driver)
        ledger = driver._initialize_test_only(raw, runtime)
        runtime.boot = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        expect_rejection(
            lambda: driver._run_test_only(raw, runtime,
                                          driver.ledger_binding(ledger)),
            "wrong boot ID was accepted")
    with tempfile.TemporaryDirectory(prefix="active25-v6-audit-memory-") as raw:
        runtime = FakeRuntime(driver, memory=1_399_999)
        ledger = driver._initialize_test_only(raw, runtime)
        expect_rejection(
            lambda: driver._run_test_only(raw, runtime,
                                          driver.ledger_binding(ledger)),
            "subthreshold memory readings were accepted")
        require(runtime.children == [], "low-memory gate dispatched arithmetic")
    with tempfile.TemporaryDirectory(prefix="active25-v6-audit-timeout-") as raw:
        runtime = FakeRuntime(driver, child_nanoseconds=601 * 10**9)
        ledger = driver._initialize_test_only(raw, runtime)
        expect_rejection(
            lambda: driver._run_test_only(raw, runtime,
                                          driver.ledger_binding(ledger)),
            "overlong child interval was accepted")
        require(not (Path(raw) / driver.STAGE_LEAVES[0]).exists(),
                "overlong child interval published a stage")
    return True


def verify_malformed_shards(driver):
    def tail(shard, common_r):
        if common_r == 25:
            shard["raw_J_cross_by_target_R"][26] = "1"

    def dimension(shard, common_r):
        if common_r == 0:
            shard["inner_basis_dimension"] = 306

    def nonpositive_i(shard, common_r):
        if common_r == 0:
            shard["inner_I"] = "-1"

    def noncanonical(shard, common_r):
        if common_r == 0:
            shard["inner_48J"] = "07/5"

    def off_support(shard, common_r):
        if common_r == 0:
            shard["raw_J_cross_by_target_R"][2] = "1"

    def wrong_r(shard, common_r):
        if common_r == 0:
            shard["common_r"] = 1

    def extra_key(shard, common_r):
        if common_r == 0:
            shard["extra"] = 0

    def inconsistent_inner(shard, common_r):
        if common_r == 1:
            shard["inner_48J"] = "9/5"

    cases = {
        "inactive_count_26_tail": tail,
        "wrong_D16_dimension": dimension,
        "nonpositive_inner_I": nonpositive_i,
        "noncanonical_fraction": noncanonical,
        "off_support_target": off_support,
        "wrong_common_r": wrong_r,
        "extra_shard_key": extra_key,
        "inconsistent_inner_identity": inconsistent_inner,
    }
    child_counts = {}
    for name, mutation in cases.items():
        with tempfile.TemporaryDirectory(
                prefix=f"active25-v6-audit-{name}-") as raw:
            runtime = FakeRuntime(driver, mutation=mutation)
            ledger = driver._initialize_test_only(raw, runtime)
            expect_rejection(
                lambda: driver._run_test_only(
                    raw, runtime, driver.ledger_binding(ledger)),
                f"malformed mathematical record accepted: {name}")
            require(not (Path(raw) / driver.MANIFEST_LEAF).exists(),
                    f"malformed record published manifest: {name}")
            child_counts[name] = len(runtime.children)
    require(child_counts["inactive_count_26_tail"] == 26 and
            child_counts["wrong_D16_dimension"] == 1 and
            child_counts["nonpositive_inner_I"] == 1,
            "hostile fixtures did not reach their intended validation gates")
    return sorted(cases)


def fake_conditional_result(assembler):
    driver = assembler.staged
    a_diag = [Q(1)] * 27
    matrix = [[Q(0) for _ in range(27)] for _ in range(27)]
    matrix[0][0] = Q(2)
    vector = [Q(1)] + [Q(0)] * 26
    solves = [{
        "eigenvalue": "2", "jacobi_rotations": 0,
        "precision": precision, "rayleigh_quotient": "2",
        "relative_residual_bound": "0",
        "vector": ["1"] + ["0"] * 26,
    } for precision in (100, 160)]
    ledger = {"leaf": driver.LEDGER_LEAF, "sha256": "1" * 64,
              "device": 7, "inode": 10}
    return {
        "48J_matrix": [[str(value) for value in row] for row in matrix],
        "I_diagonal": [str(value) for value in a_diag],
        "assembler_sha256": assembler._SELF["sha256"],
        "authorization_binding": {
            "path": "/tmp/root-authorization.json", "sha256": "3" * 64,
            "device": 7, "inode": 12},
        "complete_manifest_binding": {
            "path": "/tmp/records/manifest.json", "sha256": "2" * 64,
            "device": 7, "inode": 11},
        "dependency_sha256": assembler.dependency_record(),
        "dimension": 27,
        "eigenvalue_optimality_rigorous": False,
        "exact_margin": "1", "exact_quotient": "2",
        "exact_rational_denominator": "1",
        "exact_rational_numerator": "2",
        "finite_space_crosses_one": True,
        "format": "frontier-active25-inner-D16-conditional-pencil-v6",
        "independent_arithmetic_reconstruction": False,
        "ledger_binding": {
            "path": "/tmp/records/ledger.json", "sha256": ledger["sha256"],
            "device": ledger["device"], "inode": ledger["inode"]},
        "parameters": driver.v5.v2.core.parameter_record(),
        "precision_discovery": solves,
        "producer_driver_sha256": PINS[DRIVER],
        "rational_denominator_limit": 10**18,
        "rational_vector": [str(value) for value in vector],
        "serialized_stage_arithmetic_conditional": True,
        "shell_domain_counts": {"hh": 1, "hl": 2, "ll": 3},
        "stage_bindings": [
            {"leaf": driver.STAGE_LEAVES[r], "sha256": f"{r + 20:064x}",
             "device": 7, "inode": 100 + r} for r in range(26)],
        "status": "CONDITIONAL_DISCOVERY_ONLY",
        "theorem_ready": False,
        "two_precision_gate": {
            "precisions": [100, 160],
            "quotient_absolute_tolerance": "1e-70",
            "relative_residual_maximum": "1e-70",
        },
    }, ledger


def verify_conditional_assembler(assembler):
    value, ledger = fake_conditional_result(assembler)
    require(assembler.strict_result(value, "2" * 64, ledger, "3" * 64),
            "well-formed conditional exact result was rejected")
    mutations = {
        "forged_exact_margin": lambda row: row.update(exact_margin="2"),
        "wrong_factor_48_entry":
            lambda row: row["48J_matrix"][0].__setitem__(0, "96"),
        "theorem_ready_upgrade": lambda row: row.update(theorem_ready=True),
        "independent_reconstruction_upgrade":
            lambda row: row.update(independent_arithmetic_reconstruction=True),
        "duplicate_stage_inode":
            lambda row: row["stage_bindings"][1].update(
                inode=row["stage_bindings"][0]["inode"]),
    }
    for name, mutation in mutations.items():
        hostile = copy.deepcopy(value)
        mutation(hostile)
        expect_rejection(
            lambda hostile=hostile: assembler.strict_result(
                hostile, "2" * 64, ledger, "3" * 64),
            f"conditional assembler accepted {name}")
    expect_rejection(
        lambda: assembler._direct_cli_identity(PINS[ASSEMBLER]),
        "imported assembler obtained production capability")
    return sorted(mutations)


def build():
    for path, expected in PINS.items():
        require(sha256(path) == expected, f"frozen v6 input changed: {path}")
    require(all(not path.exists() for path in INTENDED_PATHS),
            "intended target path exists before independent audit")
    driver = load_module("independent_active25_v6_driver", DRIVER)
    assembler = load_module("independent_active25_v6_assembler", ASSEMBLER)
    closure_count = verify_static_tuple(driver, assembler)
    regressions = run_regressions()
    validate_complete_synthetic(driver)
    verify_abandonment_and_anchors(driver)
    malformed = verify_malformed_shards(driver)
    assembler_mutations = verify_conditional_assembler(assembler)
    for path, expected in PINS.items():
        require(sha256(path) == expected, f"v6 input moved during audit: {path}")
    require(all(not path.exists() for path in INTENDED_PATHS),
            "audit created or changed an intended target path")
    return {
        "status": "PRELAUNCH PASS",
        "scope": (
            "frozen active25 inner-D16 v6 one-shot producer and conditional "
            "assembler only; no target shard arithmetic certified"),
        "checker_sha256": sha256(FILE),
        "frozen_tuple": {
            str(path.relative_to(REPO)): expected
            for path, expected in PINS.items()
        },
        "checks": {
            "complete_transitive_dependency_files": closure_count,
            "normal_and_optimized_regressions": regressions,
            "synthetic_exact_stage_count": 26,
            "synthetic_dynamic_regular_inode_count": 28,
            "fresh_empty_directory_required": True,
            "resume_and_prefix_reuse_rejected_before_dispatch": True,
            "interrupted_attempt_permanently_abandoned": True,
            "external_ledger_sha_device_inode_required": True,
            "authorization_and_startup_source_rebinding": True,
            "monotonic_resource_and_child_intervals": True,
            "global_and_per_child_deadlines": True,
            "malformed_shard_cases_rejected": malformed,
            "conditional_result_mutations_rejected": assembler_mutations,
            "factor_48_applied_once_by_conditional_assembler": True,
            "target_integrations_executed": 0,
            "intended_target_paths_untouched": True,
        },
        "decision": (
            "eligible for a later explicit root authorization of exactly one "
            "fresh, no-resume attempt; staged arithmetic remains conditional "
            "until the separate one-shot independent reconstruction"),
        "launch_authorized_by_frozen_gate": False,
        "independent_arithmetic_reconstruction": False,
        "theorem_ready": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
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
