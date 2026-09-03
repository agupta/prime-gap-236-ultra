#!/usr/bin/env python3
"""Independent fail-closed mutations for the grouped dyadic result driver."""

from __future__ import annotations

import hashlib
import json
import random
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "agents/exact-integrator"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "src"))

import verify.check_c10_d12_affine_dyadic as driver  # noqa: E402
import exact_integrator as ei  # noqa: E402
from dyadic_backend import install_dyadic  # noqa: E402
from grouped_fixed_vector import precompute_orbits  # noqa: E402
from verify.affine_multiplier_oracle import compute_affine_literal  # noqa: E402
from verify.dyadic_interval import DyadicInterval  # noqa: E402
from verify.exact_capped_certificate import Parameters, build_polynomial  # noqa: E402
from fractions import Fraction as Q


EXPECTED_DRIVER_SHA256 = \
    "bf0ad4b3c1288c1d2df67e92f9ebe9e63613b9dcd2892c3f96522217d920677b"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> str:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return sha256(path)


class DyadicDriverHostileAudit(unittest.TestCase):
    def test_frozen_driver_and_real_scaling_reconstruction(self):
        self.assertEqual(sha256(Path(driver.__file__)), EXPECTED_DRIVER_SHA256)
        labels, coefficients, affine, affine_lcm, base_lcm = \
            driver.load_exact_inputs()
        self.assertEqual(len(labels), 272)
        self.assertEqual(len(coefficients), 272)
        self.assertTrue(all(value.denominator == 1 for value in coefficients))
        self.assertEqual(base_lcm.bit_length(), 714)
        self.assertEqual(affine_lcm.bit_length(), 206)
        affine.validate_for(driver.TARGET_C10_D12)

    def test_original_to_integer_scaling_mutations_fail_closed(self):
        original_base = json.loads(driver.BASE_PATH.read_bytes())
        original_source = json.loads(driver.SOURCE_PATH.read_bytes())
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)

            # This is the original counterexample: a byte-pinned integer file
            # can truthfully repeat the source SHA in metadata while carrying
            # an unrelated integer coefficient.  Reconstruction must catch it.
            mutated = json.loads(json.dumps(original_base))
            mutated["rational_vector"][0] = str(
                int(mutated["rational_vector"][0]) + 1)
            path = directory / "wrong-scaled-coefficient.json"
            expected = write_json(path, mutated)
            with patch.object(driver, "BASE_PATH", path), \
                    patch.object(driver, "BASE_SHA256", expected):
                with self.assertRaisesRegex(
                        driver.DyadicCertificateError,
                        "scaled base coefficient mismatch"):
                    driver.load_exact_inputs()

            mutated = json.loads(json.dumps(original_base))
            old_lcm = int(mutated["integer_scaling"][
                "least_common_denominator"])
            mutated["integer_scaling"]["least_common_denominator"] = \
                str(old_lcm + 1)
            path = directory / "wrong-lcm.json"
            expected = write_json(path, mutated)
            with patch.object(driver, "BASE_PATH", path), \
                    patch.object(driver, "BASE_SHA256", expected):
                with self.assertRaisesRegex(
                        driver.DyadicCertificateError,
                        "LCM was not reconstructed"):
                    driver.load_exact_inputs()

            mutated = json.loads(json.dumps(original_base))
            mutated["integer_scaling"]["untrusted_extra"] = True
            path = directory / "extra-scaling-field.json"
            expected = write_json(path, mutated)
            with patch.object(driver, "BASE_PATH", path), \
                    patch.object(driver, "BASE_SHA256", expected):
                with self.assertRaisesRegex(
                        driver.DyadicCertificateError,
                        "scaling metadata mismatch"):
                    driver.load_exact_inputs()

            # Even if a caller updates the expected file SHA after changing
            # the original vector, the separately pinned ordered payload hash
            # must reject the substitute source.
            mutated = json.loads(json.dumps(original_source))
            mutated["rational_vector"][0] = str(
                driver.parse_fraction(mutated["rational_vector"][0], "x") + 1)
            path = directory / "wrong-original-vector.json"
            expected = write_json(path, mutated)
            with patch.object(driver, "SOURCE_PATH", path), \
                    patch.object(driver, "SOURCE_VECTOR_SHA256", expected):
                with self.assertRaisesRegex(
                        driver.DyadicCertificateError,
                        "ordered D12 label/vector payload mismatch"):
                    driver.load_exact_inputs()

    def test_output_sign_k48_factor_and_reverse_order_logic(self):
        DyadicInterval.configure(384, 96)

        # Exercise the target k factor in the actual wrapper method, not a
        # copied formula: one common-count contribution J=7 must return 48J.
        factor_evaluator = types.SimpleNamespace(
            zero=DyadicInterval(0),
            scalar=DyadicInterval,
            support=types.SimpleNamespace(k=48),
            _j_component_data=lambda: ({"component": 1}, (), {}),
            _r_values_j=lambda: [0],
            evaluate_j_r_transfer=lambda lrs, by_lr, amplitudes, r, progress:
                (DyadicInterval(7), 1),
        )
        target_kj, components, domains = \
            driver.DyadicTransferEvaluator.evaluate_j_transfer(
                factor_evaluator, {})
        self.assertEqual((target_kj.lo, target_kj.hi),
                         (336 * DyadicInterval.SCALE,
                          336 * DyadicInterval.SCALE))
        self.assertEqual((components, domains), (1, 1))

        count_evaluator = types.SimpleNamespace(
            _r_values_i=lambda: [0, 1, 2],
            _r_values_j=lambda: [0, 1],
        )
        driver.reverse_count_methods(count_evaluator)
        self.assertEqual(count_evaluator._r_values_i(), [2, 1, 0])
        self.assertEqual(count_evaluator._r_values_j(), [1, 0])

        _, _, _, affine_lcm, base_lcm = driver.load_exact_inputs()
        common = driver.common_metadata(
            driver.dependency_snapshot(), 384, 96, affine_lcm, base_lcm,
            False, driver.EXPECTED_ORBIT_PRODUCT_PAIRS)
        denominator = DyadicInterval(2)
        stage = {
            "status": "c10-d12-affine-rigorous-dyadic-i-stage",
            **common,
            "driver_sha256": EXPECTED_DRIVER_SHA256,
            "I": driver.interval_data(denominator),
            "I_strictly_positive": True,
            "i_orbit_groups": driver.EXPECTED_I_GROUPS,
            "i_faces": driver.EXPECTED_I_FACES,
            "i_wall_seconds": 1.0,
            "i_cpu_seconds": 1.0,
            "i_peak_rss_kib_linux": 1,
        }

        class ResultEvaluator:
            def __init__(self, numerator):
                self.numerator = numerator

            def evaluate_j_transfer(self, amplitudes, progress=False):
                return (self.numerator, driver.EXPECTED_MARGINAL_COMPONENTS,
                        driver.EXPECTED_J_DOMAINS)

        scale = DyadicInterval.SCALE
        cases = (
            (DyadicInterval(3), True),
            (DyadicInterval(1), False),
            # The upper endpoint permits M2>I, but the lower endpoint proves
            # only equality.  A midpoint/upper-bound gate would be unsound.
            (DyadicInterval._from_bounds(2 * scale, 3 * scale), False),
        )
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            stage_path = directory / "I-stage.json"
            stage_sha = write_json(stage_path, stage)
            for index, (numerator, expected_positive) in enumerate(cases):
                output = directory / f"result-{index}.json"
                result, positive = driver.run_j(
                    ResultEvaluator(numerator), {}, common, stage_path,
                    stage_sha, output, False)
                with self.subTest(index=index):
                    self.assertIs(positive, expected_positive)
                    self.assertIs(result["margin_strictly_positive"],
                                  expected_positive)
                    self.assertEqual(
                        result["status"],
                        ("c10-d12-affine-rigorous-dyadic-positive-candidate"
                         if expected_positive else
                         "c10-d12-affine-rigorous-dyadic-nonpositive-result"))
                    self.assertEqual(
                        result["acceptance_rule"],
                        "I.lo > 0 and (M2-M1).lo > 0")
                    self.assertIs(result["theorem_ready"], False)

    def test_signed_random_direct_i_and_unordered_j_containment(self):
        generator = random.Random(0xD1A236)
        # The interval backend intentionally targets a fresh process and
        # replaces this hook.  Restore the original integer recurrence before
        # constructing each new, differently shaped low-k orbit snapshot.
        original_orbit_product = ei.multiply_monomial_orbits
        original_scalar = ei.Q
        for case in range(4):
            k = 2 + case % 2
            params = Parameters(
                name=f"dyadic-hostile-random-k{k}", k=k, degree=3,
                alpha=Q(2, 5), eta=Q(3, 10), delta=Q(1, 10),
                beta1=Q(1, 4), beta2=Q(3, 10), beta3plus=Q(7, 20))
            labels = [(0, ()), (1, ()), (2, ()), (0, (2,))]
            if k == 3:
                labels.append((0, (3,)))
            base = [Q(generator.randint(-9, 9), generator.randint(1, 11))
                    for _ in labels]
            if not any(base):
                base[0] = Q(1)
            source = {
                r: tuple(Q(generator.randint(-13, 13),
                           generator.randint(1, 13)) for _ in range(3))
                for r in range(k + 1)
            }
            expected_i, expected_kj = compute_affine_literal(
                build_polynomial(labels, base, k), params, source)
            ei.multiply_monomial_orbits = original_orbit_product
            ei.Q = original_scalar
            scalar = install_dyadic(
                precompute_orbits(labels, k), precision=384, shadow_bits=96)
            support = ei.OneStratumSupport(
                k,
                *(scalar(value.numerator, value.denominator) for value in (
                    params.alpha, params.delta, params.eta, params.beta1,
                    params.beta2, params.beta3plus)),
            )
            evaluator = driver.DyadicTransferEvaluator(
                support, labels,
                [scalar(value.numerator, value.denominator) for value in base],
                scalar)
            amplitudes = {
                r: tuple(scalar(value.numerator, value.denominator)
                         for value in source[r])
                for r in source
            }
            actual_i, _, _ = evaluator.evaluate_i_transfer(amplitudes)
            actual_kj, _, _ = evaluator.evaluate_j_transfer(amplitudes)
            with self.subTest(case=case, k=k, form="I"):
                self.assertTrue(actual_i.contains(expected_i))
            with self.subTest(case=case, k=k, form="kJ"):
                self.assertTrue(actual_kj.contains(expected_kj))

    def test_stage_field_endpoint_and_width_mutations_fail_closed(self):
        DyadicInterval.configure(384, 96)
        common = {"precision_bits": 384, "audit_sentinel": "fixed"}
        stage = {
            "status": "c10-d12-affine-rigorous-dyadic-i-stage",
            **common,
            "driver_sha256": EXPECTED_DRIVER_SHA256,
            "I": driver.interval_data(DyadicInterval(1)),
            "I_strictly_positive": True,
            "i_orbit_groups": driver.EXPECTED_I_GROUPS,
            "i_faces": driver.EXPECTED_I_FACES,
            "i_wall_seconds": 1.0,
            "i_cpu_seconds": 1.0,
            "i_peak_rss_kib_linux": 1,
        }
        with tempfile.TemporaryDirectory() as raw_directory:
            path = Path(raw_directory) / "stage.json"
            expected = write_json(path, stage)
            _, interval = driver.load_stage(path, expected, common)
            self.assertEqual((interval.lo, interval.hi),
                             (DyadicInterval.SCALE, DyadicInterval.SCALE))

            mutations = []
            value = json.loads(json.dumps(stage))
            value["untrusted_extra"] = 0
            mutations.append((value, "field set mismatch"))
            value = json.loads(json.dumps(stage))
            del value["i_faces"]
            mutations.append((value, "field set mismatch"))
            value = json.loads(json.dumps(stage))
            value["I"]["width_units"] = False
            mutations.append((value, "bounds reversed"))
            value = json.loads(json.dumps(stage))
            value["I"]["lower_fraction"] = "0"
            mutations.append((value, "rational endpoints mismatch"))
            value = json.loads(json.dumps(stage))
            value["I"]["lo_integer"] = "+1"
            mutations.append((value, "malformed I lower integer"))
            for index, (mutated, message) in enumerate(mutations):
                candidate = Path(raw_directory) / f"stage-mutated-{index}.json"
                candidate_sha = write_json(candidate, mutated)
                with self.subTest(index=index):
                    with self.assertRaisesRegex(
                            driver.DyadicCertificateError, message):
                        driver.load_stage(candidate, candidate_sha, common)

    def test_every_protected_path_and_same_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw_directory:
            safe_stage = Path(raw_directory) / "stage.json"
            safe_output = Path(raw_directory) / "output.json"
            with self.assertRaisesRegex(
                    driver.DyadicCertificateError,
                    "stage and output paths must differ"):
                driver.validate_output_paths(safe_stage, safe_stage)
            protected = {
                Path(driver.__file__).resolve(),
                driver.BASE_PATH.resolve(),
                driver.SOURCE_PATH.resolve(),
                driver.AFFINE_PATH.resolve(),
                *(path.resolve() for path in driver.DEPENDENCY_SHAS),
            }
            for path in protected:
                with self.subTest(path=path, position="stage"):
                    with self.assertRaisesRegex(
                            driver.DyadicCertificateError,
                            "collides with a pinned input or dependency"):
                        driver.validate_output_paths(path, safe_output)
                with self.subTest(path=path, position="output"):
                    with self.assertRaisesRegex(
                            driver.DyadicCertificateError,
                            "collides with a pinned input or dependency"):
                        driver.validate_output_paths(safe_stage, path)


if __name__ == "__main__":
    unittest.main()
