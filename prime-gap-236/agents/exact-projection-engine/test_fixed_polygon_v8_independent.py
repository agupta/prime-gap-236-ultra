#!/usr/bin/env python3
"""Independent hostile tests for the fixed-polygon-v8 exact engine.

This file is deliberately not imported by the producer.  It compares the
new integer numerator formula with the pre-existing Fraction triangle oracle
on every exact target polygon and exercises the repaired runtime monkeypatch
without launching a theorem-size radial calculation.
"""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
import math
from pathlib import Path
import random
import sys
import tempfile
import time


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CORE = HERE / "fixed_polygon_moments.py"
RUNNER = HERE / "d14_grid38_scaled_b_shard_fixed_polygon_v8.py"
REFERENCE = REPO / "verify/exact_capped_certificate.py"
ENGINE = HERE / "symmetric_cutoff_cross.py"
EXPECTED = {
    CORE: "4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb",
    RUNNER: "36a8e027c83cabb272aa28a5d542dc571793cbcf90c5ca48787bc20092a55b72",
    REFERENCE: "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    ENGINE: "d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726",
}

K = 48
DELTA = Q(1, 60)
ALPHA1 = Q(103, 400)
ALPHA2 = Q(9500917, 36000000)
ETA = Q(8960917, 36000000)
SCHEDULE = tuple(map(Q, (
    "1123/8000", "157041/1000000", "5267/31250",
    "87169/500000", "11593/62500", "1523/8000",
    "193097/1000000", "98573/500000", "202047/1000000",
    "20709/100000", "52917/250000", "52917/250000",
)))

# A D19 marginal has total polynomial degree at most 20; multiplying by D14
# and taking the distinguished-coordinate primitive adds another one, giving
# at most 35.  For the polygon path r,s>0 and r+s=47, the two
# aggregate-simplex densities contribute (r-1)+(s-1)=45.  Thus 80 is the
# actual uniform ceiling needed by this polygon engine.  The r=0 interval
# branch can reach 81 but never calls _polygon_monomial_batch.
MAX_POLYGON_DEGREE = (19 + 1) + 14 + 1 + ((K - 1) - 2)
if MAX_POLYGON_DEGREE != 80:
    raise RuntimeError("target polygon degree derivation changed")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def common_coordinate_denominator(polygon):
    answer = 1
    for point in polygon:
        for coordinate in point:
            answer = math.lcm(answer, Q(coordinate).denominator)
    return answer


def target_polygons(reference, engine):
    """Return every literal polygon requested by any target branch/shift."""
    rows = []
    for common_r in range(1, 13):  # r=0 is the separate interval path
        maximum_shift = reference._maximum_active_shift(
            ETA - common_r * DELTA, DELTA)
        for side, alpha in (("low", ALPHA1), ("high", ALPHA2)):
            jobs = engine.scheduled_cross_branch_jobs(
                reference, k=K, alpha=alpha, eta=ETA, delta=DELTA,
                schedule=SCHEDULE, common_r=common_r)
            for branch, _family, domain, _first in jobs:
                for shifted in range(maximum_shift + 1):
                    shift = shifted * DELTA
                    total_bound = domain.total_bound - shift
                    if total_bound < 0:
                        continue
                    polygon = tuple(reference._shifted_polygon(
                        total_bound,
                        domain.x_bound,
                        None if domain.y_lower is None
                        else domain.y_lower - shift,
                        None if domain.y_upper is None
                        else domain.y_upper - shift,
                        None if domain.total_lower is None
                        else domain.total_lower - shift))
                    rows.append((common_r, side, branch, shifted, polygon))
    return rows


def compare(core, reference, polygon, powers, label):
    observed = core.polygon_monomial_batch_fixed(polygon, powers)
    expected = reference._polygon_monomial_batch(polygon, powers)
    require(observed == expected, f"fixed/reference mismatch: {label}")
    if len(polygon) >= 3 and powers:
        maximum = max(a + b for a, b in powers)
        coordinate_denominator = common_coordinate_denominator(polygon)
        clearing = (coordinate_denominator ** (maximum + 2) *
                    math.factorial(maximum + 2))
        for power, value in observed.items():
            require(clearing % value.denominator == 0,
                    f"claimed common denominator does not clear {label} {power}")


