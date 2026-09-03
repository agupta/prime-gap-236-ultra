#!/usr/bin/env python3
"""Exact non-theorem diagnostic for the literal three-bin Type-IIb cover.

This file is intentionally outside ``verify_adaptive_support_v1.py``'s
dependency closure.  It tests a stronger future optimization mechanism:
put q_L and q_R smallest entries of the two original pools in the literal
third bin E(gamma), then use the correlated C(gamma),D(gamma) prefix lemma
on the residual entries.  Every change of predicate is an exact rational
breakpoint, so the continuum is covered without gamma sampling.

The output is an analytic design diagnostic.  It cannot certify a quotient
or a bounded-gap conclusion, and the frozen support gate does not read it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
CORE_FILE = FILE.with_name("verify_adaptive_support_v1.py")
CORE_SHA256 = "b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d"

spec = importlib.util.spec_from_file_location("adaptive_support_exact_core", CORE_FILE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load exact support core")
core = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = core
spec.loader.exec_module(core)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def e_capacity(omega: Q, gamma: Q) -> Q:
    return 2 * omega + 9 * core.ZETA + core.db(gamma, omega)


def actions(cfg, lc: int, rc: int, lb: Q, rb: Q, omega: Q):
    emax = e_capacity(omega, core.ga(cfg, omega))
    max_q = min(lc + rc, int(emax // cfg.delta))
    answer = []
    for ql in range(lc + 1):
        for qr in range(rc + 1):
            q = ql + qr
            if q > max_q:
                continue
            third_upper = ((Q(ql) * lb / lc if ql else Q(0))
                           + (Q(qr) * rb / rc if qr else Q(0)))
            if q and third_upper >= emax:
                continue
            lcn, rcn = lc - ql, rc - qr
            lbn = Q(0) if lcn == 0 else lb - ql * cfg.delta
            rbn = Q(0) if rcn == 0 else rb - qr * cfg.delta
            require(lbn >= lcn * cfg.delta and rbn >= rcn * cfg.delta,
                    "invalid residual cap")
            answer.append((ql, qr, third_upper, lcn, rcn, lbn, rbn))
    require(answer and answer[0][:2] == (0, 0), "empty-third action missing")
    return tuple(answer)


def action_at(cfg, omega: Q, gamma: Q, action):
    ql, qr, third_upper, lc, rc, lb, rb = action
    q = ql + qr
    third_margin = (e_capacity(omega, gamma) - third_upper
                    if q else e_capacity(omega, gamma))
    if third_margin <= 0:
        return None
    total_b, total_n = lb + rb, lc + rc
    first = core.iib_c(cfg, gamma)
    if total_b < first:
        return (min(third_margin, first - total_b), ql, qr,
                "all-first", 0)
    overload = total_b - first
    crossing = max(1, core.ceilq(overload / cfg.delta))
    if crossing > total_n:
        return None
    window = first + core.iib_d(omega, gamma) - total_b
    if window <= 0:
        return None
    candidates = []
    for pool, count, bound in (
            ("left", lc, lb), ("right", rc, rb),
            ("combined", total_n, total_b)):
        if count < crossing:
            continue
        tail = (bound / count if crossing == 1 else
                (bound - (crossing - 1) * cfg.delta)
                / (count - crossing + 1))
        if tail < window:
            candidates.append((window - tail, pool))
    if not candidates:
        return None
    margin, pool = max(candidates)
    return (min(third_margin, margin), ql, qr, pool, crossing)


def breakpoints(cfg, omega: Q, all_actions) -> tuple[Q, ...]:
    low, high = core.gb(cfg, omega), core.ga(cfg, omega)
    points = {low, high}
    a = 3 * core.ZETA + core.INWARD
    for action in all_actions:
        ql, qr, third_upper, lc, rc, lb, rb = action
        if ql + qr:
            threshold = (7 * third_upper + 1 + 10 * omega
                         - 63 * core.ZETA + 7 * core.H) / 3
            if low <= threshold <= high:
                points.add(threshold)
        total_b, total_n = lb + rb, lc + rc
        for crossing in range(total_n + 1):
            point = total_b + a - crossing * cfg.delta
            if low <= point <= high:
                points.add(point)
    return tuple(sorted(points))


def pair_certificate(cfg, lc: int, rc: int, lb: Q, rb: Q, omega: Q):
    all_actions = actions(cfg, lc, rc, lb, rb, omega)
    points = breakpoints(cfg, omega, all_actions)
    tests = []
    for index, point in enumerate(points):
        tests.append(("endpoint", point, point, point))
        if index + 1 < len(points):
            right = points[index + 1]
            tests.append(("interval", point, right, (point + right) / 2))
    records = []
    worst = None
    nonempty = 0
    for kind, left, right, sample in tests:
        candidates = [value for action in all_actions
                      if (value := action_at(cfg, omega, sample, action))
                      is not None]
        require(candidates, f"uncovered {kind} {lc},{rc} at {sample}")
        best = max(candidates)
        item = (best[0], kind, left, right, *best[1:])
        worst = item if worst is None or item < worst else worst
        nonempty += best[1] + best[2] > 0
        records.append((kind, left, right, *best))
    return {
        "worst": worst, "breakpoints": len(points),
        "cover_records": len(records), "nonempty_third_records": nonempty,
        "maximum_q": max(record[4] + record[5] for record in records),
        "strategy_sha256": hashlib.sha256(
            repr(records).encode("ascii")).hexdigest(),
    }


def check_candidate() -> dict[str, object]:
    cfg = core.CANDIDATE
    inner, outer = core.inner_schedule(cfg), core.outer_schedule(cfg)
    families = (
        ("mixed", inner, outer, cfg.cross_omega),
        ("transpose", outer, inner, cfg.cross_omega),
        ("outer", outer, outer, cfg.outer_omega),
        ("outer-near", outer, outer, Q(0)),
    )
    pairs = records = nonempty = max_q = 0
    worst = None
    hashes = []
    first_nonempty = None
    for name, left, right, omega in families:
        for lc in core.active(left, cfg.delta):
            for rc in core.active(right, cfg.delta):
                if lc + rc == 0:
                    continue
                cert = pair_certificate(
                    cfg, lc, rc, core.cap(left, lc), core.cap(right, rc), omega)
                item = (cert["worst"][0], name, lc, rc, *cert["worst"][1:])
                worst = item if worst is None or item < worst else worst
                pairs += 1
                records += cert["cover_records"]
                nonempty += cert["nonempty_third_records"]
                max_q = max(max_q, cert["maximum_q"])
                hashes.append((name, lc, rc, cert["strategy_sha256"]))
                if first_nonempty is None and cert["nonempty_third_records"]:
                    first_nonempty = (name, lc, rc, cert)
    require(pairs == 668 and nonempty > 0 and max_q > 0,
            "candidate three-bin diagnostic inventory")
    return {
        "ordered_pairs": pairs, "endpoint_and_interval_records": records,
        "selected_nonempty_third_records": nonempty,
        "maximum_selected_q": max_q, "worst_midpoint_or_endpoint": worst,
        "first_pair_selecting_nonempty_third": first_nonempty,
        "complete_strategy_sha256": hashlib.sha256(
            repr(hashes).encode("ascii")).hexdigest(),
    }


def stringify(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, tuple):
        return [stringify(x) for x in value]
    if isinstance(value, list):
        return [stringify(x) for x in value]
    if isinstance(value, dict):
        return {str(k): stringify(v) for k, v in value.items()}
    return value


def build() -> dict[str, object]:
    require(sha256(CORE_FILE) == CORE_SHA256, "exact core changed")
    candidate = check_candidate()
    return stringify({
        "status": "EXACT THREE-BIN DESIGN DIAGNOSTIC PASS",
        "acceptance_role": "none; not read by the frozen support gate",
        "theorem_ready": False,
        "checker_sha256": sha256(FILE), "exact_core_sha256": CORE_SHA256,
        "candidate": candidate,
        "lemma": (
            "select q_L,q_R smallest pool entries for bin E; their sum is "
            "at most q_L B_L/n_L+q_R B_R/n_R, residual pool caps are "
            "B_i-q_i delta, and the exact C,D minimal-prefix lemma applies; "
            "all predicate changes are included as rational breakpoints"),
        "interpretation": (
            "q=1 is selected in some max-margin cover records, but the frozen "
            "candidate also passes the simpler empty-third gate; this result "
            "only preserves a future schedule-optimization mechanism"),
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"))
               + "\n").encode("ascii")
    if args.output:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
