#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE.parent / "code" / "fixed_vector_support_kernel.py"
SPEC = importlib.util.spec_from_file_location("fixed_vector_support_kernel", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
kernel_mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = kernel_mod
SPEC.loader.exec_module(kernel_mod)

ei = kernel_mod.ei
grouped = kernel_mod.grouped
import scheduled_fixed_vector as scheduled  # noqa: E402


def source_bytes(k, degree, labels, coefficients):
    payload = {
        "k": k,
        "degree": degree,
        "basis_dimension": len(labels),
        "basis": [[a, list(lam)] for a, lam in labels],
        "rational_vector": [str(Fraction(x)) for x in coefficients],
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
            "\n").encode("ascii")


def direct_forms(k, labels, coefficients, parameters):
    support = ei.OneStratumSupport(k, *parameters)
    evaluator = grouped.GroupedEvaluator(
        support, labels, coefficients, Fraction)
    denominator, groups, faces = evaluator.evaluate_i(False, 1)
    j_value, components, integrals = evaluator.evaluate_j(False, 1)
    return {
        "denominator": denominator,
        "j_value": j_value,
        "numerator": k * j_value,
        "i_orbit_groups": groups,
        "i_faces": faces,
        "marginal_components": components,
        "j_branch_integrals": integrals,
    }


class SupportKernelTests(unittest.TestCase):
    def check_case(self, k, degree, labels, coefficients, parameters):
        data = source_bytes(k, degree, labels, coefficients)
        kernel = kernel_mod.compile_kernel_bytes(data)
        support = ei.OneStratumSupport(k, *parameters)
        self.assertEqual(
            direct_forms(k, labels, coefficients, parameters),
            kernel_mod.evaluate_kernel(support, kernel, Fraction, 1),
        )

        direct_evaluator = grouped.GroupedEvaluator(
            support, labels, coefficients, Fraction)
        self.assertEqual(direct_evaluator.square_residual_terms(),
                         kernel.i_grouped(support.alpha, Fraction))
        self.assertEqual(direct_evaluator.marginal_components(),
                         kernel.marginal_components(Fraction))

    def test_k1_zero_dimensional_marginal(self):
        self.check_case(
            1,
            2,
            ((0, ()), (1, ()), (0, (1,)), (0, (2,))),
            tuple(map(Fraction, (2, -1, 3, -2))),
            tuple(map(Fraction,
                      ("3/5", "1/10", "1/2", "3/20", "3/20", "1/5"))),
        )

    def test_signed_k3_two_supports(self):
        labels = ((0, ()), (1, ()), (0, (1,)), (0, (2,)),
                  (1, (1,)), (0, (1, 1)))
        coefficients = tuple(map(Fraction, (2, -3, 5, -7, 11, -13)))
        supports = (
            tuple(map(Fraction,
                      ("2/3", "1/9", "3/5", "1/4", "5/18", "1/3"))),
            tuple(map(Fraction,
                      ("7/10", "1/8", "5/8", "6/25", "7/25", "8/25"))),
        )
        data = source_bytes(3, 2, labels, coefficients)
        kernel = kernel_mod.compile_kernel_bytes(data)
        for parameters in supports:
            with self.subTest(parameters=parameters):
                support = ei.OneStratumSupport(3, *parameters)
                self.assertEqual(
                    direct_forms(3, labels, coefficients, parameters),
                    kernel_mod.evaluate_kernel(support, kernel, Fraction, 1),
                )

    def test_signed_k3_schedule_and_two_workers(self):
        labels = ((0, ()), (1, ()), (0, (1,)), (0, (2,)),
                  (1, (1,)), (0, (1, 1)))
        coefficients = tuple(map(Fraction, (2, -3, 5, -7, 11, -13)))
        kernel = kernel_mod.compile_kernel_bytes(
            source_bytes(3, 2, labels, coefficients))
        support = scheduled.ScheduledSupport.from_schedule(
            3, Fraction("2/3"), Fraction("1/9"), Fraction("3/5"),
            tuple(map(Fraction, ("1/5", "5/18", "1/3"))))
        direct = grouped.GroupedEvaluator(
            support, labels, coefficients, Fraction)
        denominator, groups, faces = direct.evaluate_i(False, 1)
        j_value, components, integrals = direct.evaluate_j(False, 1)
        expected = {
            "denominator": denominator,
            "j_value": j_value,
            "numerator": 3 * j_value,
            "i_orbit_groups": groups,
            "i_faces": faces,
            "marginal_components": components,
            "j_branch_integrals": integrals,
        }
        self.assertEqual(expected,
                         kernel_mod.evaluate_kernel(support, kernel, Fraction, 1))
        self.assertEqual(expected,
                         kernel_mod.evaluate_kernel(support, kernel, Fraction, 2))

    def test_strict_source_rejections(self):
        good = source_bytes(1, 0, ((0, ()),), (Fraction(1),))
        kernel_mod.compile_kernel_bytes(good)

        duplicate = (b'{"k":1,"k":2,"degree":0,"basis_dimension":1,'
                     b'"basis":[[0,[]]],"rational_vector":["1"]}')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            kernel_mod.compile_kernel_bytes(duplicate)

        floating = (b'{"k":1,"degree":0,"basis_dimension":1,'
                    b'"basis":[[0,[]]],"rational_vector":[1.0]}')
        with self.assertRaisesRegex(ValueError, "float"):
            kernel_mod.compile_kernel_bytes(floating)

        noncanonical = json.loads(good)
        noncanonical["rational_vector"] = ["2/2"]
        with self.assertRaisesRegex(ValueError, "noncanonical"):
            kernel_mod.compile_kernel_bytes(json.dumps(noncanonical).encode())

    def test_kernel_changes_only_at_replay(self):
        labels = ((0, ()), (0, (1,)))
        coefficients = (Fraction(1), Fraction(-2))
        data = source_bytes(2, 1, labels, coefficients)
        kernel = kernel_mod.compile_kernel_bytes(data)
        summary = kernel_mod.kernel_summary(kernel)
        support1 = ei.OneStratumSupport(
            2, *map(Fraction, ("3/5", "1/10", "1/2", "1/5", "1/4", "3/10")))
        support2 = ei.OneStratumSupport(
            2, *map(Fraction, ("5/8", "1/8", "21/40", "3/20", "9/50", "1/5")))
        forms1 = kernel_mod.evaluate_kernel(support1, kernel)
        forms2 = kernel_mod.evaluate_kernel(support2, kernel)
        self.assertNotEqual(forms1["denominator"], forms2["denominator"])
        self.assertEqual(summary, kernel_mod.kernel_summary(kernel))
        self.assertFalse(summary["rigorous"])
        self.assertFalse(summary["theorem_ready"])


if __name__ == "__main__":
    unittest.main()
