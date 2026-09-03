#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / "code" /
          "active25_cap_slack_cross_face_gate_v3.py")
SPEC = importlib.util.spec_from_file_location("active25_cap_face_gate_v3_test",
                                              SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class Active25CapFaceGateV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pilot = M.load_pilot()

    def test_frozen_reviewed_inputs_and_fixed_scope(self):
        self.assertEqual(M.require_pins(), {
            str(path.relative_to(M.REPO)): digest
            for path, digest in sorted(M.PINNED.items(), key=lambda row: str(row[0]))
        })
        self.assertEqual((M.COMMON_R, M.SELECTED_H), (10, 10))
        self.assertEqual(M.WALL_LIMIT_SECONDS, 20)
        self.assertEqual(M.RSS_LIMIT_KIB, 262144)

    def test_literal_positive_degree_oracles(self):
        records = M.literal_positive_degree_oracles(self.pilot)
        self.assertEqual(len(records), 8)
        self.assertEqual({row["degree"] for row in records}, {1, 2})
        self.assertEqual({row["branch"] for row in records},
                         {"Sdelta", "Stotal", "Ltotal", "Lbig"})
        self.assertTrue(all(Q(row["literal"]) > 0 for row in records))

    def test_label_serialization_is_canonical_and_complete(self):
        labels = self.pilot.pilot_labels()
        values = {label: Q(label[0] + 1, label[1] + 1) for label in labels}
        rows = M._canonical_label_values(labels, values)
        self.assertEqual(len(rows), 38)
        self.assertEqual(rows[0], [0, 0, "1"])
        self.assertEqual(rows[-1], [25, 0, "26"])

    def test_no_target_stage_or_quotient_surface(self):
        source = SOURCE.read_text()
        self.assertNotIn("--stage-r", source)
        self.assertNotIn("exact_quotient", source)
        self.assertNotIn("attempt_001", source)
        self.assertFalse(hasattr(M, "assemble"))


if __name__ == "__main__":
    unittest.main()
