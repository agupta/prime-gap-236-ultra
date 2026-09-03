#!/usr/bin/env python3
"""Specialized J stages for inner plus the outer total-count R=15.

For an outer marginal to have total large count 15, only two common-count
faces can contribute:

* common r=14 with the distinguished variable in Ltotal/Lbig;
* common r=15 with the distinguished variable in Sdelta/Stotal.

All other branch products are identically outside the requested coordinate.
This file enforces that filter *before* the expensive orbit product.  It emits
raw ordered J bilinear integrals.  The later 2x2 assembly applies k=48 once,
and uses ``HH + LL - 2 HL`` for the shell self entry.  Decimal output is
discovery-only.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import stat
import sys
import time


FILE = Path(__file__).resolve()
HERE = FILE.parent
TARGET_PATH = HERE / "piecewise_d16_capped_target.py"
PINNED_TARGET_SHA256 = \
    "cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c"
TARGET_TOTAL = 15
TAGS = ("fh", "fl", "hh", "hl", "ll")


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


if sha256(TARGET_PATH) != PINNED_TARGET_SHA256:
    raise RuntimeError("frozen piecewise target arithmetic changed")
SPEC = importlib.util.spec_from_file_location(
    "piecewise_R15_target_base", TARGET_PATH)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def outer_branches(target_total, common_r):
    if common_r == target_total - 1:
        return ("Ltotal", "Lbig")
    if common_r == target_total:
        return ("Sdelta", "Stotal")
    return ()


def selected_branch_blocks(evaluator, data, branches, r, h, dimension,
                           outer):
    """Build only branches capable of feeding the target coordinate."""
    lrs, by_lr = data
    answer = {}
    for branch in branches:
        constraints = evaluator.support._branch_constraints(r, h, branch)
        if dimension == 0:
            interval = evaluator.support._branch_interval(0, 0, branch)
            active = (interval is not None and
                      interval[0] <= evaluator.zero <= interval[1])
        else:
            active = (constraints is not None and evaluator.integrate_domain(
                {(0, 0): evaluator.one}, dimension, r, outer,
                constraints) > evaluator.zero)
        block = {}
        if active:
            for lr in lrs:
                polynomial = defaultdict(evaluator.scalar)
                for exponent, slack, coefficient in by_lr[lr]:
                    M.grouped.add_poly(
                        polynomial,
                        dict(evaluator.support._marginal_poly(
                            r, h, branch, exponent, slack)), coefficient)
                if polynomial:
                    block[lr] = dict(polynomial)
        answer[branch] = (block, constraints) if block else ({}, constraints)
    return answer


def specialized_cross_r(supports, kernels, scalar, pair_names, common_r,
                        target_total, progress=False, selected_h=None):
    """Return one raw J scalar per requested tag after exact branch pruning."""
    kept = outer_branches(target_total, common_r)
    if not kept:
        raise ValueError("common count cannot feed requested total count")
    support_k = next(iter(supports.values())).k
    if not 0 <= common_r < support_k:
        raise ValueError("common count outside marginal dimension")
    evaluators = M.evaluators_for_cross(supports, kernels, scalar)
    data = {name: M.component_data(evaluator)
            for name, evaluator in evaluators.items()}
    first = next(iter(evaluators.values()))
    dimension = support_k - 1
    max_h = int(first.support.eta / first.support.delta) - common_r
    if max_h < 0:
        return {tag: scalar(0) for tag, _, _ in pair_names}, \
            {tag: 0 for tag, _, _ in pair_names}, 0
    if selected_h is None:
        h_values = range(max_h + 1)
    else:
        if (isinstance(selected_h, bool) or not isinstance(selected_h, int) or
                not 0 <= selected_h <= max_h):
            raise ValueError("selected h outside common-count face range")
        h_values = (selected_h,)
    values = {tag: scalar(0) for tag, _, _ in pair_names}
    counts = {tag: 0 for tag, _, _ in pair_names}
    faces = 0
    for h in h_values:
        outer = first.support.eta - (common_r + h) * first.support.delta
        if outer <= first.zero:
            continue
        branches_by_name = {
            name: (M.BRANCHES if name.startswith("inner") else kept)
            for name in supports
        }
        blocks = {name: selected_branch_blocks(
            evaluators[name], data[name], branches_by_name[name], common_r, h,
            dimension, outer) for name in supports}
        faces += 1
        for tag, left_name, right_name in pair_names:
            left_is_inner = left_name.startswith("inner")
            right_is_inner = right_name.startswith("inner")
            left_branches = M.BRANCHES if left_is_inner else kept
            right_branches = M.BRANCHES if right_is_inner else kept
            for left_branch in left_branches:
                left, left_constraints = blocks[left_name][left_branch]
                if not left or left_constraints is None:
                    continue
                for right_branch in right_branches:
                    right, right_constraints = blocks[right_name][right_branch]
                    if not right or right_constraints is None:
                        continue
                    # Every retained outer branch has the requested total key;
                    # make that invariant executable rather than relying on
                    # its spelling.
                    if (not left_is_inner and
                            M.branch_total_r(common_r, left_branch) !=
                            target_total):
                        raise ArithmeticError("left branch filter is wrong")
                    if (not right_is_inner and
                            M.branch_total_r(common_r, right_branch) !=
                            target_total):
                        raise ArithmeticError("right branch filter is wrong")
                    constraints = left_constraints + right_constraints
                    if dimension and first.integrate_domain(
                            {(0, 0): first.one}, dimension, common_r, outer,
                            constraints) <= first.zero:
                        continue
                    combined = M.ordered_orbit_product(left, right, first)
                    integrand = defaultdict(scalar)
                    for nu, polynomial in combined.items():
                        density = first.orbit_density(
                            dimension, nu, common_r, h, max_h)
                        if density:
                            M.grouped.add_poly(
                                integrand, M.ei._poly_mul(density, polynomial),
                                first.one)
                    if not integrand:
                        continue
                    values[tag] += first.integrate_domain(
                        dict(integrand), dimension, common_r, outer,
                        constraints)
                    counts[tag] += 1
        if progress:
            print(f"R={target_total} common_r={common_r} h={h}/{max_h} "
                  f"counts={counts}", file=sys.stderr, flush=True)
        first.clear_face_caches(clear_marginals=True)
    first.clear_radial_caches()
    return values, counts, faces


def run_stage(dps, common_r, progress=False, selected_h=None):
    started = time.monotonic()
    pins = M.require_piecewise_pins()
    self_start = sha256(FILE)
    prepared = M.prepare_piecewise_decimal(dps)
    scalar = prepared["scalar"]
    all_supports = M.make_supports(scalar)
    supports = {name: all_supports[name]
                for name in ("inner_eta2", "high", "low")}
    kernels = {"inner": prepared["inner"], "outer": prepared["outer"]}
    catalog = (("fh", "inner_eta2", "high"),
               ("fl", "inner_eta2", "low"),
               ("hh", "high", "high"),
               ("hl", "high", "low"),
               ("ll", "low", "low"))
    values, counts, faces = specialized_cross_r(
        supports, kernels, scalar, catalog, common_r, TARGET_TOTAL,
        progress, selected_h)
    result = {
        "status": "piecewise-D16-R15-specialized-Decimal-J-stage",
        "rigorous": False, "theorem_ready": False,
        "never_implies": ["rigorous interval sign", "H1<=236"],
        "script_sha256": self_start,
        "target_driver_sha256": PINNED_TARGET_SHA256,
        "source_hashes": pins,
        "parameters": {
            "k": 48, "degree": 16, "target_total_count": TARGET_TOTAL,
            "common_count": common_r, "inner_c": "1",
            "outer_c": "3090/3211", "eta": "3031/12000",
            "delta": "361/50000",
        },
        "decimal_dps": dps, "selected_h": selected_h,
        "complete_common_count": selected_h is None,
        "outer_branch_filter": list(outer_branches(TARGET_TOTAL, common_r)),
        "raw_J_bilinear": {tag: str(values[tag]) for tag in TAGS},
        "branch_domain_integrals": counts, "faces": faces,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    if (sha256(FILE) != self_start or
            sha256(TARGET_PATH) != PINNED_TARGET_SHA256 or
            M.require_piecewise_pins() != pins):
        raise RuntimeError("R15 source closure changed during traversal")
    return result


def write_new(path, payload):
    target = Path(path).resolve()
    protected = {FILE.resolve(), TARGET_PATH.resolve(),
                 *(path.resolve() for path in M.PINNED)}
    if target in protected:
        raise ValueError("output aliases protected arithmetic")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError("R15 output is not a regular file")
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--common-r", type=int, choices=(14, 15), required=True)
    parser.add_argument("--decimal-dps", type=int, choices=(80, 100),
                        default=80)
    parser.add_argument("--j-h", type=int)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_stage(args.decimal_dps, args.common_r, args.progress,
                       args.j_h)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    write_new(args.output, payload)
    print(json.dumps({"artifact_sha256": sha256(payload),
                      "wall_seconds": result["wall_seconds"],
                      "peak_rss_kib": result["peak_rss_kib"],
                      "counts": result["branch_domain_integrals"]},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
