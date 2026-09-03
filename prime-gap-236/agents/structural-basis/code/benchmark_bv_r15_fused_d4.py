#!/usr/bin/env python3
"""Exact D4 wall/count benchmark for the fused signed-shell contraction."""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
FUSED_PATH = FILE.with_name("bv_d16_r15_fused_scalar_probe.py")
LEGACY_PATH = REPO / "agents/small-delta-frontier/piecewise_d16_R15_specialized.py"
PINNED_LEGACY_SHA256 = (
    "5086a4a381d301ae3a5b321f5e5afba685b677d6851694ef555f6ec76d7fdc58"
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if sha256(LEGACY_PATH) != PINNED_LEGACY_SHA256:
    raise RuntimeError("legacy specialized source changed")
F = load("bv_r15_fused_benchmark", FUSED_PATH)
L = load("bv_r15_legacy_benchmark", LEGACY_PATH)
M = F.M


def kernel(k, labels, coefficients):
    payload = {
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels),
        "degree": max(a + sum(lam) for a, lam in labels),
        "k": k,
        "rational_vector": [str(Q(value)) for value in coefficients],
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
           "\n").encode("ascii")
    return M.kernel_core.compile_kernel_bytes(raw)


def fixture():
    k = 3
    labels = tuple(M.ei.even_basis(4))
    inner = tuple(Q((-1) ** i * (i + 1), i + 2)
                  for i in range(len(labels)))
    outer = tuple(Q(2 * i + 3, i + 5) for i in range(len(labels)))
    kernels = {"inner": kernel(k, labels, inner),
               "outer": kernel(k, labels, outer)}
    delta, eta = Q(1, 10), Q(1, 4)
    inner_support = M.ei.OneStratumSupport(
        k, Q(33, 100), delta, eta,
        Q(33, 100), Q(33, 100), Q(33, 100))
    schedule = (Q(1, 5), Q(3, 10), Q(2, 5))
    supports = {
        "inner_eta2": inner_support,
        "high": M.ScheduledSupport.make(k, Q(7, 20), delta, eta, schedule),
        "low": M.ScheduledSupport.make(k, Q(33, 100), delta, eta, schedule),
    }
    return supports, kernels


CATALOG = (("fh", "inner_eta2", "high"),
           ("fl", "inner_eta2", "low"),
           ("hh", "high", "high"),
           ("hl", "high", "low"),
           ("ll", "low", "low"))


def legacy_once(supports, kernels):
    raw, counts, _ = L.specialized_cross_r(
        supports, kernels, Q, CATALOG, 2, 2, selected_h=0)
    values = {"fx": raw["fh"] - raw["fl"],
              "xx": raw["hh"] - 2 * raw["hl"] + raw["ll"]}
    return values, counts


def fused_once(supports, kernels):
    return F.fused_face(supports, kernels, Q, 2, 2, selected_h=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if isinstance(args.repeats, bool) or not 3 <= args.repeats <= 31:
        raise ValueError("repeats outside frozen benchmark range")
    supports, kernels = fixture()
    expected, legacy_counts = legacy_once(supports, kernels)
    observed, fused_diagnostics = fused_once(supports, kernels)
    if observed != expected:
        raise ArithmeticError("fused D4 value differs from literal expansion")
    timings = {"legacy": [], "fused": []}
    for repetition in range(args.repeats):
        order = ("legacy", "fused") if repetition % 2 == 0 else (
            "fused", "legacy")
        for name in order:
            start = time.perf_counter()
            value, _ = (legacy_once(supports, kernels) if name == "legacy"
                        else fused_once(supports, kernels))
            elapsed = time.perf_counter() - start
            if value != expected:
                raise ArithmeticError(f"{name} benchmark value drifted")
            timings[name].append(elapsed)
    legacy_median = statistics.median(timings["legacy"])
    fused_median = statistics.median(timings["fused"])
    result = {
        "status": "exact-D4-fused-signed-shell-cost-benchmark",
        "rigorous_values": True,
        "performance_is_environment_specific": True,
        "benchmark_sha256": sha256(FILE),
        "fused_sha256": sha256(FUSED_PATH),
        "legacy_sha256": PINNED_LEGACY_SHA256,
        "target_sha256": F.PINNED_TARGET_SHA256,
        "fixture": {"k": 3, "degree": 4, "target_total": 2,
                    "common_r": 2, "h": 0},
        "repeats": args.repeats,
        "exact_values": {name: str(value) for name, value in expected.items()},
        "legacy_domain_integrals": sum(legacy_counts.values()),
        "legacy_counts": legacy_counts,
        "fused_diagnostics": fused_diagnostics,
        "timings_seconds": timings,
        "legacy_median_seconds": legacy_median,
        "fused_median_seconds": fused_median,
        "median_speedup": legacy_median / fused_median,
    }
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    print(json.dumps({"artifact_sha256": hashlib.sha256(payload).hexdigest(),
                      "median_speedup": result["median_speedup"]},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
