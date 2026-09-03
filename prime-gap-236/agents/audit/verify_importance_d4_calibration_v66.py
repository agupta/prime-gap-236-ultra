#!/usr/bin/env python3
"""Independent hostile verifier for frozen D4 calibration v6.6."""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import importlib.util
import io
import json
import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace


HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
CODE = REPO / "agents/structural-basis/code"
sys.path.insert(0, str(CODE))

V = importlib.import_module("importance_d4_calibration_v66")
W = importlib.import_module("importance_whitening_v6")
BUILDER = importlib.import_module("build_importance_d4_calibration_gate_v66")


GATE = REPO / "agents/structural-basis/results/importance_d4_calibration_gate_v66.json"
REGRESSION = REPO / "agents/audit/test_importance_d4_calibration_v66_hostile.py"
EXPECTED = {
    "agents/structural-basis/code/importance_d4_calibration_v66.py":
        "69698f7766d9077bd5026dee8fc1e065b762a1f3d344ea2b7af0282763ce21f9",
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v66.py":
        "17176dab64811a0832c253eb9e0f964903bba951e0734a289731fc98f0d13739",
    "agents/structural-basis/tests/test_importance_d4_calibration_v66.py":
        "fb4d2c2d898c54365c5281557563ecd348481485ec62e2c6f859606cd43b5e29",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V66-SPEC.md":
        "5b056a37d9a7e8d1acfef9264ea009739debcc06df4690abbda15472fbfe8f6b",
    "agents/structural-basis/results/importance_d4_calibration_gate_v66.json":
        "fa1019605ef6b5efd486b234451806efcf1912f7b3f181c9511839d873b63bf6",
    "agents/audit/test_importance_d4_calibration_v66_hostile.py":
        "36084f03d40dc63607a5c01afeb7b9414b32e2334c500ccc21d4324e67ca513b",
}


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rejected(callback, label):
    try:
        callback()
    except (ArithmeticError, ValueError, OverflowError, TypeError,
            AttributeError, IndexError, KeyError):
        return True
    raise AuditFailure(f"hostile input accepted: {label}")


def make_adapter():
    oracle = REPO / V.v65.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[0]
    vector = REPO / V.v65.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[1]
    return W.WhitenedC10ImportanceDensity(vector, oracle)


def point(entries, z=0.0):
    unit = [0.0] * 96
    for index, value in entries.items():
        unit[index] = value
    return SimpleNamespace(
        unit_marginals=tuple(unit), z=z, log_g=0.0,
        nonzero_constant_channels=sum(unit[6 * r] != 0 for r in range(16)),
        z_bound=0.125)


def verify_gate_and_runtime():
    for relative, expected in EXPECTED.items():
        require(digest(REPO / relative) == expected,
                f"frozen v6.6 hash mismatch: {relative}")
    binding = V.load_and_validate_gate(GATE)
    gate = binding["gate"]
    require(gate["production_launch_authorized"] is False and
            gate["rigorous"] is False,
            "v6.6 gate authorizes production or claims rigor")
    require(gate["supersedes_invalid_gate_sha256"] == V.V65_GATE_SHA256,
            "v6.6 predecessor gate binding changed")
    for table in (gate["source_hashes"], gate["data_hashes"]):
        for relative, expected in table.items():
            require(digest(REPO / relative) == expected,
                    f"gate dependency changed: {relative}")
    for relative, expected in V.V65_FAILURE_ARTIFACT_HASHES.items():
        require(gate["source_hashes"].get(relative) == expected,
                f"v6.5 failure artifact is not pinned: {relative}")

    builder_sha = digest(BUILDER.HERE)
    require(BUILDER.build_gate(builder_sha) == gate,
            "independently rebuilt gate differs from frozen gate")
    require(rejected(lambda: BUILDER.build_gate("0" * 64),
                     "wrong builder trust root"),
            "wrong builder trust root was accepted")

    V.install_runtime()
    V.v65.v64.v63.v62.v61.v6._patch_v5_runtime()
    v6 = V.v65.v64.v63.v62.v61.v6
    require(v6.j_envelope_point is V.j_envelope_point and
            v6.v5.j_envelope_point is V.j_envelope_point and
            v6.validate_chain_record is V.validate_chain_record and
            v6.v5.validate_chain_record is V.validate_chain_record,
            "v6.6 runtime wrapper did not reach inherited execution sites")
    conditional = importlib.import_module("importance_conditional")
    require(conditional.j_envelope_log_density is V.j_envelope_log_density,
            "conditional density retained an older envelope wrapper")
    return gate


def verify_trusted_adapter(gate):
    adapter = make_adapter()
    V.v65.v64.v63.v62.v61.v6.validate_adapter_provenance(adapter, gate)
    expected = tuple(Fraction(1, 2 ** exponent) for exponent in
                     (7, 5, 3, 2, 2, 2, 2, 2, 2, 3, 4, 6, 8, 12, 17, 29))
    require(tuple(adapter.base_constant_weights_exact[6 * r]
                  for r in range(16)) == expected,
            "trusted tagged weights are not the expected exact powers of two")
    require(all(adapter.base_constant_weights[index] == 0.0
                for index in range(96) if index % 6),
            "trusted base weights leaked off tagged channels")
    return adapter


def verify_honest_points(adapter):
    conditional = importlib.import_module("importance_conditional")
    checks = 0
    for r in range(16):
        common = conditional.randomized_interior_start(
            adapter, "J", r, 6_600_000 + r)
        envelope = V.j_envelope_point(adapter, common)
        require(envelope is not None, f"honest stratum {r} returned no point")
        weighted, square = V._weighted_m0_and_square(adapter, envelope)
        require(math.isfinite(weighted) and math.isfinite(square) and
                V._authenticate_recomputed_square(envelope.z, square),
                f"honest stratum {r} failed square authentication")
        checks += 1
    return checks


