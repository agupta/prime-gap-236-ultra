#!/usr/bin/env python3
"""Exact analytic audit for the separate wide-C722 volume-ramp schedule.

The common source-inequality engine is the frozen independent p=.172 audit;
this wrapper replaces only the outer schedule and independently reruns every
schedule-dependent fixed and continuous packing check.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
COMMON = FILE.with_name("verify_wide_c722_p172_analytic.py")
COMMON_SHA = "b0a972af7d5a708fe0cb52eabeb9a477f70606399743c4f6856559271ab7af06"

spec = importlib.util.spec_from_file_location("volume_ramp_common_audit", COMMON)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen common audit")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
if m.sha(COMMON) != COMMON_SHA:
    raise RuntimeError("common audit hash changed")


VOLUME_START = Q(49, 625)
VOLUME_CAP = Q(1599, 10000)


def schedule_heads():
    inner = (m.INNER_CAP,) * 36
    outer = tuple(min(VOLUME_START + (count - 1) * m.DELTA, VOLUME_CAP)
                  for count in range(1, 24))
    return inner, outer


_original_schedule_check = m.check_schedule


def schedule_check(name, head, expected, margins):
    if name == "outer":
        expected = tuple(range(23))
    return _original_schedule_check(name, head, expected, margins)


def dynamic_outer(outer):
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
                    m.require(min(caps) >= 0, "negative cell capacity")
                    cert = m.prefix_certificate(
                        left_count, right_count,
                        m.bound(outer, left_count), m.bound(outer, right_count),
                        caps)
                    item = (cert[0], left_count, right_count, iw, ig,
                            cert[1], cert[2], cert[3])
                    worst = item if worst is None or item < worst else worst
                    checks += 1
            pairs += 1
    expected_pairs = len(m.active(outer)) ** 2 - 1
    m.require((pairs, checks) == (expected_pairs,
                                  expected_pairs * m.CELLS * m.CELLS),
              "dynamic inventory")
    return {"pairs": pairs, "checks": checks,
            "worst_margin": str(worst[0]), "worst": list(worst[1:])}


m.FILE = FILE
m.OUTER_CAP = VOLUME_CAP
m.schedule_heads = schedule_heads
m.check_schedule = schedule_check
m.check_dynamic_outer = dynamic_outer
m.PINNED = dict(m.PINNED)
m.PINNED.pop("results/bv_c722_wide_two_band_geometry_high_plateau_v3.json")
m.PINNED["agents/audit/verify_wide_c722_p172_analytic.py"] = COMMON_SHA
m.PINNED["results/bv_c722_wide_two_band_geometry_volume_ramp_v2.json"] = \
    "3517533fa22b4d418d17fd93420b461a44f0cc9560e6f02eef0617e5dc42821f"


def build():
    result = m.build()
    result["schedule_id"] = "volume-ramp"
    result["parameters"]["outer_start"] = str(VOLUME_START)
    result["parameters"]["outer_cap"] = str(VOLUME_CAP)
    m.require(result["fixed_prefix"]["mixed"]["pairs"] == 827,
              "mixed pair inventory")
    m.require(result["fixed_prefix"]["outer"]["pairs"] == 528,
              "outer pair inventory")
    m.require(result["dynamic_iic"]["checks"] == 135168,
              "dynamic cell inventory")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) + "\n").encode()
    if args.output:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode(), end="")


if __name__ == "__main__":
    main()
