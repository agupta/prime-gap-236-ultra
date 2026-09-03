#!/usr/bin/env python3
"""Light hostile tests for the C722 one-worker fixed-vector driver."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
TARGET = HERE / "c722_scheduled_fixed_driver.py"
SPEC = importlib.util.spec_from_file_location("c722_driver_tested", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError("cannot load C722 driver")
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)


def source_bytes(k, degree, labels, coefficients):
    return D.canonical_json_bytes({
        "k": k,
        "degree": degree,
        "basis_dimension": len(labels),
        "basis": [[a, list(lam)] for a, lam in labels],
        "rational_vector": [str(Fraction(value)) for value in coefficients],
    })


class C722DriverTests(unittest.TestCase):
    def test_00_preloaded_arithmetic_module_rejected(self):
        self.assertIsNone(D._DEPENDENCIES)
        self.assertNotIn("exact_integrator", sys.modules)
        sys.modules["exact_integrator"] = types.ModuleType("exact_integrator")
        try:
            with self.assertRaisesRegex(ValueError, "preloaded arithmetic"):
                D.load_dependencies()
        finally:
            del sys.modules["exact_integrator"]
        self.assertIsNone(D._DEPENDENCIES)

    def test_01_dual_schedule_identity_and_low_k_exact_oracle(self):
        ei, grouped, scheduled, kernel_mod, amplitude_mod = D.load_dependencies()
        schedule_snapshot = D.pinned_snapshot(D.C722_SCHEDULE, "schedule")
        schedule = D.load_schedule(schedule_snapshot, scheduled)
        self.assertEqual(len(schedule), 28)
        self.assertEqual(
            D.sha256_bytes(scheduled.canonical_schedule_bytes(schedule)),
            D.C722_EVALUATOR_SCHEDULE_SHA256)
        analytic = ("\n".join(
            f"{x.numerator}/{x.denominator}" for x in schedule) +
            "\n").encode("ascii")
        self.assertEqual(D.sha256_bytes(analytic),
                         D.C722_ANALYTIC_SCHEDULE_SHA256)

        labels = ((0, ()), (1, ()), (0, (1,)), (0, (2,)),
                  (1, (1,)), (0, (1, 1)))
        coefficients = tuple(map(Fraction, (2, -3, 5, -7, 11, -13)))
        kernel = kernel_mod.compile_kernel_bytes(
            source_bytes(3, 2, labels, coefficients))
        support = scheduled.ScheduledSupport.from_schedule(
            3, Fraction(2, 3), Fraction(1, 9), Fraction(3, 5),
            tuple(map(Fraction, ("1/5", "5/18", "1/3"))))
        direct = grouped.GroupedEvaluator(
            support, labels, coefficients, Fraction)
        direct_i, direct_groups, direct_faces = direct.evaluate_i(False, 1)
        direct_j, direct_components, direct_integrals = direct.evaluate_j(False, 1)
        self.assertEqual(
            kernel_mod.evaluate_kernel(support, kernel, Fraction, 1), {
                "denominator": direct_i,
                "j_value": direct_j,
                "numerator": 3 * direct_j,
                "i_orbit_groups": direct_groups,
                "i_faces": direct_faces,
                "marginal_components": direct_components,
                "j_branch_integrals": direct_integrals,
            })

    def test_02_strict_parsers_and_normalized_exact_payload(self):
        for payload in (b'{"x":1,"x":2}', b'{"x":1.5}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                D.strict_json_bytes(payload, "hostile")
        with self.assertRaises(ValueError):
            D.exact_int(True, "Boolean")
        with self.assertRaises(ValueError):
            D.canonical_fraction("2/2", "fraction")

        historical = D.canonical_json_bytes({
            "k": 1, "degree": 0, "basis_dimension": 1,
            "basis": [[0, []]], "rational_vector": ["1"],
            "irrelevant": "discovery field omitted",
        })
        normalized = D.normalized_kernel_source_bytes({"data": historical})
        self.assertEqual(D.strict_json_bytes(normalized, "normalized"), {
            "k": 1, "degree": 0, "basis_dimension": 1,
            "basis": [[0, []]], "rational_vector": ["1"],
        })

    def test_03_stage_and_memory_gates_fail_closed(self):
        def snapshot(label, digest):
            return {"path": f"/tmp/{label}", "sha256": digest,
                    "device": 1, "inode": len(label), "data": b""}

        gate = snapshot("gate", "1" * 64)
        auth = snapshot("auth", "2" * 64)
        source = snapshot("source", D.PINNED_SHA256[
            str(D.D12_SOURCE.relative_to(D.REPO_ROOT))])
        schedule = snapshot("schedule", D.PINNED_SHA256[
            str(D.C722_SCHEDULE.relative_to(D.REPO_ROOT))])
        raw = {
            "status": "c722-d12-decimal100-one-worker-I-stage",
            "complete": True, "rigorous": False, "theorem_ready": False,
            "decimal_dps": 100, "workers": 1,
            "driver_sha256": "3" * 64,
            "gate_binding": D.public_binding(gate),
            "authorization_binding": D.public_binding(auth),
            "source_binding": D.public_binding(source),
            "schedule_binding": D.public_binding(schedule),
            "analytic_schedule_sha256": D.C722_ANALYTIC_SCHEDULE_SHA256,
            "evaluator_schedule_sha256": D.C722_EVALUATOR_SCHEDULE_SHA256,
            "parameters": D.C722_PARAMETERS,
            "basis_dimension": 272,
            "kernel_summary": D.EXPECTED_D12_KERNEL_SUMMARY,
            "i_orbit_groups": 1575,
            "i_faces": 625,
            "i_seconds_hex": "0x1.0000000000000p+0",
            "peak_rss_kib": 1000,
            "denominator_positive": True,
            "denominator": "1",
            "memory_readings": [
                {"mem_available_kib": 1_500_000, "pswpout_pages": 10},
                {"mem_available_kib": 1_500_001, "pswpout_pages": 10},
            ],
            "dependency_sha256s": D.PINNED_SHA256,
        }
        self.assertTrue(D.validate_stage(
            raw, gate_snapshot=gate, authorization_snapshot=auth,
            source_snapshot=source, schedule_snapshot=schedule,
            driver_sha="3" * 64))
        malformed = dict(raw)
        malformed["denominator"] = True
        with self.assertRaises(ValueError):
            D.validate_stage(
                malformed, gate_snapshot=gate, authorization_snapshot=auth,
                source_snapshot=source, schedule_snapshot=schedule,
                driver_sha="3" * 64)

        resource_gate = {
            "memory_readings_required": 2,
            "minimum_mem_available_kib": 1_400_000,
            "maximum_swapout_page_growth": 0,
        }
        self.assertTrue(D.validate_memory_readings(
            raw["memory_readings"], resource_gate))
        low = [dict(item) for item in raw["memory_readings"]]
        low[1]["mem_available_kib"] = 1_399_999
        with self.assertRaises(MemoryError):
            D.validate_memory_readings(low, resource_gate)
        swapping = [dict(item) for item in raw["memory_readings"]]
        swapping[1]["pswpout_pages"] = 11
        with self.assertRaises(MemoryError):
            D.validate_memory_readings(swapping, resource_gate)

    def test_04_oexcl_publication_and_dependency_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dependency = root / "dependency.txt"
            dependency.write_bytes(b"fixed")
            binding = D.public_binding(D.read_snapshot(dependency, "dependency"))
            output = root / "output.json"
            digest = D.publish_new_json(
                output, {"status": "synthetic-pass"},
                {str(dependency): binding})
            self.assertEqual(D.sha256_file(output), digest)
            with self.assertRaises(FileExistsError):
                D.publish_new_json(
                    output, {"status": "must-not-overwrite"},
                    {str(dependency): binding})
            with self.assertRaises(ValueError):
                D.validate_output_path(dependency, [dependency])

            dependency2 = root / "dependency2.txt"
            dependency2.write_bytes(b"before")
            binding2 = D.public_binding(
                D.read_snapshot(dependency2, "dependency2"))
            rejected = root / "rejected.json"
            original = D.verify_binding
            calls = 0

            def mutate_second(value, name):
                nonlocal calls
                calls += 1
                if calls == 2:
                    dependency2.write_bytes(b"after")
                return original(value, name)

            with mock.patch.object(D, "verify_binding",
                                   side_effect=mutate_second):
                with self.assertRaises(ValueError):
                    D.publish_new_json(
                        rejected, {"status": "must-reject-mutation"},
                        {str(dependency2): binding2})
            self.assertEqual(
                json.loads(rejected.read_text())["status"],
                "rejected-incomplete-c722-output")


if __name__ == "__main__":
    unittest.main()
