#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

from verify.independent_tuple_verifier import (
    EXPECTED_SHA256,
    TupleVerificationError,
    missing_residue_witnesses,
    parse_canonical_lines,
    primes_through,
    verify_pinned_tuple,
)


class IndependentTupleVerifierTests(unittest.TestCase):
    def test_prime_generation_is_local_and_exact(self) -> None:
        self.assertEqual(primes_through(1), [])
        self.assertEqual(primes_through(20), [2, 3, 5, 7, 11, 13, 17, 19])

    def test_pinned_tuple(self) -> None:
        source = Path(__file__).resolve().parent.parent / "sources/admissible_48_236.txt"
        result = verify_pinned_tuple(source)
        self.assertTrue(result["tuple_verified"])
        self.assertEqual(result["sha256"], EXPECTED_SHA256)
        self.assertEqual(result["size"], 48)
        self.assertEqual(result["diameter"], 236)

    def test_covering_a_prime_is_rejected(self) -> None:
        with self.assertRaises(TupleVerificationError):
            missing_residue_witnesses([0, 1])

    def test_canonical_line_parser_rejects_ambiguity(self) -> None:
        for malformed in (b"", b"0", b"0\n\n", b"00\n", b"+1\n", b"1 \n", b"-1\n"):
            with self.subTest(malformed=malformed):
                with self.assertRaises(TupleVerificationError):
                    parse_canonical_lines(malformed)

    def test_altered_file_fails_hash_before_acceptance(self) -> None:
        temporary = tempfile.NamedTemporaryFile("wb", delete=False)
        path = Path(temporary.name)
        self.addCleanup(path.unlink)
        with temporary:
            temporary.write(b"0\n6\n")
        with self.assertRaises(TupleVerificationError):
            verify_pinned_tuple(path)


if __name__ == "__main__":
    unittest.main()
