#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("frontier_inner_d16_tagged_shell.py")
SPEC = importlib.util.spec_from_file_location("frontier_inner_shell", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class FrontierInnerShellTests(unittest.TestCase):
    def test_frozen_candidate_identity(self):
        self.assertTrue(M.require_pins())
        M.validate_analytic()
        self.assertEqual(M.SCHEDULE[:3],
                         (Q(597, 5000), Q(633, 5000), Q(669, 5000)))
        self.assertEqual(M.SCHEDULE[9:], (Q(3321, 20000),) * 14)
        basis, vector, amplitudes, denominator, numerator = \
            M.load_inner_coordinate()
        self.assertEqual((len(basis), len(vector)), (307, 307))
        self.assertEqual(amplitudes[0], 1)
        self.assertGreater(denominator, numerator)

    def test_low_k_target_tagging_against_canonical_j(self):
        # Same support on both sides reduces to exact_integrator's independent
        # canonical basis_j recurrence.  Signed coefficients catch dropped
        # components; summing target tags catches branch ownership.
        k = 3
        delta = Q(1, 10)
        alpha = Q(2, 5)
        eta = Q(3, 10)
        schedule = (alpha,) * k
        support = M.shell.ScheduledStratumSupport.make(
            k, alpha, eta, delta, schedule)
        labels = ((0, ()), (1, ()), (0, (2,)))
        coefficients = (Q(2), Q(-3), Q(5))
        components = M.outer_core.components(labels, coefficients, k)
        one = (((), 0, 0, Q(1)),)
        named = {"P": (support, components), "C": (support, one)}
        tables, counts, faces = M.tagged_cross_catalog(
            named, (("pc", "P", "C"),), eta)
        got = sum(tables["pc"], Q(0))
        expected = sum(coefficients[i] * support.basis_j(label, (0, ()))
                       for i, label in enumerate(labels))
        self.assertEqual(got, expected)
        self.assertGreater(counts["pc"], 0)
        self.assertGreater(faces, 0)

    def test_low_k_shell_polarization_and_count_support(self):
        k = 3
        delta = Q(1, 10)
        eta = Q(3, 10)
        schedule = (Q(1, 4), Q(3, 10), Q(7, 20))
        high = M.shell.ScheduledStratumSupport.make(
            k, Q(2, 5), eta, delta, schedule)
        low = M.shell.ScheduledStratumSupport.make(
            k, Q(7, 20), eta, delta, schedule)
        hh, _ = M.shell.cross_constant_stratum_table(high, high, eta)
        hl, _ = M.shell.cross_constant_stratum_table(high, low, eta)
        ll, _ = M.shell.cross_constant_stratum_table(low, low, eta)
        aggregate = sum((hh[i][j] - hl[i][j] - hl[j][i] + ll[i][j]
                         for i in range(k + 1) for j in range(k + 1)), Q(0))
        direct = (high.basis_j((0, ()), (0, ())) +
                  low.basis_j((0, ()), (0, ())) -
                  2 * sum((hl[i][j] for i in range(k + 1)
                           for j in range(k + 1)), Q(0)))
        self.assertEqual(aggregate, direct)
        self.assertTrue(all(hh[i][j] == 0 for i in range(k + 1)
                            for j in range(k + 1) if abs(i - j) > 1))

    def test_catalog_sign_and_selected_face(self):
        k = 2
        delta = Q(1, 10)
        alpha = Q(2, 5)
        eta = Q(3, 10)
        schedule = (alpha,) * k
        support = M.shell.ScheduledStratumSupport.make(
            k, alpha, eta, delta, schedule)
        one = (((), 0, 0, Q(1)),)
        named = {"A": (support, one), "B": (support, one)}
        tables, _, faces = M.tagged_cross_catalog(
            named, (("ab", "A", "B"), ("ba", "B", "A")), eta,
            common_strata=(1,), selected_h=0)
        self.assertEqual(tables["ab"], tables["ba"])
        self.assertEqual(faces, 1)
        with self.assertRaises(ValueError):
            M.tagged_cross_catalog(
                named, (("ab", "A", "B"),), eta, selected_h=0)

    def test_grouped_weighted_matches_literal_all_dimensions(self):
        # Exercise a genuine polygon (k=3), a w interval (r=0), a z
        # interval (k=2,r=1), and the zero-dimensional k=1 case.  Signed
        # weights force cancellation across distinct support pairs.
        for k, selected_r in ((3, None), (2, (0,)), (2, (1,)), (1, (0,))):
            delta = Q(1, 10)
            alpha = Q(2, 5)
            eta = Q(3, 10)
            schedule = (alpha,) * k
            support = M.shell.ScheduledStratumSupport.make(
                k, alpha, eta, delta, schedule)
            labels = ((0, ()), (1, ()))
            coefficients = (Q(2), Q(-3))
            components = M.outer_core.components(labels, coefficients, k)
            one = (((), 0, 0, Q(1)),)
            named = {"P": (support, components), "C": (support, one)}
            catalog = (("plus", "P", "C"),
                       ("minus", "P", "C"))
            weights = {"plus": Q(5, 7), "minus": Q(-2, 9)}
            kwargs = {} if selected_r is None else {
                "common_strata": selected_r}
            literal, counts, faces = M.tagged_cross_catalog(
                named, catalog, eta, **kwargs)
            expected = [weights["plus"] * literal["plus"][r] +
                        weights["minus"] * literal["minus"][r]
                        for r in range(k + 1)]
            got, grouped_counts, geometric, nonzero, grouped_faces = \
                M.grouped_weighted_cross(
                    named, catalog, weights, eta, **kwargs)
            self.assertEqual(got, expected)
            self.assertEqual(grouped_counts, counts)
            self.assertEqual(grouped_faces, faces)
            self.assertLessEqual(nonzero, geometric)
            self.assertGreaterEqual(geometric, nonzero)
            direct, direct_counts, _, _, direct_faces = \
                M.grouped_weighted_cross(
                    named, catalog, weights, eta,
                    direct_full_left=("P",), **kwargs)
            self.assertEqual(direct, expected)
            self.assertEqual(direct_faces, faces)
            self.assertLessEqual(sum(direct_counts.values()),
                                 sum(counts.values()))

        with self.assertRaises(ValueError):
            M.grouped_weighted_cross(
                named, catalog, {"plus": Q(1)}, eta)
        with self.assertRaises(ValueError):
            M.grouped_weighted_cross(
                named, catalog, weights, eta, direct_full_left=("C",))

    def test_exclusive_publication(self):
        with self.assertRaises(ValueError):
            M.publish(M.ANALYTIC, b"bad\n")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe.json"
            M.publish(path, b"{}\n")
            self.assertEqual(path.read_bytes(), b"{}\n")
            with self.assertRaises(FileExistsError):
                M.publish(path, b"replacement\n")


if __name__ == "__main__":
    unittest.main()
