#!/usr/bin/env python3
"""Disabled pruned cap-slack/D16 cross pilot for active-25.

V1 remains immutable.  This successor keeps every degree-zero count
coordinate and adds degrees one and two only for counts 9..14, the exact
denominator-dominant counts of the pinned D2 shell particular vector.  It
contains an executable exact shard kernel but deliberately rejects target
stage requests until an independently audited authorization successor exists.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
V1_SOURCE = FILE.with_name("active25_outer_b4_j_cross_plan_v1.py")
V1_TEST = (REPO / "agents/structural-basis/tests/"
           "test_active25_outer_b4_j_cross_plan_v1.py")
V1_SPEC = (REPO / "agents/structural-basis/"
           "ACTIVE25-OUTER-B4-J-CROSS-PLAN-V1.md")
V1_ARTIFACT = (REPO / "agents/structural-basis/results/"
               "active25_outer_b4_j_cross_disabled_plan_v1.json")
TEST_FILE = (REPO / "agents/structural-basis/tests/"
             "test_active25_cap_slack_cross_pilot_v2.py")
SPEC_FILE = (REPO / "agents/structural-basis/"
             "ACTIVE25-CAP-SLACK-CROSS-PILOT-V2.md")

PINNED_V1 = {
    V1_SOURCE: "00eb639b2c4ad954be36aaf8f34268c838a2ab66e5606a8f78ad70b1de0f4145",
    V1_TEST: "e4bc091bcaaa12d02f7cdf07b54c1e746b3da5c1f9031b3d7090ba3dcd4cd10a",
    V1_SPEC: "35a3530e30a881df9ee393086039470708712e5f212f49db40781a3ff1349170",
    V1_ARTIFACT: "69dfd7594e5a14882d742c994cf3da451239eebb0fa3de83c8fddeccd2637df5",
}


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


for _path, _expected in PINNED_V1.items():
    if sha256(_path) != _expected:
        raise RuntimeError(f"frozen v1 changed: {_path}")
_spec = importlib.util.spec_from_file_location("active25_cap_cross_v1", V1_SOURCE)
if _spec is None or _spec.loader is None:
    raise ImportError(V1_SOURCE)
V1 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = V1
_spec.loader.exec_module(V1)


PILOT_COUNTS = tuple(range(9, 15))


def pilot_labels():
    labels = tuple(label for label in V1.cap_labels(2)
                   if label[1] == 0 or label[0] in PILOT_COUNTS)
    if (len(labels) != 38 or len(set(labels)) != 38 or
            sum(label[1] > 0 for label in labels) != 12):
        raise ArithmeticError("pilot label inventory changed")
    return labels


def pilot_shard(common_r, **kwargs):
    """Exact arithmetic kernel; callers still need external authorization."""
    return V1.grouped_inner_cap_cross_shard(
        common_r, basis=pilot_labels(), **kwargs)


def pilot_work_inventory():
    labels = pilot_labels()
    by_count = {count: tuple(label for label in labels if label[0] == count)
                for count in range(26)}
    total_faces = 0
    weighted_terms = 0
    by_r = {}
    max_common = int(V1.A25.ETA2 // V1.A25.DELTA)
    for r in range(26):
        faces = max_common - r + 1
        total_faces += faces
        # Four radial/support tags; each total count occurs on two literal
        # distinguished-coordinate branches.
        per_face = 4 * (2 * len(by_count[r]) +
                        2 * len(by_count.get(r + 1, ())))
        weighted_terms += faces * per_face
        by_r[str(r)] = {
            "faces": faces,
            "labels_on_small_branches": len(by_count[r]),
            "labels_on_large_branches": len(by_count.get(r + 1, ())),
            "weighted_branch_column_terms": faces * per_face,
        }
    if total_faces != 585 or weighted_terms != 13888:
        raise ArithmeticError("pilot work inventory changed")
    return {
        "dimension": len(labels),
        "labels": [list(label) for label in labels],
        "all_degree_zero_counts": list(range(26)),
        "positive_degree_counts": list(PILOT_COUNTS),
        "positive_degrees": [1, 2],
        "common_r": list(range(26)),
        "faces": total_faces,
        "weighted_branch_column_terms": weighted_terms,
        "full_d0_d2_terms": 27280,
        "natural_b4_terms": 93600,
        "by_common_r": by_r,
    }


def exact_d2_denominator_contributions():
    """Recontract the pinned D2 shell vector by exact count block."""
    raw = json.loads(V1.CAP_RESULTS[2].read_bytes())
    expected_basis = [list(label) for label in V1.cap_labels(2)]
    if (raw.get("format") != "active25-count-cap-slack-shell-exact-v1" or
            raw.get("basis") != expected_basis or
            raw.get("dimension") != 76 or
            raw.get("maximum_cap_slack_degree") != 2 or
            raw.get("script_sha256") != V1.PINNED[V1.CAP_SOURCE]):
        raise ValueError("pinned cap D2 result identity changed")
    vector = [Q(value) for value in raw["rational_vector"]]
    matrix = [[Q(0) for _ in vector] for _ in vector]
    for i, j, value in raw["I_upper_nonzero"]:
        if (type(i) is not int or type(j) is not int or not 0 <= j <= i < 76 or
                type(value) is not str or str(Q(value)) != value):
            raise ValueError("noncanonical D2 I entry")
        matrix[i][j] = matrix[j][i] = Q(value)
    contributions = {}
    for count in range(26):
        indices = [i for i, label in enumerate(expected_basis)
                   if label[0] == count]
        contributions[count] = sum(
            (vector[i] * matrix[i][j] * vector[j]
             for i in indices for j in indices), Q(0))
    total = sum(contributions.values(), Q(0))
    if total != Q(raw["exact_denominator"]) or total <= 0:
        raise ArithmeticError("D2 denominator block reconstruction failed")
    ranked = sorted(contributions, key=contributions.get, reverse=True)
    if ranked[:6] != [12, 11, 13, 10, 9, 14]:
        raise ArithmeticError("D2 count ranking changed")
    selected = sum((contributions[count] for count in PILOT_COUNTS), Q(0))
    return {
        "total": str(total),
        "selected": str(selected),
        "selected_fraction": str(selected / total),
        "ranked_counts": ranked,
        "fractions_by_count": {
            str(count): str(contributions[count] / total)
            for count in range(26)
        },
    }


def build_plan():
    base = json.loads(V1_ARTIFACT.read_bytes())
    if (base.get("source_sha256") != PINNED_V1[V1_SOURCE] or
            base.get("target_run_started") is not False or
            base.get("contains_J_values") is not False):
        raise ValueError("v1 plan identity changed")
    work = pilot_work_inventory()
    contributions = exact_d2_denominator_contributions()
    contribution_bytes = json.dumps(
        contributions, sort_keys=True, separators=(",", ":")).encode()
    contribution_summary = {
        "exact_reconstruction_sha256": sha256(contribution_bytes),
        "ranked_counts": contributions["ranked_counts"],
        "selected_counts": list(PILOT_COUNTS),
        "selected_fraction_gt_19_over_20":
            Q(contributions["selected_fraction"]) > Q(19, 20),
        "total_matches_pinned_exact_denominator": True,
    }
    cost = V1.measured_cost_model()
    projected = 2 * cost["projected_full_constant_cross_seconds"]
    return {
        "status": "active25-cap-slack-d16-cross-pilot-disabled-v2",
        "rigorous_values": False,
        "target_run_started": False,
        "contains_cross_values": False,
        "contains_quotient": False,
        "source_sha256": sha256(FILE),
        "package_sha256": {
            str(FILE.relative_to(REPO)): sha256(FILE),
            str(TEST_FILE.relative_to(REPO)): sha256(TEST_FILE),
            str(SPEC_FILE.relative_to(REPO)): sha256(SPEC_FILE),
        },
        "pinned_v1_sha256": {
            str(path.relative_to(REPO)): digest
            for path, digest in PINNED_V1.items()
        },
        "parameters": V1.A25.parameter_record(),
        "coordinate_formula":
            "1_{count=R}*((B_R-R*delta-z_R)/(B_R-R*delta))^d",
        "work_inventory": work,
        "exact_D2_shell_denominator_ranking": contribution_summary,
        "selection_is_not_upper_bound": True,
        "cost_model": {
            "pinned_constant_cross_face_mean_seconds":
                cost["constant_cross_face_mean_seconds"],
            "pinned_constant_cross_face_peak_rss_kib":
                cost["constant_cross_probe_peak_rss_kib"],
            "projected_pilot_seconds_conservative": projected,
            "projected_pilot_hours_conservative": projected / 3600,
            "memory_gate_kib": 262144,
        },
        "staging": {
            "unit": "one complete common_r shard",
            "shards": list(range(26)),
            "arithmetic": "exact Fraction; group by coordinate and exact domain",
            "publication": "fresh O_EXCL successor artifacts only",
            "workers": 1,
        },
        "prelaunch_gate": {
            "required_face": [10, 10],
            "wall_seconds_at_most": 20,
            "peak_rss_kib_at_most": 262144,
            "projected_complete_seconds_at_most": 7200,
            "launch_authorized": False,
        },
        "continuation": {
            "expand_to_all_D2_counts_if":
                "exact pilot gain over same inner-only coordinate >=1e-4",
            "evaluate_natural_B4_if":
                "expanded exact particular quotient >=1.002",
            "otherwise": "retire outer cap-polynomial refinement",
        },
        "no_claim": "no J cross, combined quotient, or theorem claim",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--stage-r", type=int)
    args = parser.parse_args()
    if args.stage_r is not None:
        raise SystemExit("v2 target stages are externally disabled")
    if not args.preflight_only:
        raise SystemExit("v2 supports --preflight-only only")
    print(json.dumps(build_plan(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
