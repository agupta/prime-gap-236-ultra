#!/usr/bin/env python3
"""Checkpointed exact I contraction for the active25 dilated-D18 shell.

Each invocation reconstructs the frozen D18 polynomial and emits one exact
large-coordinate-count contribution to

    integral_{H minus L} F_outer(t)^2 dt.

The 26 immutable shards can later be summed exactly.  This is deliberately an
I-only diagnostic: it contains no J form and cannot certify a prime gap.
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
SCALAR = REPO / "scripts/evaluate_active25_d18_outer_i_exact.py"
PINS = {
    SCALAR:
        "014c6c9dad731203d627c72f545ee225117af7b19a1b3394a3bf68d646fbf398",
}


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def require_pins():
    observed = {}
    for path, expected in PINS.items():
        data = path.read_bytes()
        if sha256(data) != expected:
            raise RuntimeError(f"pinned stage dependency changed: {path}")
        observed[path] = data
    return observed


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
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            answer[key] = value
        return answer

    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite JSON token: {token}")))


def shell_stratum_contraction(square, high, low, stratum: int,
                              *, group_start=0, group_stop=None,
                              progress_every=500):
    """Return exact H, L, and H-L moments for a consecutive term slice."""
    if type(stratum) is not int or not 0 <= stratum <= high.k:
        raise ValueError("invalid total large-coordinate count")
    if (high.k, high.delta, tuple(high.schedule)) != \
            (low.k, low.delta, tuple(low.schedule)):
        raise ValueError("high/low scheduled supports are incompatible")
    ordered = sorted(square.items())
    if group_stop is None:
        group_stop = len(ordered)
    if not ordered and (group_start, group_stop) == (0, 0):
        return Q(0), Q(0), Q(0)
    if (type(group_start) is not int or type(group_stop) is not int or
            not 0 <= group_start < group_stop <= len(ordered)):
        raise ValueError("invalid square-orbit group interval")
    high_i = Q(0)
    low_i = Q(0)
    selected = ordered[group_start:group_stop]
    for offset, ((power, orbit), coefficient) in enumerate(selected, 1):
        if (type(power) is not int or power < 0 or
                type(orbit) is not tuple or
                not isinstance(coefficient, Q)):
            raise ValueError("malformed square-orbit term")
        high_i += coefficient * high.orbit_support_moment_in_stratum(
            orbit, power, stratum)
        low_i += coefficient * low.orbit_support_moment_in_stratum(
            orbit, power, stratum)
        if progress_every and offset % progress_every == 0:
            print(f"I stratum {stratum}: groups "
                  f"{group_start + offset}/{len(ordered)}",
                  file=sys.stderr, flush=True)
    capped = high_i - low_i
    if (group_start, group_stop) == (0, len(ordered)) and \
            (high_i < 0 or low_i < 0 or capped < 0):
        raise ArithmeticError("exact square moment violates support nesting")
    return high_i, low_i, capped


def load_target():
    scalar = load_module("active25_d18_i_scalar_source", SCALAR)
    for path, expected in scalar.PINS.items():
        if scalar.sha256(path) != expected:
            raise RuntimeError(f"scalar dependency changed: {path}")
    core = scalar.load_module("active25_d18_i_stage_core", scalar.CORE_PATH)
    dilation = scalar.load_module(
        "active25_d18_i_stage_dilation", scalar.DILATION_PATH)
    scan = scalar.load_module("active25_d18_i_stage_scan", scalar.SCAN_PATH)
    scan.self_test()
    analytic = scalar.strict_json(scalar.ANALYTIC)
    certificate = scalar.strict_json(scalar.CERTIFICATE)
    uncapped = scalar.strict_json(scalar.UNCAPPED)
    if (analytic.get("status") != "AUDIT PASS" or
            analytic.get("schedule_id") !=
            "nonuniform-outer-active25-tail-v4" or
            analytic.get("parameters", {}).get("outer_active") !=
            list(range(26)) or
            (certificate.get("k"), certificate.get("degree")) != (48, 18) or
            uncapped.get("certificate_sha256") !=
            scalar.PINS[scalar.CERTIFICATE]):
        raise ValueError("target identity changed")
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in certificate["basis"])
    vector = tuple(Q(x) for x in certificate["rational_vector"])
    if len(basis) != 471 or len(vector) != 471 or len(set(basis)) != 471:
        raise ValueError("D18 basis identity changed")
    dilation_c = core.ALPHA1 / core.ALPHA2
    outer_vector = dilation.dilate_vector(basis, vector, dilation_c)
    terms = {(a, lam): coefficient
             for coefficient, (a, lam) in zip(outer_vector, basis)
             if coefficient}
    square = scan.square_orbit_polynomial(terms)
    if len(terms) != 471 or len(square) != 10761:
        raise ArithmeticError("D18 polynomial inventory changed")
    supports = core.make_supports()
    high, low = supports["H"], supports["L"]
    if (tuple(high.schedule) != core.SCHEDULE or
            tuple(low.schedule) != core.SCHEDULE):
        raise ValueError("scheduled support mismatch")
    return scalar, core, certificate, uncapped, dilation_c, square, high, low


def build_stage(stratum: int, group_start=0, group_stop=None):
    start_self = FILE.read_bytes()
    start_pins = require_pins()
    (scalar, core, certificate, uncapped, dilation_c, square, high, low) = \
        load_target()
    source_bytes = {path: path.read_bytes() for path in scalar.PINS}
    started = time.monotonic_ns()
    if group_stop is None:
        group_stop = len(square)
    high_i, low_i, capped = shell_stratum_contraction(
        square, high, low, stratum, group_start=group_start,
        group_stop=group_stop)
    elapsed = time.monotonic_ns() - started
    if (FILE.read_bytes() != start_self or require_pins() != start_pins or
            any(path.read_bytes() != data
                for path, data in source_bytes.items())):
        raise RuntimeError("stage source closure changed during contraction")
    return {
        "basis_dimension": 471,
        "capped_outer_I_in_stratum": str(capped),
        "complete_stratum": (group_start == 0 and group_stop == len(square)),
        "dilation": str(dilation_c),
        "format": "active25-d18-natural-outer-I-stratum-v1",
        "high_I_in_stratum": str(high_i),
        "low_I_in_stratum": str(low_i),
        "parameters": core.parameter_record(),
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "rigorous_values": True,
        "scalar_source_sha256": PINS[SCALAR],
        "script_sha256": sha256(start_self),
        "source_hashes": {
            str(path.relative_to(REPO)): expected
            for path, expected in sorted(
                scalar.PINS.items(), key=lambda item: str(item[0]))
        },
        "square_orbit_groups": len(square),
        "square_orbit_group_start": group_start,
        "square_orbit_group_stop": group_stop,
        "status": "EXACT I-ONLY STRATUM DIAGNOSTIC",
        "stratum": stratum,
        "theorem_ready": False,
        "uncapped_outer_I": uncapped["I_matrix"][1][1],
        "wall_nanoseconds": elapsed,
    }


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path: Path, payload: bytes):
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stratum", type=int, required=True)
    parser.add_argument("--group-start", type=int, default=0)
    parser.add_argument("--group-stop", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.stratum not in range(26):
        parser.error("--stratum must be in 0,...,25")
    payload = canonical_json(build_stage(
        args.stratum, args.group_start, args.group_stop))
    publish_exclusive(args.output, payload)
    print(json.dumps({"output_sha256": sha256(payload),
                      "stratum": args.stratum}, sort_keys=True))


if __name__ == "__main__":
    main()
