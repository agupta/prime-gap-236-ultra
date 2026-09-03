#!/usr/bin/env python3
"""Independent hostile tests for the frozen full H1<=236 replay driver.

These tests exercise only parsers, process isolation, exact projection
arithmetic, provenance binding, and mutation rejection.  They deliberately do
not launch any target-sized integral and therefore are not a certificate run.
"""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DRIVER = REPO / "verify/check_H1_236.py"
DRIVER_SHA = (
    "99779b2954459f79caa24952ae977dc5d3504bea1be324fbbea7d4308fd04ee3")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load_driver():
    data = DRIVER.read_bytes()
    require(hashlib.sha256(data).hexdigest() == DRIVER_SHA,
            "frozen standalone driver hash changed")
    spec = importlib.util.spec_from_file_location(
        "independent_H1_236_standalone_target", DRIVER)
    if spec is None or spec.loader is None:
        raise ImportError(DRIVER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_driver()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def expect_failure(function, fragment):
    try:
        function()
    except Exception as error:
        require(fragment in str(error),
                f"wrong failure for {fragment!r}: {type(error).__name__}: {error}")
    else:
        raise AssertionError(f"mutation unexpectedly passed: {fragment}")


def exact_fixture(root):
    a_paths, b_paths = [], []
    for count in M.COUNTS:
        a_path = root / f"a{count:02d}.json"
        b_path = root / f"b{count:02d}.json"
        a_path.write_bytes(canonical({
            "count": count,
            "exact_values": {"band_I_count": str(count + 1)},
        }))
        b_path.write_bytes(canonical({
            "common_r": count,
            "scaled_b_shard": str((count + 2) * 10**100),
        }))
        a_paths.append(a_path)
        b_paths.append(b_path)
    inner = {
        "exact_denominator": "10", "exact_numerator": "8",
        "exact_deficit": "2",
    }
    return inner, a_paths, b_paths


def aggregate_fixture(exact, a_values, b_values, a_hashes, b_hashes):
    value = {
        "format": "H1-236-one-band-cached-v7-exact-shard-aggregate-v1",
        "status": "EXACT ONE-BAND SCALAR CERTIFICATE PASS",
        "rigorous": True,
        "theorem_ready_scalar": True,
        "k": 48,
        "counts": list(M.COUNTS),
        "scales": {
            "F": str(M.SCALE_F), "H": str(M.SCALE_H),
            "quadratic_inner": str(M.FORM_SCALE),
        },
        "exact": {key: str(item) for key, item in exact.items()},
        "a_shards": [
            {"count": count, "value": str(item), "sha256": a_hashes[count]}
            for count, item in enumerate(a_values)
        ],
        "b_shards": [
            {"count": count, "value": str(item), "sha256": b_hashes[count]}
            for count, item in enumerate(b_values)
        ],
        "source_hashes": {"test": "0" * 64},
        "trust_scope": "independent synthetic fixture",
        "assembler_sha256": M.PINS[M.ASSEMBLER],
        "base_assembler_sha256": M.BASE_ASSEMBLER_SHA256,
        "b_engine": "cached-fixed-v7",
    }
    return value


def test_pins_and_support_projection():
    for path, expected in M.PINS.items():
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                f"live replay pin mismatch: {path}")
    source_bytes = {
        M.REPO / relative: (M.REPO / relative).read_bytes()
        for relative in M.SUPPORT_SNAPSHOT_PINS
    }
    frozen, _ = M.canonical_object(M.SUPPORT_FROZEN)
    portable = M.deterministic_support_projection(
        frozen, "frozen", source_bytes)
    moved = copy.deepcopy(frozen)
    for index, row in enumerate(moved["snapshots"].values(), 1):
        row["dev"] += 1000 + index
        row["inode"] += 2000 + index
    require(M.deterministic_support_projection(
        moved, "moved", source_bytes) == portable,
        "host identity was not the only stripped support metadata")
    bad = copy.deepcopy(moved)
    first = next(iter(bad["snapshots"].values()))
    first["nlink"] = 2
    expect_failure(lambda: M.deterministic_support_projection(
        bad, "bad-nlink", source_bytes), "metadata malformed")
    bad = copy.deepcopy(moved)
    first = next(iter(bad["snapshots"].values()))
    first["sha256"] = "f" * 64
    expect_failure(lambda: M.deterministic_support_projection(
        bad, "bad-hash", source_bytes), "bytes differ")


