#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


TARGET = Path(__file__).with_name("assemble_active25_d18_outer_i_exact.py")
SPEC = importlib.util.spec_from_file_location("assemble_d18_outer_i", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class AssembleOuterITest(unittest.TestCase):
    def test_interval_cover(self):
        intervals = M.expected_intervals()
        self.assertEqual(intervals[0], (0, 500))
        self.assertEqual(intervals[-1], (10500, 10761))
        self.assertEqual(sum(stop - start for start, stop in intervals), 10761)
        self.assertTrue(all(left[1] == right[0]
                            for left, right in zip(intervals, intervals[1:])))
        self.assertEqual(len({M.leaf_name(3, *x) for x in intervals}),
                         len(intervals))

    def test_fraction_parser_fails_closed(self):
        self.assertEqual(M.strict_fraction("3/7", "x"), Q(3, 7))
        for value in ("6/14", "03/7", 1, True, "nan"):
            with self.assertRaises((ValueError, ZeroDivisionError)):
                M.strict_fraction(value, "x")

    def test_bad_interval_geometry(self):
        for args in ((0, 2), (2, 0), (2.0, 1), (2, True)):
            with self.assertRaises(ValueError):
                M.expected_intervals(*args)


if __name__ == "__main__":
    unittest.main()
