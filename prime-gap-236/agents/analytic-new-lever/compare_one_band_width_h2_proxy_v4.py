#!/usr/bin/env python3
"""Ancillary cap-CDF comparison for the exact v4 width portfolio.

This is deliberately *not* a feasibility or energy proof.  It linearly
interpolates the two frozen bridge runs' local CDF samples after shifting each
count's cap by the exact v4 cap gain.  It neither models the newly added shell
nor recomputes A or b.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = HERE.parents[1]
PORTFOLIO = HERE / "one_band_width_portfolio_v4_exact.json"
BRIDGES = (
    REPO / "agents/structural-basis/results/active25_d18_truncated_one_band_h2_bridge_seed2361817_v1.json",
    REPO / "agents/structural-basis/results/active25_d18_truncated_one_band_h2_bridge_seed2361818_v1.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interpolate(points: list[tuple[float, float]], x: float) -> float:
    if x <= points[0][0]:
        left, right = points[:2]
    elif x >= points[-1][0]:
        left, right = points[-2:]
    else:
        left = right = points[0]
        for left, right in zip(points, points[1:]):
            if left[0] <= x <= right[0]:
                break
    value = left[1] + ((x - left[0]) * (right[1] - left[1])
                       / (right[0] - left[0]))
    return min(1.0, max(0.0, value))


def compare(candidate: dict, bridge: dict) -> dict[str, object]:
    rows = bridge["G2_weighted_cap_geometry_diagnostics"][
        "by_large_coordinate_count"]
    shifted = baseline = covered_share = 0.0
    contributions = []
    for row in rows:
        count = row["count"]
        raw = row["large_sum_CDF_near_current_B_R"]
        if not raw or raw[0]["G2_weighted_CDF"] is None:
            continue
        points = [(float(Q(item["offset_from_current_bound"])),
                   item["G2_weighted_CDF"]) for item in raw]
        gain = float(Q(candidate[
            "cap_gains_from_lambda_37_over_40_by_count"][str(count)]))
        old_cdf = next(value for offset, value in points if offset == 0)
        new_cdf = interpolate(points, gain)
        share = row["G2_energy_share"]
        covered_share += share
        baseline += share * old_cdf
        shifted += share * new_cdf
        contributions.append({
            "count": count,
            "energy_share": share,
            "exact_cap_gain": candidate[
                "cap_gains_from_lambda_37_over_40_by_count"][str(count)],
            "baseline_local_CDF": old_cdf,
            "shifted_local_CDF_proxy": new_cdf,
            "weighted_proxy_change": share * (new_cdf - old_cdf),
        })
    return {
        "covered_energy_share": covered_share,
        "baseline_weighted_local_CDF": baseline,
        "shifted_weighted_local_CDF_proxy": shifted,
        "absolute_proxy_change": shifted - baseline,
        "relative_proxy_ratio": shifted / baseline,
        "by_count": contributions,
    }


def build() -> dict[str, object]:
    portfolio = json.loads(PORTFOLIO.read_text(encoding="ascii"))
    bridges = [json.loads(path.read_text(encoding="ascii"))
               for path in BRIDGES]
    results = []
    for candidate in portfolio["candidates"]:
        per_seed = [compare(candidate, bridge) for bridge in bridges]
        results.append({
            "label": candidate["label"],
            "width_ratio_to_lambda_37_over_40": str(
                Q(candidate["width_fraction_of_old_outer"]) / Q(37, 40)),
            "per_seed": per_seed,
            "mean_relative_proxy_ratio": sum(
                row["relative_proxy_ratio"] for row in per_seed) / 2,
        })
    return {
        "status": "ANCILLARY HEURISTIC WIDTH COMPARISON COMPLETE",
        "rigorous": False,
        "theorem_ready": False,
        "never_implies": (
            "feasibility, A, b, b^2/A, retained shell energy, a quotient, "
            "or a bounded-gap theorem"),
        "method": (
            "piecewise-linear interpolation/extrapolation of each seed's "
            "five local G2-weighted cap-CDF samples; added-width shell mass "
            "is omitted"),
        "source_hashes": {
            str(PORTFOLIO.relative_to(REPO)): sha256(PORTFOLIO),
            **{str(path.relative_to(REPO)): sha256(path) for path in BRIDGES},
        },
        "results": results,
        "recommendation": (
            "Keep lambda=37/40 as the exact-A,b priority: every wider "
            "candidate lowers this cap-side proxy, while all have identical "
            "active-count and ordered-pair inventories.  Reconsider a wider "
            "candidate only after an actual exact A,b evaluation shows that "
            "new shell mass outweighs its high-share count-3/4 cap losses."),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"))
               + "\n").encode("ascii")
    if args.output:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
