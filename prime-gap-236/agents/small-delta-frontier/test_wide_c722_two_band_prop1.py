#!/usr/bin/env python3
"""Low-cost exact regressions for the wide C722 two-band audit."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


PATH = Path(__file__).with_name("verify_wide_c722_two_band_prop1.py")
SPEC = importlib.util.spec_from_file_location("wide_c722_tested", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load checker")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class WideC722Tests(unittest.TestCase):
    def test_parameter_and_active_inventories(self):
        self.assertEqual(M.ALPHA1, Q(103, 400))
        self.assertEqual(M.ALPHA2, Q(3211, 12000))
        self.assertEqual(M.ETA1, Q(97, 400))
        self.assertEqual(M.ETA2, Q(3031, 12000))
        self.assertEqual(M.active(M.INNER), tuple(range(36)))
        self.assertEqual(M.active(M.OUTER), tuple(range(24)))
        self.assertEqual(M.OUTER[-1], Q(43, 250))

    def test_mixed_dynamic_iic_is_really_empty(self):
        gamma_min = Q(2, 5) - M.H
        gamma_max = (Q(1, 3) + 8 * M.CROSS_OMEGA +
                     Q(7, 3) * M.DELTA + 3 * M.H)
        self.assertEqual(gamma_min - gamma_max,
                         Q(71149997, 7500000000))
        result = M.dynamic_iic_family(M.INNER, M.OUTER, M.CROSS_OMEGA)
        self.assertEqual(result["checks"], 0)
        self.assertEqual(Q(result["empty_gamma_margin"]), gamma_min - gamma_max)

    def test_fixed_prefix_margins(self):
        cross = M.fixed_prefix_family(M.INNER, M.OUTER, M.CROSS_OMEGA)
        outer = M.fixed_prefix_family(M.OUTER, M.OUTER, M.OUTER_OMEGA)
        self.assertEqual(cross["pairs"], 863)
        self.assertEqual(Q(cross["worst_margin"]),
                         Q(178999904861, 90000000000000))
        self.assertEqual(outer["pairs"], 575)
        self.assertEqual(Q(outer["worst_margin"]),
                         Q(20799452461, 465000000000000))
        self.assertEqual(outer["worst_pair"], [18, 18])
        self.assertEqual(outer["worst_type"], "IIc")

    def test_corrected_iib_c3_and_mixed_two_bin_counterexample(self):
        # TeX lines 1609--1613 put the IIb third-bin minimum at the lower
        # gamma endpoint.  The checker uses a safe value exactly 2h/7 below
        # the zeta->0 inward-shifted infimum.
        for omega in (Q(0), M.CROSS_OMEGA, M.OUTER_OMEGA):
            safe = M.fixed_capacities(omega)["IIb"][2]
            self.assertEqual(safe, M.DELTA + 2 * omega)
            self.assertEqual(M.iib_c3_actual_infimum(omega) - safe,
                             2 * M.H / 7)

        # At omega=0 this mixed pair falsifies the two-bin shortcut.  The
        # production decomposition does not assign mixed moduli to this
        # branch; retaining the fixture prevents a future blanket claim.
        caps = M.fixed_capacities(Q(0))["IIb"]
        with self.assertRaises(ArithmeticError):
            M.prefix_margin(1, 17, M.INNER[0], M.OUTER[16],
                            caps[0], caps[1])
        # We intentionally do not promote a finite search on this unused
        # branch to a lemma.  Its existence is a regression against silently
        # applying the two-bin shortcut at omega=0.

    def test_outer_near_square_literal_cover(self):
        result = M.fixed_interval_family(
            M.OUTER, M.OUTER, Q(0), ("IIa", "IIb", "III"))
        self.assertEqual(result["pairs"], 575)
        self.assertEqual(result["checks"], 1725)
        self.assertEqual(result["nodes"], 1725)
        self.assertEqual(result["leaves"], 1725)
        self.assertGreater(Q(result["worst_all_first_margin"]), 0)

    def test_scalar_outer_endpoint_is_strict(self):
        margins = {}
        M.scalar_direct_hb(margins, "outer", M.OUTER_OMEGA)
        self.assertEqual(margins["outer TypeII first"],
                         Q(7699997, 15000000000))
        self.assertEqual(margins["outer TypeII second"],
                         Q(149999, 5000000000))
        self.assertEqual(margins["outer TypeIII distribution"],
                         Q(1, 1250000000))


if __name__ == "__main__":
    unittest.main()
