#!/usr/bin/env python3
"""Hostile low-cost audit tests for the independent tagged dyadic driver.

These tests deliberately do not run the target D12 traversal.  They exercise
the exact input trust chain, target active-face enumeration, interval-valued
coefficient control flow, a genuinely uncertain small-k end-to-end enclosure,
and the staged sign gate.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import types
import unittest
from fractions import Fraction as Q
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import verify.check_c10_d12_affine_exact as exact_driver  # noqa: E402
import verify.check_c10_d12_affine_independent_dyadic as driver  # noqa: E402
import verify.exact_affine_multiplier as affine_core  # noqa: E402
import verify.exact_affine_multiplier_batched as batched_core  # noqa: E402
from verify.affine_multiplier_oracle import compute_affine_literal  # noqa: E402
from verify.dyadic_interval import DyadicInterval as D  # noqa: E402
from verify.exact_affine_multiplier import (  # noqa: E402
    AffineMultipliers,
    compute_i_affine_tagged,
)
from verify.exact_affine_multiplier_batched import (  # noqa: E402
    compute_j_affine_tagged_batched,
)
from verify.exact_capped_certificate import (  # noqa: E402
    Parameters,
    _affine_power_terms,
    _pack_tagged_radials_by_shift,
    build_basis_terms,
    build_polynomial,
    poly_add_term,
)


EXPECTED_DRIVER_SHA256 = \
    "7e2ed20a68e3c3e95a9566b32cae3d403949a79a3a81adfa61b8dab833b640b9"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload) -> str:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return sha256(path)


def interval_hull(lower: Q, upper: Q) -> D:
    if lower > upper:
        raise ValueError("reversed audit hull")
    lo = lower.numerator * D.SCALE // lower.denominator
    scaled_upper = upper.numerator * D.SCALE
    hi = -((-scaled_upper) // upper.denominator)
    return D._from_bounds(lo, hi, None)


def small_parameters(k: int) -> Parameters:
    return Parameters(
        name=f"independent-dyadic-hostile-k{k}", k=k, degree=2,
        alpha=Q(2, 5), eta=Q(3, 10), delta=Q(1, 10),
        beta1=Q(1, 4), beta2=Q(3, 10), beta3plus=Q(7, 20),
    )


class IndependentDyadicDriverAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        D.configure(256, 96)

    def test_frozen_closure_and_real_source_to_integer_reconstruction(self):
        self.assertEqual(sha256(Path(driver.__file__)), EXPECTED_DRIVER_SHA256)
        self.assertEqual(
            set(exact_driver.DEPENDENCY_SHAS),
            {
                ROOT / "verify/exact_affine_multiplier.py",
                ROOT / "verify/exact_affine_multiplier_batched.py",
                ROOT / "verify/exact_capped_certificate.py",
            },
        )
        self.assertEqual(
            set(driver.DEPENDENCY_SHAS),
            {
                ROOT / "verify/check_c10_d12_affine_exact.py",
                ROOT / "verify/dyadic_interval.py",
                *set(exact_driver.DEPENDENCY_SHAS),
            },
        )
        self.assertEqual(driver.dependency_snapshot(), {
            str(path.relative_to(ROOT)): expected
            for path, expected in driver.DEPENDENCY_SHAS.items()
        })
        terms, affine, affine_lcm, base_lcm = driver.load_scaled_inputs()
        self.assertEqual(len(terms), 272)
        self.assertEqual(base_lcm.bit_length(), 714)
        self.assertEqual(affine_lcm.bit_length(), 206)
        self.assertTrue(all(value.denominator == 1 for value in terms.values()))
        self.assertTrue(all(
            value.denominator == 1
            for triple in affine.coefficients for value in triple
        ))

    def test_source_and_scaled_input_mutations_fail_closed(self):
        original_base = json.loads(exact_driver.BASE_PATH.read_bytes())
        original_source = json.loads(exact_driver.SOURCE_PATH.read_bytes())
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)

            mutated = json.loads(json.dumps(original_base))
            mutated["rational_vector"][0] = str(
                int(mutated["rational_vector"][0]) + 1)
            path = directory / "wrong-scaled.json"
            expected = write_json(path, mutated)
            with patch.object(exact_driver, "BASE_PATH", path), \
                    patch.object(exact_driver, "BASE_SHA256", expected):
                with self.assertRaisesRegex(
                        exact_driver.ExactAffineCertificateError,
                        "scaled base coefficient mismatch"):
                    driver.load_scaled_inputs()

            mutated = json.loads(json.dumps(original_base))
            mutated["integer_scaling"]["least_common_denominator"] = str(
                int(mutated["integer_scaling"][
                    "least_common_denominator"]) + 1)
            path = directory / "wrong-lcm.json"
            expected = write_json(path, mutated)
            with patch.object(exact_driver, "BASE_PATH", path), \
                    patch.object(exact_driver, "BASE_SHA256", expected):
                with self.assertRaisesRegex(
                        exact_driver.ExactAffineCertificateError,
                        "LCM was not reconstructed"):
                    driver.load_scaled_inputs()

            mutated = json.loads(json.dumps(original_source))
            mutated["rational_vector"][0] = str(
                Q(mutated["rational_vector"][0]) + 1)
            path = directory / "wrong-source.json"
            expected = write_json(path, mutated)
            with patch.object(exact_driver, "SOURCE_PATH", path), \
                    patch.object(exact_driver, "SOURCE_VECTOR_SHA256", expected):
                with self.assertRaisesRegex(
                        exact_driver.ExactAffineCertificateError,
                        "ordered D12 label/vector payload mismatch"):
                    driver.load_scaled_inputs()

    def test_target_active_faces_are_complete_in_both_orders(self):
        params = driver.TARGET_C10_D12
        expected = list(range(16))
        self.assertEqual(driver.active_face_counts(), (16, 16))
        self.assertGreater(params.beta(15) - 15 * params.delta, 0)
        self.assertLessEqual(params.beta(16) - 16 * params.delta, 0)
        self.assertGreater(params.eta - 15 * params.delta, 0)
        self.assertFalse(
            params.beta(16) - 16 * params.delta > 0 or
            params.beta(17) - 17 * params.delta > 0)

        terms = {(0, ()): D(1)}
        affine = AffineMultipliers(tuple(
            (D(1), D(0), D(0)) for _ in range(params.k + 1)
        ))
        for reverse in (False, True):
            expected_order = list(reversed(expected)) if reverse else expected
            seen_i = []
            seen_j = []

            def fake_i(payload, received_params, r):
                self.assertIs(received_params, params)
                seen_i.append(r)
                return D(0)

            def fake_j(payload, received_params, r):
                self.assertIs(received_params, params)
                seen_j.append(r)
                return D(0)

            with patch.object(affine_core, "_compute_i_affine_face", fake_i):
                compute_i_affine_tagged(
                    terms, params, affine, reverse_faces=reverse, workers=1)
            with patch.object(
                    batched_core, "_compute_j_affine_face_batched", fake_j):
                compute_j_affine_tagged_batched(
                    terms, params, affine, reverse_faces=reverse, workers=1)
            self.assertEqual(seen_i, expected_order)
            self.assertEqual(seen_j, expected_order)

    def test_zero_containing_coefficients_are_never_dropped(self):
        uncertain_zero = D._from_bounds(-1, 1, None)
        self.assertTrue(uncertain_zero)
        self.assertNotEqual(uncertain_zero, 0)

        polynomial = {}
        poly_add_term(polynomial, (), uncertain_zero)
        self.assertIn((), polynomial)
        poly_add_term(polynomial, (), -uncertain_zero)
        self.assertIn((), polynomial)

        terms = build_basis_terms([(0, ())], [uncertain_zero])
        self.assertIn((0, ()), terms)
        affine_terms = _affine_power_terms(
            1, uncertain_zero, D(0), D(0))
        self.assertIn((0, 0), affine_terms)
        packed = _pack_tagged_radials_by_shift({
            (0, 0): {(0, 0, 0): uncertain_zero},
        })
        self.assertEqual(len(packed[0]), 1)

    def test_uncertain_small_k_path_encloses_independent_literal_oracle(self):
        params = small_parameters(2)
        labels = [(0, ()), (1, ()), (0, (2,))]
        base_ranges = [
            (Q(-1, 5), Q(2, 5)),
            (Q(1, 7), Q(3, 7)),
            (Q(-2, 9), Q(-1, 9)),
        ]
        affine_ranges = {
            0: ((Q(-1, 4), Q(1, 3)),
                (Q(1, 5), Q(2, 5)),
                (Q(-1, 7), Q(2, 7))),
            1: ((Q(1, 6), Q(1, 2)),
                (Q(-2, 5), Q(1, 5)),
                (Q(1, 8), Q(3, 8))),
            2: ((Q(-1, 3), Q(1, 4)),
                (Q(1, 9), Q(4, 9)),
                (Q(-2, 7), Q(1, 7))),
        }
        interval_terms = build_basis_terms(
            labels, [interval_hull(*bounds) for bounds in base_ranges])
        interval_affine = AffineMultipliers(tuple(
            tuple(interval_hull(*bounds) for bounds in affine_ranges[r])
            for r in range(params.k + 1)
        ))

        actual = []
        for reverse in (False, True):
            i_value = compute_i_affine_tagged(
                interval_terms, params, interval_affine,
                reverse_faces=reverse, workers=1)
            kj_value = D(params.k) * compute_j_affine_tagged_batched(
                interval_terms, params, interval_affine,
                reverse_faces=reverse, workers=1)
            self.assertIsInstance(i_value, D)
            self.assertIsInstance(kj_value, D)
            actual.append((i_value, kj_value))

        def endpoint(bounds, selector):
            lower, upper = bounds
            if selector == 0:
                return lower
            if selector == 1:
                return (lower + upper) / 2
            return upper

        patterns = (
            (0, 0, 0, 0),
            (1, 1, 1, 1),
            (2, 2, 2, 2),
            (0, 2, 1, 2),
            (2, 0, 2, 0),
        )
        for pattern in patterns:
            base = [endpoint(bounds, pattern[index % len(pattern)])
                    for index, bounds in enumerate(base_ranges)]
            source = {
                r: tuple(endpoint(bounds, pattern[(r + channel) % 4])
                         for channel, bounds in enumerate(affine_ranges[r]))
                for r in range(params.k + 1)
            }
            expected_i, expected_kj = compute_affine_literal(
                build_polynomial(labels, base, params.k), params, source)
            for reverse, (i_value, kj_value) in zip(
                    (False, True), actual, strict=True):
                with self.subTest(pattern=pattern, reverse=reverse, form="I"):
                    self.assertTrue(i_value.contains(expected_i))
                with self.subTest(pattern=pattern, reverse=reverse, form="kJ"):
                    self.assertTrue(kj_value.contains(expected_kj))

    def test_stage_schema_k48_factor_and_lower_endpoint_sign_gate(self):
        common = {
            "precision_bits": D.PRECISION,
            "dependency_sha256": {"audit": "fixed"},
            "audit_sentinel": "fixed",
        }
        stage = {
            "status": "c10-d12-affine-independent-dyadic-i-stage",
            **common,
            "driver_sha256": EXPECTED_DRIVER_SHA256,
            "I": driver.interval_data(D(96)),
            "I_strictly_positive": True,
            "i_wall_seconds": 1.0,
            "i_peak_rss_kib_linux": 1,
        }
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            stage_path = directory / "stage.json"
            stage_sha = write_json(stage_path, stage)
            loaded, denominator = driver.load_stage(
                stage_path, stage_sha, common)
            self.assertEqual(loaded, stage)
            self.assertEqual(
                (denominator.lo, denominator.hi),
                (96 * D.SCALE, 96 * D.SCALE),
            )

            mutations = []
            value = json.loads(json.dumps(stage))
            value["extra"] = 0
            mutations.append(value)
            value = json.loads(json.dumps(stage))
            value["I"]["width_units"] = False
            mutations.append(value)
            value = json.loads(json.dumps(stage))
            value["I"]["lower_fraction"] = "0"
            mutations.append(value)
            value = json.loads(json.dumps(stage))
            value["I"]["lo_integer"] = "+1"
            mutations.append(value)
            for index, mutation in enumerate(mutations):
                path = directory / f"mutation-{index}.json"
                expected_sha = write_json(path, mutation)
                with self.subTest(stage_mutation=index):
                    with self.assertRaises(driver.IndependentDyadicError):
                        driver.load_stage(path, expected_sha, common)

            scale = D.SCALE
            cases = (
                (D(3), True),
                (D(1), False),
                (D._from_bounds(2 * scale, 3 * scale, None), False),
            )
            for index, (j_value, expected_positive) in enumerate(cases):
                output = directory / f"output-{index}.json"
                with patch.object(
                        driver, "compute_j_affine_tagged_batched",
                        return_value=j_value), \
                        patch.object(
                            driver, "dependency_snapshot",
                            return_value=common["dependency_sha256"]), \
                        patch.object(driver, "reread_inputs", return_value=None):
                    result, positive = driver.run_j(
                        {}, types.SimpleNamespace(), common,
                        stage_path, stage_sha, output, False)
                # run_j receives J, so J=3 is multiplied by target k=48.
                expected_numerator = D(48) * j_value
                self.assertEqual(
                    result["M2"]["lo_integer"], str(expected_numerator.lo))
                self.assertIs(positive, expected_positive)

            # A direct margin with lower endpoint zero must not pass.
            numerator = D._from_bounds(96 * scale, 144 * scale, None)
            self.assertEqual((numerator - D(96)).lo, 0)
            self.assertFalse((numerator - D(96)).lo > 0)

    def test_every_protected_path_and_same_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw_directory:
            safe_stage = Path(raw_directory) / "stage.json"
            safe_output = Path(raw_directory) / "output.json"
            with self.assertRaisesRegex(
                    driver.IndependentDyadicError,
                    "stage and output paths must differ"):
                driver.validate_paths(safe_stage, safe_stage)
            protected = {
                Path(driver.__file__).resolve(),
                driver.SOURCE_PATH.resolve(),
                driver.BASE_PATH.resolve(),
                driver.AFFINE_PATH.resolve(),
                *(path.resolve() for path in driver.DEPENDENCY_SHAS),
            }
            for path in protected:
                with self.subTest(path=path, position="stage"):
                    with self.assertRaises(driver.IndependentDyadicError):
                        driver.validate_paths(path, safe_output)
                with self.subTest(path=path, position="output"):
                    with self.assertRaises(driver.IndependentDyadicError):
                        driver.validate_paths(safe_stage, path)


if __name__ == "__main__":
    unittest.main()
