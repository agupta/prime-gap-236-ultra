#!/usr/bin/env python3
"""Exact grouped evaluation for an explicit constant-extended B_m schedule.

This is deliberately separate from ``grouped_fixed_vector.py``: the latter is
the pinned certificate implementation for the three-parameter
``(B_1,B_2,B_{3+})`` support.  Here a JSON input supplies every
``B_1,...,B_M`` and ``B_m=B_M`` for ``m>M``.  The grouped integration formulas
are inherited unchanged; only the support's ``beta(r)`` lookup is replaced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import sys
import time
from dataclasses import dataclass
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import (  # noqa: E402
    GroupedEvaluator,
    install_decimal,
    parse_rational_decimal,
    precompute_orbits,
)


RATIONAL_TOKEN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?$")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_schedule_bytes(schedule) -> bytes:
    """Canonical, path-independent identity of the whole finite schedule."""
    payload = {
        "beta_schedule": [str(Fraction(value)) for value in schedule],
        "extension": "constant",
        "status": "constant-extension-beta-schedule",
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
            "\n").encode("ascii")


def canonical_support_bytes(k, alpha, delta, eta, schedule) -> bytes:
    """Canonical identity of all geometry, including every supplied B_m."""
    payload = {
        "alpha": str(Fraction(alpha)),
        "beta_schedule_sha256": _sha256(canonical_schedule_bytes(schedule)),
        "delta": str(Fraction(delta)),
        "eta": str(Fraction(eta)),
        "extension": "constant",
        "k": int(k),
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
            "\n").encode("ascii")


def parse_schedule_payload(raw, k):
    """Fail closed on an ambiguous or irrelevant schedule description."""
    expected_keys = {"status", "extension", "beta_schedule"}
    if not isinstance(raw, dict) or set(raw) != expected_keys:
        raise ValueError("schedule JSON must have exactly status/extension/beta_schedule")
    if raw["status"] != "constant-extension-beta-schedule":
        raise ValueError("wrong schedule status")
    if raw["extension"] != "constant":
        raise ValueError("only constant extension is implemented")
    tokens = raw["beta_schedule"]
    if not isinstance(tokens, list) or not 1 <= len(tokens) <= int(k):
        raise ValueError("beta_schedule length must lie in [1,k]")
    schedule = []
    for token in tokens:
        if not isinstance(token, str) or RATIONAL_TOKEN.fullmatch(token) is None:
            raise ValueError("schedule entries must be canonical rational strings")
        value = Fraction(token)
        if token != str(value):
            raise ValueError(f"noncanonical schedule entry: {token!r}")
        if value <= 0:
            raise ValueError("schedule entries must be positive")
        schedule.append(value)
    return tuple(schedule)


def load_schedule(path, k):
    data = Path(path).read_bytes()
    raw = json.loads(data)
    schedule = parse_schedule_payload(raw, k)
    canonical = canonical_schedule_bytes(schedule)
    return schedule, {
        "schedule_json": str(path),
        "schedule_file_sha256": _sha256(data),
        "beta_schedule_sha256": _sha256(canonical),
        "beta_schedule": [str(x) for x in schedule],
        "beta_schedule_length": len(schedule),
        "extension": "constant",
    }


@dataclass(frozen=True)
class ScheduledSupport(ei.OneStratumSupport):
    """One-stratum geometry with explicit B_1,...,B_M, then B_M forever."""

    beta_schedule: tuple = ()
    extension: str = "constant"

    def __post_init__(self):
        if not self.beta_schedule:
            raise ValueError("empty beta schedule")
        if self.extension != "constant":
            raise ValueError("unsupported beta extension")
        if len(self.beta_schedule) > self.k:
            raise ValueError("schedule longer than k has unbound irrelevant entries")
        if any(value <= 0 for value in self.beta_schedule):
            raise ValueError("beta schedule must be positive")
        proxies = (self.beta_schedule[0],
                   self.beta_schedule[min(1, len(self.beta_schedule) - 1)],
                   self.beta_schedule[min(2, len(self.beta_schedule) - 1)])
        if (self.beta1, self.beta2, self.beta3plus) != proxies:
            raise ValueError("legacy beta proxy fields disagree with schedule")

    @classmethod
    def from_schedule(cls, k, alpha, delta, eta, schedule):
        schedule = tuple(schedule)
        if not schedule:
            raise ValueError("empty beta schedule")
        return cls(k, alpha, delta, eta,
                   schedule[0], schedule[min(1, len(schedule) - 1)],
                   schedule[min(2, len(schedule) - 1)], schedule, "constant")

    def beta(self, r):
        if r <= 0:
            raise ValueError("beta is defined only for positive r")
        return self.beta_schedule[min(r, len(self.beta_schedule)) - 1]


def evaluate_scheduled(support, labels, coefficients, scalar=Fraction,
                       progress=False, workers=1):
    """Return scalar I,J plus traversal counts for programmatic tests/search."""
    evaluator = GroupedEvaluator(support, labels, coefficients, scalar)
    denominator, groups, faces = evaluator.evaluate_i(progress, workers)
    j_value, components, integrals = evaluator.evaluate_j(progress, workers)
    return {
        "denominator": denominator,
        "j_value": j_value,
        "numerator": scalar(support.k) * j_value,
        "i_orbit_groups": groups,
        "i_faces": faces,
        "marginal_components": components,
        "j_branch_integrals": integrals,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--alpha", required=True)
    parser.add_argument("--delta", required=True)
    parser.add_argument("--eta", required=True)
    parser.add_argument("--beta-schedule-json", required=True)
    parser.add_argument("--decimal-dps", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")

    input_bytes = Path(args.input_json).read_bytes()
    raw = json.loads(input_bytes)
    k = int(raw["k"])
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    if len(labels) != len(raw["rational_vector"]):
        raise SystemExit("basis/vector dimension mismatch")
    schedule_q, schedule_metadata = load_schedule(args.beta_schedule_json, k)
    geometry_q = tuple(Fraction(x) for x in
                       (args.alpha, args.delta, args.eta))
    if any(x <= 0 for x in geometry_q):
        raise SystemExit("alpha, delta, and eta must be positive")

    orbit_table = precompute_orbits(labels, k)
    if args.decimal_dps:
        getcontext().prec = args.decimal_dps
        scalar = install_decimal(orbit_table, args.decimal_dps)
        parse = parse_rational_decimal
        rigorous = False
    else:
        scalar, parse, rigorous = Fraction, Fraction, True
    alpha, delta, eta = (parse(x) for x in
                         (args.alpha, args.delta, args.eta))
    schedule = tuple(parse(str(x)) for x in schedule_q)
    support = ScheduledSupport.from_schedule(
        k, alpha, delta, eta, schedule)
    coefficients = [parse(x) for x in raw["rational_vector"]]

    start = time.perf_counter()
    forms = evaluate_scheduled(
        support, labels, coefficients, scalar, args.progress, args.workers)
    elapsed = time.perf_counter() - start
    denominator, numerator = forms["denominator"], forms["numerator"]
    support_sha = _sha256(canonical_support_bytes(
        k, *geometry_q, schedule_q))
    result = {
        "status": ("exact-scheduled-grouped-fixed-vector" if rigorous else
                   "multiprecision-scheduled-grouped-fixed-vector-discovery"),
        "rigorous": rigorous,
        "decimal_dps": args.decimal_dps,
        "input_json": args.input_json,
        "input_sha256": _sha256(input_bytes),
        "script_sha256": _sha256(Path(__file__).read_bytes()),
        "grouped_evaluator_sha256": _sha256(Path(
            os.path.join(HERE, "grouped_fixed_vector.py")).read_bytes()),
        "integrator_sha256": _sha256(Path(ei.__file__).read_bytes()),
        "k": k,
        "parameters": {"alpha": args.alpha, "delta": args.delta,
                       "eta": args.eta},
        "support_sha256": support_sha,
        **schedule_metadata,
        "basis_dimension": len(labels),
        "workers": args.workers,
        "elapsed_seconds": elapsed,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "i_orbit_groups": forms["i_orbit_groups"],
        "i_faces": forms["i_faces"],
        "marginal_components": forms["marginal_components"],
        "j_branch_integrals": forms["j_branch_integrals"],
        "denominator_positive": denominator > 0,
        "margin_positive": numerator > denominator,
        "denominator": str(denominator),
        "j_value": str(forms["j_value"]),
        "numerator": str(numerator),
        "quotient": str(numerator / denominator),
        "margin": str(numerator - denominator),
    }
    rendered = json.dumps(result, indent=2) + "\n"
    Path(args.output).write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
