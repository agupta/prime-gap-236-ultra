#!/usr/bin/env python3
"""Independent exact pairwise checker for a scheduled grouped result.

The checker does not import ``scheduled_fixed_vector`` or
``grouped_fixed_vector`` and does not trust matrix/result entries.  It defines
the constant-extended support lookup independently, reconstructs every basis
pair with ``exact_integrator``'s canonical one-orbit recurrence, and contracts
the supplied rational vector.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

import exact_integrator as ei  # noqa: E402


TOKEN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?$")


def sha(data):
    if isinstance(data, (str, Path)):
        data = Path(data).read_bytes()
    return hashlib.sha256(data).hexdigest()


def parse_schedule_bytes(data, k):
    raw = json.loads(data)
    if (not isinstance(raw, dict) or
            set(raw) != {"status", "extension", "beta_schedule"} or
            raw.get("status") != "constant-extension-beta-schedule" or
            raw.get("extension") != "constant"):
        raise ValueError("invalid constant-extension schedule schema")
    tokens = raw.get("beta_schedule")
    if not isinstance(tokens, list) or not 1 <= len(tokens) <= k:
        raise ValueError("invalid schedule length")
    values = []
    for token in tokens:
        if not isinstance(token, str) or TOKEN.fullmatch(token) is None:
            raise ValueError("invalid rational token")
        value = Q(token)
        if str(value) != token or value <= 0:
            raise ValueError("noncanonical/nonpositive schedule entry")
        values.append(value)
    return tuple(values)


def canonical_schedule_bytes(schedule):
    payload = {
        "beta_schedule": [str(x) for x in schedule],
        "extension": "constant",
        "status": "constant-extension-beta-schedule",
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
            "\n").encode("ascii")


def canonical_support_bytes(k, alpha, delta, eta, schedule):
    payload = {
        "alpha": str(alpha),
        "beta_schedule_sha256": sha(canonical_schedule_bytes(schedule)),
        "delta": str(delta),
        "eta": str(eta),
        "extension": "constant",
        "k": k,
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
            "\n").encode("ascii")


@dataclass(frozen=True)
class PairwiseScheduledSupport(ei.OneStratumSupport):
    schedule: tuple = ()

    @classmethod
    def from_schedule(cls, k, alpha, delta, eta, schedule):
        schedule = tuple(schedule)
        if not schedule or len(schedule) > k or any(x <= 0 for x in schedule):
            raise ValueError("invalid pairwise schedule")
        return cls(k, alpha, delta, eta,
                   schedule[0], schedule[min(1, len(schedule) - 1)],
                   schedule[min(2, len(schedule) - 1)], schedule)

    def beta(self, r):
        if r <= 0:
            raise ValueError("beta requires positive r")
        return self.schedule[min(r, len(self.schedule)) - 1]


def pairwise_forms(support, labels, coefficients):
    denominator = Q(0)
    j_value = Q(0)
    pairs = 0
    for i, left in enumerate(labels):
        for j in range(i + 1):
            factor = coefficients[i] * coefficients[j] * (2 if i != j else 1)
            denominator += factor * support.basis_m1(left, labels[j])
            j_value += factor * support.basis_j(left, labels[j])
            pairs += 1
    return denominator, j_value, support.k * j_value, pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result_json")
    parser.add_argument("--input-json", required=True)
    parser.add_argument("--schedule-json", required=True)
    parser.add_argument("--expect-above", type=Q)
    args = parser.parse_args()

    result_bytes = Path(args.result_json).read_bytes()
    result = json.loads(result_bytes)
    input_bytes = Path(args.input_json).read_bytes()
    source = json.loads(input_bytes)
    k = int(source.get("k", -1))
    schedule_bytes = Path(args.schedule_json).read_bytes()
    schedule = parse_schedule_bytes(schedule_bytes, k)
    if result.get("status") != "exact-scheduled-grouped-fixed-vector" or \
            result.get("rigorous") is not True:
        raise SystemExit("result is not a rigorous scheduled evaluation")
    if result.get("k") != k or result.get("basis_dimension") != len(source["basis"]):
        raise SystemExit("dimension mismatch")
    if result.get("input_sha256") != sha(input_bytes):
        raise SystemExit("input SHA mismatch")
    if result.get("schedule_file_sha256") != sha(schedule_bytes):
        raise SystemExit("schedule file SHA mismatch")
    if result.get("beta_schedule") != [str(x) for x in schedule] or \
            result.get("beta_schedule_length") != len(schedule) or \
            result.get("extension") != "constant":
        raise SystemExit("serialized schedule mismatch")
    canonical_sha = sha(canonical_schedule_bytes(schedule))
    if result.get("beta_schedule_sha256") != canonical_sha:
        raise SystemExit("canonical schedule SHA mismatch")
    parameters = result.get("parameters", {})
    try:
        alpha, delta, eta = (Q(parameters[key]) for key in
                             ("alpha", "delta", "eta"))
    except Exception as exc:
        raise SystemExit(f"invalid geometry: {exc}")
    support_sha = sha(canonical_support_bytes(
        k, alpha, delta, eta, schedule))
    if result.get("support_sha256") != support_sha:
        raise SystemExit("support SHA mismatch")
    scheduled_script = HERE / "scheduled_fixed_vector.py"
    if result.get("script_sha256") != sha(scheduled_script):
        raise SystemExit("scheduled producer SHA mismatch")
    if result.get("integrator_sha256") != sha(ei.__file__):
        raise SystemExit("integrator SHA mismatch")

    labels = [(int(a), tuple(int(x) for x in lam))
              for a, lam in source["basis"]]
    coefficients = [Q(x) for x in source["rational_vector"]]
    if len(labels) != len(coefficients):
        raise SystemExit("basis/vector mismatch")
    support = PairwiseScheduledSupport.from_schedule(
        k, alpha, delta, eta, schedule)
    denominator, j_value, numerator, pairs = pairwise_forms(
        support, labels, coefficients)
    expected = {
        "denominator": denominator,
        "j_value": j_value,
        "numerator": numerator,
        "quotient": numerator / denominator,
        "margin": numerator - denominator,
    }
    for key, value in expected.items():
        if Q(result.get(key, "NaN")) != value:
            raise SystemExit(f"{key} mismatch")
    if result.get("denominator_positive") != (denominator > 0) or \
            result.get("margin_positive") != (numerator > denominator):
        raise SystemExit("serialized sign flag mismatch")
    if args.expect_above is not None and not expected["quotient"] > args.expect_above:
        raise SystemExit("quotient does not exceed requested threshold")
    print("SCHEDULED PAIRWISE CHECK PASS")
    print(f"result_sha256={sha(result_bytes)}")
    print(f"checker_sha256={sha(__file__)}")
    print(f"basis_pairs={pairs}")
    print(f"denominator={denominator}")
    print(f"j_value={j_value}")
    print(f"numerator={numerator}")
    print(f"quotient={expected['quotient']}")
    print(f"margin={expected['margin']}")


if __name__ == "__main__":
    main()
