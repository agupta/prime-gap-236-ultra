#!/usr/bin/env python3

import copy
import importlib.util
import sys
import unittest
from decimal import Decimal
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve()
SOURCE = HERE.parents[1] / "code" / "bv_d18_refinement_plan.py"
SPEC = importlib.util.spec_from_file_location("bv_d18_plan_tested", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load D18 refinement plan")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class BvD18RefinementPlanTests(unittest.TestCase):
    def test_exact_basis_and_entry_inventory(self):
        plan = M.build_plan()
        self.assertEqual(plan["target"]["basis_dimension"], 471)
        self.assertEqual(plan["target"]["symmetric_entry_count"], 111156)
        entries = plan["resource_estimates"]["symmetric_entries"]
        self.assertEqual(entries, {
            "D14": 19110, "D16": 47278, "D18": 111156,
            "new_D14_to_D16": 28168,
            "new_D16_to_D18": 63878})
        self.assertEqual(M.exact.even_basis(18)[:307],
                         M.exact.even_basis(16))

    def test_historical_trace_exposes_underconvergence(self):
        _, _, certificate = M.validate_completed_artifacts()
        diagnostic = M.d16_convergence_diagnostic(certificate)
        gains = [Decimal(value)
                 for value in diagnostic["forty_iteration_gains"]]
        ratios = [Decimal(value)
                  for value in diagnostic["successive_gain_ratios"]]
        self.assertTrue(all(left > right
                            for left, right in zip(gains, gains[1:])))
        self.assertGreater(gains[-1], Decimal("1e-12"))
        self.assertLess(ratios[-1], Decimal("0.08"))
        self.assertGreater(ratios[-1], Decimal("0.06"))
        self.assertGreater(
            Decimal(diagnostic["geometric_tail_estimate_after_320"]),
            Decimal("7e-13"))
        self.assertEqual(
            diagnostic["additional_iterations_to_gain_threshold"]["1E-20"],
            320)

    def test_resource_plan_and_thresholds_are_predeclared(self):
        plan = M.build_plan()
        build = plan["resource_estimates"]["matrix_build"]
        refinement = plan["resource_estimates"]["decimal_refinement"]
        self.assertGreater(Q(build["linear_D18_seconds"]), 1800)
        self.assertLess(Q(build["linear_D18_seconds"]), 1900)
        self.assertEqual(
            Q(build["threefold_conservative_D18_seconds"]),
            3 * Q(build["linear_D18_seconds"]))
        self.assertEqual(refinement["primary_precision"], 180)
        self.assertEqual(refinement["primary_max_iterations"], 640)
        self.assertEqual(refinement["replay_precision"], 240)
        self.assertEqual(refinement["replay_iterations"], 160)
        ready = plan["adaptive_refinement"]["rationalization_readiness"]
        self.assertEqual(ready["maximum_geometric_tail_heuristic"], "1e-16")
        self.assertEqual(ready["maximum_two_vector_Ritz_gain"], "1e-18")

    def test_active_cache_is_neither_named_nor_read(self):
        plan = M.build_plan()
        encoded = M.canonical_json(plan)
        self.assertNotIn(b"bv_aquarter_sourcebound_v2.sqlite3", encoded)
        self.assertFalse(plan["active_D18_cache_read"])
        self.assertFalse(plan["active_D18_cache_modified"])
        self.assertFalse(plan["D18_refinement_run"])
        self.assertFalse(plan["D18_cache_free_checker_run"])

    def test_pruned_d20_inventory_and_cost_obstruction(self):
        _, d16, _ = M.validate_completed_artifacts()
        route = M.d20_pruned_route(d16)
        self.assertEqual(route["basis"]["D20_dimension"], 707)
        self.assertEqual(route["basis"]["new_B20_minus_B18_labels"], 236)
        labels = route["basis"]["new_labels"]
        self.assertEqual(len(labels), 236)
        self.assertEqual(route["basis"]["new_label_degree_counts"],
                         {"19": 97, "20": 139})
        self.assertEqual(labels[0], {
            "a": 19, "partition": [], "total_degree": 19})
        self.assertEqual(labels[-1], {
            "a": 0, "partition": [2] * 10, "total_degree": 20})
        self.assertEqual(
            [(row["a"], tuple(row["partition"])) for row in labels],
            M.exact.even_basis(20)[471:])
        scan = route["exact_one_coordinate_scan"]
        self.assertEqual(scan["base_new_cross_pairs"], 111156)
        self.assertEqual(scan["new_diagonal_pairs"], 236)
        selected = route["selected_block"]
        self.assertEqual(selected["selection_count"], 24)
        self.assertEqual(selected["additional_selected_off_diagonal_pairs"],
                         276)
        self.assertEqual(selected["incremental_pairs_after_D18"], 111668)
        self.assertEqual(selected["full_D20_incremental_pairs_after_D18"],
                         139122)
        self.assertEqual(selected["selected_total_symmetric_entries"],
                         122760)
        self.assertGreater(Q(selected["incremental_pair_fraction_of_full"]),
                           Q(4, 5))
        self.assertLess(Q(selected["total_matrix_fraction_of_full"]), Q(1, 2))
        gate = route["continuation_gate"]
        self.assertFalse(gate["pruned_D20_scan_authorized"])
        self.assertFalse(gate["full_D20_build_authorized"])

    def test_source_or_trace_mutation_rejects(self):
        relative = next(iter(M.PINNED))
        expected = M.PINNED[relative]
        M.PINNED[relative] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                M.validate_sources()
        finally:
            M.PINNED[relative] = expected
        _, _, certificate = M.validate_completed_artifacts()
        mutation = copy.deepcopy(certificate)
        mutation["power_trace"][-1][1] = mutation["power_trace"][-2][1]
        with self.assertRaises(ArithmeticError):
            M.d16_convergence_diagnostic(mutation)


if __name__ == "__main__":
    unittest.main()
