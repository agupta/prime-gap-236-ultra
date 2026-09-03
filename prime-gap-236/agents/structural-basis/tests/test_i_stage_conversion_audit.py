#!/usr/bin/env python3
"""Independent provenance tests for the legacy Decimal C10 I-stage conversion.

These tests establish discovery provenance only.  They do not make a Decimal
calculation rigorous and do not authorize a converted stage in the final exact
certificate run.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
AGENTS = HERE.parents[1]
EXACT = AGENTS / "exact-integrator"
RESULTS = EXACT / "results"
RAW = RESULTS / "c10_capped_fullD12_vector_grouped_mp100.json.I-stage.json"
CONVERTED = RESULTS / "c10_capped_fullD12_vector_grouped_mp100.converted.I-stage.json"
INPUT = RESULTS / "hb_c10_fullsimplex_noones_D12.json"
DRIVER = EXACT / "grouped_fixed_vector.py"
INTEGRATOR = EXACT / "src" / "exact_integrator.py"
CONVERTER = EXACT / "convert_legacy_mp_stage.py"

OLD_SHA = "9ee84b1a1a05c884b37f70bd68680bf5ed8650bd5d1aa0afa63fe4a0db3ae298"
NEW_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
EI_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
CONVERTER_SHA = "564ce9adb3cce12a165e42e79cbd3920877338162c5a251581eb62adcc922e58"
RAW_SHA = "f69847971d40ba0abe916a42c63533f32b0012b7441df9b7483314a5a188e38b"
CONVERTED_SHA = "9441f2b227b761fd71f61211f16308eed77f95eddfe9458957a111b504424eaa"
INPUT_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"

PARAMETERS = {
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
    "beta1": "3/20",
    "beta2": "3/20",
    "beta3plus": "97/625",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def conversion_command(source: Path, output: Path) -> list[str]:
    return [
        sys.executable, str(CONVERTER), str(source), str(output),
        "--expected-old-script-sha", OLD_SHA,
        "--expected-new-script-sha", NEW_SHA,
        "--expected-integrator-sha", EI_SHA,
    ]


class IStageConversionAudit(unittest.TestCase):
    def test_pinned_hashes_and_payload_preservation(self) -> None:
        self.assertEqual(sha(RAW), RAW_SHA)
        self.assertEqual(sha(CONVERTED), CONVERTED_SHA)
        self.assertEqual(sha(INPUT), INPUT_SHA)
        self.assertEqual(sha(DRIVER), NEW_SHA)
        self.assertEqual(sha(INTEGRATOR), EI_SHA)
        self.assertEqual(sha(CONVERTER), CONVERTER_SHA)

        raw = json.loads(RAW.read_bytes())
        converted = json.loads(CONVERTED.read_bytes())
        record = converted.pop("legacy_nonrigorous_conversion")
        attached = converted.pop("integrator_sha256")
        self.assertEqual(converted, raw)
        self.assertEqual(converted["denominator"], raw["denominator"])
        self.assertEqual(converted["parameters"], PARAMETERS)
        self.assertEqual(attached, EI_SHA)
        self.assertEqual(record, {
            "source_stage_sha256": RAW_SHA,
            "origin_script_sha256": OLD_SHA,
            "resume_script_sha256": NEW_SHA,
            "attached_integrator_sha256": EI_SHA,
            "conversion_script_sha256": CONVERTER_SHA,
            "scope": "non-rigorous Decimal discovery only",
        })
        source = json.loads(INPUT.read_bytes())
        self.assertEqual(source["k"], 48)
        self.assertEqual(len(source["basis"]), 272)
        self.assertEqual(len(source["rational_vector"]), 272)
        self.assertEqual(len({(a, tuple(lam)) for a, lam in source["basis"]}), 272)

    def test_converter_reproduces_production_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "converted.json"
            completed = subprocess.run(conversion_command(RAW, output),
                                       capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(output.read_bytes(), CONVERTED.read_bytes())

    def test_converter_rejects_core_mutations(self) -> None:
        original = json.loads(RAW.read_bytes())
        mutations = {
            "rigorous": lambda d: d.__setitem__("rigorous", True),
            "decimal_mode": lambda d: d.__setitem__("decimal_dps", None),
            "incomplete": lambda d: d.__setitem__("i_complete", False),
            "nonpositive": lambda d: d.__setitem__("denominator_positive", False),
            "already_hashed": lambda d: d.__setitem__("integrator_sha256", EI_SHA),
            "old_driver": lambda d: d.__setitem__("script_sha256", "0" * 64),
            "input": lambda d: d.__setitem__("input_sha256", "0" * 64),
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for name, mutate in mutations.items():
                with self.subTest(name=name):
                    bad = json.loads(json.dumps(original))
                    mutate(bad)
                    source = tmp_path / f"{name}.json"
                    output = tmp_path / f"{name}.out.json"
                    source.write_text(json.dumps(bad), encoding="utf-8")
                    completed = subprocess.run(conversion_command(source, output),
                                               capture_output=True, text=True,
                                               check=False)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertFalse(output.exists())

    def test_old_and_current_i_algorithms_agree_at_decimal_precision(self) -> None:
        # Re-evaluate only I for the tiny C20 D4 regression under the final
        # driver.  The old SHA's preserved stage has the same 20 groups and 90
        # faces; the one-ulp-scale difference is only Decimal summation order.
        module_spec = importlib.util.spec_from_file_location("grouped_final", DRIVER)
        module = importlib.util.module_from_spec(module_spec)
        assert module_spec.loader is not None
        module_spec.loader.exec_module(module)
        d4_input = RESULTS / "hb_a2558_eps005_cut_noones_D4.json"
        source = json.loads(d4_input.read_bytes())
        labels = [(int(a), tuple(int(x) for x in lam))
                  for a, lam in source["basis"]]
        table = module.precompute_orbits(labels, int(source["k"]))
        scalar = module.install_decimal(table, 80)
        values = [module.parse_rational_decimal(x) for x in
                  ("163/625", "1/50", "627/2500",
                   "3/20", "3/20", "17/100")]
        support = module.ei.OneStratumSupport(48, *values)
        coefficients = [module.parse_rational_decimal(x)
                        for x in source["rational_vector"]]
        evaluator = module.GroupedEvaluator(support, labels, coefficients, scalar)
        current, groups, faces = evaluator.evaluate_i(workers=1)
        old_stage = json.loads((RESULTS /
            "grouped_mp80_c20_D4_bounded_regression.json.I-stage.json").read_bytes())
        old = Decimal(old_stage["denominator"])
        self.assertEqual((groups, faces),
                         (old_stage["i_orbit_groups"], old_stage["i_faces"]))
        self.assertLess(abs(current - old) / abs(current), Decimal("2e-79"))

        # Both Decimal paths also agree with the independently checked exact
        # Fraction result well beyond what is needed for a discovery sign.
        exact_result = json.loads((RESULTS /
            "grouped_exact_c20_D4_parallel2_regression.json").read_bytes())
        exact_fraction = Fraction(exact_result["denominator"])
        getcontext().prec = 120
        exact = (Decimal(exact_fraction.numerator) /
                 Decimal(exact_fraction.denominator))
        self.assertLess(abs(old - exact) / abs(exact), Decimal("1e-62"))

    def test_final_resume_regression_and_override_scope(self) -> None:
        old_result = json.loads((RESULTS /
            "grouped_mp80_c20_D4_bounded_regression.json").read_bytes())
        stage = json.loads((RESULTS /
            "grouped_mp80_c20_D4_bounded_regression.converted.I-stage.json").read_bytes())
        resumed = json.loads((RESULTS /
            "grouped_mp80_c20_D4_converted_resume_regression.json").read_bytes())
        self.assertEqual(Decimal(stage["denominator"]),
                         Decimal(resumed["denominator"]))
        self.assertEqual(old_result["quotient"], resumed["quotient"])
        self.assertEqual(resumed["script_sha256"], NEW_SHA)
        self.assertEqual(resumed["integrator_sha256"], EI_SHA)

        # Without the explicit non-rigorous old-SHA allowance, the final
        # driver rejects the converted D4 stage before any J integration.
        command = [
            sys.executable, str(DRIVER),
            str(RESULTS / "hb_a2558_eps005_cut_noones_D4.json"),
            "--alpha", "163/625", "--delta", "1/50",
            "--eta", "627/2500", "--beta1", "3/20",
            "--beta2", "3/20", "--beta3plus", "17/100",
            "--decimal-dps", "80", "--resume-i-stage",
            str(RESULTS /
                "grouped_mp80_c20_D4_bounded_regression.converted.I-stage.json"),
        ]
        completed = subprocess.run(command, capture_output=True, text=True,
                                   check=False)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("I-stage mismatch for script_sha256",
                      completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
