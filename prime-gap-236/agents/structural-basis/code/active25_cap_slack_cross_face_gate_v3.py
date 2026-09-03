#!/usr/bin/env python3
"""Exact, resource-bounded one-face gate for the cap-slack/D16 pilot.

This program is intentionally limited to ``(common_r,h)=(10,10)``.  It uses
the independently reviewed cap marginal and grouped inner-density lift from
the frozen v2 planner, then independently evaluates the degree-zero columns
through the established active25 core.  It cannot traverse a common-r shard
or assemble a quotient.
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
import signal
import stat
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
PILOT_SOURCE = FILE.with_name("active25_cap_slack_cross_pilot_v2.py")
PILOT_TEST = (REPO / "agents/structural-basis/tests/"
              "test_active25_cap_slack_cross_pilot_v2.py")
PILOT_SPEC = (REPO / "agents/structural-basis/"
              "ACTIVE25-CAP-SLACK-CROSS-PILOT-V2.md")
PILOT_ARTIFACT = (REPO / "agents/structural-basis/results/"
                  "active25_cap_slack_d16_cross_pilot_disabled_v2.json")
AUDIT_CHECKER = (REPO / "agents/audit/"
                 "verify_active25_cap_slack_cross_pilot_v2.py")
AUDIT_RESULT = (REPO / "agents/audit/results/"
                "active25_cap_slack_cross_pilot_v2_prelaunch_audit.json")
AUDIT_REPORT = (REPO / "agents/audit/"
                "ACTIVE25-CAP-SLACK-CROSS-PILOT-V2-PRELAUNCH-AUDIT.md")
CORE_SOURCE = (REPO / "agents/small-delta-frontier/"
               "frontier_active25_inner_d16_tagged_shell.py")
V6_SOURCE = (REPO / "agents/small-delta-frontier/"
             "frontier_active25_inner_d16_staged_v6.py")

PINNED = {
    PILOT_SOURCE:
        "cd20a85e51d623476b5433626ec4ce35d242e8a00a5f706db1af05509b59d913",
    PILOT_TEST:
        "8f16fdc5a72f8e26ffc5c7b2a0ee5f0e8fc734a4383edeb3a2d414a97df94a1f",
    PILOT_SPEC:
        "ce965d905274af92a3c64496369ffdb5cd97bf5c75a088432428f5707d032851",
    PILOT_ARTIFACT:
        "3a07078ca5b480b0d8d554019b42e05b7fb732a1225d97ff761d5b5231abd31c",
    AUDIT_CHECKER:
        "881622f7bb8e189f240e76c8a31750ef0fb2db42b1561d9e03e06dc1124348fe",
    AUDIT_RESULT:
        "bbda024a64b32bca96c76cc7b77917b4779daa3c1c108f3a2ff163200249112d",
    AUDIT_REPORT:
        "bf8e3bbfec2c6fe3bec3a9a30a7c6caa26ad6912b93b4082253feb4438e5b17a",
    CORE_SOURCE:
        "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    V6_SOURCE:
        "cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e",
}

COMMON_R = 10
SELECTED_H = 10
WALL_LIMIT_SECONDS = 20
RSS_LIMIT_KIB = 256 * 1024
OUTPUT_FORMAT = "active25-cap-slack-D16-one-face-gate-v3"


class GateTimeout(RuntimeError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def strict_sha(value, name):
    if (type(value) is not str or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"{name} is not a canonical SHA-256")
    return value


def require_pins():
    observed = {}
    for path, expected in PINNED.items():
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"frozen gate input changed: {path}: {actual}")
        observed[str(path.relative_to(REPO))] = actual
    return dict(sorted(observed.items()))


def load_pilot():
    spec = importlib.util.spec_from_file_location(
        "active25_cap_slack_gate_frozen_pilot", PILOT_SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(PILOT_SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def thread_count():
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("Threads:"):
            return int(line.split()[1])
    raise RuntimeError("process thread count is unavailable")


def evaluate_polynomial(polynomial, z, w):
    return sum((Q(value) * z ** a * w ** b
                for (a, b), value in polynomial.items()), Q(0))


def literal_positive_degree_oracles(pilot):
    """Literal endpoint checks for d=1,2 on every marginal branch."""
    delta = Q(1, 20)
    support = pilot.V1.A25.shell.ScheduledStratumSupport.make(
        4, Q(3, 10), Q(1, 4), delta,
        (Q(3, 20), Q(1, 5), Q(1, 4), Q(3, 10)))
    r, h = 1, 1
    u0 = (r + h) * delta
    samples = {
        "Sdelta": (Q(1, 100), Q(1, 200)),
        "Stotal": (Q(2, 25), Q(3, 40)),
        "Lbig": (Q(1, 50), Q(1, 100)),
        "Ltotal": (Q(1, 50), Q(7, 100)),
    }
    records = []
    for branch in ("Sdelta", "Stotal", "Ltotal", "Lbig"):
        z, w = samples[branch]
        count = pilot.V1.branch_total(r, branch)
        gamma = support.beta(count) - count * delta
        total_upper = support.alpha - u0 - z - w
        cap_upper = support.beta(count) - r * delta - z
        for degree in (1, 2):
            if branch == "Sdelta":
                literal = delta * (gamma - z) ** degree
            elif branch == "Stotal":
                literal = total_upper * (gamma - z) ** degree
            else:
                anchor = gamma + delta - z
                upper = cap_upper if branch == "Lbig" else total_upper
                literal = ((anchor - delta) ** (degree + 1) -
                           (anchor - upper) ** (degree + 1)) / (degree + 1)
            literal /= gamma ** degree
            custom = evaluate_polynomial(
                pilot.V1.independent_cap_marginal(
                    support, r, h, branch, degree), z, w)
            reference = evaluate_polynomial(
                pilot.V1.CAP.cap_slack_marginal(
                    support, r, h, branch, degree), z, w)
            if custom != literal or reference != literal:
                raise ArithmeticError(
                    f"literal d>0 marginal oracle failed: {branch}, d={degree}")
            records.append({"branch": branch, "degree": degree,
                            "literal": str(literal)})
    return records


def _canonical_label_values(labels, values):
    return [[label[0], label[1], str(values[label])] for label in labels]


def degree_zero_core_face(pilot):
    core = pilot.V1.A25
    named, catalog, amplitudes, inner_i, inner_b = \
        core.production_cross_inputs()
    table, counts, geometric, nonzero, faces = core.grouped_weighted_cross(
        named, catalog, core.production_pair_weights(amplitudes), core.ETA2,
        common_strata=(COMMON_R,), selected_h=SELECTED_H,
        direct_full_left=("R", "V"), progress=False)
    if faces != 1:
        raise ArithmeticError("degree-zero reference did not evaluate one face")
    return table, {
        "domain_counts": counts,
        "faces": faces,
        "geometric_groups": geometric,
        "nonzero_groups": nonzero,
        "inner_I": str(inner_i),
        "inner_48J": str(inner_b),
    }


def run_gate():
    process_started = time.monotonic_ns()
    if thread_count() != 1:
        raise RuntimeError("the one-face gate requires exactly one thread")
    pins = require_pins()
    pilot = load_pilot()
    oracle_records = literal_positive_degree_oracles(pilot)

    pilot_started = time.monotonic_ns()
    values, metadata = pilot.pilot_shard(
        COMMON_R, selected_h=SELECTED_H, progress=False)
    pilot_finished = time.monotonic_ns()
    if (metadata.get("faces") != 1 or
            metadata.get("complete_common_r") is not False or
            metadata.get("selected_h") != SELECTED_H):
        raise ArithmeticError("pilot gate returned the wrong face scope")

    reference_started = time.monotonic_ns()
    degree_zero, reference_meta = degree_zero_core_face(pilot)
    reference_finished = time.monotonic_ns()
    labels = pilot.pilot_labels()
    mismatches = [count for count in range(26)
                  if values[(count, 0)] != degree_zero[count]]
    if mismatches:
        raise ArithmeticError(
            f"pilot degree-zero/core mismatch on counts {mismatches}")
    if any(degree_zero[count] for count in range(26)
           if count not in (COMMON_R, COMMON_R + 1)):
        raise ArithmeticError("degree-zero reference leaked off adjacent counts")

    process_finished = time.monotonic_ns()
    wall = (process_finished - process_started) / 1_000_000_000
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if wall > WALL_LIMIT_SECONDS:
        raise RuntimeError(f"one-face wall gate failed: {wall:.9f} seconds")
    if peak > RSS_LIMIT_KIB:
        raise RuntimeError(f"one-face RSS gate failed: {peak} KiB")
    if thread_count() != 1:
        raise RuntimeError("the one-face gate created an extra thread")
    if require_pins() != pins:
        raise RuntimeError("frozen gate input changed during evaluation")

    serialized = _canonical_label_values(labels, values)
    degree_zero_serialized = [str(degree_zero[count]) for count in range(26)]
    positive = [row for row in serialized if row[1] > 0]
    return {
        "status": "PASS",
        "format": OUTPUT_FORMAT,
        "claim_scope": "one exact face for resource cost only; no quotient",
        "rigorous_values": True,
        "theorem_ready": False,
        "complete_cross": False,
        "launch_authorized": False,
        "workers": 1,
        "common_r": COMMON_R,
        "selected_h": SELECTED_H,
        "coordinates": len(labels),
        "source_sha256": sha256(FILE),
        "dependency_sha256": pins,
        "parameters": pilot.V1.A25.parameter_record(),
        "custom_marginal_literal_oracles": {
            "degrees": [1, 2],
            "branches": ["Sdelta", "Stotal", "Ltotal", "Lbig"],
            "cases": len(oracle_records),
            "records_sha256": sha256_bytes(canonical_json(oracle_records)),
            "all_exact": True,
        },
        "pilot_raw_J_cross_by_label": serialized,
        "pilot_raw_J_cross_sha256": sha256_bytes(canonical_json(serialized)),
        "positive_degree_raw_J_cross_sha256":
            sha256_bytes(canonical_json(positive)),
        "degree_zero_reference": {
            "description": "pinned v6 arithmetic core, same grouped face",
            "core_sha256": PINNED[CORE_SOURCE],
            "v6_driver_sha256": PINNED[V6_SOURCE],
            "raw_J_cross_by_count": degree_zero_serialized,
            "raw_J_cross_sha256":
                sha256_bytes(canonical_json(degree_zero_serialized)),
            "exact_countwise_match": True,
            **reference_meta,
        },
        "pilot_metadata": {
            key: (str(value) if key in ("inner_I", "inner_48J") else value)
            for key, value in metadata.items()
        },
        "resource_gate": {
            "wall_limit_seconds": WALL_LIMIT_SECONDS,
            "rss_limit_kib": RSS_LIMIT_KIB,
            "process_wall_seconds": wall,
            "pilot_face_wall_seconds":
                (pilot_finished - pilot_started) / 1_000_000_000,
            "degree_zero_reference_wall_seconds":
                (reference_finished - reference_started) / 1_000_000_000,
            "peak_rss_kib": peak,
            "wall_pass": True,
            "rss_pass": True,
        },
    }


def _timeout_handler(_signum, _frame):
    raise GateTimeout("one-face gate exceeded its 20-second hard deadline")


def enforce_cli_limits():
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    requested = RSS_LIMIT_KIB * 1024
    if hard != resource.RLIM_INFINITY and hard < requested:
        raise RuntimeError("existing address-space hard limit is below gate limit")
    resource.setrlimit(resource.RLIMIT_AS, (requested, hard))
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, WALL_LIMIT_SECONDS)


def publish(path, payload):
    target = Path(path).resolve()
    protected = {FILE.resolve(), *(item.resolve() for item in PINNED)}
    if target in protected:
        raise ValueError("gate output aliases a protected input")
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o644)
    try:
        written = 0
        while written < len(payload):
            count = os.write(descriptor, payload[written:])
            if count <= 0:
                raise OSError("short gate-artifact write")
            written += count
        os.fsync(descriptor)
        observed = os.fstat(descriptor)
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            raise RuntimeError("gate output is not a singly linked regular file")
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args()
    expected = strict_sha(args.expected_self_sha256, "expected self SHA")
    if sha256(FILE) != expected:
        raise RuntimeError("gate source differs from externally supplied SHA")
    enforce_cli_limits()
    result = run_gate()
    payload = canonical_json(result)
    publish(args.output, payload)
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps({
        "artifact_sha256": sha256_bytes(payload),
        "launch_authorized": False,
        **result["resource_gate"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
