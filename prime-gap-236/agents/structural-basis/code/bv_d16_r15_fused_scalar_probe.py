#!/usr/bin/env python3
"""Fused scalar contractions for ``inner`` and one signed shell count.

This is a discovery/cost instrument.  On a fixed ``(r,h)`` face it represents
the shell marginal literally as ``X = H - L`` and constructs only

    <F, X>  and  <X, X>.

Signed products with the same exact intersection polytope are accumulated
before integration.  Marginal blocks which are byte-for-byte equal (notably
the high/low Sdelta or Lbig pieces) share their orbit product and density
lift.  No Decimal value emitted here is a rigorous certificate.
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
REPO = FILE.parents[3]
TARGET = REPO / "agents/small-delta-frontier/piecewise_d16_capped_target.py"
PINNED_TARGET_SHA256 = (
    "cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c"
)
TARGET_TOTAL = 15


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


if sha256(TARGET) != PINNED_TARGET_SHA256:
    raise RuntimeError("frozen piecewise target changed")
_spec = importlib.util.spec_from_file_location("bv_r15_fused_target", TARGET)
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)


def outer_branches(target_total: int, common_r: int):
    if common_r == target_total - 1:
        return ("Ltotal", "Lbig")
    if common_r == target_total:
        return ("Sdelta", "Stotal")
    return ()


def selected_branch_blocks(evaluator, data, branches, r, h, dimension,
                           outer):
    """Return marginal orbit blocks only for the requested branch pieces."""
    lrs, by_lr = data
    result = {}
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
                for exponent, residual, coefficient in by_lr[lr]:
                    M.grouped.add_poly(
                        polynomial,
                        dict(evaluator.support._marginal_poly(
                            r, h, branch, exponent, residual)), coefficient)
                if polynomial:
                    block[lr] = dict(polynomial)
        result[branch] = (block, constraints) if block else ({}, constraints)
    return result


def block_signature(block):
    """Exact, hashable marginal-block identity (no floating tolerance)."""
    return tuple((orbit, tuple(sorted(polynomial.items())))
                 for orbit, polynomial in sorted(block.items()))


def canonical_constraints(constraints):
    """Canonicalize duplicate/positively-rescaled half planes exactly."""
    tightest = {}
    for az, aw, cap in constraints:
        pivot = az if az else aw
        if not pivot:
            if cap < 0:
                # Retain an explicit impossible half-plane.
                tightest[(az, aw)] = cap
            continue
        scale = abs(pivot)
        row = (az / scale, aw / scale, cap / scale)
        normal = row[:2]
        if normal not in tightest or row[2] < tightest[normal]:
            tightest[normal] = row[2]
    return tuple(sorted(((az, aw, cap) for (az, aw), cap in tightest.items()),
                        key=lambda row: tuple(str(value) for value in row)))


def fused_face(supports, kernels, scalar, common_r, target_total=TARGET_TOTAL,
               selected_h=0, progress=False):
    """Evaluate one or all faces of the exact scalar ``F/X`` pencil.

    ``F`` is the full inner marginal and ``X`` is high scheduled minus low
    scheduled at ``target_total``.  The square is expanded as an unordered
    component-pair sum, with factor two only for distinct components.
    """
    if set(supports) != {"inner_eta2", "high", "low"}:
        raise ValueError("fused supports have the wrong inventory")
    kept = outer_branches(target_total, common_r)
    if not kept:
        raise ValueError("common count cannot feed target count")
    support_k = supports["high"].k
    if any(support.k != support_k for support in supports.values()):
        raise ValueError("support dimensions disagree")
    evaluators = M.evaluators_for_cross(supports, kernels, scalar)
    data = {name: M.component_data(evaluator)
            for name, evaluator in evaluators.items()}
    dummy = evaluators["high"]
    dimension = support_k - 1
    max_h = int(dummy.support.eta / dummy.support.delta) - common_r
    if max_h < 0:
        return {"fx": scalar(0), "xx": scalar(0)}, {
            "faces": 0, "signed_terms": 0, "unique_domains": 0,
            "unique_block_products": 0, "domain_integrals": 0,
        }
    if selected_h is None:
        h_values = range(max_h + 1)
    else:
        if (isinstance(selected_h, bool) or not isinstance(selected_h, int) or
                not 0 <= selected_h <= max_h):
            raise ValueError("selected h outside face range")
        h_values = (selected_h,)

    values = {"fx": scalar(0), "xx": scalar(0)}
    diagnostics = {
        "faces": 0, "signed_terms": 0, "unique_domains": 0,
        "unique_block_products": 0, "domain_integrals": 0,
        "naive_density_lifts": 0,
    }
    for h in h_values:
        outer = dummy.support.eta - (common_r + h) * dummy.support.delta
        if outer <= dummy.zero:
            continue
        inventories = {
            "inner_eta2": M.BRANCHES,
            "high": kept,
            "low": kept,
        }
        blocks = {name: selected_branch_blocks(
            evaluators[name], data[name], branches, common_r, h, dimension,
            outer) for name, branches in inventories.items()}

        def components(name, sign):
            answer = []
            for branch in inventories[name]:
                block, constraints = blocks[name][branch]
                if block and constraints is not None:
                    if (name != "inner_eta2" and
                            M.branch_total_r(common_r, branch) != target_total):
                        raise ArithmeticError("outer branch filter is wrong")
                    answer.append((name, branch, sign, block, constraints))
            return answer

        inner = components("inner_eta2", 1)
        shell = components("high", 1) + components("low", -1)
        tasks = []
        for left in inner:
            for right in shell:
                tasks.append(("fx", left[2] * right[2], left, right))
        for i, left in enumerate(shell):
            for j in range(i + 1):
                right = shell[j]
                weight = left[2] * right[2] * (1 if i == j else 2)
                tasks.append(("xx", weight, left, right))
        diagnostics["signed_terms"] += len(tasks)
        diagnostics["naive_density_lifts"] += len(tasks)

        # Intern exactly equal block polynomials.  For the production r=15
        # face the high and low Sdelta block is identical, although its domain
        # indicator differs; that product must be formed only once.
        block_ids = {}
        block_values = []

        def intern(block):
            signature = block_signature(block)
            if signature not in block_ids:
                block_ids[signature] = len(block_values)
                block_values.append(block)
            return block_ids[signature]

        domain_terms = {"fx": defaultdict(list), "xx": defaultdict(list)}
        for form, weight, left, right in tasks:
            constraints = canonical_constraints(left[4] + right[4])
            if (dimension != 0 and dummy.integrate_domain(
                    {(0, 0): dummy.one}, dimension, common_r, outer,
                    constraints) <= dummy.zero):
                continue
            left_id, right_id = intern(left[3]), intern(right[3])
            product_key = tuple(sorted((left_id, right_id)))
            domain_terms[form][constraints].append((weight, product_key))

        lifted = {}

        def lifted_product(product_key):
            if product_key in lifted:
                return lifted[product_key]
            left_id, right_id = product_key
            combined = M.ordered_orbit_product(
                block_values[left_id], block_values[right_id], dummy)
            integrand = defaultdict(scalar)
            for nu, polynomial in combined.items():
                density = dummy.orbit_density(
                    dimension, nu, common_r, h, max_h)
                if density:
                    M.grouped.add_poly(
                        integrand, M.ei._poly_mul(density, polynomial),
                        dummy.one)
            lifted[product_key] = dict(integrand)
            return lifted[product_key]

        for form in ("fx", "xx"):
            for constraints, terms in domain_terms[form].items():
                combined_integrand = defaultdict(scalar)
                # Combine repeated products on this exact domain before the
                # large polynomial addition/integration.
                weights = defaultdict(int)
                for weight, product_key in terms:
                    weights[product_key] += weight
                for product_key, weight in weights.items():
                    if weight:
                        M.grouped.add_poly(
                            combined_integrand, lifted_product(product_key),
                            scalar(weight))
                if combined_integrand:
                    values[form] += dummy.integrate_domain(
                        dict(combined_integrand), dimension, common_r, outer,
                        constraints)
                    diagnostics["domain_integrals"] += 1
        diagnostics["faces"] += 1
        diagnostics["unique_domains"] += sum(
            len(table) for table in domain_terms.values())
        diagnostics["unique_block_products"] += len(lifted)
        if progress:
            print(f"fused R={target_total} r={common_r} h={h}/{max_h} "
                  f"diag={diagnostics}", file=sys.stderr, flush=True)
        dummy.clear_face_caches(clear_marginals=True)
    dummy.clear_radial_caches()
    return values, diagnostics


def run_stage(dps, common_r, selected_h, progress=False):
    started = time.monotonic()
    self_start = sha256(FILE)
    pins = M.require_piecewise_pins()
    prepared = M.prepare_piecewise_decimal(dps)
    scalar = prepared["scalar"]
    all_supports = M.make_supports(scalar)
    supports = {name: all_supports[name]
                for name in ("inner_eta2", "high", "low")}
    kernels = {"inner": prepared["inner"], "outer": prepared["outer"]}
    values, diagnostics = fused_face(
        supports, kernels, scalar, common_r, TARGET_TOTAL, selected_h,
        progress)
    result = {
        "status": "piecewise-D16-R15-fused-scalar-Decimal-J-stage",
        "rigorous": False,
        "theorem_ready": False,
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
        "decimal_dps": dps,
        "selected_h": selected_h,
        "complete_common_count": selected_h is None,
        "raw_J_scalar": {name: str(value)
                         for name, value in values.items()},
        "diagnostics": diagnostics,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    if (sha256(FILE) != self_start or sha256(TARGET) != PINNED_TARGET_SHA256
            or M.require_piecewise_pins() != pins):
        raise RuntimeError("fused source closure changed during traversal")
    return result


def write_new(path, payload):
    target = Path(path).resolve()
    protected = {FILE, TARGET, *(path.resolve() for path in M.PINNED)}
    if target in protected:
        raise ValueError("output aliases protected input")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(fd, payload)
        os.fsync(fd)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError("output is not regular")
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--common-r", type=int, choices=(14, 15), required=True)
    parser.add_argument("--j-h", type=int, required=True)
    parser.add_argument("--decimal-dps", type=int, choices=(80, 100),
                        default=80)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_stage(args.decimal_dps, args.common_r, args.j_h,
                       args.progress)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    write_new(args.output, payload)
    print(json.dumps({"artifact_sha256": sha256(payload),
                      "wall_seconds": result["wall_seconds"],
                      "peak_rss_kib": result["peak_rss_kib"],
                      "diagnostics": result["diagnostics"]},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
