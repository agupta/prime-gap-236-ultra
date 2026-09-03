#!/usr/bin/env python3

import hashlib
import importlib.util
import json
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
BUILDER_PATH = PROJECT/"agents/structural-basis/code/build_sparse_pair_core6.py"
MANIFEST_PATH = PROJECT/"agents/structural-basis/results/c10_D12_sparse_core6_pair_manifest_v2.json"
COORDINATE_MANIFEST = PROJECT/"agents/small-delta-frontier/results/c10_D12_sparse_coordinate_scan_manifest.json"
EXPECTED_BUILDER = "ac8186bd7d6e3b569e0b02b4385f8b55f9e5abb4b96cd89f68cef217fe9d2667"
EXPECTED_MANIFEST = "32d7e86840b0ba8a859cd41b30f3242bcde3cc8518e0a598f30a304e741ca4ad"
EXPECTED_COUNTS = {
    (10, 9): (9, 13, 6, 12, 4), (10, 6): (9, 13, 6, 6, 4),
    (9, 6): (4, 5, 2, 6, 4), (10, 8): (9, 13, 6, 18, 4),
    (9, 8): (9, 13, 6, 24, 4), (6, 8): (9, 13, 6, 18, 4),
    (10, 5): (9, 13, 6, 12, 4), (9, 5): (9, 13, 6, 18, 4),
    (6, 5): (9, 13, 6, 12, 4), (8, 5): (4, 5, 2, 10, 4),
    (10, 11): (16, 26, 5, 5, 4), (9, 11): (16, 26, 7, 13, 4),
    (6, 11): (16, 26, 7, 7, 4), (8, 11): (9, 14, 7, 19, 4),
    (5, 11): (9, 14, 7, 13, 4),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module():
    spec = importlib.util.spec_from_file_location("pair_builder_test", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SparsePairCore6Tests(unittest.TestCase):
    def test_frozen_package_exactly_reconstructs_signed_sums(self):
        self.assertEqual(sha(BUILDER_PATH), EXPECTED_BUILDER)
        self.assertEqual(sha(MANIFEST_PATH), EXPECTED_MANIFEST)
        manifest = json.loads(MANIFEST_PATH.read_text())
        coordinates = json.loads(COORDINATE_MANIFEST.read_text())
        by_coordinate = {item["coordinate"]: item
                         for item in coordinates["full_ranking"]}
        self.assertEqual(manifest["coordinates"], [10, 9, 6, 8, 5, 11])
        self.assertEqual(manifest["pair_semantics"], "unscaled_sum")
        self.assertEqual(len(manifest["pairs"]), 15)
        self.assertEqual({tuple(sorted(item["coordinates"]))
                          for item in manifest["pairs"]},
                         {tuple(sorted(pair)) for pair in EXPECTED_COUNTS})
        for entry in manifest["pairs"]:
            pair = tuple(entry["coordinates"])
            path = Path(entry["input_path"])
            self.assertEqual(sha(path), entry["input_sha256"])
            payload = json.loads(path.read_text())
            left = json.loads(Path(by_coordinate[pair[0]]["path"]).read_text())
            right = json.loads(Path(by_coordinate[pair[1]]["path"]).read_text())
            self.assertEqual(payload["basis"], left["basis"]+right["basis"])
            self.assertEqual(payload["rational_vector"],
                             left["rational_vector"]+right["rational_vector"])
            expected_compressed = [
                str(Fraction(left["orientation"] if i == pair[0] else
                             right["orientation"] if i == pair[1] else 0))
                for i in range(20)]
            self.assertEqual(payload["compressed_direction"], expected_compressed)
            counts = payload["expected_grouped_counts"]
            observed = tuple(counts[key] for key in
                             ("precomputed_orbit_keys", "precomputed_orbit_terms",
                              "i_orbit_groups", "i_grouped_residual_terms",
                              "marginal_components"))
            self.assertEqual(observed, EXPECTED_COUNTS[pair])
            self.assertEqual(counts["direction_labels"], 2)
            self.assertEqual(counts["i_faces"], 312)
            self.assertEqual(counts["j_branch_integrals"], 1200)
            self.assertEqual(payload["provenance"]["builder_sha256"],
                             EXPECTED_BUILDER)
            self.assertEqual(entry["i_stage_path"],
                             str(path).replace("_direction.json",
                                               "_self_mp100.I-stage.json"))
            self.assertEqual(entry["result_path"],
                             str(path).replace("_direction.json",
                                               "_self_mp100.json"))

    def test_batches_are_nested_clique_completion(self):
        manifest = json.loads(MANIFEST_PATH.read_text())
        seen = set()
        completed_sizes = []
        recorded = set()
        for batch_number, batch in enumerate(manifest["batches"], 1):
            self.assertLessEqual(len(batch), 3)
            seen.update(tuple(sorted(pair)) for pair in batch)
            for size in range(2, 7):
                prefix = manifest["coordinates"][:size]
                clique = {tuple(sorted((prefix[i], prefix[j])))
                          for i in range(size) for j in range(i)}
                if clique.issubset(seen) and size not in recorded:
                    completed_sizes.append((batch_number, size))
                    recorded.add(size)
        self.assertEqual(completed_sizes,
                         [(1, 2), (1, 3), (2, 4), (4, 5), (5, 6)])

    def test_polarization_factor_two(self):
        Aii, Ajj, Aij = Fraction(2), Fraction(5), Fraction(-3, 7)
        Bii, Bjj, Bij = Fraction(11), Fraction(13), Fraction(4, 9)
        Asum = Aii+Ajj+2*Aij
        Bsum = Bii+Bjj+2*Bij
        self.assertEqual((Asum-Aii-Ajj)/2, Aij)
        self.assertEqual((Bsum-Bii-Bjj)/2, Bij)
        self.assertNotEqual(Bsum-Bii-Bjj, Bij)

    def test_publish_rejects_alias_and_detects_trusted_mutation(self):
        builder = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trusted_path = root/"trusted"
            trusted_path.write_bytes(b"old")
            with self.assertRaises(ValueError):
                builder.publish({trusted_path: b"new"}, {trusted_path: b"old"})
            output = root/"output"
            trusted_path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                builder.publish({output: b"payload"}, {trusted_path: b"old"})
            self.assertTrue(output.exists())
            rejection = json.loads(output.read_text())
            self.assertEqual(rejection["status"], "REJECTED")
            self.assertEqual(trusted_path.read_bytes(), b"changed")


if __name__ == "__main__":
    unittest.main()
