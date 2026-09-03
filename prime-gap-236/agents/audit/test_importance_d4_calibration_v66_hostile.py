#!/usr/bin/env python3
"""Independent hostile regression suite for frozen calibration v6.6.

Unlike the historical v6--v6.5 regressions, every test in this file is
expected to pass: v6.6 must reject each old counterexample and each new
binary64 boundary mutation before production can be authorized.
"""

from __future__ import annotations

import copy
import importlib
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


class V66HostileRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V.install_runtime()
        V.v65.v64.v63.v62.v61.v6._patch_v5_runtime()
        cls.adapter = make_adapter()

    def test_square_resolution_boundaries_both_signs(self):
        lower = math.nextafter(float.fromhex("0x1p-511"), 0.0)
        boundary = float.fromhex("0x1p-511")
        for sign in (1.0, -1.0):
            with self.subTest(sign=sign, side="below"), \
                    self.assertRaises(ArithmeticError):
                V._finite_resolved_square(sign * lower)
            self.assertEqual(
                V._finite_resolved_square(sign * boundary),
                sys.float_info.min)

    def test_square_overflow_boundary_both_signs(self):
        last_finite = float.fromhex("0x1.fffffffffffffp+511")
        first_overflow = math.nextafter(last_finite, math.inf)
        for sign in (1.0, -1.0):
            with self.subTest(sign=sign, side="finite"):
                self.assertTrue(math.isfinite(
                    V._finite_resolved_square(sign * last_finite)))
            with self.subTest(sign=sign, side="overflow"), \
                    self.assertRaises(ArithmeticError):
                V._finite_resolved_square(sign * first_overflow)

    def test_exact_cancellation_and_subnormal_residual(self):
        # Actual tagged weights are 2^-7 and 2^-5.  Products cancel exactly.
        exact = point({0: 0.5, 6: -0.125,
                       1: math.sqrt(47.0) / 8.0})
        weighted, square = V._weighted_m0_and_square(self.adapter, exact)
        self.assertEqual((weighted, square), (0.0, 0.0))

        # Adjacent normal products leave exactly one minimum subnormal after
        # fsum.  That nonzero cancellation residual must not become z=0.
        minimum = sys.float_info.min
        adjacent = math.nextafter(minimum, math.inf)
        unit0 = math.ldexp(minimum, 7)
        unit6 = -math.ldexp(adjacent, 5)
        residual = point({0: unit0, 6: unit6, 1: 1.0})
        self.assertEqual(
            math.fsum((self.adapter.base_constant_weights[0] * unit0,
                       self.adapter.base_constant_weights[6] * unit6)),
            -math.ulp(0.0))
        with self.assertRaises(ArithmeticError):
            V._weighted_m0_and_square(self.adapter, residual)

    def test_product_sum_and_input_nonfinite_paths_reject(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.subTest(kind="unit", bad=bad), \
                    self.assertRaises(ArithmeticError):
                V._weighted_m0_and_square(self.adapter, point({0: bad}))

        # Mutate a fresh adapter locally to reach product and fsum overflow
        # branches; production provenance independently forbids the weights.
        product_adapter = make_adapter()
        weights = list(product_adapter.base_constant_weights)
        exact = list(product_adapter.base_constant_weights_exact)
        weights[0] = sys.float_info.max
        exact[0] = Fraction.from_float(sys.float_info.max)
        product_adapter.base_constant_weights = tuple(weights)
        product_adapter.base_constant_weights_exact = tuple(exact)
        just_over_one = math.nextafter(1.0, math.inf)
        with self.assertRaises(ArithmeticError):
            V._weighted_m0_and_square(
                product_adapter, point({0: just_over_one}))

        sum_adapter = make_adapter()
        weights = list(sum_adapter.base_constant_weights)
        exact = list(sum_adapter.base_constant_weights_exact)
        for index in (0, 6):
            weights[index] = sys.float_info.max
            exact[index] = Fraction.from_float(sys.float_info.max)
        sum_adapter.base_constant_weights = tuple(weights)
        sum_adapter.base_constant_weights_exact = tuple(exact)
        u = math.sqrt(0.5)
        with self.assertRaises(ArithmeticError):
            V._weighted_m0_and_square(sum_adapter, point({0: u, 6: u}))

    def test_recorded_z_fails_closed(self):
        for recorded in (math.nan, math.inf, -math.inf, -0.0,
                         -math.ulp(0.0)):
            with self.subTest(recorded=recorded), \
                    self.assertRaises(ArithmeticError):
                V._authenticate_recomputed_square(recorded, 0.0)
        with self.assertRaises(ArithmeticError):
            V._authenticate_recomputed_square(0.0, sys.float_info.min)
        with self.assertRaises(ArithmeticError):
            V._authenticate_recomputed_square(math.ulp(0.0), 0.0)
        with self.assertRaises(ArithmeticError):
            V._authenticate_recomputed_square(
                sys.float_info.max, -sys.float_info.max)

    def test_public_wrapper_closes_v64_presquare_attack(self):
        adapter = make_adapter()
        marginals = [0.0] * 96
        marginals[0] = float.fromhex("0x1p-600")
        marginals[1] = 1.0
        adapter.j_support = lambda _common: True
        adapter.j_marginals = lambda _common: tuple(marginals)

        def j_m0(_common, transformed=None):
            values = marginals if transformed is None else transformed
            return math.fsum(
                adapter.base_constant_weights[6 * r] * values[6 * r]
                for r in adapter.strata)

        adapter.j_m0 = j_m0
        with self.assertRaises(ArithmeticError):
            V.j_envelope_point(adapter, (0.0,) * 47)

    def test_public_wrapper_closes_v65_overflow_attack(self):
        forged = point({0: sys.float_info.max}, z=0.125)
        original = V.FROZEN_V65_J_ENVELOPE_POINT
        V.FROZEN_V65_J_ENVELOPE_POINT = lambda _adapter, _common: forged
        try:
            with self.assertRaises(ArithmeticError):
                V.j_envelope_point(self.adapter, ())
        finally:
            V.FROZEN_V65_J_ENVELOPE_POINT = original

    def test_all_historical_record_mutations_reject(self):
        schedule = V.v65.v64.v63.v62.v61.v6.v5.tiny_smoke_schedule()
        spec = V.v65.v64.v63.v62.v61.v6.v5.expected_chain_table()[124]
        record = V.v65.v64.v63.v62.v61.v6.v5.run_one_chain(
            self.adapter, spec, schedule)
        self.assertTrue(V.validate_chain_record(
            record, spec, schedule, adapter=self.adapter))
        encode = V.v65.v64.v63.v62.v61.v6.v5.float_hex
        parse = V.v65.v64.v63.v62.v61.v6.v5.parse_float_hex

        mutations = []
        mutation = copy.deepcopy(record)
        bound = float(V.v65.v64.v63.v62.v61.J_Z_BOUNDS_EXACT[15])
        seconds = [parse(value) for value in
                   mutation["batch_z_second_means"]]
        seconds[0] = 2.0 * bound * bound
        mutation["batch_z_second_means"][0] = encode(seconds[0])
        mutation["raw_second_sum"][-1] = encode(
            schedule["samples_per_batch"] * math.fsum(seconds))
        mutations.append(mutation)                         # v6

        mutation = copy.deepcopy(record)
        mutation["raw_sum"][-1] = encode(0.0)
        mutations.append(mutation)                         # v6.1 regrouping

        mutation = copy.deepcopy(record)
        seconds = [parse(value) for value in
                   mutation["batch_z_second_means"]]
        seconds[0] = 0.0
        mutation["batch_z_second_means"][0] = encode(0.0)
        mutation["raw_second_sum"][-1] = encode(
            schedule["samples_per_batch"] * math.fsum(seconds))
        mutations.append(mutation)                         # v6.1 Jensen

        tiny = math.ulp(0.0)
        mutation = copy.deepcopy(record)
        mutation["batch_z_means"] = [encode(0.0)] * 4
        mutation["batch_z_second_means"] = [encode(0.0)] * 4
        mutation["raw_sum"][-1] = encode(tiny)
        mutation["raw_second_sum"][-1] = encode(0.0)
        mutations.append(mutation)                         # v6.2 raw loss

        mutation = copy.deepcopy(record)
        mutation["batch_z_means"] = [encode(0.0)] * 4
        mutation["batch_z_second_means"] = [encode(tiny),
                                               encode(0.0), encode(0.0),
                                               encode(0.0)]
        mutation["raw_sum"][-1] = encode(0.0)
        mutation["raw_second_sum"][-1] = encode(2.0 * tiny)
        mutations.append(mutation)                         # v6.2 batch loss

        h = float.fromhex("0x1p-537")
        mutation = copy.deepcopy(record)
        mutation["batch_z_means"] = [encode(h)] * 4
        mutation["batch_z_second_means"] = [encode(0.0)] * 4
        mutation["raw_sum"][-1] = encode(8.0 * h)
        mutation["raw_second_sum"][-1] = encode(0.0)
        mutations.append(mutation)                         # v6.3 zero second

        for index, mutation in enumerate(mutations):
            with self.subTest(historical=index), \
                    self.assertRaises(ArithmeticError):
                V.validate_chain_record(
                    mutation, spec, schedule, adapter=self.adapter)


if __name__ == "__main__":
    unittest.main()
