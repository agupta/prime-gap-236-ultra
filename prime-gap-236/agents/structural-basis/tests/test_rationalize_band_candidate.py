#!/usr/bin/env python3
"""Exact unit tests for compact common-grid candidate rationalization."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
sys.path.insert(0, str(CODE))

from band_operator import BandMap  # noqa: E402
from rationalize_band_candidate import (common_grid_quantize,  # noqa: E402
                                        candidate_payload,
                                        C10_PARAMETERS,
                                        file_sha,
                                        PINNED_BAND_OPERATOR_SHA,
                                        PINNED_QUADRATIC_POSTPROCESSOR_SHA,
                                        PINNED_RESULT_AUDITOR_SHA,
                                        publish_reserved,
                                        rebind_expected,
                                        reserve_output,
                                        require_distinct_output,
                                        strict_json_loads,
                                        validate_and_expand)


ROOT = HERE.parents[2]
SOURCE = ROOT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
BANDS = ROOT / "agents/structural-basis/results/c10_D12_degree_bands.json"
DIRECT = ROOT / "agents/structural-basis/results/c10_D12_h12_near_20pct_v3.json"


class RationalizeBandCandidateTests(unittest.TestCase):
    def test_band_expansion_dependency_is_pinned(self):
        import hashlib
        self.assertEqual(hashlib.sha256((CODE / "band_operator.py").read_bytes()).hexdigest(),
                         PINNED_BAND_OPERATOR_SHA)

    def test_common_grid_is_primitive_and_has_uniform_error(self):
        values = [Fraction(1), Fraction(-1, 3), Fraction(7, 19), Fraction(0)]
        primitive, limit, common, errors = common_grid_quantize(values, 10)
        self.assertEqual(limit, 10**10)
        self.assertGreater(common, 0)
        divisor = 0
        for value in primitive:
            divisor = __import__("math").gcd(divisor, abs(value))
        self.assertEqual(divisor, 1)
        self.assertLessEqual(max(errors), Fraction(1, 2 * limit))
        represented = [Fraction(common * x, limit) for x in primitive]
        self.assertEqual(errors,
                         [abs(x - y) for x, y in zip(values, represented)])

    def test_actual_band_expansion_is_bound_exactly(self):
        band_map = BandMap.from_source_and_bands(str(SOURCE), str(BANDS))
        source = json.loads(SOURCE.read_bytes())
        candidate = json.loads(DIRECT.read_bytes())
        expanded = [Fraction(x) for x in candidate["rational_vector"]]
        self.assertEqual(validate_and_expand(candidate, band_map, source), expanded)
        candidate["rational_vector"][17] = str(expanded[17] + 1)
        with self.assertRaisesRegex(ValueError, "explicit expansion"):
            validate_and_expand(candidate, band_map, source)

    def test_direct_trial_and_quadratic_payloads_are_supported(self):
        band_map = BandMap.from_source_and_bands(str(SOURCE), str(BANDS))
        source = json.loads(SOURCE.read_bytes())
        direct = json.loads(DIRECT.read_bytes())
        self.assertEqual(validate_and_expand(direct, band_map, source),
                         [Fraction(x) for x in direct["rational_vector"]])
        quadratic = {
            "status": "exact-rational-quadratic-from-mp100-discovery-forms",
            "rigorous": False, "fresh_exact_reconstruction_required": True,
            "coordinate": "theta(s)", "trial_sha256": "a" * 64,
            "scalar_result_sha256": "b" * 64, "i_stage_sha256": "c" * 64,
            "recovery_artifact_sha256": "d" * 64,
            "postprocessor_sha256": PINNED_QUADRATIC_POSTPROCESSOR_SHA,
            "auditor_sha256": PINNED_RESULT_AUDITOR_SHA,
            "quadratic": {
                "D_coefficients": ["1", "0", "1"],
                "N_coefficients": ["1", "0", "1"],
                "stationary_polynomial_coefficients": ["0", "0", "0"],
                "base_action_euler_D_error": "0",
                "base_action_euler_N_error": "0",
                "trial_displacement_first_derivative_exact": "0",
            },
            "ranked_projective_candidates": [{
                "name": "stationary_0", "s": "1",
                "denominator_exact": "1", "numerator_exact": "1",
                "quotient_exact": "1", "quotient_decimal": "1",
            }],
            "selected_candidate": {
                "status":
                    "rational-stationary-band-trial-awaiting-exact-reconstruction",
                "rigorous": False, "fresh_exact_reconstruction_required": True,
                "k": 48, "parameters": C10_PARAMETERS,
                "basis": direct["basis"],
                "stationary_parameter_exact_decimal_rational": "1",
                "compressed_theta": direct["compressed_theta"],
                "rational_vector": direct["rational_vector"],
                "max_compressed_relative_change": "1/5",
            },
            "warning": "discovery only",
        }
        payload, theta = candidate_payload(quadratic)
        self.assertEqual(payload, quadratic["selected_candidate"])
        self.assertEqual(len(theta), 20)
        self.assertEqual(validate_and_expand(quadratic, band_map, source),
                         [Fraction(x) for x in direct["rational_vector"]])

    def test_main_emits_checker_schema_and_byte_pins(self):
        candidate_sha = __import__("hashlib").sha256(DIRECT.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "compact.json"
            command = [sys.executable, str(CODE / "rationalize_band_candidate.py"),
                       "--source", str(SOURCE), "--bands", str(BANDS),
                       "--candidate", str(DIRECT),
                       "--candidate-sha256", candidate_sha,
                       "--denominator-digits", "10", "--output", str(output)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            result = json.loads(output.read_bytes())
            self.assertEqual((result["degree"], result["basis_dimension"]),
                             (12, 272))
            self.assertEqual(result["parameters"], C10_PARAMETERS)
            self.assertIs(result["rigorous"], False)
            self.assertIs(result["fresh_scalar_mp_recheck_required"], True)
            self.assertEqual(result["rationalization"]["candidate_sha256"],
                             candidate_sha)
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("already exists", second.stderr)

    def test_strict_json_and_noncanonical_rationals_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            strict_json_loads(b'{"status":"a","status":"b"}')
        with self.assertRaisesRegex(ValueError, "JSON float"):
            strict_json_loads(b'{"x":1.0}')
        band_map = BandMap.from_source_and_bands(str(SOURCE), str(BANDS))
        source = json.loads(SOURCE.read_bytes())
        candidate = json.loads(DIRECT.read_bytes())
        candidate["compressed_theta"][19] = "01"
        with self.assertRaisesRegex(ValueError, "noncanonical rational"):
            validate_and_expand(candidate, band_map, source)

    def test_alias_create_race_and_postwrite_mutations_fail(self):
        with self.assertRaisesRegex(ValueError, "output aliases"):
            require_distinct_output(SOURCE, [SOURCE])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            occupied = root / "occupied"
            occupied.write_bytes(b"other process")
            with self.assertRaises(FileExistsError):
                reserve_output(occupied)

            path = root / "candidate"
            output = root / "output"
            path.write_bytes(b"pinned")
            expected = __import__("hashlib").sha256(b"pinned").hexdigest()
            rebind_expected({path.resolve(): expected})
            descriptor, identity = reserve_output(output)

            def mutate_dependency(_):
                path.write_bytes(b"mutated after publication")

            with self.assertRaisesRegex(ValueError,
                                        "trusted rationalizer byte changed"):
                publish_reserved(output, "valid output\n", descriptor, identity,
                                 {path.resolve(): expected}, mutate_dependency)
            self.assertEqual(
                strict_json_loads(output.read_bytes()),
                {"status": "REJECTED-rationalizer-publication",
                 "rigorous": False})
            self.assertFalse(list(root.glob("output.rejected.*")))

            path.write_bytes(b"pinned")
            output2 = root / "output2"
            descriptor, identity = reserve_output(output2)

            def mutate_output(target):
                target.write_bytes(b"corrupt published bytes")

            with self.assertRaisesRegex(ValueError, "output bytes changed"):
                publish_reserved(output2, "valid output\n", descriptor, identity,
                                 {path.resolve(): expected}, mutate_output)
            self.assertEqual(
                strict_json_loads(output2.read_bytes()),
                {"status": "REJECTED-rationalizer-publication",
                 "rigorous": False})
            self.assertFalse(list(root.glob("output2.rejected.*")))

            output3 = root / "output3"
            descriptor, identity = reserve_output(output3)

            def replace_reservation(target):
                target.unlink()
                target.write_bytes(b"other process")

            with self.assertRaisesRegex(ValueError,
                                        "output reservation was replaced"):
                publish_reserved(output3, "valid output\n", descriptor, identity,
                                 {path.resolve(): expected}, replace_reservation)
            self.assertEqual(output3.read_bytes(), b"other process")

    def test_stat_then_foreign_replacement_never_renames_foreign_inode(self):
        """Regression for the former ownership-check/rename quarantine race.

        The ownership stat deliberately returns the saved reservation inode
        after replacing its pathname by a foreign inode.  A simultaneous
        dependency mutation then forces the exception path.  Publication may
        reject only through its still-open reservation fd, so the foreign
        pathname must remain byte-for-byte untouched.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dependency = root / "dependency"
            dependency.write_bytes(b"pinned")
            expected = file_sha(dependency)
            output = root / "output"
            descriptor, identity = reserve_output(output)
            saved_stat = os.stat(output, follow_symlinks=False)
            real_stat = os.stat
            swapped = False

            def lie_once(path, *args, **kwargs):
                nonlocal swapped
                if Path(path) == output and not swapped:
                    output.unlink()
                    output.write_bytes(b"other process")
                    swapped = True
                    return saved_stat
                return real_stat(path, *args, **kwargs)

            def mutate_dependency(_target):
                dependency.write_bytes(b"mutated")

            with mock.patch("rationalize_band_candidate.os.stat",
                            side_effect=lie_once), \
                    mock.patch("rationalize_band_candidate.os.replace",
                               side_effect=AssertionError(
                                   "exception path must never rename")):
                with self.assertRaisesRegex(
                        ValueError, "trusted rationalizer byte changed"):
                    publish_reserved(
                        output, "valid output\n", descriptor, identity,
                        {dependency.resolve(): expected}, mutate_dependency)
            self.assertTrue(swapped)
            self.assertEqual(output.read_bytes(), b"other process")
            self.assertFalse(list(root.glob("output.rejected.*")))


if __name__ == "__main__":
    unittest.main()