def verify_local_float_edges(adapter):
    edges = {}
    square_root = float.fromhex("0x1p-511")
    below_square_root = math.nextafter(square_root, 0.0)
    overflow_root = float.fromhex("0x1.fffffffffffffp+511")
    first_overflow = math.nextafter(overflow_root, math.inf)
    for sign in (1.0, -1.0):
        key = "positive" if sign > 0 else "negative"
        edges[f"square_underflow_{key}"] = rejected(
            lambda sign=sign: V._finite_resolved_square(
                sign * below_square_root), f"{key} square underflow")
        edges[f"square_boundary_{key}"] = (
            V._finite_resolved_square(sign * square_root) ==
            sys.float_info.min)
        edges[f"square_overflow_{key}"] = rejected(
            lambda sign=sign: V._finite_resolved_square(
                sign * first_overflow), f"{key} square overflow")
        edges[f"square_last_finite_{key}"] = math.isfinite(
            V._finite_resolved_square(sign * overflow_root))

    # Exact cancellation must remain distinguishable from a one-ULP
    # subnormal residual of two individually normal exact dyadic products.
    cancellation = point({0: 0.5, 6: -0.125,
                          1: math.sqrt(47.0) / 8.0})
    edges["exact_signed_cancellation"] = (
        V._weighted_m0_and_square(adapter, cancellation) == (0.0, 0.0))
    minimum = sys.float_info.min
    adjacent = math.nextafter(minimum, math.inf)
    residual = point({0: math.ldexp(minimum, 7),
                      6: -math.ldexp(adjacent, 5), 1: 1.0})
    edges["subnormal_cancellation_residual"] = rejected(
        lambda: V._weighted_m0_and_square(adapter, residual),
        "subnormal cancellation residual")

    # The comparison is truly local: exactly 16 ULPs pass and 17 reject at
    # the smallest-normal scale, on either side of the boundary.
    for direction, target in (("down", 0.0), ("up", math.inf)):
        at = minimum
        over = minimum
        for _ in range(16):
            at = math.nextafter(at, target)
            over = math.nextafter(over, target)
        over = math.nextafter(over, target)
        edges[f"local_16_ulp_{direction}"] = \
            V._authenticate_recomputed_square(at, minimum)
        edges[f"local_17_ulp_{direction}"] = rejected(
            lambda over=over: V._authenticate_recomputed_square(
                over, minimum), f"17 local ULPs {direction}")

    for name, value in (("nan", math.nan), ("positive_inf", math.inf),
                        ("negative_inf", -math.inf),
                        ("negative_zero", -0.0)):
        edges[f"recorded_{name}"] = rejected(
            lambda value=value: V._authenticate_recomputed_square(value, 0.0),
            f"recorded {name}")
    edges["zero_nonzero_mismatch"] = rejected(
        lambda: V._authenticate_recomputed_square(0.0, minimum),
        "zero/nonzero mismatch")
    edges["nonfinite_discrepancy"] = rejected(
        lambda: V._authenticate_recomputed_square(
            sys.float_info.max, -sys.float_info.max),
        "overflowing discrepancy")

    malformed = [
        (SimpleNamespace(unit_marginals=[0.0] * 96), adapter),
        (SimpleNamespace(unit_marginals=(0.0,) * 95), adapter),
        (point({0: math.nan}), adapter),
        (point({0: math.inf}), adapter),
        (point({0: 1.25}), adapter),
    ]
    for index, (bad_point, bad_adapter) in enumerate(malformed):
        edges[f"malformed_{index}"] = rejected(
            lambda bad_point=bad_point, bad_adapter=bad_adapter:
                V._weighted_m0_and_square(bad_adapter, bad_point),
            f"malformed unit {index}")

    off_tag = make_adapter()
    weights = list(off_tag.base_constant_weights)
    exact = list(off_tag.base_constant_weights_exact)
    weights[1] = 1.0
    exact[1] = Fraction(1)
    off_tag.base_constant_weights = tuple(weights)
    off_tag.base_constant_weights_exact = tuple(exact)
    edges["off_tag_weight"] = rejected(
        lambda: V._weighted_m0_and_square(off_tag, point({1: 1.0})),
        "off-tag weight")

    mismatch = make_adapter()
    exact = list(mismatch.base_constant_weights_exact)
    exact[0] *= 2
    mismatch.base_constant_weights_exact = tuple(exact)
    edges["exact_float_weight_mismatch"] = rejected(
        lambda: V._weighted_m0_and_square(mismatch, point({1: 1.0})),
        "exact/float weight mismatch")

    require(all(edges.values()), "one or more local arithmetic edges failed")
    return edges


def run_frozen_regression():
    module_spec = importlib.util.spec_from_file_location(
        "independent_v66_regression", REGRESSION)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    require(result.wasSuccessful() and result.testsRun == 8,
            "independent hostile regression suite failed:\n" + stream.getvalue())
    return result.testsRun


def main():
    gate = verify_gate_and_runtime()
    adapter = verify_trusted_adapter(gate)
    honest = verify_honest_points(adapter)
    edges = verify_local_float_edges(adapter)
    regressions = run_frozen_regression()
    print(json.dumps({
        "status": "AUDIT PASS",
        "gate_sha256": digest(GATE),
        "production_launch_authorized_by_gate": False,
        "source_count": len(gate["source_hashes"]),
        "data_count": len(gate["data_hashes"]),
        "honest_strata_checked": honest,
        "hostile_float_edges_checked": len(edges),
        "independent_regression_tests": regressions,
        "all_v6_through_v65_attacks_closed": True,
        "runtime_wrapper_closed": True,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
