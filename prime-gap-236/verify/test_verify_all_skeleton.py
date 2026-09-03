#!/usr/bin/env python3

import contextlib
import io
import unittest
from unittest.mock import patch

import verify_all


class VerifyAllSkeletonTests(unittest.TestCase):
    def test_unarmed_skeleton_launches_no_subprocess_and_makes_no_claim(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("verify_all.subprocess.run") as run:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = verify_all.main([])
        self.assertEqual(status, 3)
        run.assert_not_called()
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("unarmed", stderr.getvalue())
        self.assertNotIn("AUDIT PASS", stderr.getvalue())

    def test_arguments_fail_before_any_subprocess(self) -> None:
        with patch("verify_all.subprocess.run") as run:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = verify_all.main(["--unsafe"])
        self.assertEqual(status, 2)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
