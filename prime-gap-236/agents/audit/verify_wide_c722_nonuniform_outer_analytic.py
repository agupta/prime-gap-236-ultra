#!/usr/bin/env python3
"""Exact analytic audit of a nonuniform enlargement of the .104/.166 support.

The checker imports the frozen source-level C722 analytic verifier, not a
schedule-discovery program.  It installs an explicit rational outer sequence,
reruns every fixed and continuous packing case, certifies a componentwise
open box, and includes hostile one-coordinate mutations.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
COMMON = FILE.with_name("verify_wide_c722_p172_analytic.py")
COMMON_SHA = "b0a972af7d5a708fe0cb52eabeb9a477f70606399743c4f6856559271ab7af06"
BASELINE_CHECKER = FILE.with_name(
    "verify_wide_c722_start104_plateau166_analytic.py")
BASELINE_CHECKER_SHA = (
    "faa23bd7370c9c4d1cc00aa3e21577884a2553bca68258f918fca992cf4d111a")
BASELINE_JSON = FILE.with_name("results") / (
    "wide_c722_start104_plateau166_analytic_audit.json")
BASELINE_JSON_SHA = (
    "148852f6021119015fb1dbf0ae61d842ac16371e14ee94001d80a3e832c892e7")

spec = importlib.util.spec_from_file_location(
    "nonuniform_outer_common_source_audit", COMMON)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen common analytic verifier")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
if m.sha(COMMON) != COMMON_SHA:
    raise RuntimeError("frozen common analytic verifier changed")


PLATEAU = Q(83, 500)
BOX_RADIUS = Q(1, 200000)
EXPECTED_ACTIVE = tuple(range(23))
INNER = (m.INNER_CAP,) * 36
OUTER = (
    Q(597, 5000),
    Q(633, 5000),
    Q(669, 5000),
    Q(141, 1000),
    Q(737, 5000),
    Q(773, 5000),
    Q(1553, 10000),
    Q(809, 5000),
    Q(81, 500),
) + (PLATEAU,) * 14
BASELINE = tuple(
    min(Q(13, 125) + (count - 1) * m.DELTA, PLATEAU)
    for count in range(1, 24))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(path: Path):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            answer[key] = value
        return answer

    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite token in {path}: {token}")))


def canonical_schedule_hash(head: tuple[Q, ...]) -> str:
    payload = (json.dumps([str(x) for x in head],
                          separators=(",", ":")) + "\n").encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def schedule_heads():
    return INNER, OUTER


_source_schedule_check = m.check_schedule


def schedule_check(name, head, expected, margins):
    if name == "outer":
        expected = EXPECTED_ACTIVE
    return _source_schedule_check(name, head, expected, margins)


def dynamic_outer(outer: tuple[Q, ...]) -> dict[str, object]:
    """Full exact 16-by-16 continuum cover for every ordered active pair."""
    gmin, gmax = Q(2, 5) - m.H, m.gb(m.OUTER_W)
    worst = None
    pairs = checks = 0
    for left_count in m.active(outer):
        for right_count in m.active(outer):
            if left_count + right_count == 0:
                continue
            for iw in range(m.CELLS):
                wl = m.OUTER_W * iw / m.CELLS
                wu = m.OUTER_W * (iw + 1) / m.CELLS
                for ig in range(m.CELLS):
                    gl = gmin + (gmax - gmin) * ig / m.CELLS
                    gu = gmin + (gmax - gmin) * (ig + 1) / m.CELLS
                    caps = m.cell_capacities(gl, gu, wl, wu)
                    m.require(min(caps) >= 0,
                              "negative dynamic-IIc cell capacity")
                    cert = m.prefix_certificate(
                        left_count, right_count,
                        m.bound(outer, left_count),
                        m.bound(outer, right_count), caps)
                    item = (cert[0], left_count, right_count, iw, ig,
                            cert[1], cert[2], cert[3])
                    worst = item if worst is None or item < worst else worst
                    checks += 1
            pairs += 1
    expected_pairs = len(m.active(outer)) ** 2 - 1
    m.require((pairs, checks) == (
        expected_pairs, expected_pairs * m.CELLS * m.CELLS),
        "dynamic-IIc inventory changed")
    m.require(worst is not None and worst[0] > 0,
              "no strict dynamic-IIc certificate")
    return {"pairs": pairs, "checks": checks,
            "worst_margin": str(worst[0]), "worst": list(worst[1:])}


def fixed_families(outer: tuple[Q, ...]) -> dict[str, object]:
    return {
        "mixed": m.check_fixed_family(INNER, outer, m.CROSS_W, "mixed"),
        "transpose": m.check_fixed_family(
            outer, INNER, m.CROSS_W, "transpose"),
        "outer": m.check_fixed_family(
            outer, outer, m.OUTER_W, "outer"),
        "outer_near": m.check_fixed_family(
            outer, outer, Q(0), "outer-near"),
    }


def first_fixed_failure(outer: tuple[Q, ...]):
    families = (
        ("mixed", INNER, outer, m.CROSS_W),
        ("transpose", outer, INNER, m.CROSS_W),
        ("outer", outer, outer, m.OUTER_W),
        ("outer-near", outer, outer, Q(0)),
    )
    for family, left, right, omega in families:
        for left_count in m.active(left):
            for right_count in m.active(right):
                if left_count + right_count == 0:
                    continue
                for branch, caps in m.fixed_capacities(omega).items():
                    try:
                        m.prefix_certificate(
                            left_count, right_count,
                            m.bound(left, left_count),
                            m.bound(right, right_count), caps)
                    except ArithmeticError:
                        return {"family": family, "branch": branch,
                                "pair": [left_count, right_count],
                                "capacities": [str(x) for x in caps]}
    return None


def box_head(mask: int) -> tuple[Q, ...]:
    first = tuple(OUTER[index] +
                  (BOX_RADIUS if mask & (1 << index) else -BOX_RADIUS)
                  for index in range(9))
    plateau = PLATEAU + (
        BOX_RADIUS if mask & (1 << 9) else -BOX_RADIUS)
    return first + (plateau,) * 14


# Install the explicit central schedule in the source-level verifier.
m.FILE = FILE
m.OUTER_CAP = PLATEAU
m.schedule_heads = schedule_heads
m.check_schedule = schedule_check
m.check_dynamic_outer = dynamic_outer
m.PINNED = dict(m.PINNED)
m.PINNED["agents/audit/verify_wide_c722_p172_analytic.py"] = COMMON_SHA
m.PINNED[
    "agents/audit/verify_wide_c722_start104_plateau166_analytic.py"
] = BASELINE_CHECKER_SHA
m.PINNED[
    "agents/audit/results/"
    "wide_c722_start104_plateau166_analytic_audit.json"
] = BASELINE_JSON_SHA


def build():
    m.require(sha(BASELINE_CHECKER) == BASELINE_CHECKER_SHA and
              sha(BASELINE_JSON) == BASELINE_JSON_SHA,
              "frozen .104/.166 baseline changed")
    baseline_raw = strict_json(BASELINE_JSON)
    serialized_baseline = tuple(
        Q(x) for x in baseline_raw["parameters"][
            "outer_schedule_through_first_empty"])
    m.require(serialized_baseline == BASELINE,
              "baseline formula disagrees with its frozen audit")

    result = m.build()
    m.require(result["parameters"]["outer_active"] == list(range(23)) and
              result["fixed_prefix"]["mixed"]["pairs"] == 827 and
              result["fixed_prefix"]["outer"]["pairs"] == 528 and
              result["dynamic_iic"]["checks"] == 135168,
              "central nonuniform support inventory changed")

    gains = tuple(new - old for old, new in zip(BASELINE, OUTER))
    m.require(all(gain >= 0 for gain in gains) and
              all(gain > 0 for gain in gains[:9]) and
              all(gain == 0 for gain in gains[9:]),
              "pointwise dominance pattern changed")

    # Enumerate every vertex of the independent B1,...,B9 box and the shared
    # plateau interval.  This proves schedule/active-set geometry throughout
    # the box because those conditions are affine.  Packing is monotone under
    # support inclusion, so it suffices to verify the componentwise upper
    # corner with all fixed cases and all dynamic continuum cells.
    corner_worst = None
    for mask in range(1 << 10):
        head = box_head(mask)
        margins = {}
        _source_schedule_check(
            f"box-corner-{mask}", head, EXPECTED_ACTIVE, margins)
        item = (min(margins.values()), mask)
        corner_worst = item if corner_worst is None or item < corner_worst \
            else corner_worst
    upper = box_head((1 << 10) - 1)
    upper_fixed = fixed_families(upper)
    upper_dynamic = dynamic_outer(upper)
    m.require(corner_worst is not None and corner_worst[0] > 0 and
              all(a <= b for a, b in zip(OUTER, upper)),
              "strict component box verification failed")

    # Hostile sensitivity fixtures.  Both mutations retain valid schedule
    # geometry but must fail the complete fixed-prefix audit at the asserted
    # first source branch.
    mutation1 = list(OUTER)
    mutation1[0] += Q(1, 10000)
    margins1 = {}
    _source_schedule_check("hostile-B1", tuple(mutation1),
                           EXPECTED_ACTIVE, margins1)
    failure1 = first_fixed_failure(tuple(mutation1))
    mutation9 = list(OUTER)
    mutation9[8] += Q(1, 10000)
    margins9 = {}
    _source_schedule_check("hostile-B9", tuple(mutation9),
                           EXPECTED_ACTIVE, margins9)
    failure9 = first_fixed_failure(tuple(mutation9))
    m.require(failure1 is not None and
              (failure1["family"], failure1["branch"], failure1["pair"]) ==
              ("mixed", "III", [1, 1]) and
              failure9 is not None and
              (failure9["family"], failure9["branch"], failure9["pair"]) ==
              ("mixed", "IIb", [1, 9]),
              "hostile one-coordinate failures changed")

    result["schedule_id"] = "nonuniform-outer-v1"
    result["parameters"].update({
        "outer_schedule_through_first_empty": [str(x) for x in OUTER],
        "outer_schedule_canonical_sha256":
            canonical_schedule_hash(OUTER),
        "outer_plateau": str(PLATEAU),
    })
    result["pointwise_dominance"] = {
        "baseline_schedule_id": "start104-plateau166",
        "coordinate_gains": [str(x) for x in gains],
        "strictly_improved_counts": list(range(1, 10)),
        "unchanged_counts": list(range(10, 24)),
        "sum_of_first_empty_head_gains": str(sum(gains, Q(0))),
    }
    result["strict_component_interior"] = {
        "independent_coordinates": list(range(1, 10)),
        "shared_plateau_counts": list(range(10, 24)),
        "radius_each": str(BOX_RADIUS),
        "definition1_vertices_checked": 1 << 10,
        "worst_vertex": corner_worst[1],
        "worst_vertex_schedule_margin": str(corner_worst[0]),
        "pointwise_upper_corner_fixed_prefix": upper_fixed,
        "pointwise_upper_corner_dynamic_iic": upper_dynamic,
        "continuum_argument": (
            "all schedule constraints are affine and pass at all 1024 box "
            "vertices; every box support is a subset of the fully verified "
            "componentwise upper corner"),
    }
    result["hostile_mutation_fixtures"] = {
        "B1_plus_1_over_10000": failure1,
        "B9_plus_1_over_10000": failure9,
        "both_mutated_schedules_retain_Definition1_geometry": True,
    }
    result["decision"] = (
        "the explicit nonuniform outer schedule is a strict-interior "
        "analytic Proposition-1 support and pointwise strictly enlarges "
        "the frozen .104/.166 support at counts 1 through 9; no finite-"
        "dimensional quotient is proved")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