def test_process_isolation_and_fail_closed_io():
    with tempfile.TemporaryDirectory(prefix="H1-driver-process-test-") as directory:
        root = Path(directory)
        prefix_path = root / "never-created-cache"
        prefix = M.python_prefix(prefix_path)
        probe = (
            "import json,sys;print(json.dumps({"
            "'dont_write':sys.dont_write_bytecode,"
            "'isolated':sys.flags.isolated,"
            "'ignore_environment':sys.flags.ignore_environment,"
            "'optimize':sys.flags.optimize,"
            "'prefix':sys.pycache_prefix},sort_keys=True))")
        output = M.run_stage(
            "isolation probe", prefix + ["-c", probe], 10)
        result = json.loads(output)
        require(result == {
            "dont_write": True,
            "ignore_environment": 1,
            "isolated": 1,
            "optimize": sys.flags.optimize,
            "prefix": str(prefix_path.resolve()),
        }, "child interpreter isolation differs")
        require(not prefix_path.exists(), "private pycache path was created")

        noisy = prefix + ["-c", "import sys;sys.stderr.write('warning\\n')"]
        expect_failure(lambda: M.run_stage("noise", noisy, 10),
                       "emitted stderr")
        accepted = M.run_stage(
            "explicit progress", noisy, 10,
            stderr_validator=lambda data: data == b"warning\n")
        require(accepted == b"", "accepted progress changed stdout")
        expect_failure(lambda: M.run_stage(
            "rejected progress", noisy, 10,
            stderr_validator=lambda data: data == b"different\n"),
            "malformed progress stderr")
        failing = prefix + ["-c", "raise SystemExit(7)"]
        expect_failure(lambda: M.run_stage("nonzero", failing, 10),
                       "exited 7")
        sleeping = prefix + ["-c", "import time;time.sleep(1)"]
        expect_failure(lambda: M.run_stage("timeout", sleeping, 0.01),
                       "could not complete")


def test_progress_and_count_scheduler():
    for count in M.COUNTS:
        good = (
            f"fast-v2 kernel r={count} {{'a': 1}} seconds=0.001\n"
            f"fast-v2 families r={count} {{'b': {{'c': 2}}}} seconds=12.345\n"
            f"fast-v2 done r={count} seconds=999.999\n").encode("ascii")
        require(M.validate_b_progress(good, count),
                f"valid progress rejected at r={count}")
        require(not M.validate_b_progress(good + b"warning\n", count),
                "extra progress line accepted")
        wrong = (count + 1) % len(M.COUNTS)
        require(not M.validate_b_progress(good, wrong),
                "wrong-count progress accepted")
        require(not M.validate_b_progress(
            good.replace(b"seconds=0.001", b"seconds=nan", 1), count),
            "nonfinite progress time accepted")

    old = M.run_stage
    calls = []
    try:
        def fake_run(name, arguments, timeout, stderr_validator=None):
            count = int(arguments[-1])
            line = f"count={count}".encode("ascii")
            require(stderr_validator is not None and stderr_validator(line),
                    f"validator was not count-local at {count}")
            calls.append(count)
            return line
        M.run_stage = fake_run
        results = M.run_count_jobs(
            "synthetic", 2, lambda count: ["synthetic", str(count)], 1,
            stderr_validator_for_count=lambda count: (
                lambda data: data == f"count={count}".encode("ascii")))
    finally:
        M.run_stage = old
    require(set(calls) == set(M.COUNTS), "scheduler omitted a count")
    require(set(results) == set(M.COUNTS), "scheduler result inventory differs")


