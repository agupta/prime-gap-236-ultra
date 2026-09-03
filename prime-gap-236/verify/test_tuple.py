#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_tuple import load_tuple, verify  # noqa: E402


class TupleVerifierTests(unittest.TestCase):
    def test_pinned_tuple(self) -> None:
        values = load_tuple(HERE.parent / "sources" / "admissible_48_236.txt")
        witnesses = verify(values, 48, 236)
        self.assertEqual([q for q, _ in witnesses], [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47])

    def test_duplicate_fails_closed(self) -> None:
        values = load_tuple(HERE.parent / "sources" / "admissible_48_236.txt")
        values[-1] = values[-2]
        with self.assertRaises(SystemExit):
            verify(values, 48, 236)

    def test_full_residue_cover_fails(self) -> None:
        # A deliberately malformed 3-tuple covers every class modulo 3.
        with self.assertRaises(SystemExit):
            verify([0, 1, 2], 3, 2)


if __name__ == "__main__":
    unittest.main()