def test_all_target_polygons(core, reference, engine):
    rows = target_polygons(reference, engine)
    unique = {}
    branch_keys = set()
    for common_r, side, branch, shifted, polygon in rows:
        unique.setdefault(polygon, []).append(
            (common_r, side, branch, shifted))
        branch_keys.add((side, branch))
    require(len(rows) == 804, f"target polygon row count changed: {len(rows)}")
    require(len(unique) == 438,
            f"target unique polygon count changed: {len(unique)}")
    require(branch_keys == {
        (side, branch) for side in ("low", "high")
        for branch in ("Sdelta", "Stotal", "Ltotal", "Lbig")},
        f"target branch coverage changed: {sorted(branch_keys)}")
    # These hit zero/low degree, a genuinely mixed interior monomial, both
    # extreme axes at degree 80, and both near-axis mixed degree-80 cases.
    sentinels = {
        (0, 0), (1, 0), (0, 1), (2, 3),
        (MAX_POLYGON_DEGREE, 0), (0, MAX_POLYGON_DEGREE),
        (MAX_POLYGON_DEGREE - 1, 1),
        (1, MAX_POLYGON_DEGREE - 1),
    }
    for index, (polygon, labels) in enumerate(unique.items()):
        compare(core, reference, polygon, sentinels,
                f"target polygon {index} labels={labels[:2]}")
    return len(rows), len(unique), len(sentinels)


def seeded_convex_polygons():
    rng = random.Random(236_80_438)
    polygons = []
    for _ in range(8):
        x0 = Q(rng.randint(-4, 4), rng.randint(11, 31))
        y0 = Q(rng.randint(-4, 4), rng.randint(13, 37))
        width = Q(rng.randint(2, 9), rng.randint(11, 29))
        height = Q(rng.randint(2, 9), rng.randint(13, 31))
        skew = Q(rng.randint(1, 7), rng.randint(17, 41))
        # A counterclockwise convex trapezoid, sometimes crossing an axis.
        polygons.append((
            (x0, y0), (x0 + width, y0),
            (x0 + width + skew, y0 + height),
            (x0 + skew, y0 + height)))
    return polygons


def test_seeded_degree_sweep(core, reference):
    # Every total degree 0..80 occurs.  Alternating axis and mixed near-axis
    # exponents keeps the independent Fraction oracle tractable while still
    # testing x/y coupling and the full factorial ceiling.
    powers = set()
    for degree in range(MAX_POLYGON_DEGREE + 1):
        if degree == 0:
            powers.add((0, 0))
        elif degree % 4 == 0:
            powers.add((degree, 0))
        elif degree % 4 == 1:
            powers.add((degree - 1, 1))
        elif degree % 4 == 2:
            powers.add((1, degree - 1))
        else:
            powers.add((0, degree))
    require({sum(power) for power in powers} ==
            set(range(MAX_POLYGON_DEGREE + 1)),
            "seeded sweep omitted a target degree")
    for index, polygon in enumerate(seeded_convex_polygons()):
        compare(core, reference, polygon, powers, f"seeded convex {index}")
        compare(core, reference, tuple(reversed(polygon)), powers,
                f"seeded reversed convex {index}")
    # One balanced maximum-degree moment exercises the largest Cartesian
    # product of the two affine expansions without repeating it 438 times.
    polygon = seeded_convex_polygons()[0]
    compare(core, reference, polygon, {(40, 40)},
            "seeded balanced maximum degree")
    return len(seeded_convex_polygons()) * 2, len(powers)


def test_recursive_pins(runner):
    for path, expected in EXPECTED.items():
        require(sha256(path) == expected, f"top-level pin changed: {path}")
    for path, expected in runner.LOCAL_PINNED.items():
        require(sha256(path) == expected, f"runner local pin failed: {path}")
    v7 = load("v8_independent_pin_v7", runner.V7_RUNNER_PATH)
    for path, expected in v7.LOCAL_PINNED.items():
        require(sha256(path) == expected, f"v7 pin failed: {path}")
    v6 = load("v8_independent_pin_v6", v7.V6_RUNNER_PATH)
    for path, expected in v6.LOCAL_PINNED.items():
        require(sha256(path) == expected, f"v6 pin failed: {path}")
    v5 = load("v8_independent_pin_v5", v6.V5_RUNNER_PATH)
    for path, expected in v5.LOCAL_PINNED.items():
        require(sha256(path) == expected, f"v5 pin failed: {path}")
    v2 = load("v8_independent_pin_v2", v5.V2_PATH)
    for path, expected in v2.LOCAL_PINNED.items():
        require(sha256(path) == expected, f"v2 pin failed: {path}")
    base = load("v8_independent_pin_base", v2.BASE_PATH)
    for path, expected in base.PINNED.items():
        require(sha256(path) == expected, f"base recursive pin failed: {path}")
    return sum(map(len, (runner.LOCAL_PINNED, v7.LOCAL_PINNED,
                         v6.LOCAL_PINNED, v5.LOCAL_PINNED,
                         v2.LOCAL_PINNED, base.PINNED)))


