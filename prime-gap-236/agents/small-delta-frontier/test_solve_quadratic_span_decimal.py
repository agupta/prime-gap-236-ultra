#!/usr/bin/env python3
"""Hostile tests for the unlaunched Decimal span consumer."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location(
    "solve_quadratic_span_decimal", HERE / "solve_quadratic_span_decimal.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
RESULTS = ROOT / "agents" / "exact-integrator" / "results"


def write_json(path, payload):
    data = (json.dumps(payload, indent=2) + "\n").encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def make_stage(multiplier_sha):
    return {
        "status": "multiprecision-quadratic-transfer-I-stage",
        "rigorous": False,
        "complete": True,
        "decimal_dps": 100,
        "input_sha256": MOD.SCALED_INPUT_SHA,
        "multiplier_sha256": multiplier_sha,
        "parameters": MOD.builder.PARAMETERS,
        "dependency_hashes": MOD.TRANSFER_DEPENDENCIES,
        "i_orbit_groups": 1575,
        "i_faces": 312,
        "i_by_r": ["1"] * 16,
        "denominator": "16",
        "i_seconds": 1.0,
    }


def make_transfer(multiplier_sha, stage_path, stage_sha):
    return {
        "status": "multiprecision-transferred-quadratic-candidate",
        "rigorous": False,
        "complete": True,
        "space_note": "fixture",
        "theorem_ready": False,
        "decimal_dps": 100,
        "input_json": "scaled.json",
        "input_sha256": MOD.SCALED_INPUT_SHA,
        "multiplier_json": "multiplier.json",
        "multiplier_sha256": multiplier_sha,
        "parameters": MOD.builder.PARAMETERS,
        "dependency_hashes": MOD.TRANSFER_DEPENDENCIES,
        "fixed_basis_dimension": 272,
        "multiplier_dimension": 96,
        "i_stage_json": str(stage_path),
        "i_stage_sha256": stage_sha,
        "i_by_r": ["1"] * 16,
        "j_by_common_r": ["1"] + ["0"] * 15,
        "denominator": "16",
        "numerator": "48",
        "quotient": "3",
        "margin": "32",
        "margin_positive": True,
        "i_orbit_groups": 1575,
        "i_faces": 312,
        "marginal_components": 695,
        "j_branch_domains": 1200,
        "i_seconds": 1.0,
        "j_seconds": 1.0,
        "total_seconds": 2.0,
        "peak_rss_kib": 100,
        "gates": {key: True for key in MOD.TRANSFER_GATES},
        "gates_passed": True,
    }


class QuadraticSpanConsumerTests(unittest.TestCase):
    def test_pinned_base_scaling_and_factor(self):
        _, base = MOD.builder.read_pinned(
            RESULTS / "c10_capped_fullD12_vector_grouped_mp100.json",
            MOD.BASE_OUTPUT_SHA, "base")
        _, original = MOD.builder.read_pinned(
            RESULTS / "hb_c10_fullsimplex_noones_D12.json",
            MOD.ORIGINAL_INPUT_SHA, "original")
        _, scaled = MOD.builder.read_pinned(
            RESULTS / "hb_c10_fullsimplex_noones_D12_integer_scaled.json",
            MOD.SCALED_INPUT_SHA, "scaled")
        d0, n0 = MOD.validate_base(base)
        lcm = MOD.validate_scaled_input(scaled, original)
        self.assertGreater(lcm.bit_length(), 700)
        self.assertGreater(d0, 0)
        self.assertLess(n0, d0)

        bad = copy.deepcopy(base)
        bad["numerator"] = bad["j_value"]
        bad["quotient"] = str(Decimal(bad["numerator"]) /
                              Decimal(bad["denominator"]))
        bad["margin"] = str(Decimal(bad["numerator"]) -
                            Decimal(bad["denominator"]))
        with self.assertRaises(ValueError):
            MOD.validate_base(bad)

    def test_transfer_stage_schema_and_factor48(self):
        multiplier_sha = "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            stage_path = Path(directory) / "stage.json"
            stage_sha = write_json(stage_path, make_stage(multiplier_sha))
            payload = make_transfer(multiplier_sha, stage_path, stage_sha)
            self.assertEqual(
                MOD.validate_transfer(payload, multiplier_sha, stage_path,
                                      stage_sha, "fixture"),
                (Fraction(16), Fraction(48)))
            bad = copy.deepcopy(payload)
            bad["numerator"] = "1"
            bad["quotient"] = "0.0625"
            bad["margin"] = "-15"
            bad["margin_positive"] = False
            with self.assertRaises(ValueError):
                MOD.validate_transfer(bad, multiplier_sha, stage_path,
                                      stage_sha, "fixture")
            bad = copy.deepcopy(payload)
            bad["gates"]["counts_complete"] = False
            with self.assertRaises(ValueError):
                MOD.validate_transfer(bad, multiplier_sha, stage_path,
                                      stage_sha, "fixture")
            bad = copy.deepcopy(payload)
            bad["unexpected"] = 1
            with self.assertRaises(ValueError):
                MOD.validate_transfer(bad, multiplier_sha, stage_path,
                                      stage_sha, "fixture")

    def test_h_multiplier_exact_coordinate_reconstruction(self):
        _, source_raw = MOD.builder.read_pinned(
            RESULTS / "c10_stratum_quadratic_cappedopt_D4_exact.json",
            MOD.Q_MULTIPLIER_SHA, "Q")
        parsed = MOD.builder.parse_source(source_raw)
        s = Fraction(1, 1024)
        reconstructed = MOD.builder.reconstruct(parsed, s)
        payload = {key: None for key in MOD.H_MULTIPLIER_KEYS}
        base, q, cross, h = (reconstructed["base_forms"],
                             reconstructed["q_forms"],
                             reconstructed["cross_forms"],
                             reconstructed["h_forms"])
        payload.update({
            "status": "exact-stratum-quadratic-rational-vector",
            "construction": "H=Q+s*1 exact D4 span contingency",
            "rigorous_forms": True,
            "block_direct_bitwise_equal": True,
            "theorem_ready": False,
            "source_multiplier_sha256": MOD.Q_MULTIPLIER_SHA,
            "input_sha256": MOD.builder.INPUT_SHA,
            "script_sha256": MOD.BUILDER_SHA,
            "constant_scale_s": str(s),
            "rational_vector": [str(x) for x in reconstructed["h"]],
            "k": 48,
            "parameters": MOD.builder.PARAMETERS,
            "fixed_basis_dimension": 12,
            "quadratic_basis_dimension": 96,
            "discovery_basis_dimension": 93,
            "channel_powers": [list(x) for x in MOD.builder.CHANNEL_POWERS],
            "quadratic_labels": [[r, channel] for r in range(16)
                                 for channel in MOD.builder.CHANNELS],
            "active_quadratic_labels": [
                [r, channel] for r in range(16)
                for channel in MOD.builder.CHANNELS
                if (r, channel) not in MOD.builder.NULL_LABELS],
            "discarded_gram_dependent_labels":
                [list(x) for x in MOD.builder.NULL_LABELS],
            "dependency_hashes": {
                name: expected for name, (_path, expected)
                in MOD.builder.DEPENDENCIES.items()},
            "base_denominator": str(base[0]),
            "base_numerator": str(base[1]),
            "q_denominator": str(q[0]),
            "q_numerator": str(q[1]),
            "base_q_i_cross": str(cross[0]),
            "base_q_n_cross": str(cross[1]),
            "denominator": str(h[0]),
            "numerator": str(h[1]),
            "quotient": str(h[1] / h[0]),
            "margin": str(h[1] - h[0]),
            "denominator_positive": h[0] > 0,
            "margin_positive": h[1] > h[0],
            "i_orbit_groups": 20,
            "i_faces": 312,
            "marginal_components": 19,
            "j_branch_domains": 1200,
            "direct_i_faces": 312,
            "direct_j_branch_domains": 1200,
            "direct_seconds": 1.0,
            "d4_span_stationary": MOD.builder.d4_span_stationary(reconstructed),
            "exact_gates": {
                "source_q_forms_reconstructed": True,
                "block_sparse_bitwise_equal": True,
                "polarization_identity_exact": True,
                "fresh_direct_bitwise_equal": True,
                "direct_counts_complete": True,
                "denominator_positive": True,
            },
        })
        self.assertEqual(MOD.validate_h_multiplier(payload), s)
        bad = copy.deepcopy(payload)
        bad["rational_vector"][0] = str(
            Fraction(bad["rational_vector"][0]) + 1)
        with self.assertRaises(ValueError):
            MOD.validate_h_multiplier(bad)
        bad = copy.deepcopy(payload)
        bad["constant_scale_s"] = "0"
        with self.assertRaises(ValueError):
            MOD.validate_h_multiplier(bad)

    def test_polarization_and_projective_solve(self):
        base = (Fraction(1), Fraction(9, 10))
        q = (Fraction(1), Fraction(11, 10))
        cross = (Fraction(0), Fraction(1, 10))
        s = Fraction(2)
        h = (q[0] + 2 * s * cross[0] + s * s * base[0],
             q[1] + 2 * s * cross[1] + s * s * base[1])
        reconstructed, solution = MOD.reconstruct_span(base, q, h, s)
        self.assertEqual(reconstructed, cross)
        self.assertEqual(len(solution["ranked_projective_points"]), 3)
        self.assertGreater(Decimal(solution["maximum"]["quotient"]), Decimal(1))
        with self.assertRaises(ValueError):
            MOD.reconstruct_span(base, q, h, Fraction(0))
        with self.assertRaises(ValueError):
            MOD.solve_pencil(Fraction(1), Fraction(1), Fraction(1),
                             Fraction(1), Fraction(2), Fraction(0))

    def test_explicit_heuristic_opt_in_precedes_io(self):
        arguments = [
            "--base-output", "a", "--expect-base-sha256", MOD.BASE_OUTPUT_SHA,
            "--original-input", "b", "--expect-original-input-sha256",
            MOD.ORIGINAL_INPUT_SHA, "--scaled-input", "c",
            "--expect-scaled-input-sha256", MOD.SCALED_INPUT_SHA,
            "--q-output", "d", "--expect-q-output-sha256", "d" * 64,
            "--q-stage", "e", "--expect-q-stage-sha256", "e" * 64,
            "--h-multiplier", "f", "--expect-h-multiplier-sha256", "f" * 64,
            "--h-output", "g", "--expect-h-output-sha256", "1" * 64,
            "--h-stage", "h", "--expect-h-stage-sha256", "2" * 64,
            "--output", "i",
        ]
        with self.assertRaisesRegex(ValueError, "explicit heuristic opt-in"):
            MOD.main(arguments)


if __name__ == "__main__":
    unittest.main()
