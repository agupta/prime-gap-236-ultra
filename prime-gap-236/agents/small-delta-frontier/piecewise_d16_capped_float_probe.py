#!/usr/bin/env python3
"""Fast non-rigorous float probe for the piecewise D16 capped recurrence.

This is only a ranking/cost tool.  It runs the identical finite branch and
orbit recurrence as ``piecewise_d16_capped_target.py`` after replacing scalar
arithmetic by binary64.  A stored Decimal80 one-face result is used as a
mandatory calibration; no float result has certificate status.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import importlib.util
import json
from math import comb, factorial, isfinite
import os
from pathlib import Path
import resource
import sys
import time


FILE = Path(__file__).resolve()
HERE = FILE.parent
TARGET = HERE / "piecewise_d16_capped_target.py"
CALIBRATION = HERE / (
    "results/piecewise_D16_capped_costprobe_r12_h11_fh_decimal80.json")
PINNED_TARGET_SHA256 = \
    "cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c"
PINNED_CALIBRATION_SHA256 = \
    "e5ee2ca854503a70013b44781a936e5f9f1259566ca377dd0c7f0d05f6810958"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if sha256(TARGET) != PINNED_TARGET_SHA256:
    raise RuntimeError("frozen Decimal target arithmetic changed")
SPEC = importlib.util.spec_from_file_location("piecewise_float_target_base", TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
ei = M.ei


def install_float(orbit_table):
    """Install binary64 analogues of the audited Decimal arithmetic hooks."""
    for function in (ei.multiply_monomial_orbits, ei._linear_power,
                     ei.polygon_monomial, ei.polygon, ei._large_shift_dp,
                     ei._small_box_dp, ei._selected_exponent_splits):
        clear = getattr(function, "cache_clear", None)
        if clear is not None:
            clear()
    for name in ("_piece_residual", "canonical_support_residual",
                 "canonical_support_moment", "_branch_constraints",
                 "_marginal_poly", "_j_piece", "canonical_j_moment",
                 "basis_m1", "basis_j"):
        clear = getattr(ei.OneStratumSupport, name).cache_clear
        clear()

    frozen = dict(orbit_table)

    def fpq(numerator=0, denominator=None):
        return (float(numerator) if denominator is None else
                float(numerator) / float(denominator))

    def orbit_lookup(lam, mu):
        key = (tuple(lam), tuple(mu))
        if key in frozen:
            return frozen[key]
        return frozen[(key[1], key[0])]

    ei.Q = fpq
    ei.multiply_monomial_orbits = orbit_lookup

    @lru_cache(maxsize=None)
    def linear_power(c0, cz, cw, n):
        out = defaultdict(float)
        for i in range(n + 1):
            for j in range(n - i + 1):
                h = n - i - j
                coefficient = (factorial(n) /
                               (factorial(i) * factorial(j) * factorial(h)))
                out[(i, j)] += (coefficient *
                                (1.0 if i == 0 else cz ** i) *
                                (1.0 if j == 0 else cw ** j) *
                                (1.0 if h == 0 else c0 ** h))
        return tuple(out.items())

    ei._linear_power = linear_power

    def power(x, n):
        return 1.0 if n == 0 else x ** n

    @lru_cache(maxsize=None)
    def polygon_monomial(poly, az, aw):
        if not poly:
            return 0.0
        answer = 0.0
        ap = az + 1
        for index, (x0, y0) in enumerate(poly):
            x1, y1 = poly[(index + 1) % len(poly)]
            dx, dy = x1 - x0, y1 - y0
            if dy == 0:
                continue
            if dx == 0:
                answer += (power(x0, ap) *
                           (power(y1, aw + 1) - power(y0, aw + 1)) /
                           (ap * (aw + 1)))
            elif dx + dy == 0:
                constant = x0 + y0
                edge = 0.0
                for i in range(ap + 1):
                    edge += (((-1) ** i * comb(ap, i)) /
                             (aw + i + 1) * power(constant, ap - i) *
                             (power(y1, aw + i + 1) -
                              power(y0, aw + i + 1)))
                answer += edge / ap
            else:
                edge = 0.0
                for i in range(ap + 1):
                    for j in range(aw + 1):
                        edge += (comb(ap, i) * comb(aw, j) /
                                 (i + j + 1) * power(x0, ap - i) *
                                 power(dx, i) * power(y0, aw - j) *
                                 power(dy, j))
                answer += dy * edge / ap
        return answer

    ei.polygon_monomial = polygon_monomial
    return fpq


def prepare_float():
    inner_bytes, basis_i, _ = M.transformed_source_bytes(M.INNER_C)
    outer_bytes, basis_o, _ = M.transformed_source_bytes(M.OUTER_C)
    if basis_i != basis_o:
        raise ArithmeticError("float piecewise basis mismatch")
    inner = M.kernel_core.compile_kernel_bytes(inner_bytes)
    outer = M.kernel_core.compile_kernel_bytes(outer_bytes)
    if inner.orbit_products != outer.orbit_products:
        raise ArithmeticError("float piecewise orbit table mismatch")
    scalar = install_float(inner.orbit_products)
    return {"inner": inner, "outer": outer}, scalar


def calibration_relative_error(observed):
    if sha256(CALIBRATION) != PINNED_CALIBRATION_SHA256:
        raise RuntimeError("Decimal80 face calibration changed")
    raw = json.loads(CALIBRATION.read_bytes())
    expected = {(item["left_total_count"], item["right_total_count"]):
                float(item["value"])
                for item in raw["j_stage"]["tables"]["fh"]}
    if set(observed) != set(expected):
        raise ArithmeticError("float/Decimal calibration table keys differ")
    scale = max(abs(x) for x in expected.values())
    return max(abs(observed[key] - expected[key]) / scale for key in expected)


def run(common_r, probe_h, tags, total_r=None, progress=False):
    started = time.monotonic()
    M.require_piecewise_pins()
    kernels, scalar = prepare_float()
    supports = M.make_supports(scalar)
    output = {"status": "piecewise-D16-capped-binary64-probe",
              "rigorous": False, "theorem_ready": False,
              "never_implies": ["validated numerical sign", "H1<=236"],
              "common_r": common_r, "probe_h": probe_h,
              "total_r": total_r, "blocks": list(tags),
              "i_stage": None, "j_stage": None}
    if total_r is not None:
        t0 = time.monotonic()
        hi, lo, shell, faces = M.fused_i_shell_r(
            supports["high"], supports["low"], kernels["outer"], float,
            total_r, progress)
        output["i_stage"] = {"high": repr(hi), "low": repr(lo),
                             "shell": repr(shell), "faces": faces,
                             "seconds": time.monotonic() - t0}
    if common_r is not None:
        catalog = {"fh": ("inner_eta2", "high"),
                   "fl": ("inner_eta2", "low"),
                   "hh": ("high", "high"), "hl": ("high", "low"),
                   "lh": ("low", "high"), "ll": ("low", "low")}
        selected = tuple((tag, *catalog[tag]) for tag in tags)
        needed = {name: supports[name]
                  for _, left, right in selected for name in (left, right)}
        t0 = time.monotonic()
        tables, counts, faces = M.cross_bundle_r(
            needed, kernels, float, selected, common_r, progress, probe_h)
        if any(not isfinite(value) for table in tables.values()
               for value in table.values()):
            raise ArithmeticError("nonfinite float recurrence")
        output["j_stage"] = {
            "tables": {tag: M.encode_table(table)
                       for tag, table in tables.items()},
            "counts": counts, "faces": faces,
            "seconds": time.monotonic() - t0,
        }
        if common_r == 12 and probe_h == 11 and tags == ("fh",):
            error = calibration_relative_error(tables["fh"])
            output["decimal80_calibration_relative_error"] = repr(error)
            output["decimal80_calibration_pass"] = error < 1e-8
            if not output["decimal80_calibration_pass"]:
                raise ArithmeticError(
                    f"binary64 calibration failed: relative error={error!r}")
    output["wall_seconds"] = time.monotonic() - started
    output["peak_rss_kib"] = resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--common-r", type=int)
    parser.add_argument("--probe-h", type=int)
    parser.add_argument("--total-r", type=int)
    parser.add_argument("--blocks", default="fh,fl,hh,hl,lh,ll")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tags = tuple(x for x in args.blocks.split(",") if x)
    if len(tags) != len(set(tags)) or any(x not in M.BLOCK_TAGS for x in tags):
        parser.error("invalid/duplicate block tag")
    if args.common_r is None and args.total_r is None:
        parser.error("at least one count selector is required")
    result = run(args.common_r, args.probe_h, tags, args.total_r,
                 args.progress)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"sha256": hashlib.sha256(payload).hexdigest(),
                      "wall_seconds": result["wall_seconds"],
                      "peak_rss_kib": result["peak_rss_kib"],
                      "calibration": result.get(
                          "decimal80_calibration_relative_error")},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
