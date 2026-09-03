#!/usr/bin/env python3
"""Exact per-count I(H) shards for the frozen one-band natural D14 proposal.

The polynomial is the selected 10^-38 common-grid D14 vector, naturally
dilated from the inner/outer interface ``alpha1`` to the outer endpoint
``alpha2``.  A shard evaluates one large-coordinate count only:

    I_R(H 1_V) = I_R(H; S < alpha2) - I_R(H; S < alpha1),

with the same frozen cap schedule in both terms.  The producer has no all-count
or resume mode; every invocation binds one explicit count and publishes one
new file with O_EXCL.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import gc
import hashlib
import importlib.util
import json
from math import comb
import os
from pathlib import Path
import resource
import signal
import sys
import time


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
EI_SRC = REPO / "agents/exact-integrator/src"
EXACT_INTEGRATOR = EI_SRC / "exact_integrator.py"
EXACT_INTEGRATOR_SHA256 = \
    "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
STRATUM_INTEGRATOR = EI_SRC / "stratum_integrator.py"
STRATUM_INTEGRATOR_SHA256 = \
    "0566f77860b0b61ce0ed342b5bb3a4743990725099d8b0cd6e685efad3c7394f"
GROUPED_INTEGRATOR = REPO / "agents/exact-integrator/grouped_fixed_vector.py"
GROUPED_INTEGRATOR_SHA256 = \
    "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
FINE_SOURCE = FILE.with_name("prepare_bv_D14_common_grid_candidates_v2.py")
FINE_SOURCE_SHA256 = \
    "83dfdd7d88ee7f2f2a4dfbf492af693b9ae99c2bfaf983816c0fdcdec3229a57"
FINE_RESULT = REPO / (
    "agents/structural-basis/results/bv_D14_fine_common_grid_candidates_exact_v2.json")
FINE_RESULT_SHA256 = \
    "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0"
FINE_TEST = REPO / (
    "agents/structural-basis/tests/test_prepare_bv_D14_common_grid_candidates_v2.py")
FINE_TEST_SHA256 = \
    "d7f0f8856f677080495a59dcb04f93c732e7a7103546da9f65311916796e49c3"
ONE_BAND_CHECKER = REPO / (
    "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py")
ONE_BAND_CHECKER_SHA256 = \
    "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5"
ONE_BAND_RESULT = REPO / (
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json")
ONE_BAND_RESULT_SHA256 = \
    "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f"
ONE_BAND_TEST = REPO / (
    "agents/analytic-new-lever/test_truncated_lower_energy_v3.py")
ONE_BAND_TEST_SHA256 = \
    "9b0e1409ef4ea2dda1292a69881c344a35d52f4886f0568c0e8a71f806d0b1fa"

PINNED_INPUTS = {
    EXACT_INTEGRATOR: EXACT_INTEGRATOR_SHA256,
    STRATUM_INTEGRATOR: STRATUM_INTEGRATOR_SHA256,
    GROUPED_INTEGRATOR: GROUPED_INTEGRATOR_SHA256,
    FINE_SOURCE: FINE_SOURCE_SHA256,
    FINE_RESULT: FINE_RESULT_SHA256,
    FINE_TEST: FINE_TEST_SHA256,
    ONE_BAND_CHECKER: ONE_BAND_CHECKER_SHA256,
    ONE_BAND_RESULT: ONE_BAND_RESULT_SHA256,
    ONE_BAND_TEST: ONE_BAND_TEST_SHA256,
}

K = 48
DEGREE = 14
DIMENSION = 195
GRID_DIGITS = 38
VECTOR_SCALE = 10 ** GRID_DIGITS
ALPHA1 = Q(103, 400)
ALPHA2 = Q(9500917, 36000000)
ETA = Q(8960917, 36000000)
DELTA = Q(1, 60)
SCHEDULE_HEAD = tuple(Q(x, 1_000_000) for x in (
    140375, 157041, 168544, 174338, 185488, 190375,
    193097, 197146, 202047, 207090, 211668, 211668,
))
SCHEDULE = SCHEDULE_HEAD + (SCHEDULE_HEAD[-1],) * (K - len(SCHEDULE_HEAD))
ACTIVE_COUNTS = tuple(range(13))
EXPECTED_SQUARE_RESIDUAL_TERMS = 3034
MAX_ADDRESS_SPACE_BYTES = 768 * 1024 * 1024
TIME_LIMIT_SECONDS = 1200


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json_bytes(data: bytes, label: str):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key {key!r} in {label}")
            out[key] = value
        return out

    def reject(token):
        raise ValueError(f"nonfinite JSON token {token!r} in {label}")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=reject)


def load_module(name: str, path: Path, expected_sha256: str):
    if sha256(path) != expected_sha256:
        raise RuntimeError(f"pinned exact-A dependency changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_integrators():
    if str(EI_SRC) not in sys.path:
        sys.path.insert(0, str(EI_SRC))
    exact = load_module(
        "d14_one_band_exact_integrator_v1", EXACT_INTEGRATOR,
        EXACT_INTEGRATOR_SHA256)
    # stratum_integrator imports the public name exact_integrator.
    sys.modules["exact_integrator"] = exact
    stratum = load_module(
        "d14_one_band_stratum_integrator_v1", STRATUM_INTEGRATOR,
        STRATUM_INTEGRATOR_SHA256)
    grouped = load_module(
        "d14_one_band_grouped_integrator_v1", GROUPED_INTEGRATOR,
        GROUPED_INTEGRATOR_SHA256)
    if grouped.ei is not exact:
        raise RuntimeError("grouped integrator did not bind the pinned exact core")
    return exact, stratum, grouped


def validate_pins(snapshots):
    for path, expected in PINNED_INPUTS.items():
        payload = snapshots.get(path, path.read_bytes())
        if sha256(payload) != expected:
            raise RuntimeError(f"pinned exact-A input changed: {path}")


def load_inputs():
    fine = strict_json_bytes(FINE_RESULT.read_bytes(), str(FINE_RESULT))
    one_band = strict_json_bytes(
        ONE_BAND_RESULT.read_bytes(), str(ONE_BAND_RESULT))
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in fine.get("basis", ()))
    rows = [row for row in fine.get("candidates", ())
            if row.get("grid_digits") == GRID_DIGITS]
    if (fine.get("status") !=
            "EXACT D14 FINE COMMON-GRID PARTICULAR VECTORS PASS" or
            fine.get("rigorous") is not True or
            fine.get("cache_read") is not False or
            fine.get("serialized_matrix_entries_read") is not False or
            fine.get("k") != K or fine.get("degree") != DEGREE or
            fine.get("basis_dimension") != DIMENSION or len(rows) != 1):
        raise ValueError("fine-grid D14 identity mismatch")
    row = rows[0]
    vector = tuple(Q(x) for x in row.get("rational_vector", ()))
    if (row.get("name") != "D14_grid_1e-38" or
            len(basis) != DIMENSION or len(vector) != DIMENSION or
            max(abs(x) for x in vector) != 1 or
            row.get("maximum_reduced_denominator_bits") != 127 or
            abs(Q(row.get("exact_quotient", "0")) -
                Q(fine.get("source_D14", {}).get("exact_quotient", "0"))) >=
            Q(1, 10**20)):
        raise ValueError("selected 10^-38 D14 row mismatch")
    params = one_band.get("parameters", {})
    if (one_band.get("status") !=
            "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS" or
            one_band.get("checker_sha256") != ONE_BAND_CHECKER_SHA256 or
            params.get("k") != K or params.get("delta") != str(DELTA) or
            tuple(Q(x) for x in params.get("alpha", ())) != (ALPHA1, ALPHA2) or
            tuple(Q(x) for x in
                  params.get("outer_schedule_through_first_empty", ())) !=
            SCHEDULE_HEAD or
            tuple(params.get("outer_active_counts", ())) != ACTIVE_COUNTS or
            one_band.get("definition5_single_outer_band", {}).get(
                "eta_outer_outer") != str(ETA)):
        raise ValueError("frozen one-band geometry identity mismatch")
    return fine, row, basis, vector, one_band


def natural_dilation_common_vector(basis, vector, dilation):
    """Write F(dilation*t) in the same (1-S)^a P_lambda basis."""
    dilation = Q(dilation)
    out = defaultdict(Q)
    for theta, (a, lam) in zip(vector, basis):
        orbit_scale = dilation ** sum(lam)
        for b in range(a + 1):
            out[(b, lam)] += (
                theta * comb(a, b) * (1 - dilation) ** (a - b) *
                dilation ** b * orbit_scale)
    labels = set(basis)
    if set(out) - labels:
        raise ArithmeticError("natural dilation left the frozen D14 basis")
    result = tuple(out[label] for label in basis)
    if not any(result):
        raise ArithmeticError("natural dilation produced the zero polynomial")
    return result


def centered_from_common(basis, common_vector, center):
    """Convert (1-S)^a coefficients to (center-S)^b coefficients."""
    center = Q(center)
    out = defaultdict(Q)
    for theta, (a, lam) in zip(common_vector, basis):
        for b in range(a + 1):
            out[(b, lam)] += (
                theta * comb(a, b) * (1 - center) ** (a - b))
    return out


def centered_direct_from_original(basis, vector, dilation, center):
    """Independent direct expansion of F(dilation*t) about center-S."""
    dilation, center = Q(dilation), Q(center)
    out = defaultdict(Q)
    for theta, (a, lam) in zip(vector, basis):
        for b in range(a + 1):
            out[(b, lam)] += (
                theta * comb(a, b) *
                (1 - dilation * center) ** (a - b) *
                dilation ** (b + sum(lam)))
    return out


def rational_decimal(value, digits=36):
    value = Q(value)
    with localcontext() as ctx:
        ctx.prec = digits
        return format(Decimal(value.numerator) / Decimal(value.denominator), ".28E")


def canonical_q(value):
    value = Q(value)
    return str(value.numerator) if value.denominator == 1 else str(value)


def make_support_class(stratum_module):
    @dataclass(frozen=True)
    class ScheduledStratumSupport(stratum_module.StratumSupport):
        schedule: tuple[Q, ...] = ()

        @classmethod
        def make(cls, *, alpha):
            return cls(K, Q(alpha), DELTA, ETA,
                       SCHEDULE[0], SCHEDULE[1], SCHEDULE[2], SCHEDULE)

        def beta(self, r):
            if isinstance(r, bool) or not isinstance(r, int) or r <= 0:
                raise ValueError("beta requires a positive integer count")
            return self.schedule[min(r, len(self.schedule)) - 1]

    return ScheduledStratumSupport


def validate_geometry(Support):
    high = Support.make(alpha=ALPHA2)
    low = Support.make(alpha=ALPHA1)
    if (any(right < left or right > left + DELTA
            for left, right in zip(SCHEDULE, SCHEDULE[1:])) or
            tuple(r for r in range(K + 1)
                  if r == 0 or r * DELTA < SCHEDULE[r - 1]) != ACTIVE_COUNTS or
            high.max_large() != 12 or low.max_large() != 12 or
            not ALPHA1 < ALPHA2 or ETA >= ALPHA1):
        raise ArithmeticError("one-band scheduled-support geometry mismatch")
    return high, low


def exact_constant_volume(support, count):
    return support.orbit_support_moment_in_stratum((), 0, count)


def grouped_constant_volume(grouped_module, support, count):
    evaluator = grouped_module.GroupedEvaluator(
        support, ((0, ()),), (Q(1),), Q)
    grouped = evaluator.square_residual_terms()
    value, faces = evaluator.evaluate_i_r(grouped, count, False)
    return value, faces


def evaluate_one_side(grouped_module, support, basis, common_vector,
                      count, progress):
    evaluator = grouped_module.GroupedEvaluator(
        support, basis, common_vector, Q)
    grouped = evaluator.square_residual_terms()
    term_count = sum(len(row) for row in grouped.values())
    if term_count != EXPECTED_SQUARE_RESIDUAL_TERMS:
        raise ArithmeticError(
            f"D14 square inventory changed: {term_count}")
    value, faces = evaluator.evaluate_i_r(grouped, count, progress)
    return value, len(grouped), term_count, faces


def build_shard(count: int, *, progress=False):
    if isinstance(count, bool) or not isinstance(count, int) or \
            count not in ACTIVE_COUNTS:
        raise ValueError("count must be one of the frozen active counts 0..12")
    tracked = (FILE,) + tuple(PINNED_INPUTS)
    snapshots = {path: path.read_bytes() for path in tracked}
    validate_pins(snapshots)
    exact, stratum, grouped = load_integrators()
    fine, selected, basis, vector, one_band = load_inputs()
    if tuple(exact.even_basis(DEGREE)) != basis:
        raise ArithmeticError("D14 basis is not the pinned even basis")
    Support = make_support_class(stratum)
    high, low = validate_geometry(Support)
    dilation = ALPHA1 / ALPHA2
    scaled_vector = tuple(VECTOR_SCALE * value for value in vector)
    if any(value.denominator != 1 for value in scaled_vector):
        raise ArithmeticError("10^38 did not clear the selected grid denominators")
    unscaled_common = natural_dilation_common_vector(basis, vector, dilation)
    common_vector = natural_dilation_common_vector(
        basis, scaled_vector, dilation)
    if common_vector != tuple(VECTOR_SCALE * value
                              for value in unscaled_common):
        raise ArithmeticError("natural dilation did not commute with scaling")
    # Two algebraically distinct expansions must agree before integration.
    for center in (ALPHA1, ALPHA2):
        if centered_from_common(basis, common_vector, center) != \
                centered_direct_from_original(
                    basis, scaled_vector, dilation, center):
            raise ArithmeticError("natural-dilation expansion mismatch")

    started = time.monotonic()
    high_volume_termwise = exact_constant_volume(high, count)
    high_volume_grouped, high_volume_faces = grouped_constant_volume(
        grouped, high, count)
    low_volume_termwise = exact_constant_volume(low, count)
    low_volume_grouped, low_volume_faces = grouped_constant_volume(
        grouped, low, count)
    if (high_volume_termwise != high_volume_grouped or
            low_volume_termwise != low_volume_grouped):
        raise ArithmeticError("low-dimensional/grouped stratum volume mismatch")
    band_volume = high_volume_termwise - low_volume_termwise
    if band_volume <= 0:
        raise ArithmeticError("active one-band stratum has nonpositive volume")

    high_value, high_groups, high_terms, high_faces = evaluate_one_side(
        grouped, high, basis, common_vector, count, progress)
    gc.collect()
    low_value, low_groups, low_terms, low_faces = evaluate_one_side(
        grouped, low, basis, common_vector, count, progress)
    band_value = high_value - low_value
    if high_value <= 0 or low_value <= 0 or band_value <= 0:
        raise ArithmeticError("exact squared-polynomial positivity failed")
    if (high_groups != low_groups or high_terms != low_terms or
            high_volume_faces != high_faces or low_volume_faces != low_faces):
        raise ArithmeticError("high/low grouped inventory mismatch")
    elapsed = time.monotonic() - started
    for path, payload in snapshots.items():
        if path.read_bytes() != payload:
            raise RuntimeError(f"exact-A source closure changed: {path}")

    return {
        "format": "exact-d14-one-band-a-count-shard-v1",
        "status": "EXACT D14 ONE-BAND A COUNT SHARD PASS",
        "rigorous": True,
        "claim_scope": (
            "one exact large-coordinate-count contribution to I(H) on the "
            "frozen single outer band; no J or final Rayleigh claim"),
        "count": count,
        "active_counts": list(ACTIVE_COUNTS),
        "k": K,
        "degree": DEGREE,
        "basis_dimension": DIMENSION,
        "candidate": {
            "name": selected["name"],
            "grid_digits": GRID_DIGITS,
            "vector_sha256": sha256((json.dumps(
                [canonical_q(x) for x in vector], separators=(",", ":")) +
                "\n").encode("ascii")),
            "evaluation_vector_scale": canonical_q(VECTOR_SCALE),
            "evaluation_vector_is_integral": True,
            "scaled_vector_sha256": sha256((json.dumps(
                [canonical_q(x) for x in scaled_vector],
                separators=(",", ":")) + "\n").encode("ascii")),
            "rayleigh_scaling_invariant": (
                "A scales by 10^76 and b by 10^38, so b^2/A is unchanged"),
            "natural_dilation": canonical_q(dilation),
            "exact_full_simplex_I": selected["exact_denominator"],
            "exact_full_simplex_48J": selected["exact_numerator_48J"],
            "exact_full_simplex_quotient": selected["exact_quotient"],
            "scaled_exact_full_simplex_I": canonical_q(
                Q(selected["exact_denominator"]) * VECTOR_SCALE ** 2),
            "scaled_exact_full_simplex_48J": canonical_q(
                Q(selected["exact_numerator_48J"]) * VECTOR_SCALE ** 2),
        },
        "geometry": {
            "alpha1": canonical_q(ALPHA1),
            "alpha2": canonical_q(ALPHA2),
            "eta": canonical_q(ETA),
            "delta": canonical_q(DELTA),
            "schedule": [canonical_q(x) for x in SCHEDULE],
            "schedule_extension": "terminal plateau through count 48",
            "band": "alpha1 <= sum(t) < alpha2, boundaries immaterial",
        },
        "exact_values": {
            "high_support_I_count": canonical_q(high_value),
            "low_support_I_count": canonical_q(low_value),
            "band_I_count": canonical_q(band_value),
            "band_I_count_decimal": rational_decimal(band_value),
            "high_support_volume_count": canonical_q(high_volume_termwise),
            "low_support_volume_count": canonical_q(low_volume_termwise),
            "band_volume_count": canonical_q(band_volume),
        },
        "checks": {
            "natural_dilation_two_expansions_equal": True,
            "integer_vector_scale_and_dilation_commute": True,
            "termwise_vs_grouped_constant_volume_equal": True,
            "high_support_square_positive": True,
            "low_support_square_positive": True,
            "band_square_positive": True,
            "nested_supports_same_schedule": True,
        },
        "inventory": {
            "square_orbit_partition_groups": high_groups,
            "square_residual_terms": high_terms,
            "high_faces": high_faces,
            "low_faces": low_faces,
            "workers": 1,
        },
        "elapsed_seconds": elapsed,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "memory_limit_bytes": MAX_ADDRESS_SPACE_BYTES,
        "time_limit_seconds": TIME_LIMIT_SECONDS,
        "source_sha256": sha256(snapshots[FILE]),
        "source_hashes": {
            str(path.relative_to(REPO)): expected
            for path, expected in PINNED_INPUTS.items()
        },
        "one_band_status": one_band["status"],
        "fine_grid_status": fine["status"],
        "cache_read": False,
        "serialized_matrix_entries_read": False,
        "launch_authorized": True,
        "target_kind": "authorized exact A-only prerequisite",
        "resume_supported": False,
        "checkpoint_unit": "one immutable explicit-count shard",
        "theorem_ready": False,
    }


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def apply_limits():
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    new_hard = hard if hard != resource.RLIM_INFINITY else MAX_ADDRESS_SPACE_BYTES
    resource.setrlimit(
        resource.RLIMIT_AS, (min(MAX_ADDRESS_SPACE_BYTES, new_hard), new_hard))
    signal.alarm(TIME_LIMIT_SECONDS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, choices=ACTIVE_COUNTS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    apply_limits()
    result = build_shard(args.count, progress=args.progress)
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"],
        "count": args.count,
        "band_I_count_decimal": result["exact_values"]["band_I_count_decimal"],
        "elapsed_seconds": result["elapsed_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
        "output_sha256": sha256(payload),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
