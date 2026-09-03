#!/usr/bin/env python3
"""Independent scoped tests for the cached-v7 scalar assembler wrapper."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "verify/assemble_one_band_236_cached_v7.py"
SOURCE_SHA = (
    "08fb7e612f37050a21bc94d27e4b8ed0ad1838f64ce5e2a147d15aef9f076f05")
V7_FIXTURE_SOURCE = HERE / "test_verify_cached_v7_cross_shard.py"
V6_FIXTURE_SOURCE = HERE / "test_verify_fixed_v6_cross_shard.py"
FIXTURE_PINS = {
    V7_FIXTURE_SOURCE:
        "669ab6178848201927a42c36c9271a27c119f67038606873ca9924a2883db186",
    V6_FIXTURE_SOURCE:
        "3f7eb92c2f14923740f3eb6454eca354793420a7d033d83b5cda7a63438fb887",
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


require(hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA,
        "cached-v7 assembler source changed")
for _path, _expected in FIXTURE_PINS.items():
    require(hashlib.sha256(_path.read_bytes()).hexdigest() == _expected,
            f"cached-v7 assembler fixture changed: {_path}")
M = load("independent_cached_v7_assembler", SOURCE)
T7 = load("independent_cached_v7_conversion", V7_FIXTURE_SOURCE)
T6 = load("independent_cached_v7_v6_fixture", V6_FIXTURE_SOURCE)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def fixture():
    return T7.to_v7(M.V7, T6.synthetic_r0(M.V7.V6))


def expect_failure(function, fragment):
    try:
        function()
    except Exception as error:
        require(fragment in str(error),
                f"wrong failure for {fragment!r}: {type(error).__name__}: {error}")
    else:
        raise AssertionError(f"mutation unexpectedly passed: {fragment}")


def test_pin_union_and_exact_snapshot_parser():
    require(M.V6_ASSEMBLER in M.PINS and M.V7_CHECKER in M.PINS and
            M.V7_RUNNER in M.PINS and M.V7_BACKEND in M.PINS and
            M.V7_TEST in M.PINS, "direct v7 closure absent from pin union")
    runtime_checkers = {
        M.V7.V6_CHECKER_PATH: M.V7.V6_CHECKER_SHA,
        M.V7.V6.V5_CHECKER_PATH: M.V7.V6.V5_CHECKER_SHA,
        M.V7.V6.V5.BASE_AUDITOR_PATH: M.V7.V6.V5.BASE_AUDITOR_SHA,
    }
    for path, expected in runtime_checkers.items():
        require(M.PINS.get(path) == expected,
                f"transitive runtime checker missing from flat closure: {path}")
    for relative, expected in M.V7.SOURCE_HASHES.items():
        require(M.PINS[M.REPO / relative] == expected,
                f"recursive v7 source missing: {relative}")
    for path, expected in M.PINS.items():
        require(M.sha256(path) == expected, f"live pin mismatch: {path}")

    raw = fixture()
    original = canonical(raw)
    with tempfile.TemporaryDirectory(prefix="v7-assembler-snapshot-") as directory:
        path = Path(directory) / "common_r_00.json"
        path.write_bytes(original)
        supplied = path.read_bytes()
        # Change the named file after taking the byte snapshot.  The parser
        # must audit the supplied immutable bytes, not reopen this path.
        path.write_bytes(b"{}\n")
        value = M.parse_b_shard(path, supplied, 0)
        require(str(value) == raw["scaled_b_shard"],
                "snapshot parser did not return exact audited value")

    mutant = copy.deepcopy(raw)
    mutant["scaled_b_shard"] = "0"
    expect_failure(lambda: M.parse_b_shard(
        Path("mutant.json"), canonical(mutant), 0), "factor 48")
    mutant = copy.deepcopy(raw)
    mutant["common_r"] = 0.0
    expect_failure(lambda: M.parse_b_shard(
        Path("mutant.json"), canonical(mutant), 0), "common_r")
    mutant = copy.deepcopy(raw)
    mutant["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["cached_delta_scale_tables"] = 0
    expect_failure(lambda: M.parse_b_shard(
        Path("mutant.json"), canonical(mutant), 0), "cache inventory")
    expect_failure(lambda: M.parse_b_shard(
        Path("mutant.json"), original.replace(b"\n", b" \n"), 0),
        "noncanonical JSON")


def test_complete_file_inventory():
    with tempfile.TemporaryDirectory(prefix="v7-assembler-inventory-") as directory:
        root = Path(directory)
        for count in M.V6.B.COUNTS:
            (root / f"common_r_{count:02d}.json").write_bytes(b"{}\n")
        paths = M.V6.B.require_exact_files(root, "common_r_")
        require(len(paths) == 13, "complete shard set was not returned")
        extra = root / "common_r_13.json"
        extra.write_bytes(b"{}\n")
        expect_failure(lambda: M.V6.B.require_exact_files(root, "common_r_"),
                       "noncanonical shard set")
        extra.unlink()
        missing = root / "common_r_12.json"
        missing.unlink()
        expect_failure(lambda: M.V6.B.require_exact_files(root, "common_r_"),
                       "noncanonical shard set")


def test_main_snapshot_passage_and_monkeypatch_restoration():
    original_parser = M.V6.B.parse_b_shard
    original_build = M.V6.B.build
    observed = {}
    try:
        def fake_build(a_dir, b_dir, snapshots):
            observed["parser"] = M.V6.B.parse_b_shard
            observed["keys"] = set(snapshots)
            observed["bytes"] = dict(snapshots)
            return {"theorem_ready_scalar": False}
        M.V6.B.build = fake_build
        with tempfile.TemporaryDirectory(prefix="v7-assembler-main-") as directory:
            root = Path(directory)
            output = root / "aggregate.json"
            code = M.main([
                "--a-dir", str(root / "unused-A"),
                "--b-dir", str(root / "unused-b"),
                "--output", str(output),
                "--expected-self-sha256", SOURCE_SHA,
            ])
            require(code == 1, "synthetic non-theorem aggregate exit differs")
            result = M.V6.B.strict_json(output.read_bytes(), str(output))
            require(result["format"] ==
                    "H1-236-one-band-cached-v7-exact-shard-aggregate-v1" and
                    result["b_engine"] == "cached-fixed-v7" and
                    result["assembler_sha256"] == SOURCE_SHA and
                    result["base_assembler_sha256"] == M.V6_ASSEMBLER_SHA256,
                    "v7 aggregate identity fields differ")
            require(result["source_hashes"] == {
                str(path.relative_to(M.REPO)): expected
                for path, expected in M.PINS.items()},
                "aggregate source closure differs")
    finally:
        M.V6.B.build = original_build
    require(M.V6.B.parse_b_shard is original_parser,
            "b parser was not restored after successful build")
    require(observed.get("parser") is M.parse_b_shard,
            "v7 parser was not installed during build")
    require(observed.get("keys") == set(M.PINS),
            "base build did not receive the complete pin snapshots")
    require(all(observed["bytes"][path] == path.read_bytes()
                for path in M.PINS),
            "base build snapshot bytes differ from frozen sources")

    try:
        def failing_build(a_dir, b_dir, snapshots):
            require(M.V6.B.parse_b_shard is M.parse_b_shard,
                    "v7 parser absent on failure path")
            raise RuntimeError("injected build failure")
        M.V6.B.build = failing_build
        with tempfile.TemporaryDirectory(prefix="v7-assembler-failure-") as directory:
            root = Path(directory)
            expect_failure(lambda: M.main([
                "--a-dir", str(root / "unused-A"),
                "--b-dir", str(root / "unused-b"),
                "--output", str(root / "never.json"),
                "--expected-self-sha256", SOURCE_SHA,
            ]), "injected build failure")
    finally:
        M.V6.B.build = original_build
    require(M.V6.B.parse_b_shard is original_parser,
            "b parser was not restored after failed build")


def main():
    tests = (
        test_pin_union_and_exact_snapshot_parser,
        test_complete_file_inventory,
        test_main_snapshot_passage_and_monkeypatch_restoration,
    )
    for test in tests:
        test()
    print(f"{len(tests)}/{len(tests)} independent cached-v7 assembler suites passed")


if __name__ == "__main__":
    main()
