#!/usr/bin/env python3
"""Exact uncapped D18 two-band calibration at rational outer parameters.

The resulting shell is not analytically approved.  This program computes an
exact relaxation and the one-coordinate projection of the shell Riesz
representer; it can prioritize capped geometries but cannot prove a prime-gap
bound.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
DILATION = REPO / "scripts/full_simplex_dilated_vector_proxy.py"
PENCIL = REPO / "scripts/full_simplex_two_band_dilated_pencil.py"
SCAN = REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"
CERT = REPO / (
    "agents/exact-integrator/results/"
    "aquarter_fullsimplex_k48_B18_refined_exact.json")
PINS = {
    DILATION: "3219047bd9d339e15946947f68bd6484d23af722337ba70771c488e3e1238794",
    PENCIL: "85c4847c4803015d9aa14f67d257be62a4d23edbff5843f191e903ce885d4804",
    SCAN: "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9",
    CERT: "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58",
}
K = 48
ALPHA1 = Q(103, 400)
ETA1 = Q(97, 400)


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def strict_json(path: Path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key {key!r} in {path}")
            result[key] = value
        return result
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite JSON token {token}")))


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path: Path, payload: bytes) -> None:
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def compute(alpha2: Q, eta2: Q, delta: Q):
    if not (Q(0) < delta < ALPHA1 < alpha2 < Q(1, 2) and
            ETA1 < eta2 < alpha2):
        raise ValueError("inconsistent rational two-band parameters")
    start_self = FILE.read_bytes()
    start_inputs = {}
    for path, expected in PINS.items():
        data = path.read_bytes()
        if sha256(data) != expected:
            raise RuntimeError(f"pinned input changed: {path}")
        start_inputs[path] = data
    dilation = load_module("param_d18_dilation_v1", DILATION)
    pencil = load_module("param_d18_pencil_v1", PENCIL)
    scan = load_module("param_d18_scan_v1", SCAN)
    scan.self_test()
    cert = strict_json(CERT)
    if ((cert.get("k"), cert.get("degree")) != (K, 18) or
            cert.get("format") != "bv-even-exact-vector-v1"):
        raise ValueError("D18 certificate identity changed")
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in cert["basis"])
    inner = tuple(Q(x) for x in cert["rational_vector"])
    if len(basis) != 471 or len(inner) != 471 or len(set(basis)) != 471:
        raise ValueError("D18 basis inventory changed")
    outer_c = ALPHA1 / alpha2
    outer = dilation.dilate_vector(basis, inner, outer_c)

    a00, b00, *_ = scan.direct_forms(
        K, basis, inner, ALPHA1, ETA1, delta)
    ao1, bo1, *_ = scan.direct_forms(
        K, basis, outer, ALPHA1, eta2, delta)
    ao2, bo2, *_ = scan.direct_forms(
        K, basis, outer, alpha2, eta2, delta)
    a11 = ao2 - ao1
    mi = scan.marginal_polynomial(basis, inner, K, ALPHA1)
    mo1 = scan.marginal_polynomial(basis, outer, K, ALPHA1)
    mo2 = scan.marginal_polynomial(basis, outer, K, alpha2)
    ci2, n_ci2 = pencil.marginal_cross(
        K, mi, mo2, ALPHA1, alpha2, eta2)
    ci1, n_ci1 = pencil.marginal_cross(
        K, mi, mo1, ALPHA1, ALPHA1, eta2)
    co12, n_co12 = pencil.marginal_cross(
        K, mo1, mo2, ALPHA1, alpha2, eta2)
    b01 = K * (ci2 - ci1)
    b11 = bo2 + bo1 - 2 * K * co12
    if not (a00 > 0 and a11 > 0 and b11 >= 0):
        raise ArithmeticError("nonpositive exact form")

    stationary = pencil.stationary_amplitude(
        a00, a11, b00, b01, b11, 170)
    amplitude = Q(format(stationary, ".80E"))
    denominator, numerator, quotient = pencil.exact_quotient(
        a00, a11, b00, b01, b11, amplitude)
    projection = b01 * b01 / a11
    deficit = a00 - b00
    if FILE.read_bytes() != start_self or any(
            path.read_bytes() != data for path, data in start_inputs.items()):
        raise RuntimeError("source closure changed during exact computation")
    return {
        "format": "parameterized-d18-uncapped-pencil-exact-v1",
        "status": "EXACT UNAPPROVED RELAXATION",
        "rigorous_values": True,
        "analytic_support_approved": False,
        "theorem_ready": False,
        "never_implies": ["a capped-support quotient", "Proposition 1",
                          "H1<=236"],
        "parameters": {"k": K, "alpha1": str(ALPHA1),
                       "eta1": str(ETA1), "alpha2": str(alpha2),
                       "eta2": str(eta2), "delta": str(delta),
                       "outer_c": str(outer_c)},
        "basis_dimension": len(basis),
        "I_matrix": [[str(a00), "0"], ["0", str(a11)]],
        "kJ_matrix": [[str(b00), str(b01)],
                       [str(b01), str(b11)]],
        "inner_quotient": str(b00 / a00),
        "inner_deficit_over_I": str(deficit / a00),
        "natural_projection_over_inner_I": str(projection / a00),
        "natural_projection_over_deficit": str(projection / deficit),
        "rationalized_stationary_amplitude": str(amplitude),
        "optimized_exact_denominator": str(denominator),
        "optimized_exact_numerator": str(numerator),
        "optimized_exact_quotient": str(quotient),
        "optimized_margin": str(numerator - denominator),
        "optimized_margin_positive": numerator > denominator,
        "marginal_cross_products": [n_ci2, n_ci1, n_co12],
        "source_sha256": sha256(start_self),
        "source_hashes": {str(path.relative_to(REPO)): digest
                          for path, digest in PINS.items()},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha2", type=Q, required=True)
    parser.add_argument("--eta2", type=Q, required=True)
    parser.add_argument("--delta", type=Q, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = compute(args.alpha2, args.eta2, args.delta)
    result["wall_seconds"] = time.monotonic() - started
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "output_sha256": sha256(payload),
        "optimized_quotient": result["optimized_exact_quotient"],
        "projection_over_deficit": result[
            "natural_projection_over_deficit"],
        "wall_seconds": result["wall_seconds"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
