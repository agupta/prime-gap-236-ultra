#!/usr/bin/env python3
"""Fail-closed analytic transfer to the sharpened B889 one-band support.

The A, delta, epsilon, Heath--Brown, Type-0, prime-power, Proposition-2,
and Proposition-1 data are identical to the frozen .177 audit.  This checker
rebinds those exact bytes, reconstructs the changed cap schedule, and reruns
the only changed analytic ingredient: every continuum partition case.
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
SCALAR_SCRIPT = HERE / "verify_one_band_177_prop1.py"
SCALAR_SCRIPT_SHA256 = "1bcd87f3aa3bcd5e817d596726a9918103d4ce9501efbc597e22bd9f933e4f61"
SCALAR_RESULT = HERE / "results/one_band_177_prop1_audit.json"
SCALAR_RESULT_SHA256 = "8d8fc9da82012c607a5239596774b806d049458124b811f51f20bfa34a3e5fba"
GEOMETRY_SCRIPT = HERE / "one_band_889_frontier_audit.py"
GEOMETRY_SCRIPT_SHA256 = "bdc551e27f05e33d6395dd241ee116248874b17ebcb832f10c6cd6906fe580ba"
GEOMETRY_RESULT = HERE / "results/one_band_889_sharpened_geometry.json"
GEOMETRY_RESULT_SHA256 = "0bef3e4be5f4a9963f43ebdfd62f3017cd41bfa948624667619ec337733c1b63"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(path: Path, expected: str) -> bytes:
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError(f"SHA mismatch for {path}: {actual} != {expected}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    require(SCALAR_SCRIPT, SCALAR_SCRIPT_SHA256)
    scalar = json.loads(require(SCALAR_RESULT, SCALAR_RESULT_SHA256))
    require(GEOMETRY_SCRIPT, GEOMETRY_SCRIPT_SHA256)
    geometry = json.loads(require(GEOMETRY_RESULT, GEOMETRY_RESULT_SHA256))
    if (scalar["status"] != "one-band-177-analytic-parameter-pass" or
            scalar["theorem_ready"] is not False or
            geometry["status"] !=
            "one-band-889-sharpened-exact-geometric-cover-pass" or
            geometry["theorem_ready"] is not False):
        raise ValueError("upstream status gates failed")

    p = scalar["parameters"]
    gp = geometry["parameters"]
    for key in ("k", "epsilon", "delta", "A0", "A1", "omega"):
        if p[key] != gp[key]:
            raise ValueError(f"parameter transfer mismatch in {key}")
    schedule_head = tuple(Q(x) for x in gp["schedule_through_first_empty"])
    expected = (Q(159999999, 10**9), Q(159999999, 10**9)) + \
        (Q(889, 5000),) * 5
    if schedule_head != expected or gp["first_empty_count"] != 7:
        raise ValueError("sharpened schedule changed")
    delta = Q(gp["delta"])
    schedule = schedule_head[:6] + (schedule_head[5],) * 29
    if len(schedule) != 35:
        raise AssertionError("full schedule length changed")
    margins: dict[str, str] = {}
    for index, b in enumerate(schedule):
        if b <= delta:
            raise AssertionError(f"B{index + 1}<=delta")
        margins[f"Definition1 B{index + 1}-delta"] = str(b - delta)
        if index and not schedule[index - 1] <= b <= schedule[index - 1] + delta:
            raise AssertionError(f"Definition1 transition {index}->{index + 1}")
    if not 6 * delta <= schedule[5] < 7 * delta:
        raise AssertionError("first empty count changed")
    beta = Q(p["beta"])
    if beta <= schedule[0] or beta <= schedule[1]:
        raise AssertionError("Proposition-1 small-prime beta gate failed")
    margins["Prop1 beta-B11"] = str(beta - schedule[0])
    margins["Prop1 beta-B12"] = str(beta - schedule[1])

    cover = geometry["cover"]
    if (cover["pair_count"] != 27 or cover["node_totals"] !=
            {"IIa": 27, "IIb": 27, "III": 27, "IIc": 1845}):
        raise ArithmeticError("fresh B-dependent partition result incomplete")
    # The scalar/source-level proof has no other B_m use.  Preserve the exact
    # dependency closure rather than silently copying a narrative verdict.
    analytic_dependencies = scalar["pinned_analytic_dependencies"]
    if len(analytic_dependencies) != 5:
        raise ValueError("analytic dependency closure changed")

    result = {
        "status": "one-band-889-sharpened-prop1-analytic-pass",
        "scope": (
            "all four Proposition-1 hypotheses via the pinned source-level "
            "direct-HB proof plus a fresh exact B-dependent continuum cover"
        ),
        "script_sha256": sha256(FILE),
        "scalar_script_sha256": SCALAR_SCRIPT_SHA256,
        "scalar_result_sha256": SCALAR_RESULT_SHA256,
        "geometry_script_sha256": GEOMETRY_SCRIPT_SHA256,
        "geometry_result_sha256": GEOMETRY_RESULT_SHA256,
        "parameters": gp,
        "new_schedule_margins": margins,
        "unchanged_scalar_margins": scalar["margins"],
        "fresh_partition_counts": {
            "pairs": cover["pair_count"], "nodes": cover["node_totals"]},
        "pinned_analytic_dependencies": analytic_dependencies,
        "rho_transfer": {
            "direct_HB": "rho=(log n/log(3x))*1_P on [x,2x]",
            "alternate_Proposition2_branch": "xi=(19/50,2/5,2/5) gives c1=c2=0",
            "c1": "0", "c2": "0", "beta": str(beta),
        },
        "theorem_ready": False,
        "remaining": "exact k=48 quotient above one and independent final audit",
    }
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode()
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode(), end="")


if __name__ == "__main__":
    main()
