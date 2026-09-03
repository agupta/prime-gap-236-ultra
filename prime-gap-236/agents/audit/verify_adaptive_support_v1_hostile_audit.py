#!/usr/bin/env python3
"""Independent hostile audit of the frozen delta=1/60 analytic support.

The discovery checker is never imported.  All support inventories, scalar
inequalities, and continuum packing certificates are rebuilt with Fraction
arithmetic from the pinned parameter tuple and the pinned primary TeX
definitions.  Only after that reconstruction is complete is the producer
JSON parsed and compared.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from dataclasses import dataclass, replace
from fractions import Fraction as F
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]

PRIMARY_PINS = {
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex":
        "60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30",
    "sources/polymath8-edz-1402.0811-src/newergap.tex":
        "fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea",
}

PRODUCER_PINS = {
    "agents/analytic-new-lever/verify_adaptive_support_v1.py":
        "b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d",
    "agents/analytic-new-lever/adaptive_support_v1_exact.json":
        "b7070c2677815b22a86b5a55ce41b3a2477d593495062256356a5df2a37befa7",
}

H = F(1, 10**10)             # epsilon in the printed analytic lemmas
HB_SLACK = H / 10
ZETA = H / 1000
INWARD = H / 10
DELTA = F(1, 60)
SUPPORT_EPSILON = F(3, 400)
A1 = F(1, 4)
A2 = F(231241, 900000)
XI1, XI2, XI3 = F(19, 50), F(2, 5), F(2, 5)
CELLS = 16
CAP_RADIUS = F(1, 10**6)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qtext(value: F) -> str:
    return (str(value.numerator) if value.denominator == 1 else
            f"{value.numerator}/{value.denominator}")


def encode(value):
    if isinstance(value, F):
        return qtext(value)
    if isinstance(value, tuple):
        return [encode(item) for item in value]
    if isinstance(value, list):
        return [encode(item) for item in value]
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    return value


def ceil_fraction(value: F) -> int:
    return -((-value.numerator) // value.denominator)


def min_record(current, candidate):
    return candidate if current is None or candidate < current else current


def regular_snapshot(path: Path) -> dict[str, int | str]:
    before = path.stat(follow_symlinks=False)
    require(stat.S_ISREG(before.st_mode), f"not a regular file: {path}")
    require(before.st_nlink == 1, f"non-single-link provenance: {path}")
    digest = sha256(path)
    after = path.stat(follow_symlinks=False)
    identity_before = (before.st_dev, before.st_ino, before.st_size,
                       before.st_mtime_ns, before.st_nlink)
    identity_after = (after.st_dev, after.st_ino, after.st_size,
                      after.st_mtime_ns, after.st_nlink)
    require(identity_before == identity_after, f"file changed while hashing: {path}")
    return {"sha256": digest, "size": before.st_size, "dev": before.st_dev,
            "inode": before.st_ino, "nlink": before.st_nlink}


def strict_object(pairs):
    answer = {}
    for key, value in pairs:
        require(key not in answer, f"duplicate JSON key: {key}")
        answer[key] = value
    return answer


def strict_json(path: Path):
    raw = path.read_bytes()
    require(raw.endswith(b"\n") and b"\r" not in raw,
            "producer JSON is not canonical LF/newline text")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ArithmeticError("producer JSON is not ASCII") from exc
    return json.loads(text, object_pairs_hook=strict_object,
                      parse_float=lambda _: (_ for _ in ()).throw(
                          ArithmeticError("JSON float forbidden")),
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          ArithmeticError("JSON non-finite number forbidden")))


@dataclass(frozen=True)
class Support:
    outer_head: tuple[F, ...]

    @property
    def x(self) -> F:
        return A2 - A1

    @property
    def cross_omega(self) -> F:
        return self.x / 2

    @property
    def outer_omega(self) -> F:
        return self.x

    @property
    def inner(self) -> tuple[F, ...]:
        return (A1 + SUPPORT_EPSILON,) * int(F(1) // DELTA)

    @property
    def outer(self) -> tuple[F, ...]:
        length = int(F(1) // DELTA)
        return self.outer_head + (self.outer_head[-1],) * (length-len(self.outer_head))


CANDIDATE = Support(tuple(F(value, 10**6) for value in (
    138360, 155020, 158662, 171688, 177684, 180588,
    183402, 185486, 187011, 188221, 189137, 189137)))


def active(schedule: tuple[F, ...]) -> tuple[int, ...]:
    return (0,) + tuple(m for m, bound in enumerate(schedule, 1)
                        if m * DELTA <= bound)


def cap(schedule: tuple[F, ...], count: int) -> F:
    return F(0) if count == 0 else schedule[count-1]


def definition_one(support: Support) -> dict[str, object]:
    require(-SUPPORT_EPSILON < A1 < A2 < F(1, 2)-SUPPORT_EPSILON,
            "Definition 1 A ordering")
    schedules = {"inner": support.inner, "outer": support.outer}
    transitions = {}
    minimum = None
    for name, schedule in schedules.items():
        require(len(schedule) == 60, f"{name} schedule length")
        zero_steps = []
        for index, bound in enumerate(schedule):
            require(bound > DELTA, f"{name} B_{index+1} <= delta")
            if index:
                step = bound-schedule[index-1]
                require(F(0) <= step <= DELTA,
                        f"{name} bad transition {index}->{index+1}: {step}")
                if step == 0:
                    zero_steps.append(index+1)
            minimum = bound-DELTA if minimum is None else min(minimum, bound-DELTA)
        transitions[name] = zero_steps
    inner_counts, outer_counts = active(support.inner), active(support.outer)
    require(inner_counts == tuple(range(16)), f"inner active inventory {inner_counts}")
    require(outer_counts == tuple(range(12)), f"outer active inventory {outer_counts}")
    first_empty = 12*DELTA-support.outer[11]
    require(first_empty > 0, "outer count 12 not empty")
    return {"inner_active": inner_counts, "outer_active": outer_counts,
            "outer_first_empty_margin": first_empty,
            "zero_steps": transitions, "minimum_B_minus_delta": minimum}


def ga(omega: F) -> F:
    return F(2, 5)+F(24, 5)*omega+F(7, 5)*DELTA+2*H


def gb(omega: F) -> F:
    return F(1, 3)+8*omega+F(7, 3)*DELTA+3*H


def delta_iia(gamma: F, omega: F) -> F:
    return F(5, 7)*gamma-F(2, 7)-F(24, 7)*omega-H


def delta_iib(gamma: F, omega: F) -> F:
    return F(3, 7)*gamma-F(1, 7)-F(24, 7)*omega-H


def fixed_capacities(omega: F) -> dict[str, tuple[F, F]]:
    gamma3 = F(2, 5)-HB_SLACK
    d3 = F(1, 2)-F(7, 2)*omega-F(9, 8)*gamma3-H
    return {
        "IIa": (F(2, 5)+F(24, 5)*omega+F(7, 5)*DELTA-2*H,
                 F(1, 14)-F(24, 7)*omega-2*H),
        "III": (F(1, 3)+F(4, 3)*d3-F(4, 3)*omega-H,
                 F(1, 6)-d3/F(3)+F(4, 3)*omega-H),
    }


def fixed_prefix(delta: F, lc: int, rc: int, lb: F, rb: F,
                 capacities: tuple[F, ...]):
    """A universal sorted-prefix certificate for a fixed capacity vector."""
    total_n, total_bound = lc+rc, lb+rb
    first = capacities[0]
    if total_bound < first:
        return first-total_bound, "all-first", 0, 0
    overload = total_bound-first
    rmax = max(1, ceil_fraction(overload/delta))
    choices = []
    for pool, n, bound in (("left", lc, lb), ("right", rc, rb),
                           ("combined", total_n, total_bound)):
        if n < rmax:
            continue
        require(bound >= n*delta, "inactive pool reached packing")
        upper = (bound/n if rmax == 1 else
                 overload+(bound-overload)/(n-rmax+1))
        for slot, capacity in enumerate(capacities[1:], 1):
            if upper < capacity:
                choices.append((capacity-upper, pool, rmax, slot))
    require(choices, f"fixed packing failure counts=({lc},{rc}) caps={capacities}")
    return max(choices)


def iib_c(gamma: F) -> F:
    return gamma-3*ZETA-INWARD


def iib_d(omega: F, gamma: F) -> F:
    return F(1, 2)-gamma-2*omega-6*ZETA-INWARD


def iib_continuum(lc: int, rc: int, lb: F, rb: F, omega: F):
    """Check every cap-overload crossing on the full real gamma interval."""
    lower, upper = gb(omega), ga(omega)
    require(lower < upper, "empty/reversed IIb source interval")
    total_bound, total_n = lb+rb, lc+rc
    window = iib_c(lower)+iib_d(omega, lower)-total_bound
    require(window > 0, f"nonpositive IIb constant window ({lc},{rc})")
    maximum_overload = total_bound-iib_c(lower)
    if maximum_overload < 0:
        return (-maximum_overload, "all-first", 0, 0), 0
    crossings = max(1, ceil_fraction(maximum_overload/DELTA))
    worst = None
    for crossing in range(1, crossings+1):
        choices = []
        for pool, n, bound in (("left", lc, lb), ("right", rc, rb),
                               ("combined", total_n, total_bound)):
            if n < crossing:
                continue
            tail = (bound/n if crossing == 1 else
                    (bound-(crossing-1)*DELTA)/(n-crossing+1))
            if tail < window:
                choices.append((window-tail, pool, crossing, 0))
        require(choices, f"IIb crossing failure ({lc},{rc}), r={crossing}")
        worst = min_record(worst, max(choices))
    return worst, crossings


def family_inventory(support: Support) -> dict[str, object]:
    families = (
        ("mixed", support.inner, support.outer, support.cross_omega),
        ("transpose", support.outer, support.inner, support.cross_omega),
        ("outer", support.outer, support.outer, support.outer_omega),
        ("outer-near", support.outer, support.outer, F(0)),
    )
    pair_count = nonempty = fixed_count = crossings = 0
    zero_zero = 0
    one_zero = 0
    worst_fixed = worst_iib = None
    per_family = {}
    for name, left, right, omega in families:
        family_pairs = family_nonempty = family_crossings = 0
        for lc in active(left):
            for rc in active(right):
                pair_count += 1
                family_pairs += 1
                if lc == 0 and rc == 0:
                    zero_zero += 1
                    # Every relevant source capacity is nonnegative, so the
                    # four/three/two empty bins are a literal certificate.
                    require(min(sum((list(v) for v in fixed_capacities(omega).values()), [])) > 0,
                            "empty fixed case has negative capacity")
                    continue
                nonempty += 1
                family_nonempty += 1
                if (lc == 0) != (rc == 0):
                    one_zero += 1
                lb, rb = cap(left, lc), cap(right, rc)
                for branch, capacities in fixed_capacities(omega).items():
                    cert = fixed_prefix(DELTA, lc, rc, lb, rb, capacities)
                    worst_fixed = min_record(
                        worst_fixed, (cert[0], name, branch, lc, rc, *cert[1:]))
                    fixed_count += 1
                cert, count = iib_continuum(lc, rc, lb, rb, omega)
                worst_iib = min_record(
                    worst_iib, (cert[0], name, lc, rc, *cert[1:]))
                crossings += count
                family_crossings += count
        per_family[name] = {"ordered_pairs_including_empty": family_pairs,
                            "nonempty_pairs": family_nonempty,
                            "IIb_crossings": family_crossings}
    require(zero_zero == 4, "four ordered-family (0,0) cases not seen")
    require(nonempty == 668 and fixed_count == 1336 and crossings == 767,
            f"fixed inventory mismatch {nonempty}/{fixed_count}/{crossings}")
    require(worst_fixed and worst_fixed[0] > 0, "fixed margin")
    require(worst_iib and worst_iib[0] > 0, "IIb margin")
    return {"ordered_pairs_including_empty": pair_count,
            "nonempty_pairs": nonempty, "zero_zero_cases": zero_zero,
            "exactly_one_zero_cases": one_zero, "fixed_checks": fixed_count,
            "IIb_crossing_checks": crossings, "families": per_family,
            "worst_fixed": worst_fixed, "worst_IIb": worst_iib}


def iic_geometry(omega: F) -> dict[str, F]:
    gmin, gmax = F(2, 5)-H, gb(omega)
    d = DELTA+H/4
    margins = {
        "range": gmax-gmin,
        "factor_width_after_inward": d-2*INWARD-DELTA,
        "distribution_1": 1-(8*omega+4*d+2*gmax),
        "distribution_2": gmin-(32*omega+10*d),
        "distribution_3": 4*gmin-48*omega-16*d-1,
        "proof_start": gmin-4*omega-d,
        "C1_domination": H-2*(d-DELTA)-58*ZETA+INWARD,
        "C2_domination": H-6*ZETA-INWARD,
        "C3_domination": d-DELTA+H,
        "C4_domination": 2*INWARD,
    }
    for name, margin in margins.items():
        require(margin > 0, f"IIc non-strict source margin {name}: {margin}")
    return margins


def iic_capacities(gl: F, gu: F, wl: F, wu: F) -> tuple[F, F, F, F]:
    capacities = (gl-2*DELTA-8*wu-H,
                  F(1, 2)-gu-2*wu-H,
                  4*wl+DELTA-H,
                  8*wl)
    require(min(capacities) >= 0, "negative IIc adverse-cell capacity")
    return capacities


def iic_inventory(support: Support) -> dict[str, object]:
    omega = support.outer_omega
    geometry = iic_geometry(omega)
    gmin, gmax = F(2, 5)-H, gb(omega)
    counts = active(support.outer)
    pairs = nonempty = checks = empty_checks = 0
    one_zero = 0
    worst = None
    for lc in counts:
        for rc in counts:
            pairs += 1
            if (lc == 0) != (rc == 0):
                one_zero += 1
            lb, rb = cap(support.outer, lc), cap(support.outer, rc)
            for iw in range(CELLS):
                wl, wu = omega*iw/CELLS, omega*(iw+1)/CELLS
                for ig in range(CELLS):
                    gl = gmin+(gmax-gmin)*ig/CELLS
                    gu = gmin+(gmax-gmin)*(ig+1)/CELLS
                    capacities = iic_capacities(gl, gu, wl, wu)
                    if lc == 0 and rc == 0:
                        empty_checks += 1
                        continue
                    nonempty += (iw == 0 and ig == 0)
                    cert = fixed_prefix(DELTA, lc, rc, lb, rb, capacities)
                    worst = min_record(worst,
                                       (cert[0], lc, rc, iw, ig, *cert[1:]))
                    checks += 1
    require(pairs == 144 and nonempty == 143, "IIc ordered inventory")
    require(checks == 143*256 and empty_checks == 256,
            "IIc cell inventory")
    require(worst and worst[0] > 0, "IIc continuum margin")
    return {"ordered_pairs_including_empty": pairs, "nonempty_pairs": nonempty,
            "zero_zero_cell_checks": empty_checks,
            "exactly_one_zero_pairs": one_zero, "nonempty_cell_checks": checks,
            "cells_per_pair": 256, "source_geometry": geometry,
            "worst": worst}


def scalar_source_checks(support: Support) -> dict[str, object]:
    sigma = F(1, 10)+HB_SLACK
    gamma3 = F(2, 5)-HB_SLACK
    margins = {
        "HB_sigma_open": sigma-F(1, 10),
        "HB_K10": 2*sigma-F(1, 10),
        "central_reaches_2/5-h": (F(1, 2)-sigma)-(F(2, 5)-H),
        "III_atom_lower": 2*sigma-(F(1, 5)-H),
        "III_atom_upper": (F(2, 5)+H)-(F(1, 2)-sigma),
        "III_pair": (F(1, 2)+sigma)-(F(3, 5)-H),
        "Prop2_scalar_1": 2-(2*XI1+3*XI2),
        "Prop2_scalar_2": 4-(XI1+9*XI2),
        "Prop2_scalar_3": 2*XI1+XI2-1,
        "Prop2_scalar_4": 7-17*XI2,
        "Prop1_beta": F(1, 2)-max(support.inner[0], support.outer[0]),
    }
    regime = {}
    for name, omega in (("near", F(0)), ("mixed", support.cross_omega),
                        ("outer", support.outer_omega)):
        gamma_a, gamma_b = ga(omega), gb(omega)
        d_a_low = delta_iia(gamma_a, omega)
        d_a_high = delta_iia(F(1, 2), omega)
        d_b_low, d_b_high = (delta_iib(gamma_b, omega),
                             delta_iib(gamma_a, omega))
        d3 = F(1, 2)-F(7, 2)*omega-F(9, 8)*gamma3-H
        iii_a = F(1, 3)+d3/F(3)-F(4, 3)*omega
        iii_b = F(1, 3)+F(4, 3)*d3-F(4, 3)*omega
        safe_iia = fixed_capacities(omega)["IIa"]
        local = {
            "IIa_range": F(1, 2)-gamma_a,
            "IIa_factor_width": d_a_low-2*INWARD-DELTA,
            "IIa_distribution_1": -2-(24*omega+7*d_a_low-5*gamma_a),
            "IIa_distribution_2": -(8*omega+3*d_a_high-F(1, 2)),
            "IIa_factor_lower_endpoint": gamma_a-3*ZETA-d_a_low+INWARD,
            "IIa_capacity_1_domination":
                gamma_a-3*ZETA-INWARD-safe_iia[0],
            "IIa_capacity_2_domination":
                F(1, 14)-F(24, 7)*omega-H-INWARD-safe_iia[1],
            "IIb_range": gamma_a-gamma_b,
            "IIb_factor_width": d_b_low-2*INWARD-DELTA,
            "IIb_distribution_1": -1-(24*omega+7*d_b_low-3*gamma_b),
            "IIb_distribution_2": -(8*omega+3*d_b_high-gamma_a),
            "IIb_first_factor_endpoint": gamma_b-3*ZETA-d_b_low+INWARD,
            "IIb_second_factor_endpoint":
                F(1, 2)-gamma_a-2*omega-6*ZETA-d_b_high+INWARD,
            "IIb_structural_sum": 2*omega+2*INWARD,
            "IIb_third_capacity_positive": DELTA+2*omega+F(2, 7)*H+9*ZETA,
            "III_width": d3-2*H-DELTA,
            "III_distribution": 4-(28*omega+9*gamma3+8*d3),
            "III_distribution_2": 4-(16*omega+9*gamma3+2*d3),
            "III_distribution_3": 4-(28*omega+9*gamma3-d3),
            "III_factor_sum_lower": 1-4*omega+4*d3,
            "III_factor_sum_upper": 1-2*d3+8*omega,
            "III_omega_bound": F(1, 12)-omega,
            "III_lower_endpoint": iii_a+H,
            "III_upper_endpoint": F(1, 2)-(iii_b-H),
            "Type0_sharp": 1-((F(1, 2)-sigma)+(F(1, 2)+2*omega)),
            "Type0_Poisson": 1-(1-2*sigma+4*omega),
            "prime_square": 1-(F(1, 2)+2*omega),
            "higher_prime_powers": 1-(F(1, 2)+2*omega)-F(1, 3),
            "direct_II_face_1": F(19, 2)-36*(A1+omega)-13*DELTA+100*H,
            "direct_II_face_2": F(21, 25)-F(16, 5)*(A1+omega)-2*H-DELTA,
            "direct_II_face_3": F(63, 80)-3*(A1+omega)-2*H-DELTA,
        }
        for key, value in local.items():
            require(value > 0, f"{name} source strictness {key}: {value}")
        regime[name] = local
    require(gb(F(0)) < F(2, 5)-H, "near IIc is not empty")
    require(gb(support.cross_omega) < F(2, 5)-H,
            "mixed IIc is not empty")
    for name, value in margins.items():
        require(value > 0, f"scalar source margin {name}: {value}")
    require(XI2 == XI3 == F(2, 5), "rho endpoint changed")
    return {"margins": margins, "regimes": regime,
            "minimum_margin": min(list(margins.values()) +
                                  [x for group in regime.values()
                                   for x in group.values()])}


def primary_anchor_checks() -> dict[str, object]:
    stadlmann = (REPO / "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex").read_text()
    polymath = (REPO / "sources/polymath8-edz-1402.0811-src/newergap.tex").read_text()
    anchors = {
        "definition1_strict_B": r"\delta<B_{j,m} \leq B_{j,m+1}",
        "prop1_prime_minorant": r"-c_2 \leq \rho(n;x) \leq 1_{\mathbb{P}}(n)",
        "prop2_universal_H": r"Suppose  further that for every $f \in \mathcal{H}",
        "rho_equals_prime_at_endpoint": r"$\rho(n;x)$ is simply $1_{\mathbb{P}}(n)$",
        "IIb_gamma_capacity": r"\sum_{i \in I_1} y_i \leq \gamma-2\epsilon",
        "IIc_omega_range": r"\omega_0 \in [ -\varepsilon_0, \omega_",
    }
    for name, anchor in anchors.items():
        require(anchor in stadlmann, f"missing primary Stadlmann anchor {name}")
    poly_anchors = {
        "HB_identity": r"\begin{lemma}[Heath-Brown identity]",
        "HB_trichotomy": r"\item[(Type 0)] There is a $t_i$",
        "bilinear_BV": r"\begin{theorem}[Bombieri-Vinogradov theorem]",
        "subconvolution_SW": r"\alpha_S$ satisfies the Siegel-Walfisz property",
    }
    for name, anchor in poly_anchors.items():
        require(anchor in polymath, f"missing primary Polymath anchor {name}")
    return {"stadlmann": sorted(anchors), "polymath": sorted(poly_anchors)}


def reconstruct(support: Support) -> dict[str, object]:
    # The computation deliberately precedes reading the producer artifact.
    definition = definition_one(support)
    scalar = scalar_source_checks(support)
    families = family_inventory(support)
    iic = iic_inventory(support)
    return {"definition1": definition, "source_scalars": scalar,
            "fixed_and_IIb": families, "IIc": iic}


def common_translation_check() -> dict[str, object]:
    lower = replace(CANDIDATE,
                    outer_head=tuple(x-CAP_RADIUS for x in CANDIDATE.outer_head))
    upper = replace(CANDIDATE,
                    outer_head=tuple(x+CAP_RADIUS for x in CANDIDATE.outer_head))
    lower_definition = definition_one(lower)
    upper_reconstruction = reconstruct(upper)
    # This is intentionally only a scope guard: independent perturbations
    # are not claimed.  The equal B11=B12 step immediately disproves that box.
    independent_box_counterexample = {
        "B11_plus_radius": CANDIDATE.outer_head[10]+CAP_RADIUS,
        "B12_minus_radius": CANDIDATE.outer_head[11]-CAP_RADIUS,
        "violates_B11_le_B12_by":
            CANDIDATE.outer_head[10]+CAP_RADIUS-
            (CANDIDATE.outer_head[11]-CAP_RADIUS),
    }
    require(independent_box_counterexample["violates_B11_le_B12_by"] > 0,
            "independent cap-box scope guard vanished")
    return {"radius": CAP_RADIUS, "lower_definition": lower_definition,
            "upper_reconstruction": upper_reconstruction,
            "independent_coordinate_box_not_claimed": independent_box_counterexample}


def compare_producer(record, reconstructed: dict[str, object]) -> dict[str, object]:
    require(record.get("status") == "EXACT ADAPTIVE ANALYTIC SUPPORT PASS",
            "producer status changed")
    candidate = record.get("candidate")
    require(isinstance(candidate, dict), "producer candidate missing")
    parameters = candidate.get("parameters", {})
    expected_parameters = {
        "delta": qtext(DELTA), "epsilon": qtext(SUPPORT_EPSILON),
        "A": [qtext(-SUPPORT_EPSILON), qtext(A1), qtext(A2)],
        "A2_minus_A1": qtext(A2-A1),
        "cross_omega": qtext((A2-A1)/2),
        "outer_omega": qtext(A2-A1),
    }
    for key, value in expected_parameters.items():
        require(parameters.get(key) == value,
                f"producer parameter mismatch {key}: {parameters.get(key)}")
    definition = candidate.get("definition1", {})
    require(definition.get("inner_active") == list(range(16)),
            "producer inner inventory differs")
    require(definition.get("outer_active") == list(range(12)),
            "producer outer inventory differs")
    fixed = candidate.get("fixed_and_literal_IIb", {})
    require(fixed.get("ordered_pairs") == 668 and
            fixed.get("IIa_III_checks") == 1336 and
            fixed.get("IIb_crossing_number_checks") == 767,
            "producer fixed/IIb inventory differs")
    dynamic = candidate.get("dynamic_IIc", {})
    require(dynamic.get("ordered_pairs") == 143 and
            dynamic.get("cells_per_pair") == 256 and
            dynamic.get("checks") == 143*256,
            "producer IIc inventory differs")
    prop = candidate.get("proposition2_and_prop1", {})
    require(prop.get("c1") == "0" and prop.get("c2") == "0" and
            prop.get("beta") == "1/2", "producer Prop1 constants differ")
    require(prop.get("rho") ==
            "(log n/log(3x))*1_P on [x,2x], zero outside",
            "producer selected rho differs")
    return {
        "arithmetic_fields_match": True,
        "producer_nonempty_fixed_pairs": fixed["ordered_pairs"],
        "audit_pairs_including_four_empty_cases":
            reconstructed["fixed_and_IIb"]["ordered_pairs_including_empty"],
        "producer_nonempty_IIc_pairs": dynamic["ordered_pairs"],
        "audit_IIc_pairs_including_empty":
            reconstructed["IIc"]["ordered_pairs_including_empty"],
    }


def build() -> dict[str, object]:
    primary_snapshots = {}
    for relative, expected in PRIMARY_PINS.items():
        snap = regular_snapshot(REPO/relative)
        require(snap["sha256"] == expected, f"primary pin mismatch {relative}")
        primary_snapshots[relative] = snap
    anchors = primary_anchor_checks()

    reconstructed = reconstruct(CANDIDATE)
    translation = common_translation_check()

    producer_snapshots = {}
    for relative, expected in PRODUCER_PINS.items():
        snap = regular_snapshot(REPO/relative)
        require(snap["sha256"] == expected, f"producer pin mismatch {relative}")
        producer_snapshots[relative] = snap
    record = strict_json(REPO/"agents/analytic-new-lever/adaptive_support_v1_exact.json")
    comparison = compare_producer(record, reconstructed)

    # Re-hash everything after parsing/comparison to fail closed on mutation.
    for relative, expected in {**PRIMARY_PINS, **PRODUCER_PINS}.items():
        require(sha256(REPO/relative) == expected,
                f"dependency changed during audit {relative}")

    return encode({
        "status": "ADAPTIVE SUPPORT V1 HOSTILE AUDIT PASS",
        "scope": "exact analytic support and direct weighted-prime Prop1 interface only",
        "checker_sha256": sha256(FILE),
        "primary_snapshots": primary_snapshots,
        "producer_snapshots": producer_snapshots,
        "primary_source_anchors": anchors,
        "independent_reconstruction": reconstructed,
        "common_cap_translation": translation,
        "producer_comparison": comparison,
        "theorem_interface": {
            "printed_Proposition_3": "not invoked",
            "printed_Proposition_2": (
                "not invoked: the direct HB argument does not prove its universal "
                "every-f-in-H premise"),
            "printed_Proposition_2_endpoint_fact":
                "at xi2=2/5 its own rho is exactly 1_P and c2=0",
            "selected_direct_rho":
                "(log n/log(3x))*1_P on [x,2x], zero outside",
            "selected_rho_is_not_literal_1_P": True,
            "Proposition_1_hypotheses": {
                "1_minorant": "0 <= log(n)/log(3x) < 1 on [x,2x]",
                "2_equidistribution": (
                    "direct K=10 HB trichotomy; Type0/BV/IIa/IIb/IIc/III "
                    "branches reconstructed above, then prime powers removed"),
                "3_roughness": "beta=1/2 exceeds max B_j1=103/400",
                "4_mass": "PNT gives (theta(2x)-theta(x))/log(3x)~x/log(x)",
            },
            "c1": F(0), "c2": F(0), "beta": F(1, 2),
            "theorem_ready": False,
        },
        "scope_guards": {
            "independent_cap_box":
                "false and not claimed; only a common translation is certified",
            "producer_rho_reason_wording": (
                "Prop2 supplies literal 1_P at xi2=2/5; the normalized weighted "
                "rho instead comes from the separate direct HB route"),
        },
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if args.output:
        destination = args.output.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