def test_exact_projection_and_certificate_mutations():
    with tempfile.TemporaryDirectory(prefix="H1-driver-exact-test-") as directory:
        inner, a_paths, b_paths = exact_fixture(Path(directory))
        (exact, a_values, b_values, a_hashes,
         b_hashes) = M.exact_scalar_reconstruction(inner, a_paths, b_paths)
        a_total = Q(sum(range(1, 14)))
        b_total = Q(sum((count + 2) * 10**100 for count in M.COUNTS))
        i_value = Q(10 * M.FORM_SCALE)
        d_value = Q(2 * M.FORM_SCALE)
        margin = b_total**2 - a_total * d_value
        denominator = a_total * i_value + b_total**2
        independently = {
            "A_scaled": a_total,
            "b_scaled": b_total,
            "I_F_scaled": i_value,
            "D_scaled": d_value,
            "margin_b_squared_minus_A_D": margin,
            "mixing_coefficient_b_over_A": b_total / a_total,
            "normalized_inner_deficit": d_value / i_value,
            "normalized_projected_energy": b_total**2 / (a_total * i_value),
            "quotient_margin_lower_bound": margin / denominator,
            "quotient_lower_bound": Q(1) + margin / denominator,
        }
        require(exact == independently, "exact projection identity differs")
        aggregate = aggregate_fixture(
            exact, a_values, b_values, a_hashes, b_hashes)
        certificate = copy.deepcopy(aggregate)
        # Archived certificate hashes may differ for timing-bearing shards,
        # but they remain canonical lowercase SHA strings.
        for rows in (certificate["a_shards"], certificate["b_shards"]):
            for row in rows:
                row["sha256"] = "f" * 64
        M.compare_certificate(certificate, aggregate, exact, a_values,
                              b_values, a_hashes, b_hashes)

        mutations = []
        bad = copy.deepcopy(certificate)
        bad["k"] = 48.0
        mutations.append((bad, aggregate, "armed k=48"))
        bad = copy.deepcopy(certificate)
        bad["counts"][0] = False
        mutations.append((bad, aggregate, "armed k=48"))
        bad = copy.deepcopy(certificate)
        bad["a_shards"][0]["count"] = 0.0
        mutations.append((bad, aggregate, "exact integer"))
        bad = copy.deepcopy(certificate)
        bad["b_shards"][0]["sha256"] = None
        mutations.append((bad, aggregate, "SHA-256 is malformed"))
        bad = copy.deepcopy(certificate)
        bad["unexpected"] = 1
        mutations.append((bad, aggregate, "schema is not exact"))
        bad = copy.deepcopy(certificate)
        bad["format"] = "H1-236-one-band-fixed-v6-exact-shard-aggregate-v1"
        mutations.append((bad, aggregate, "armed k=48"))
        bad = copy.deepcopy(certificate)
        bad["b_engine"] = "fixed-denominator-v6"
        mutations.append((bad, aggregate, "armed k=48"))
        bad = copy.deepcopy(certificate)
        bad["base_assembler_sha256"] = "0" * 64
        mutations.append((bad, aggregate, "armed k=48"))
        bad_aggregate = copy.deepcopy(aggregate)
        bad_aggregate["a_shards"][3]["sha256"] = "e" * 64
        mutations.append((certificate, bad_aggregate, "SHA-256 differs"))
        bad_aggregate = copy.deepcopy(aggregate)
        bad_aggregate["exact"].pop("quotient_lower_bound")
        mutations.append((certificate, bad_aggregate,
                          "exact-scalar schema differs"))
        for candidate, fresh, fragment in mutations:
            expect_failure(lambda candidate=candidate, fresh=fresh:
                M.compare_certificate(candidate, fresh, exact, a_values,
                                      b_values, a_hashes, b_hashes), fragment)

        # The snapshots returned by reconstruction really are byte hashes,
        # and a subsequent replacement is detected by the driver's binding
        # predicate.
        original = a_paths[0].read_bytes()
        a_paths[0].write_bytes(original + b" ")
        require(a_paths[0].read_bytes() != original,
                "test mutation did not change shard bytes")
        require(hashlib.sha256(a_paths[0].read_bytes()).hexdigest() != a_hashes[0],
                "changed shard retained its bound hash")


def main():
    tests = (
        test_pins_and_support_projection,
        test_process_isolation_and_fail_closed_io,
        test_progress_and_count_scheduler,
        test_exact_projection_and_certificate_mutations,
    )
    for test in tests:
        test()
    print(f"{len(tests)}/{len(tests)} independent standalone-driver suites passed")


if __name__ == "__main__":
    main()
