#!/usr/bin/env python3
"""Mutation tests for the independent D12 face-result consumer."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_stratum_moment_d12_face_benchmark as audit  # noqa: E402


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.gate = json.loads(audit.GATE.read_bytes())

    def fake(self, mode):
        values = [
            self.gate["worker_sha256"],
            self.gate["fused_engine_sha256"],
            self.gate["unfused_engine_sha256"],
            self.gate["d12_original_input_sha256"],
            self.gate["d12_scaled_input_sha256"],
        ] + [f"{i:064x}" for i in range(5)]
        dependencies = {f"/p/{i}": value for i, value in enumerate(values)}
        i_table = [[0, 0, "1"]]
        j_table = [[0, 0, 0, 0, 0, 0, "1"]]
        i_results = [{
            "face": face, "table": copy.deepcopy(i_table),
            "table_sha256": audit.sha256(json.dumps(
                i_table, separators=(",", ":")).encode("ascii")),
            "face_polynomial_seconds": 1.0,
            "aggregate_integral_seconds": 2.0,
            "scalar_integrals": 28,
        } for face in audit.EXPECTED_I_FACES]
        j_results = []
        for face in audit.EXPECTED_J_FACES:
            fused = mode == "fused"
            j_results.append({
                "face": face, "table": copy.deepcopy(j_table),
                "table_sha256": audit.sha256(json.dumps(
                    j_table, separators=(",", ":")).encode("ascii")),
                "branch_domains": 5, "fused_traversals": 5 if fused else 0,
                "logical_moment_products": 100, "scalar_integrals": 200,
                "orbit_pair_visits": 10 if fused else 0,
                "tagged_polynomial_multiplies": 20 if fused else 0,
                "density_visits": 30 if fused else 0,
                "density_tag_contractions": 40 if fused else 0,
                "branch_blocks_seconds": 1.0,
                "product_integral_seconds": 2.0,
            })
        return {
            "status": "exact-D12-degree3-fused-face-benchmark-pass",
            "rigorous_sample_forms": True, "theorem_ready": False,
            "scope": "test", "mode": mode, "k": 48, "base_degree": 12,
            "multiplier_degree": 3,
            "parameters": copy.deepcopy(audit.EXPECTED_PARAMETERS),
            "original_input_sha256": self.gate["d12_original_input_sha256"],
            "scaled_input_sha256": self.gate["d12_scaled_input_sha256"],
            "base_lcm_bits": 714, "basis_dimension": 272,
            "integer_vector_content": 1,
            "prelaunch_available_memory_mib": 1844,
            "required_prelaunch_available_memory_mib": 1844,
            "tag_schema": audit.independent_degree_three_schema(),
            "tag_schema_sha256": self.gate[
                "degree_three_tag_schema_sha256"],
            "selected_i_faces": copy.deepcopy(audit.EXPECTED_I_FACES),
            "selected_j_faces": copy.deepcopy(audit.EXPECTED_J_FACES),
            "i_orbit_groups": 1575, "marginal_components": 695,
            "i_setup_seconds": 1.0, "j_setup_seconds": 2.0,
            "i_results": i_results, "j_results": j_results,
            "total_seconds": 10.0, "peak_rss_kib": 50000,
            "dependency_hashes": dependencies,
        }

    def validate(self, value, mode):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            raw = (json.dumps(value, indent=2) + "\n").encode()
            path.write_bytes(raw)
            return audit.validate_worker_result(
                path, audit.sha256(raw), mode, self.gate)

    def test_valid_fused_and_unfused_and_d4(self):
        self.validate(self.fake("fused"), "fused")
        self.validate(self.fake("unfused"), "unfused")
        audit.validate_d4(self.gate)

    def test_schema_table_counter_and_memory_mutations_reject(self):
        mutations = []
        value = self.fake("fused")
        value["tag_schema"]["channels"][0][0] = True
        mutations.append(value)
        value = self.fake("fused")
        value["i_results"][0]["table"] = [[1, 0, "1"], [0, 0, "1"]]
        value["i_results"][0]["table_sha256"] = audit.sha256(json.dumps(
            value["i_results"][0]["table"],
            separators=(",", ":")).encode("ascii"))
        mutations.append(value)
        value = self.fake("fused")
        value["j_results"][0]["scalar_integrals"] = True
        mutations.append(value)
        value = self.fake("fused")
        value["prelaunch_available_memory_mib"] = 1843
        mutations.append(value)
        value = self.fake("fused")
        value["unexpected"] = 1
        mutations.append(value)
        for value in mutations:
            with self.assertRaises(audit.AnalysisError):
                self.validate(value, "fused")

    def test_fraction_and_table_hash_mutations_reject(self):
        for token in ("2/2", "01", "-0", True, 1):
            with self.assertRaises(audit.AnalysisError):
                audit.canonical_fraction(token, "mutation")
        value = self.fake("unfused")
        value["j_results"][1]["table_sha256"] = "0" * 64
        with self.assertRaises(audit.AnalysisError):
            self.validate(value, "unfused")


if __name__ == "__main__":
    unittest.main()
