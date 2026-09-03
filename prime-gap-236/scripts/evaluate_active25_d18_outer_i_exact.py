#!/usr/bin/env python3
"""Exact denominator loss for the active-25 capped D18 outer polynomial.

This evaluates only the I form of the naturally dilated D18 polynomial on
the audited scheduled shell H\L.  It is a prioritization diagnostic, not a
Rayleigh quotient: no J block and no theorem claim are produced.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
CORE_PATH = REPO / (
    "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py")
DILATION_PATH = REPO / "scripts/full_simplex_dilated_vector_proxy.py"
SCAN_PATH = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
CERTIFICATE = REPO / (
    "agents/exact-integrator/results/"
    "aquarter_fullsimplex_k48_B18_refined_exact.json")
ANALYTIC = REPO / (
    "agents/audit/results/"
    "wide_c722_nonuniform_active25_tail_analytic_audit.json")
UNCAPPED = REPO / (
    "results/wide_c722_B18_piecewise_cinner1_couter_natural_exact.json")
PINS = {
    CORE_PATH: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    DILATION_PATH: "3219047bd9d339e15946947f68bd6484d23af722337ba70771c488e3e1238794",
    SCAN_PATH: "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9",
    CERTIFICATE: "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58",
    ANALYTIC: "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
    UNCAPPED: "49ecca1b962d06a8ee793e7ce0a3dcdf4ef1fd38595ccd86c784950636d903fd",
}


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


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
                          ValueError(f"nonfinite JSON token: {token}")))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path, expected in PINS.items():
        if sha256(path) != expected:
            raise RuntimeError(f"pinned input changed: {path}")
    before = {path: path.read_bytes() for path in PINS}

    core = load_module("active25_d18_i_core", CORE_PATH)
    dilation = load_module("active25_d18_i_dilation", DILATION_PATH)
    scan = load_module("active25_d18_i_scan", SCAN_PATH)
    scan.self_test()
    analytic = strict_json(ANALYTIC)
    certificate = strict_json(CERTIFICATE)
    uncapped = strict_json(UNCAPPED)
    if (analytic.get("status") != "AUDIT PASS" or
            analytic.get("schedule_id") !=
            "nonuniform-outer-active25-tail-v4" or
            analytic.get("parameters", {}).get("outer_active") !=
            list(range(26))):
        raise ValueError("analytic support identity changed")
    if ((certificate.get("k"), certificate.get("degree")) != (48, 18) or
            uncapped.get("certificate_sha256") != PINS[CERTIFICATE]):
        raise ValueError("D18 certificate identity changed")
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in certificate["basis"])
    vector = tuple(Q(x) for x in certificate["rational_vector"])
    if len(basis) != 471 or len(vector) != 471 or len(set(basis)) != 471:
        raise ValueError("D18 basis identity changed")
    c = core.ALPHA1 / core.ALPHA2
    outer_vector = dilation.dilate_vector(basis, vector, c)
    terms = {(a, lam): coefficient
             for coefficient, (a, lam) in zip(outer_vector, basis)
             if coefficient}
    square = scan.square_orbit_polynomial(terms)
    supports = core.make_supports()
    high, low = supports["H"], supports["L"]
    if (tuple(high.schedule) != core.SCHEDULE or
            tuple(low.schedule) != core.SCHEDULE):
        raise ValueError("scheduled support mismatch")

    started = time.monotonic()
    high_i = Q(0)
    low_i = Q(0)
    for index, ((power, orbit), coefficient) in enumerate(
            sorted(square.items()), 1):
        high_i += coefficient * high.orbit_support_moment(orbit, power)
        low_i += coefficient * low.orbit_support_moment(orbit, power)
        if index % 500 == 0:
            print(f"I terms {index}/{len(square)}", flush=True)
    capped_i = high_i - low_i
    uncapped_i = Q(uncapped["I_matrix"][1][1])
    if not (Q(0) < low_i < high_i and Q(0) < capped_i <= uncapped_i):
        raise ArithmeticError("capped-shell denominator nesting failed")
    if any(path.read_bytes() != data for path, data in before.items()):
        raise RuntimeError("input changed during exact contraction")

    result = {
        "format": "active25-d18-natural-outer-I-exact-v1",
        "status": "EXACT I-ONLY DIAGNOSTIC",
        "rigorous_values": True,
        "theorem_ready": False,
        "never_implies": ["a Rayleigh quotient", "Proposition 1", "H1<=236"],
        "parameters": core.parameter_record(),
        "dilation": str(c),
        "basis_dimension": len(basis),
        "nonzero_dilated_coefficients": len(terms),
        "square_orbit_groups": len(square),
        "high_I": str(high_i),
        "low_I": str(low_i),
        "capped_outer_I": str(capped_i),
        "uncapped_outer_I": str(uncapped_i),
        "exact_retained_fraction": str(capped_i / uncapped_i),
        "retained_fraction_decimal": format(float(capped_i / uncapped_i), ".17g"),
        "wall_seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "script_sha256": sha256(FILE),
        "source_hashes": {str(path.relative_to(REPO)): digest
                          for path, digest in PINS.items()},
    }
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({
        "capped_outer_I": str(capped_i),
        "retained_fraction_decimal": result["retained_fraction_decimal"],
        "output_sha256": sha256(payload),
        "wall_seconds": result["wall_seconds"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
