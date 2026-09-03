#!/usr/bin/env python3

from __future__ import annotations

from decimal import Decimal, localcontext
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).with_name("assemble_piecewise_d16_R15.py")
SPEC = importlib.util.spec_from_file_location("assemble_R15_tested", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class AssembleR15Tests(unittest.TestCase):
    def test_factor48_and_shell_polarization(self):
        rows = [
            {"fh": Decimal(7), "fl": Decimal(2),
             "hh": Decimal(17), "hl": Decimal(5), "ll": Decimal(11)},
            {"fh": Decimal(3), "fl": Decimal(1),
             "hh": Decimal(13), "hl": Decimal(4), "ll": Decimal(9)},
        ]
        A, B = M.assemble(Decimal(19), Decimal(23), Decimal(29), rows)
        self.assertEqual(A, [[Decimal(19), Decimal(0)],
                             [Decimal(0), Decimal(29)]])
        self.assertEqual(B[0][1], Decimal(48) * (5 + 2))
        self.assertEqual(B[1][0], B[0][1])
        self.assertEqual(B[1][1], Decimal(48) * ((17 + 11 - 10) +
                                                 (13 + 9 - 8)))

    def test_stationary_roots_match_characteristic_polynomial(self):
        with localcontext() as context:
            context.prec = 80
            a00, a11 = Decimal(7), Decimal(11)
            b00, b01, b11 = Decimal(5), Decimal(3), Decimal(13)
            rows = M.stationary_candidates(a00, a11, b00, b01, b11)
            stationary = [row for row in rows if row[0].startswith("stationary")]
            self.assertEqual(len(stationary), 2)
            for _, amplitude, quotient in stationary:
                derivative = (a11 * b01 * amplitude * amplitude +
                              (a11 * b00 - b11 * a00) * amplitude -
                              b01 * a00)
                self.assertLess(abs(derivative), Decimal("1e-70"))
                direct = (b00 + 2 * amplitude * b01 +
                          amplitude * amplitude * b11) / (
                              a00 + amplitude * amplitude * a11)
                self.assertEqual(quotient, direct)
            best = max(rows, key=lambda item: item[2])
            # Independent generalized characteristic root.
            aa = a00 * a11
            bb = -(b00 * a11 + b11 * a00)
            cc = b00 * b11 - b01 * b01
            root = (-bb + (bb * bb - 4 * aa * cc).sqrt()) / (2 * aa)
            self.assertLess(abs(best[2] - root), Decimal("1e-70"))

    def test_nonpositive_I_rejected(self):
        with self.assertRaises(ArithmeticError):
            M.assemble(Decimal(1), Decimal(1), Decimal(0), [])
        with self.assertRaises(ArithmeticError):
            M.stationary_candidates(Decimal(0), Decimal(1),
                                    Decimal(1), Decimal(0), Decimal(1))


if __name__ == "__main__":
    unittest.main()