def test_runner_runtime_substitution(runner):
    """Run repaired wiring with a fake build and inspect imported modules."""
    original_load = runner.load
    imported_by_path = {}
    runtime_modules = {}
    fixed_module = [None]

    def fake_build(common_r, _v2_snapshots, dependency_snapshots, base,
                   _cached_v7, *, progress=True):
        del progress
        radial = base.import_snapshot(
            "v8_independent_runtime_radial", base.RADIAL,
            dependency_snapshots[base.RADIAL])
        engine = base.import_snapshot(
            "v8_independent_runtime_engine", base.ENGINE,
            dependency_snapshots[base.ENGINE])
        require(common_r == 0, "fake runtime received the wrong shard")
        require(fixed_module[0] is not None,
                "fixed-moment module was not loaded before build")
        require(radial._polygon_monomial_batch is
                fixed_module[0].polygon_monomial_batch_fixed,
                "runtime radial module did not receive the exact replacement")
        require(getattr(engine, "_polygon_monomial_batch", None) is not
                fixed_module[0].polygon_monomial_batch_fixed,
                "replacement leaked into a non-radial imported module")
        return {"source_hashes": {}}

    def intercept_load(name, path, data):
        module = original_load(name, path, data)
        imported_by_path.setdefault(path, []).append(module)
        if name == "d14_grid38_fixed_polygon_v8_v2":
            module.build = fake_build
        if name == "d14_grid38_fixed_polygon_v8_moments":
            fixed_module[0] = module
        if name == "d14_grid38_fixed_polygon_v8_base":
            original_import_snapshot = module.import_snapshot

            def observed_import_snapshot(import_name, import_path, import_data):
                imported = original_import_snapshot(
                    import_name, import_path, import_data)
                runtime_modules.setdefault(import_path, []).append(imported)
                return imported

            module.import_snapshot = observed_import_snapshot
        return module

    runner.load = intercept_load
    old_argv = sys.argv
    try:
        with tempfile.TemporaryDirectory(prefix="fixed-v8-wire-audit-") as root:
            output = Path(root) / "wire.json"
            sys.argv = [str(RUNNER), "--common-r", "0", "--output",
                        str(output), "--expected-self-sha256",
                        EXPECTED[RUNNER]]
            runner.main()
            require(output.is_file(), "fake-build runner did not publish")
            require(len(runtime_modules) == 2,
                    f"fake build imported unexpected runtime paths: "
                    f"{sorted(map(str, runtime_modules))}")
            require(all(len(modules) == 1
                        for modules in runtime_modules.values()),
                    "fake build imported a runtime module more than once")
    finally:
        sys.argv = old_argv
        runner.load = original_load
    return len(imported_by_path)


def main():
    started = time.monotonic()
    for path, expected in EXPECTED.items():
        require(sha256(path) == expected, f"frozen source changed: {path}")
    core = load("fixed_polygon_v8_independent_core", CORE)
    reference = load("fixed_polygon_v8_independent_reference", REFERENCE)
    engine = load("fixed_polygon_v8_independent_engine", ENGINE)
    runner = load("fixed_polygon_v8_independent_runner", RUNNER)
    pins = test_recursive_pins(runner)
    rows, unique, sentinels = test_all_target_polygons(
        core, reference, engine)
    seeded, swept = test_seeded_degree_sweep(core, reference)
    imports = test_runner_runtime_substitution(runner)
    elapsed = time.monotonic() - started
    print(
        "FIXED-POLYGON-V8 INDEPENDENT TEST PASS "
        f"target_rows={rows} unique_polygons={unique} "
        f"sentinels={sentinels} seeded_orientations={seeded} "
        f"degrees_swept={swept} recursive_pins={pins} "
        f"runtime_import_paths={imports} seconds={elapsed:.3f}")


if __name__ == "__main__":
    main()
