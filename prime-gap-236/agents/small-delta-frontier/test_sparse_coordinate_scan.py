#!/usr/bin/env python3
"""Independent lightweight tests for the 19-coordinate sparse manifest."""

import hashlib
import json
import subprocess
import sys
import tempfile
from fractions import Fraction as F
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
GENERATOR = HERE/"build_sparse_coordinate_scan.py"
MANIFEST = HERE/"results/c10_D12_sparse_coordinate_scan_manifest.json"
SOURCE = PROJECT/"agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
BANDS = PROJECT/"agents/structural-basis/results/c10_D12_degree_bands.json"
RECOVERY = PROJECT/"agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json"


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def blocks():
    bands = load(BANDS)
    answer, names = [], []
    for i, item in enumerate(bands["core"]):
        key = (item["label"][0], tuple(item["label"][1]))
        answer.append({key: F(1)}); names.append(f"core_{i}:{key}")
    for degree in range(5, 13):
        answer.append({(x["label"][0], tuple(x["label"][1])): F(x["coefficient"])
                       for x in bands["bands"][str(degree)]})
        names.append(f"H{degree}")
    return answer, names


def test_all_directions_actions_and_ranking():
    manifest, recovery = load(MANIFEST), load(RECOVERY)
    all_blocks, names = blocks()
    entries = manifest["full_ranking"]
    require(manifest["coordinates_included"] == list(range(19)) and
            len(entries) == 19 and {x["coordinate"] for x in entries} == set(range(19)) and
            all(x["coordinate"] != 19 for x in entries), "19-coordinate coverage/gauge")
    D0, N0 = F(recovery["denominator"]), F(recovery["numerator"])
    aa = list(map(F, recovery["a_theta_exact_fraction_half"]))
    bb = list(map(F, recovery["b_theta_exact_fraction_half"]))
    theta = list(map(F, recovery["theta"]))
    observed_scores = []
    for entry in entries:
        i = entry["coordinate"]
        require(entry["name"] == names[i] and sha(entry["path"]) == entry["sha256"],
                f"entry identity {i}")
        direction = load(entry["path"])
        raw_R = D0*bb[i]-N0*aa[i]
        orientation = 1 if raw_R > 0 else -1
        expected_labels = list(all_blocks[i])
        expected_vector = [orientation*all_blocks[i][x] for x in expected_labels]
        actual_labels = [(x[0], tuple(x[1])) for x in direction["basis"]]
        require(direction["coordinate"] == i and direction["orientation"] == orientation and
                actual_labels == expected_labels and
                list(map(F, direction["rational_vector"])) == expected_vector and
                list(map(F, direction["compressed_direction"])) ==
                    [F(orientation if j == i else 0) for j in range(20)],
                f"literal signed coordinate {i}")
        action = direction["cross_action"]
        a, b = orientation*aa[i], orientation*bb[i]
        R = D0*b-N0*a
        score = 2*abs(theta[i])*R/D0**2
        require(F(action["denominator_D0"]) == D0 and
                F(action["numerator_N0"]) == N0 and
                F(action["A_cross_a01"]) == a and
                F(action["B48_cross_b01"]) == b and
                F(action["ascent_residual_R"]) == R > 0 and
                F(action["quotient_first_derivative"]) == 2*R/D0**2 and
                F(entry["relative_first_order_score"]) == score,
                f"cross action/factor 48 {i}")
        costs = entry["expected_grouped_counts"]
        require(costs == direction["expected_grouped_counts"] and
                costs["direction_labels"] == len(expected_labels) and
                costs["i_faces"] == 312 and costs["j_branch_integrals"] == 1200,
                f"count schema {i}")
        observed_scores.append(score)
    require(observed_scores == sorted(observed_scores, reverse=True) and
            [x["name"] for x in entries[:4]] == ["H6", "H7", "H5", "H8"] and
            [x["name"] for x in manifest["post_H6_launch_queue"][:2]] == ["H7", "H5"],
            "exact residual launch ranking")


def test_h7_h5_reproducible_subset_and_counts():
    full = load(MANIFEST)
    expected = {x["name"]: x for x in full["full_ranking"] if x["name"] in ("H7", "H5")}
    require(expected["H7"]["expected_grouped_counts"] == {
        "direction_labels": 15, "precomputed_orbit_keys": 225,
        "precomputed_orbit_terms": 689, "i_orbit_groups": 129,
        "i_grouped_residual_terms": 502, "i_faces": 312,
        "marginal_components": 34, "distinct_marginal_orbits": 15,
        "j_branch_integrals": 1200}, "H7 frozen costs")
    require(expected["H5"]["expected_grouped_counts"] == {
        "direction_labels": 7, "precomputed_orbit_keys": 49,
        "precomputed_orbit_terms": 102, "i_orbit_groups": 38,
        "i_grouped_residual_terms": 134, "i_faces": 312,
        "marginal_components": 14, "distinct_marginal_orbits": 7,
        "j_branch_integrals": 1200}, "H5 frozen costs")
    with tempfile.TemporaryDirectory(prefix="sparse-scan-test.") as directory:
        directory = Path(directory); out = directory/"out"; manifest = directory/"manifest.json"
        command = [sys.executable, str(GENERATOR), "--source", str(SOURCE),
                   "--bands", str(BANDS), "--recovery", str(RECOVERY),
                   "--coordinates", "14,12", "--output-dir", str(out),
                   "--manifest", str(manifest)]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        generated = load(manifest)
        got = {x["name"]: x for x in generated["full_ranking"]}
        require(got["H7"]["sha256"] == expected["H7"]["sha256"] and
                got["H5"]["sha256"] == expected["H5"]["sha256"],
                "H7/H5 byte reproducibility")
        again = subprocess.run(command, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        require(again.returncode != 0, "existing output overwrite")


def main():
    tests = [test_all_directions_actions_and_ranking,
             test_h7_h5_reproducible_subset_and_counts]
    for test in tests:
        test(); print("PASS", test.__name__)
    print("PASS all", len(tests), "tests")
    print("generator_sha256", sha(GENERATOR)); print("manifest_sha256", sha(MANIFEST))


if __name__ == "__main__":
    main()
