#!/usr/bin/env python3
"""Pin-bound counterexample to the v3 cumulative 4-hour wall claim.

No real target integration is performed.  A deterministic fake clock and
synthetic exact shards show that a timed-out invocation can leave resumable
work and a later invocation can publish a successful manifest whose recorded
wall time excludes the earlier invocation entirely.
"""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
STAGED = REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_staged_v3.py"
STAGED_TEST = REPO / "agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v3.py"
ASSEMBLER = REPO / "agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v3.py"
ASSEMBLER_TEST = REPO / "agents/small-delta-frontier/test_assemble_frontier_active25_inner_d16_v3.py"
GATE = REPO / "agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_authorized_gate_v3.json"
SPEC = REPO / "agents/small-delta-frontier/FRONTIER-ACTIVE25-INNER-D16-STAGED-V3-PRELAUNCH.md"
PINS = {
    STAGED: "79cbeb74b994e8d6bdd5f16e7d0f7d11aa148d6f9d6d4f32a12932854d62efd8",
    STAGED_TEST: "ab74ac22409f58e3bc7c3ae5a8c50a05c482c47cea69f6f30493adbeaa864e73",
    ASSEMBLER: "c48feddb0cfd1a70ab7140813f4cf0037ae6f21374c229a38089198404079788",
    ASSEMBLER_TEST: "f69f4dac10b610a5a08ec792b7e6bb4c74c4199d0edab78492dadd9703f8aa19",
    GATE: "19ab3d54c08fbd24d6b70ea9d946ca7272030bf20716da383f4bed285de411bb",
    SPEC: "9649807e7dfb9111a188ae87b52b59ef0b3d3dab7b7ed20a0492bf8c2082c754",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_staged():
    spec = importlib.util.spec_from_file_location(
        "hostile_active25_v3_resume_wall", STAGED)
    if spec is None or spec.loader is None:
        raise ImportError(STAGED)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fake_shard(module, r):
    vector = [Q(0)] * (module.v2.core.K + 1)
    vector[r] = Q(r + 1)
    vector[r + 1] = -Q(r + 1, 2)
    return {
        "common_r": r, "complete_common_r": True,
        "domain_counts": {tag: 1 for tag in ("rh", "rl", "vh", "vl")},
        "faces": 1, "geometric_group_count": 1,
        "inner_48J": "7/5", "inner_I": "3/2",
        "inner_basis_dimension": 307, "nonzero_group_count": 1,
        "raw_J_cross_by_target_R": [str(x) for x in vector],
    }


def fake_stage(module, r):
    return {
        "arithmetic_core_sha256": module.v2.PINNED[module.v2.CORE_PATH],
        "complete_common_r": True,
        "dependency_sha256": module.dependency_record(),
        "driver_sha256": module.sha256(module.FILE),
        "format": "frontier-active25-inner-D16-common-r-stage-v3",
        "gate_sha256": module.PINNED[module.GATE],
        "parameters": module.v2.core.parameter_record(),
        "peak_rss_kib": 1, "shard": fake_shard(module, r),
        "status": "complete", "theorem_ready": False,
        "wall_nanoseconds": 1,
    }


class Clock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


def main() -> int:
    for path, expected in PINS.items():
        require(sha(path) == expected, f"frozen v3 input changed: {path}")
    module = load_staged()
    limit_ns = module.load_gate()["resource_gate"][
        "max_total_wall_seconds"] * 10**9
    original_clock = module.time.monotonic_ns
    with tempfile.TemporaryDirectory() as directory:
        # Invocation one spends more than the complete authorized budget.  It
        # is rejected only after publishing one otherwise valid shard.
        module.time.monotonic_ns = Clock((0, limit_ns + 1))
        try:
            module.run_all(
                directory, stage_builder=lambda r: fake_stage(module, r),
                mem_reader=lambda: 2_000_000, sleeper=lambda _: None)
        except RuntimeError as error:
            require("wall gate" in str(error), "wrong first-run failure")
        else:
            raise AssertionError("over-budget first invocation was accepted")
        leaves_after_timeout = sorted(Path(directory).iterdir())
        require([path.name for path in leaves_after_timeout] ==
                [module.STAGE_LEAVES[0]],
                "timed-out invocation did not preserve one resumable shard")

        # A fresh process would receive a fresh monotonic origin.  Model that
        # reset and let the remaining 25 stages finish in 27 ns.  The v3 code
        # accepts and publishes a complete manifest despite aggregate elapsed
        # time already being strictly greater than four hours.
        module.time.monotonic_ns = Clock(range(28))
        completed = module.run_all(
            directory, stage_builder=lambda r: fake_stage(module, r),
            mem_reader=lambda: 2_000_000, sleeper=lambda _: None)
        require(completed["resumed_complete"] is False,
                "second invocation did not publish manifest")
        handle = module.open_record_dir(directory)
        try:
            snapshot = module.read_leaf(handle, module.MANIFEST_LEAF)
            manifest = json.loads(snapshot["data"])
            module.strict_manifest(manifest, handle, snapshot["sha256"])
        finally:
            module.close_record_dir(handle)
        require(manifest["wall_nanoseconds"] == 27 and
                len(manifest["stages"]) == 26,
                "counterexample manifest shape changed")
    module.time.monotonic_ns = original_clock

    # A separate race/integrity counterexample: directory membership is
    # checked only before traversal.  An extra leaf created after that scan is
    # neither rejected before manifest publication nor by strict_manifest.
    with tempfile.TemporaryDirectory() as directory:
        injected = [False]

        def stage_with_extra_leaf(r):
            if not injected[0]:
                (Path(directory) / "unauthorized-after-initial-scan").write_bytes(
                    b"not part of the manifest\n")
                injected[0] = True
            return fake_stage(module, r)

        accepted = module.run_all(
            directory, stage_builder=stage_with_extra_leaf,
            mem_reader=lambda: 2_000_000, sleeper=lambda _: None)
        require(accepted["resumed_complete"] is False and
                (Path(directory) / "unauthorized-after-initial-scan").is_file() and
                (Path(directory) / module.MANIFEST_LEAF).is_file(),
                "post-scan extra-leaf counterexample was unexpectedly closed")
    print(json.dumps({
        "status": "PRELAUNCH AUDIT FAIL",
        "counterexample": "four-hour budget resets across resumptions",
        "first_invocation_elapsed_ns": limit_ns + 1,
        "accepted_manifest_elapsed_ns": 27,
        "successful_manifest_after_aggregate_over_budget": True,
        "unauthorized_leaf_added_after_initial_scan_and_manifest_accepted": True,
        "injected_memory_values_and_zero_delay_are_manifest_indistinguishable": True,
        "real_target_integration_run": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
