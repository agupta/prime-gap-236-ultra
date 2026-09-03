#!/usr/bin/env python3
"""Deterministic cost probe for one hard target r=8 polygon batch."""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = load("green_target_benchmark_radial", REPO / "verify/exact_capped_certificate.py")
C = load("green_target_benchmark_cross", HERE / "symmetric_cutoff_cross.py")
G = load("green_target_benchmark_core", HERE / "green_polygon_moments.py")


def main():
    delta = Q(1, 60)
    alpha = Q(103, 400)
    eta = Q(8960917, 36000000)
    schedule = tuple(map(Q, (
        "1123/8000", "157041/1000000", "5267/31250",
        "87169/500000", "11593/62500", "1523/8000",
        "193097/1000000", "98573/500000", "202047/1000000",
        "20709/100000", "52917/250000", "52917/250000")))
    jobs = C.scheduled_cross_branch_jobs(
        R, k=48, alpha=alpha, eta=eta, delta=delta,
        schedule=schedule, common_r=8)
    matches = [domain for branch, _family, domain, _first in jobs
               if branch == "Stotal"]
    if len(matches) != 1:
        raise RuntimeError("target low-Stotal domain inventory changed")
    domain = matches[0]
    shift = 3 * delta
    polygon = R._shifted_polygon(
        domain.total_bound - shift, domain.x_bound,
        None if domain.y_lower is None else domain.y_lower - shift,
        None if domain.y_upper is None else domain.y_upper - shift,
        None if domain.total_lower is None else domain.total_lower - shift)
    powers = {(8 + a, 37 + b)
              for a in range(36) for b in range(36 - a)}
    if len(powers) != 666 or max(a + b for a, b in powers) != 80:
        raise RuntimeError("hard target moment inventory changed")
    started = time.monotonic()
    moments = G.polygon_monomial_batch_green(polygon, powers)
    elapsed = time.monotonic() - started
    encoded = "\n".join(
        f"{a},{b}:{moments[(a,b)]}" for a, b in sorted(powers)).encode("ascii")
    print(
        "GREEN TARGET BATCH PASS "
        f"vertices={len(polygon)} moments={len(moments)} "
        f"max_degree=80 sha256={hashlib.sha256(encoded).hexdigest()} "
        f"seconds={elapsed:.6f}")


if __name__ == "__main__":
    main()
