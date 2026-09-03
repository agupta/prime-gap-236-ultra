#!/usr/bin/env python3
"""Exact gate for three inner-plus-one-outer width/cap alternatives.

The proof kernel is the frozen v3 one-outer-band checker.  For each candidate
this wrapper replaces only its rational endpoint and rational outer schedule,
runs every Definition-1/source/IIa/IIb/IIc/III check (including the strict cap
neighbourhood), and restores the frozen module globals before proceeding.

No empirical H^2 diagnostic is read by this file.  In particular, the search
ordering that produced the schedules is not a proof dependency.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
V3_FILE = FILE.with_name("verify_truncated_lower_energy_v3.py")
V3_SHA256 = "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5"

spec = importlib.util.spec_from_file_location("one_band_width_v4_kernel",
                                              V3_FILE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen v3 exact kernel")
v3 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v3
spec.loader.exec_module(v3)
v2 = v3.v2
core = v3.core
CFG = v3.CFG

OLD_ENDPOINT = v2.ENDPOINTS[-1]
OLD_WIDTH = OLD_ENDPOINT - core.A1
BASELINE_ENDPOINT = v3.ENDPOINT
BASELINE_HEAD = tuple(v2.LOWER_HEAD)
BASELINE_ETA = v3.ETA_OUTER


@dataclass(frozen=True)
class Candidate:
    label: str
    width_fraction: Q
    head_millionths: tuple[int, ...]

    @property
    def endpoint(self) -> Q:
        return core.A1 + self.width_fraction * OLD_WIDTH

    @property
    def head(self) -> tuple[Q, ...]:
        return tuple(Q(value, 1_000_000) for value in self.head_millionths)


CANDIDATES = (
    Candidate(
        "lambda_19_over_20", Q(19, 20),
        (141072, 157274, 167751, 173648, 184820, 190315, 191873,
         197631, 201942, 206705, 211467, 215216)),
    Candidate(
        "lambda_39_over_40", Q(39, 40),
        (141766, 157158, 167088, 172955, 184749, 189621, 191266,
         197779, 201335, 206088, 210932, 214740)),
    Candidate(
        "lambda_1_old_endpoint", Q(1),
        (142459, 157043, 166329, 172261, 185389, 188928, 190659,
         196720, 202462, 206792, 210255, 214263)),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


@contextlib.contextmanager
def configured(candidate: Candidate):
    """Temporarily configure the hash-pinned one-band proof kernel."""
    before = (v3.ENDPOINT, v3.ETA_OUTER, tuple(v2.LOWER_HEAD))
    require(before == (BASELINE_ENDPOINT, BASELINE_ETA, BASELINE_HEAD),
            "v3 kernel globals dirty at candidate entry")
    v3.ENDPOINT = candidate.endpoint
    v3.ETA_OUTER = candidate.endpoint - CFG.epsilon
    v2.LOWER_HEAD = candidate.head
    try:
        yield
    finally:
        v3.ENDPOINT, v3.ETA_OUTER, v2.LOWER_HEAD = before
    require((v3.ENDPOINT, v3.ETA_OUTER, tuple(v2.LOWER_HEAD)) == before,
            "v3 kernel globals not restored")


def minimum_reserve(packing: dict[str, object]) -> tuple[Q, str]:
    choices = (
        (packing["IIa_III_worst"][0], "IIa_III"),
        (packing["IIb_worst"][0], "IIb"),
        (packing["dynamic_worst"][0], "IIc_dynamic"),
    )
    return min(choices)


def check_candidate(candidate: Candidate) -> dict[str, object]:
    with configured(candidate):
        definition = v3.definition1_check()
        source = v3.source_geometry_check()
        packing = v3.packing_check()
        lower_definition = v3.definition1_check(-v3.CAP_RADIUS)
        upper_definition = v3.definition1_check(v3.CAP_RADIUS)
        upper_packing = v3.packing_check(v3.CAP_RADIUS)
        proposition = core.proposition2_and_prop1_check(CFG)
        bands = v3.schedules()
        require(proposition["maximum_Bj1"] == max(schedule[0]
                                                    for schedule in bands),
                f"{candidate.label}: Proposition-2 B1 maximum")
        extended_head = core.extend(candidate.head, CFG.delta)
        require(extended_head[12] == candidate.head[-1],
                f"{candidate.label}: terminal plateau extension missing")
        require(core.active(extended_head, CFG.delta) == tuple(range(13)),
                f"{candidate.label}: unexpected outer inventory")

        width = candidate.endpoint - core.A1
        face = 3 * width + CFG.delta
        face_reserve = Q(3, 80) - face
        require(face_reserve > 0,
                f"{candidate.label}: main direct-HB face not strict")
        base_min, base_case = minimum_reserve(packing)
        upper_min, upper_case = minimum_reserve(upper_packing)

        result = {
            "label": candidate.label,
            "width_fraction_of_old_outer": candidate.width_fraction,
            "A": (-CFG.epsilon, core.A1, candidate.endpoint),
            "alpha": (core.A1 + CFG.epsilon,
                      candidate.endpoint + CFG.epsilon),
            "definition5_eta": {
                "inner_inner": core.A1 - CFG.epsilon,
                "inner_outer": candidate.endpoint - CFG.epsilon,
                "outer_outer": candidate.endpoint - CFG.epsilon,
            },
            "outer_schedule_head_12": candidate.head,
            "outer_schedule_through_first_empty": candidate.head +
            (candidate.head[-1],),
            "outer_active_counts": tuple(range(13)),
            "cap_gains_from_lambda_37_over_40_by_count": {
                count: ((candidate.head + (candidate.head[-1],))[count - 1]
                        - (BASELINE_HEAD + (BASELINE_HEAD[-1],))[count - 1])
                for count in range(1, 14)
            },
            "main_direct_HB_face": face,
            "main_direct_HB_face_reserve": face_reserve,
            "definition1": definition,
            "source_geometry": source,
            "ordered_pair_packing": packing,
            "proposition2_and_prop1": proposition,
            "strict_outer_cap_interval": {
                "radius": v3.CAP_RADIUS,
                "lower_active": lower_definition["active_counts"][
                    "wide_outer"],
                "upper_active": upper_definition["active_counts"][
                    "wide_outer"],
                "base_minimum_packing_reserve": base_min,
                "base_minimum_packing_case": base_case,
                "upper_minimum_packing_reserve": upper_min,
                "upper_minimum_packing_case": upper_case,
                "upper_fixed_worst": upper_packing["IIa_III_worst"],
                "upper_IIb_worst": upper_packing["IIb_worst"],
                "upper_dynamic_worst": upper_packing["dynamic_worst"],
            },
        }
    return result


def stringify(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, tuple):
        return [stringify(item) for item in value]
    if isinstance(value, list):
        return [stringify(item) for item in value]
    if isinstance(value, dict):
        return {str(key): stringify(item) for key, item in value.items()}
    return value


def dependency_check() -> None:
    require(sha256(V3_FILE) == V3_SHA256, "frozen v3 kernel changed")
    require(sha256(v3.V2_FILE) == v3.V2_SHA256,
            "v2 exact primitives changed")
    require(sha256(v2.FROZEN_FILE) == v2.FROZEN_SHA256,
            "frozen source evaluator changed")
    require(sha256(v2.frozen.CORE_FILE) == v2.frozen.CORE_SHA256,
            "frozen core changed")
    for relative, expected in core.PINNED.items():
        require(sha256(core.REPO / relative) == expected,
                f"pinned source changed: {relative}")


def build() -> dict[str, object]:
    dependency_check()
    results = [check_candidate(candidate) for candidate in CANDIDATES]
    require((v3.ENDPOINT, v3.ETA_OUTER, tuple(v2.LOWER_HEAD)) ==
            (BASELINE_ENDPOINT, BASELINE_ETA, BASELINE_HEAD),
            "v3 kernel globals dirty after portfolio")

    # The source face is strict, so a literal maximum rational interior width
    # does not exist.  Its exact supremum and a constructive midpoint proof are
    # recorded rather than mislabelling lambda=1 as maximal.
    width_supremum = (Q(3, 80) - CFG.delta) / 3
    require(width_supremum == Q(1, 144), "width supremum identity")
    require(OLD_WIDTH < width_supremum, "old endpoint is not interior")
    return stringify({
        "status": "EXACT ONE-OUTER-BAND WIDTH PORTFOLIO PASS",
        "scope": (
            "specialized direct-HB analytic support only; no empirical H2 "
            "input, no energy lower bound, no quotient, and no bounded-gap "
            "theorem claim"),
        "checker_sha256": sha256(FILE),
        "frozen_v3_kernel_sha256": V3_SHA256,
        "parameters_common": {
            "k": 48,
            "delta": CFG.delta,
            "epsilon": CFG.epsilon,
            "strict_outer_cap_radius": v3.CAP_RADIUS,
            "old_outer_width": OLD_WIDTH,
        },
        "candidates": results,
        "maximum_rational_interior_width_obstruction": {
            "strict_face_inequality": "3*w+delta<3/80",
            "width_supremum": width_supremum,
            "supremum_fraction_of_old_outer": width_supremum / OLD_WIDTH,
            "no_maximum_proof": (
                "For every rational w<1/144, the rational midpoint "
                "(w+1/144)/2 is larger and still satisfies the strict face; "
                "hence no maximal rational interior width exists."),
            "largest_portfolio_width_fraction": Q(1),
            "largest_portfolio_face_reserve": results[-1][
                "main_direct_HB_face_reserve"],
        },
        "acceptance_independence": (
            "No structural-basis result, Monte Carlo file, cap CDF, or "
            "projection proxy is imported or hashed by this verifier."),
        "proof_kernel": (
            "Every candidate uses the hash-pinned v3 exhaustive ordered-pair "
            "gate: enhanced fixed two-bin packing, literal continuum-gamma "
            "IIb breakpoints, and all adverse IIc cells with the sorted "
            "three-block alternative."),
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
