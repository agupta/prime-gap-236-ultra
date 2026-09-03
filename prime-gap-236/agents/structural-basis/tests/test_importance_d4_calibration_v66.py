#!/usr/bin/env python3

import copy
import importlib
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
V = importlib.import_module("importance_d4_calibration_v66")
W = importlib.import_module("importance_whitening_v6")
G = importlib.import_module("build_importance_d4_calibration_gate_v66")


def make_adapter():
    return W.WhitenedC10ImportanceDensity(
        REPO / V.v65.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[1],
        REPO / V.v65.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[0])


def unit_point(entries, z=0.0):
    unit = [0.0] * 96
    for index, value in entries.items():
        unit[index] = value
    return SimpleNamespace(
        unit_marginals=tuple(unit), z=z, log_g=0.0,
        nonzero_constant_channels=sum(
            unit[6 * r] != 0 for r in range(16)), z_bound=0.125)


class CalibrationV66Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V.install_runtime()
        V.v65.v64.v63.v62.v61.v6._patch_v5_runtime()
        cls.adapter = make_adapter()
        cls.schedule = V.v65.v64.v63.v62.v61.v6.v5.tiny_smoke_schedule()

    def test_v65_real_adapter_square_overflow_rejects(self):
        point = unit_point({0: sys.float_info.max}, z=0.125)
        with self.assertRaises(ArithmeticError):
            V._weighted_m0_and_square(self.adapter, point)
        frozen = V.FROZEN_V65_J_ENVELOPE_POINT
        V.FROZEN_V65_J_ENVELOPE_POINT = lambda _adapter, _common: point
        try:
            with self.assertRaises(ArithmeticError):
                V.j_envelope_point(self.adapter, ())
        finally:
            V.FROZEN_V65_J_ENVELOPE_POINT = frozen

    def test_finite_square_and_authentication_guards(self):
        with self.assertRaises(ArithmeticError):
            V._finite_resolved_square(float.fromhex("0x1p+512"))
        with self.assertRaises(ArithmeticError):
            V._finite_resolved_square(math.inf)
        with self.assertRaises(ArithmeticError):
            V._authenticate_recomputed_square(math.inf, 0.0)
        with self.assertRaises(ArithmeticError):
            V._authenticate_recomputed_square(math.nan, 0.0)
        with self.assertRaises(ArithmeticError):
            V._authenticate_recomputed_square(-0.0, 0.0)
        with self.assertRaises(ArithmeticError):
            V._authenticate_recomputed_square(sys.float_info.max,
                                               -sys.float_info.max)
        with mock.patch.object(V.math, "ulp", return_value=math.inf):
            with self.assertRaises(ArithmeticError):
                V._authenticate_recomputed_square(0.25, 0.25)

    def test_exact_cancellation_and_resolved_boundary(self):
        # w0=2^-7 and w6=2^-5.  These two products cancel exactly; the
        # nonconstant coordinate completes a unit vector without changing m0.
        point = unit_point({0: 0.5, 6: -0.125,
                            1: math.sqrt(47.0) / 8.0})
        weighted, square = V._weighted_m0_and_square(self.adapter, point)
        self.assertEqual(weighted, 0.0)
        self.assertEqual(square, 0.0)
        self.assertTrue(V._authenticate_recomputed_square(0.0, square))

        for sign in (1.0, -1.0):
            # Tagged 2^-504 times w0=2^-7 gives 2^-511, whose square is
            # exactly the smallest normal.  Coordinate 1 makes the rounded
            # binary64 unit norm exactly one.
            point = unit_point({0: sign * float.fromhex("0x1p-504"),
                                1: 1.0})
            weighted, square = V._weighted_m0_and_square(self.adapter, point)
            self.assertEqual(abs(weighted), float.fromhex("0x1p-511"))
            self.assertEqual(square, sys.float_info.min)

    def test_tagged_product_rounding_and_unit_forgery_reject(self):
        for sign in (1.0, -1.0):
            point = unit_point({0: sign * float.fromhex("0x1p-1018"),
                                1: 1.0})
            with self.assertRaises(ArithmeticError):
                V._weighted_m0_and_square(self.adapter, point)
        for bad in (math.inf, -math.inf, math.nan, 1.25):
            point = unit_point({0: bad})
            with self.assertRaises(ArithmeticError):
                V._weighted_m0_and_square(self.adapter, point)

    def test_honest_real_points_all_strata(self):
        conditional = importlib.import_module("importance_conditional")
        for r in range(16):
            common = conditional.randomized_interior_start(
                self.adapter, "J", r, 966_000 + r)
            point = V.j_envelope_point(self.adapter, common)
            self.assertIsNotNone(point)
            _, square = V._weighted_m0_and_square(self.adapter, point)
            self.assertTrue(V._authenticate_recomputed_square(point.z, square))

    def test_predecessor_record_underflow_and_jensen_reject(self):
        spec = V.v65.v64.v63.v62.v61.v6.v5.expected_chain_table()[124]
        record = V.v65.v64.v63.v62.v61.v6.v5.run_one_chain(
            self.adapter, spec, self.schedule)
        self.assertTrue(V.validate_chain_record(
            record, spec, self.schedule, adapter=self.adapter))
        encode = V.v65.v64.v63.v62.v61.v6.v5.float_hex

        mutation = copy.deepcopy(record)
        mutation["batch_z_means"] = [encode(0.0)] * 4
        mutation["batch_z_second_means"] = [encode(0.0)] * 4
        mutation["raw_sum"][-1] = encode(math.ulp(0.0))
        mutation["raw_second_sum"][-1] = encode(0.0)
        with self.assertRaises(ArithmeticError):
            V.validate_chain_record(
                mutation, spec, self.schedule, adapter=self.adapter)

        h = float.fromhex("0x1p-537")
        mutation = copy.deepcopy(record)
        mutation["batch_z_means"] = [encode(h)] * 4
        mutation["batch_z_second_means"] = [encode(0.0)] * 4
        mutation["raw_sum"][-1] = encode(8 * h)
        mutation["raw_second_sum"][-1] = encode(0.0)
        with self.assertRaises(ArithmeticError):
            V.validate_chain_record(
                mutation, spec, self.schedule, adapter=self.adapter)

    def test_gate_pins_v65_failure_and_remains_disabled(self):
        self.assertTrue(V.validate_v65_failure_artifacts())
        builder_sha = V.v65.v64.v63.v62.v61.v6.v5.sha256_file(G.HERE)
        gate = G.build_gate(builder_sha)
        self.assertFalse(gate["production_launch_authorized"])
        self.assertEqual(gate["supersedes_invalid_gate_sha256"],
                         V.V65_GATE_SHA256)
        for relative, expected in V.V65_FAILURE_ARTIFACT_HASHES.items():
            self.assertEqual(gate["source_hashes"][relative], expected)
        with self.assertRaises(ValueError):
            G.build_gate("0" * 64)

    def test_v65_failure_artifact_mutation_rejects(self):
        relative, expected = next(iter(V.V65_FAILURE_ARTIFACT_HASHES.items()))
        V.V65_FAILURE_ARTIFACT_HASHES[relative] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                V.validate_v65_failure_artifacts()
        finally:
            V.V65_FAILURE_ARTIFACT_HASHES[relative] = expected


if __name__ == "__main__":
    unittest.main()
