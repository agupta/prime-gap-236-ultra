#!/usr/bin/env python3
"""Lightweight independent replay of the frozen facts quoted in PROOF.md.

This is not an integral checker and cannot establish the pending scalar
certificate.  It deliberately imports no project arithmetic module.
"""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import json
from math import lcm
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]

PINS = {
    "PROOF.md":
        "1c221e0bcdaf2b6985ddc1164bae35ffd977210ad0f44088aacdb391c00d23aa",
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "agents/audit/PROP1-TO-H1-ONE-BAND-AUDIT.md":
        "951e927d91b961a1aa734ce73c620725d5a5b9286eed92aa0183a553c58629b3",
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json":
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    "agents/audit/results/truncated_lower_energy_v3_hostile_audit.json":
        "fea750c78b8bc7a022d8ee7d407a59405f4f790b1729305f47b21f8d4f2117a1",
    "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json":
        "8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170",
    "agents/structural-basis/results/"
    "bv_D14_fine_common_grid_candidates_exact_v2.json":
        "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0",
    "sources/admissible_48_236.txt":
        "adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_json(relative: str):
    return json.loads((REPO / relative).read_text(encoding="utf-8"))


def partitions(total: int, maximum: int | None = None):
    """Independent weakly-decreasing integer partitions."""
    if total == 0:
        yield ()
        return
    if maximum is None or maximum > total:
        maximum = total
    for first in range(maximum, 0, -1):
        for tail in partitions(total - first, first):
            yield (first,) + tail


def even_basis(degree: int):
    labels = []
    for half_degree in range(degree // 2 + 1):
        for half_partition in partitions(half_degree):
            partition = tuple(2 * item for item in half_partition)
            for radial_power in range(degree - 2 * half_degree + 1):
                labels.append((radial_power, partition))
    labels.sort(key=lambda label: (
        label[0] + sum(label[1]), sum(label[1]), len(label[1]),
        label[1], label[0]))
    return labels


def parse_vector(raw, expected_length: int, label: str):
    if (type(raw) is not list or len(raw) != expected_length or
            any(type(token) is not str for token in raw)):
        fail(f"{label} vector inventory is malformed")
    values = []
    for token in raw:
        try:
            value = Q(token)
        except (ValueError, ZeroDivisionError) as exc:
            raise RuntimeError(f"{label} has malformed rational") from exc
        if str(value) != token:
            fail(f"{label} has noncanonical rational {token!r}")
        values.append(value)
    return values


def primes_through(limit: int):
    answer = []
    for candidate in range(2, limit + 1):
        if all(candidate % prime for prime in answer
               if prime * prime <= candidate):
            answer.append(candidate)
    return answer


def main() -> int:
    snapshots = {}
    for relative, expected in PINS.items():
        data = (REPO / relative).read_bytes()
        if digest(data) != expected:
            fail(f"pinned input changed: {relative}")
        snapshots[relative] = data

    proof = snapshots["PROOF.md"].decode("utf-8")
    required_draft_markers = (
        "the exact-certificate field is still pending",
        "this file does not yet claim $H_1\\le236$",
        "`(C)` is not claimed",
        "proof draft, not a theorem proof",
    )
    if any(marker not in proof for marker in required_draft_markers):
        fail("PROOF.md lost a mandatory conditional-status marker")

    tex = snapshots[
        "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex"
    ].decode("utf-8")
    for literal in (
            "$(a,p)=1$ for all primes $p \\leq x$",
            "$2a+b \\leq 21$",
            "$\\mathcal{B}_{19}$"):
        if literal not in tex:
            fail(f"paper source no longer contains {literal!r}")

    support = load_json(
        "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json")
    parameters = support.get("parameters")
    expected_parameters = {
        "k": 48,
        "delta": "1/60",
        "epsilon": "3/400",
        "A": ["-3/400", "1/4", "9230917/36000000"],
        "alpha": ["103/400", "9500917/36000000"],
    }
    for key, expected in expected_parameters.items():
        if parameters.get(key) != expected:
            fail(f"support parameter mismatch: {key}")
    schedule = tuple(Q(token) for token in
                     parameters["outer_schedule_through_first_empty"])
    if len(schedule) != 12:
        fail("outer schedule does not have twelve frozen entries")
    delta = Q(parameters["delta"])
    extended = schedule + (schedule[-1],) * (60 - len(schedule))
    if any(value <= delta for value in extended):
        fail("a cap does not strictly exceed delta")
    if any(not left <= right <= left + delta
           for left, right in zip(extended, extended[1:])):
        fail("a cap-chain transition fails")
    if 13 * delta - extended[12] != Q(3749, 750000):
        fail("outer-count cutoff reserve mismatch")
    alpha1, alpha2 = map(Q, parameters["alpha"])
    a2 = Q(parameters["A"][2])
    epsilon = Q(parameters["epsilon"])
    if (a2 - epsilon != Q(8960917, 36000000) or
            alpha1 / alpha2 != Q(9270000, 9500917)):
        fail("cutoff or dilation mismatch")
    definition5 = support.get("definition5_single_outer_band")
    if definition5 != {
            "eta_inner_inner": "97/400",
            "eta_inner_outer": "8960917/36000000",
            "eta_outer_outer": "8960917/36000000",
            "eta_rule": "max(A_m-epsilon,A_mprime-epsilon)",
            "reason": ("there is exactly one outer band; no indefinite "
                       "cross-band outer-J summation is asserted by this gate")
            }:
        fail("Definition-5 cutoff record mismatch")

    inner = load_json(
        "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json")
    inner_basis = [(item[0], tuple(item[1])) for item in inner.get("basis", [])]
    if inner_basis != even_basis(19) or len(inner_basis) != 568:
        fail("D19 basis is not the complete canonical even basis")
    inner_vector = parse_vector(inner.get("rational_vector"), 568, "D19")
    if lcm(*(value.denominator for value in inner_vector)) != 10**87:
        fail("D19 coefficient denominator is not 10^87")
    inner_i = Q(inner.get("exact_denominator"))
    inner_d = Q(inner.get("exact_deficit"))
    inner_j48 = Q(inner.get("exact_numerator"))
    inner_normalized = Q(inner.get("exact_normalized_deficit"))
    if (inner_i <= 0 or inner_d <= 0 or inner_i - inner_j48 != inner_d or
            inner_d / inner_i != inner_normalized):
        fail("inner exact-form relation fails")

    outer = load_json(
        "agents/structural-basis/results/"
        "bv_D14_fine_common_grid_candidates_exact_v2.json")
    outer_basis = [(item[0], tuple(item[1])) for item in outer.get("basis", [])]
    if outer_basis != even_basis(14) or len(outer_basis) != 195:
        fail("D14 basis is not the complete canonical even basis")
    candidates = [item for item in outer.get("candidates", [])
                  if item.get("name") == "D14_grid_1e-38"]
    if len(candidates) != 1:
        fail("D14_grid_1e-38 candidate inventory mismatch")
    outer_vector = parse_vector(
        candidates[0].get("rational_vector"), 195, "D14")
    if lcm(*(value.denominator for value in outer_vector)) != 10**38:
        fail("D14 coefficient denominator is not 10^38")

    tuple_data = snapshots["sources/admissible_48_236.txt"]
    if not tuple_data.endswith(b"\n"):
        fail("tuple file is not newline terminated")
    values = [int(line) for line in tuple_data.splitlines()]
    if (len(values) != 48 or len(set(values)) != 48 or
            values != sorted(values) or values[-1] - values[0] != 236):
        fail("tuple size/distinctness/order/diameter mismatch")
    expected_witnesses = {
        2: 1, 3: 1, 5: 2, 7: 2, 11: 9, 13: 10, 17: 4, 19: 13,
        23: 13, 29: 15, 31: 1, 37: 7, 41: 10, 43: 2, 47: 5,
    }
    observed = {}
    for prime in primes_through(48):
        occupied = {value % prime for value in values}
        missing = [residue for residue in range(prime)
                   if residue not in occupied]
        if not missing:
            fail(f"tuple is inadmissible modulo {prime}")
        observed[prime] = missing[0]
    if observed != expected_witnesses:
        fail("tuple witness table mismatch")

    # Detect a concurrent edit after all semantic reads.
    for relative, data in snapshots.items():
        if (REPO / relative).read_bytes() != data:
            fail(f"input changed during replay: {relative}")
    print("PRE-CERTIFICATE FROZEN-FACT REPLAY PASS")
    print(f"proof_sha256={PINS['PROOF.md']}")
    print("basis_dimensions=D19:568,D14:195 tuple_size=48 diameter=236")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
