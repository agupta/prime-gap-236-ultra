#!/usr/bin/env python3
"""Hostile post-run audit of the frozen count-pencil MCMC artifact."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
RESULT = "results/heuristic_capped_count_pencil_mcmc_v1.json"
SOURCE = "scripts/heuristic_capped_count_pencil_mcmc.py"
FORMULA_AUDIT = "agents/audit/results/heuristic_capped_count_pencil_mcmc_audit.json"
PINNED = {
    RESULT:
        "e8a93753ceb5b5cf10af0cae61937ed05647aad40863da67b3385d84ef12f29c",
    SOURCE:
        "5accfe97f9561ce08f3fb403d9d0579847caf289a9cbd2ca8ad6229f6bc11c7b",
    FORMULA_AUDIT:
        "fe62c0865e93b9b14fab3227c4677094863b74de73c0abb84dd9d474b3846976",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def strict_json(relative):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate key in {relative}: {key}")
            answer[key] = value
        return answer

    return json.loads(
        (REPO / relative).read_bytes(), object_pairs_hook=pairs,
        parse_float=Decimal,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {relative}: {token}")))


def finite_decimal(value):
    try:
        result = Decimal(value)
    except Exception:
        return None
    return result if result.is_finite() else None


def build():
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"frozen MCMC result input changed: {relative}")
    raw = strict_json(RESULT)
    audit = strict_json(FORMULA_AUDIT)
    require(audit.get("status") == "SEARCH-INSTRUMENT PASS" and
            raw.get("status") == "HEURISTIC ONLY" and
            raw.get("rigorous") is False and
            raw.get("theorem_ready") is False and
            raw.get("script_sha256_before_output") == PINNED[SOURCE] and
            raw.get("parameters", {}).get("counts") ==
            list(range(6, 16)),
            "result identity/scope changed")

    group_tokens = raw.get("group_top_quotients")
    require(isinstance(group_tokens, list) and len(group_tokens) == 8,
            "group-root inventory changed")
    parsed_groups = [finite_decimal(x) for x in group_tokens]
    finite_groups = [x for x in parsed_groups if x is not None]
    nonfinite_indices = [i for i, x in enumerate(parsed_groups) if x is None]
    group_se = finite_decimal(raw.get("group_quotient_standard_error"))
    require(len(nonfinite_indices) == 2 and group_se is None,
            "expected frozen nonfinite group pathology changed")
    group_min, group_max = min(finite_groups), max(finite_groups)

    labels = ["inner"] + list(range(6, 16))
    diagonal = np.array(
        [np.longdouble(x) for x in raw["I_diagonal"]],
        dtype=np.longdouble)
    matrix = np.array(
        [[np.longdouble(x) for x in row] for row in raw["kJ_matrix"]],
        dtype=np.longdouble)
    require(diagonal.shape == (11,) and matrix.shape == (11, 11) and
            np.isfinite(diagonal).all() and np.isfinite(matrix).all() and
            np.all(diagonal > 0) and np.array_equal(matrix, matrix.T),
            "aggregate matrix is malformed/nonfinite")
    for i, left in enumerate(labels[1:], 1):
        for j, right in enumerate(labels[1:], 1):
            require(abs(left - right) <= 1 or matrix[i, j] == 0,
                    "aggregate matrix has a fake nonadjacent entry")

    scale = np.sqrt(diagonal)
    whitened = np.asarray(
        matrix / scale[:, None] / scale[None, :], dtype=np.float64)
    values, vectors = np.linalg.eigh(whitened)
    top = values[-1]
    reported = float(Decimal(raw["estimated_top_quotient"]))
    require(abs(top - reported) < 2e-15,
            "reported aggregate eigenvalue does not replay")
    coefficient = vectors[:, -1] / np.asarray(scale, dtype=np.float64)
    i_mass = coefficient * coefficient * np.asarray(diagonal, dtype=float)
    i_mass /= i_mass.sum()
    dominant_index = int(np.argmax(i_mass))
    require(labels[dominant_index] == 15 and i_mass[dominant_index] > .77,
            "frozen aggregate direction is no longer R15-dominated")

    parameters = raw["parameters"]
    draws = int(parameters["chains"]) * int(parameters["steps"])
    frequencies = [Decimal(x) for x in raw["I_capped_frequency_by_count"]]
    common = [Decimal(x) for x in raw["J_common_count_frequency"]]
    i_counts = {r: int((frequencies[r] * draws).to_integral_value())
                for r in range(6, 16)}
    common_counts = {r: int((common[r] * draws).to_integral_value())
                     for r in range(13, 17)}
    require(i_counts[6] == 75 and i_counts[15] == 277 and
            common_counts == {13: 1389, 14: 652, 15: 202, 16: 17},
            "frozen tail observation counts changed")

    # A literal zero adjacent estimate is sampling output, not an exact
    # structural identity.  This entry and the decisive R15 blocks have no
    # serialized groupwise error bars.
    zero_outer_entries = []
    for i in range(1, 10):
        if matrix[i, i + 1] == 0:
            zero_outer_entries.append(f"B({labels[i]},{labels[i+1]})")
    require("B(6,7)" in zero_outer_entries,
            "expected frozen zero adjacent estimate changed")

    return {
        "status": "AUDIT FAIL",
        "scope": "MCMC artifact as evidence for an exact capped launch/sign",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "failures": {
            "nonfinite_group_root_indices_zero_based": nonfinite_indices,
            "group_standard_error_nonfinite": True,
            "finite_group_min": str(group_min),
            "finite_group_max": str(group_max),
            "finite_group_range": str(group_max - group_min),
            "aggregate_q_not_blessed": raw["estimated_top_quotient"],
            "dominant_coordinate": "R15",
            "dominant_I_mass_fraction": str(i_mass[dominant_index]),
            "I_observations_R6": i_counts[6],
            "I_observations_R15": i_counts[15],
            "J_common_observations_R14": common_counts[14],
            "J_common_observations_R15": common_counts[15],
            "sampling_zero_entries_not_structural": zero_outer_entries,
            "per_entry_group_error_bars_serialized": False,
        },
        "statistically_unusable": [
            "the aggregate 1.032431 sign",
            "the NaN group pencils and NaN group standard error",
            "the decisive B(15,15), B(inner,15), and A(15) estimates",
            "the literal zero estimate B(6,7)",
            "all individual entry signs as certified statements",
        ],
        "conservative_qualitative_ranking": [
            "compute R15 shell I first",
            "compute inner-R15 and R15-R15 J blocks from common r=14,15",
            "compute R14-R15 as an adjacency/control block",
            "do not infer the capped quotient sign from this run",
        ],
        "decision": (
            "formula implementation passed separately, but this Monte Carlo "
            "run is statistically unstable and cannot authorize or justify "
            "an exact launch on the claimed positive sign"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
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
