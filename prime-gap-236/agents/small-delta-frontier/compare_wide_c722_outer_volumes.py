#!/usr/bin/env python3
"""Exact constant-function shell volumes for two wide-C722 cap schedules."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
EI_DIR = REPO / "agents/exact-integrator"
sys.path.insert(0, str(EI_DIR / "src"))
import exact_integrator as ei  # noqa: E402


INTEGRATOR_SHA256 = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
K = 48
DELTA = Q(361, 50000)
EPSILON = Q(3, 400)
ALPHA1 = Q(1, 4) + EPSILON
ALPHA2 = Q(3121, 12000) + EPSILON
ETA2 = Q(3121, 12000) - EPSILON
BALANCED_150 = tuple(min(Q(11, 200) + (m - 1) * DELTA, Q(3, 20))
                     for m in range(1, 22))
BALANCED = tuple(min(Q(11, 200) + (m - 1) * DELTA, Q(43, 250))
                 for m in range(1, 25))
HIGH_COUNT = tuple(min(Q(723, 100000) + (m - 1) * DELTA, Q(9, 50))
                   for m in range(1, 26))
VOLUME_RAMP = tuple(min(Q(49, 625) + (m - 1) * DELTA, Q(1599, 10000))
                    for m in range(1, 24))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class ScheduledSupport(ei.OneStratumSupport):
    schedule: tuple = ()

    @classmethod
    def make(cls, schedule: tuple[Q, ...], alpha: Q):
        if (not schedule or any(x <= 0 for x in schedule) or
                any(y < x or y > x + DELTA
                    for x, y in zip(schedule, schedule[1:]))):
            raise ValueError("invalid Definition-1 schedule")
        return cls(K, alpha, DELTA, ETA2, schedule[0], schedule[1],
                   schedule[2], schedule)

    def beta(self, count):
        if count <= 0:
            raise ValueError("beta requires positive count")
        return self.schedule[min(count, len(self.schedule)) - 1]


def active(schedule):
    return tuple(m for m, value in enumerate(schedule, 1)
                 if m * DELTA <= value)


def shell_volume(schedule):
    high = ScheduledSupport.make(schedule, ALPHA2)
    low = ScheduledSupport.make(schedule, ALPHA1)
    label = (0, ())
    return high.basis_m1(label, label) - low.basis_m1(label, label)


def build_result():
    if sha256(Path(ei.__file__)) != INTEGRATOR_SHA256:
        raise RuntimeError("exact integrator changed")
    if active(BALANCED_150) != tuple(range(1, 21)):
        raise ArithmeticError("old balanced active inventory changed")
    if active(BALANCED) != tuple(range(1, 24)):
        raise ArithmeticError("balanced active inventory changed")
    if active(HIGH_COUNT) != tuple(range(1, 25)):
        raise ArithmeticError("high-count active inventory changed")
    if active(VOLUME_RAMP) != tuple(range(1, 23)):
        raise ArithmeticError("volume-ramp active inventory changed")
    balanced_150 = shell_volume(BALANCED_150)
    balanced = shell_volume(BALANCED)
    high_count = shell_volume(HIGH_COUNT)
    volume_ramp = shell_volume(VOLUME_RAMP)
    ratio = high_count / balanced
    if not 0 < ratio < Q(1, 10**20):
        raise ArithmeticError("high-count volume falsification disappeared")
    if balanced < balanced_150:
        raise ArithmeticError("43/250 plateau unexpectedly loses shell mass")
    if volume_ramp <= 10 * balanced:
        raise ArithmeticError("volume-ramp advantage disappeared")
    return {
        "status": "exact-shell-volume-comparison-pass",
        "scope": "constant-function I shell mass only; no J form or quotient",
        "script_sha256": sha256(FILE),
        "integrator_sha256": INTEGRATOR_SHA256,
        "parameters": {"k": K, "delta": str(DELTA),
                       "epsilon": str(EPSILON), "alpha1": str(ALPHA1),
                       "alpha2": str(ALPHA2), "eta2": str(ETA2)},
        "balanced": {"schedule": [str(x) for x in BALANCED],
                     "active_counts": [0, *active(BALANCED)],
                     "exact_I_shell": str(balanced)},
        "balanced_3_over_20": {
            "schedule": [str(x) for x in BALANCED_150],
            "active_counts": [0, *active(BALANCED_150)],
            "exact_I_shell": str(balanced_150)},
        "high_count": {"schedule": [str(x) for x in HIGH_COUNT],
                       "active_counts": [0, *active(HIGH_COUNT)],
                       "exact_I_shell": str(high_count)},
        "volume_ramp": {"schedule": [str(x) for x in VOLUME_RAMP],
                        "active_counts": [0, *active(VOLUME_RAMP)],
                        "exact_I_shell": str(volume_ramp)},
        "exact_high_over_balanced": str(ratio),
        "exact_volume_ramp_over_balanced": str(volume_ramp / balanced),
        "conclusion": (
            "high-count ramp is rejected for the constant outer coordinate; "
            "the volume-ramp schedule is promoted to a separate analytic "
            "audit; neither comparison is a finite-space upper bound"),
        "theorem_ready": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build_result(), sort_keys=True,
                          separators=(",", ":")) + "\n").encode("ascii")
    if args.output:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode(), end="")


if __name__ == "__main__":
    main()
