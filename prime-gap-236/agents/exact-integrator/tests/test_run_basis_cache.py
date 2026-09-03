import os
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "src"))

from exact_integrator import OneStratumSupport  # noqa: E402
from run_basis import cached_matrices  # noqa: E402


class SourceBoundCacheTests(unittest.TestCase):
    def test_integrator_hash_separates_cache_entries(self):
        support = OneStratumSupport(
            2, Fraction(1, 4), Fraction(1, 20), Fraction(1, 5),
            Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        basis = [(0, ())]
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "moments.sqlite3")
            first = cached_matrices(support, basis, path, "source-a")
            second = cached_matrices(support, basis, path, "source-a")
            changed = cached_matrices(support, basis, path, "source-b")
        self.assertEqual(first[2:], (0, 1))
        self.assertEqual(second[2:], (1, 0))
        self.assertEqual(changed[2:], (0, 1))
        self.assertEqual(first[:2], second[:2])
        self.assertEqual(first[:2], changed[:2])


if __name__ == "__main__":
    unittest.main()
