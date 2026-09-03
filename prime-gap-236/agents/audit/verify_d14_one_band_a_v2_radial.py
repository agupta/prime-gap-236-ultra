#!/usr/bin/env python3
"""Independent exact radial reconstruction of frozen paired-A shards.

This checker deliberately does not import either exact_d14_one_band_a_shard_v1
or exact_d14_one_band_a_shard_v2.  It reads the frozen D14 coefficient vector,
performs the natural dilation and orbit-square collection locally, and then
uses the separately audited ``symmetric_cutoff_cross.radialized_band_i_r``
path to reconstruct the high, low, and band values in a supplied A-v2 shard.

The calculation is exact ``fractions.Fraction`` arithmetic.  A successful run
therefore compares two independently organized exact integrations, rather than
two serializations of the same matrix or grouped-face routine.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from math import comb
import math
import os
from pathlib import Path
import resource
import sys
import time


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
ENGINE = REPO / "agents/exact-projection-engine/symmetric_cutoff_cross.py"
FRONTIER = REPO / (
    "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py"
)
RADIAL = REPO / "verify/exact_capped_certificate.py"
OUTER = REPO / (
    "agents/structural-basis/results/"
    "bv_D14_fine_common_grid_candidates_exact_v2.json"
)
SUPPORT = REPO / (
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json"
)

PINNED = {
    ENGINE: "d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726",
    FRONTIER: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    RADIAL: "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    OUTER: "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0",
    SUPPORT: "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
}

PRODUCER = REPO / (
    "agents/structural-basis/code/exact_d14_one_band_a_shard_v2.py"
)
PRODUCER_SHA256 = \
    "2e91dbd8bcb8d0bfd102f964236d3a7d60d974bfecedab96a4a19a1124e81c2d"
BASE_PRODUCER_SHA256 = \
    "6fa3c7c99735ec9eeb5817413e4dfc77dc6ae57e1cef26c720f54f33eb93896e"
EXPECTED_OUTPUT_SOURCE_HASHES = {
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "agents/exact-integrator/src/stratum_integrator.py":
        "0566f77860b0b61ce0ed342b5bb3a4743990725099d8b0cd6e685efad3c7394f",
    "agents/exact-integrator/grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "agents/structural-basis/code/prepare_bv_D14_common_grid_candidates_v2.py":
        "83dfdd7d88ee7f2f2a4dfbf492af693b9ae99c2bfaf983816c0fdcdec3229a57",
    "agents/structural-basis/results/bv_D14_fine_common_grid_candidates_exact_v2.json":
        "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0",
    "agents/structural-basis/tests/test_prepare_bv_D14_common_grid_candidates_v2.py":
        "d7f0f8856f677080495a59dcb04f93c732e7a7103546da9f65311916796e49c3",
    "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py":
        "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5",
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json":
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    "agents/analytic-new-lever/test_truncated_lower_energy_v3.py":
        "9b0e1409ef4ea2dda1292a69881c344a35d52f4886f0568c0e8a71f806d0b1fa",
    "agents/structural-basis/code/exact_d14_one_band_a_shard_v1.py":
        BASE_PRODUCER_SHA256,
}

K = 48
DEGREE = 14
DIMENSION = 195
SCALE = 10**38
DELTA = Q(1, 60)
ALPHA1 = Q(103, 400)
ALPHA2 = Q(9500917, 36000000)
ETA = Q(8960917, 36000000)
DILATION = ALPHA1 / ALPHA2
SCHEDULE_HEAD = tuple(map(Q, (
    "1123/8000", "157041/1000000", "5267/31250",
    "87169/500000", "11593/62500", "1523/8000",
    "193097/1000000", "98573/500000", "202047/1000000",
    "20709/100000", "52917/250000", "52917/250000",
)))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes, name: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {name}")
            result[key] = value
        return result

    def reject(token):
        raise ValueError(f"nonfinite JSON token {token!r} in {name}")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=reject)


def canonical_q(token, name: str) -> Q:
    if type(token) is not str:
        raise TypeError(f"{name} is not a rational string")
    value = Q(token)
    if str(value) != token:
        raise ValueError(f"{name} is not a canonical rational")
    return value


def load_snapshot(name: str, path: Path, data: bytes):
    if path.read_bytes() != data:
        raise RuntimeError(f"source changed before import: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def parse_basis(raw, expected):
    if not isinstance(raw, list):
        raise TypeError("basis is not a list")
    labels = []
    for index, item in enumerate(raw):
        if (not isinstance(item, list) or len(item) != 2 or
                type(item[0]) is not int or item[0] < 0 or
                not isinstance(item[1], list) or
                any(type(x) is not int or x <= 0 for x in item[1])):
            raise ValueError(f"malformed basis label {index}")
        labels.append((item[0], tuple(item[1])))
    labels = tuple(labels)
    if labels != tuple(expected):
        raise ValueError("basis is not the canonical ordered even D14 basis")
    return labels


def local_natural_dilation(basis, vector):
    """Expand H(d*t) in (1-S)^b P_lambda, independently of production."""
    terms = defaultdict(Q)
    for (a, lam), theta in zip(basis, vector, strict=True):
        if not theta:
            continue
        for b in range(a + 1):
            terms[(b, lam)] += (
                theta * comb(a, b) *
                (1 - DILATION) ** (a - b) *
                DILATION ** (b + sum(lam))
            )
    return {label: value for label, value in terms.items() if value}


def local_orbit_square(ei, terms):
    """Collect H^2 independently of production and engine square helpers."""
    items = tuple(terms.items())
    collected = defaultdict(Q)
    for i, ((a, lam), left) in enumerate(items):
        for j in range(i + 1):
            (b, mu), right = items[j]
            factor = left * right * (1 if i == j else 2)
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                collected[(nu, a + b)] += factor * multiplicity
    grouped = defaultdict(dict)
    for (nu, power), value in collected.items():
        if value:
            grouped[nu][power] = value
    return dict(grouped)


def validate_inputs(frontier, outer, support):
    if (outer.get("format") !=
            "bv-D14-fine-common-grid-candidates-exact-v2" or
            outer.get("status") !=
            "EXACT D14 FINE COMMON-GRID PARTICULAR VECTORS PASS" or
            outer.get("rigorous") is not True or
            outer.get("k") != K or outer.get("degree") != DEGREE or
            outer.get("basis_dimension") != DIMENSION):
        raise ValueError("frozen D14 source identity mismatch")
    basis = parse_basis(outer.get("basis"), frontier.ei.even_basis(DEGREE))
    candidates = outer.get("candidates")
    if not isinstance(candidates, list):
        raise TypeError("candidate inventory is not a list")
    matches = [row for row in candidates
               if isinstance(row, dict) and
               row.get("name") == "D14_grid_1e-38" and
               row.get("grid_digits") == 38]
    if len(matches) != 1:
        raise ValueError("unique frozen grid38 D14 candidate is absent")
    raw_vector = matches[0].get("rational_vector")
    if not isinstance(raw_vector, list) or len(raw_vector) != DIMENSION:
        raise ValueError("D14 vector dimension mismatch")
    vector = tuple(canonical_q(x, f"coefficient[{i}]")
                   for i, x in enumerate(raw_vector))
    if not any(vector) or max(map(abs, vector)) != 1:
        raise ValueError("D14 vector normalization mismatch")
    scaled = tuple(SCALE * x for x in vector)
    if any(x.denominator != 1 for x in scaled):
        raise ArithmeticError("10^38 failed to clear D14 coefficients")

    params = support.get("parameters", {})
    if (support.get("status") !=
            "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS" or
            params.get("k") != K or
            canonical_q(params.get("delta"), "support delta") != DELTA or
            tuple(canonical_q(x, "support alpha")
                  for x in params.get("alpha", ())) != (ALPHA1, ALPHA2) or
            tuple(canonical_q(x, "support schedule") for x in
                  params.get("outer_schedule_through_first_empty", ())) !=
            SCHEDULE_HEAD or
            tuple(params.get("outer_active_counts", ())) != tuple(range(13))):
        raise ValueError("frozen one-band support identity mismatch")
    return basis, scaled


def validate_shard(raw, path: Path, count: int):
    if set(raw) != {
            "active_counts", "base_source_sha256", "cache_read", "candidate",
            "checks", "checkpoint_unit", "claim_scope", "count", "degree",
            "elapsed_seconds", "exact_values", "fine_grid_status", "format",
            "geometry", "inventory", "k", "launch_authorized",
            "memory_limit_bytes", "one_band_status", "peak_rss_kib",
            "resume_supported", "rigorous", "serialized_matrix_entries_read",
            "source_hashes", "source_sha256", "status", "target_kind",
            "theorem_ready", "time_limit_seconds", "basis_dimension"}:
        raise ValueError(f"unexpected top-level schema in {path}")
    if (raw.get("format") != "exact-d14-one-band-a-count-shard-v2" or
            raw.get("status") !=
            "EXACT D14 ONE-BAND A COUNT SHARD PASS" or
            raw.get("rigorous") is not True or raw.get("count") != count or
            raw.get("active_counts") != list(range(13)) or
            raw.get("k") != K or raw.get("degree") != DEGREE or
            raw.get("basis_dimension") != DIMENSION or
            raw.get("source_sha256") != PRODUCER_SHA256 or
            raw.get("base_source_sha256") != BASE_PRODUCER_SHA256 or
            raw.get("cache_read") is not False or
            raw.get("serialized_matrix_entries_read") is not False or
            raw.get("theorem_ready") is not False or
            raw.get("source_hashes") != EXPECTED_OUTPUT_SOURCE_HASHES or
            raw.get("launch_authorized") is not True or
            raw.get("target_kind") != "authorized exact A-only prerequisite" or
            raw.get("resume_supported") is not False or
            raw.get("checkpoint_unit") != "one immutable explicit-count shard" or
            raw.get("one_band_status") !=
                "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS" or
            raw.get("fine_grid_status") !=
                "EXACT D14 FINE COMMON-GRID PARTICULAR VECTORS PASS" or
            type(raw.get("elapsed_seconds")) not in (int, float) or
            isinstance(raw.get("elapsed_seconds"), bool) or
            not math.isfinite(raw.get("elapsed_seconds")) or
            raw.get("elapsed_seconds") < 0 or
            type(raw.get("peak_rss_kib")) is not int or
            raw.get("peak_rss_kib") < 0):
        raise ValueError(f"A-v2 shard identity mismatch in {path}")
    geometry = raw.get("geometry", {})
    if (set(geometry) != {
            "alpha1", "alpha2", "band", "delta", "eta", "schedule",
            "schedule_extension"} or
            canonical_q(geometry.get("alpha1"), "shard alpha1") != ALPHA1 or
            canonical_q(geometry.get("alpha2"), "shard alpha2") != ALPHA2 or
            canonical_q(geometry.get("delta"), "shard delta") != DELTA or
            canonical_q(geometry.get("eta"), "shard eta") != ETA or
            tuple(canonical_q(x, "shard schedule")
                  for x in geometry.get("schedule", ())) !=
            SCHEDULE_HEAD + (SCHEDULE_HEAD[-1],) * (K - len(SCHEDULE_HEAD)) or
            geometry.get("schedule_extension") !=
                "terminal plateau through count 48" or
            geometry.get("band") !=
                "alpha1 <= sum(t) < alpha2, boundaries immaterial"):
        raise ValueError(f"A-v2 shard geometry mismatch in {path}")
    checks = raw.get("checks")
    if checks != {
            "natural_dilation_two_expansions_equal": True,
            "integer_vector_scale_and_dilation_commute": True,
            "termwise_vs_grouped_constant_volume_equal": True,
            "high_support_square_positive": True,
            "low_support_square_positive": True,
            "band_square_positive": True,
            "nested_supports_same_schedule": True,
            "paired_face_density_reuse": True}:
        raise ValueError(f"A-v2 recorded checks mismatch in {path}")
    inventory = raw.get("inventory", {})
    if (inventory.get("square_orbit_partition_groups") != 508 or
            inventory.get("square_residual_terms_per_support") != 3034 or
            inventory.get("high_faces") != 16 - count or
            inventory.get("low_faces") != 16 - count or
            inventory.get("shared_density_faces") != 16 - count or
            inventory.get("workers") != 1):
        raise ValueError(f"A-v2 face inventory mismatch in {path}")
    values = raw.get("exact_values", {})
    if set(values) != {
            "high_support_I_count", "low_support_I_count", "band_I_count",
            "band_I_count_decimal", "unscaled_band_I_count",
            "unscaled_band_I_count_decimal", "high_support_volume_count",
            "low_support_volume_count", "band_volume_count"}:
        raise ValueError(f"A-v2 exact-value schema mismatch in {path}")
    high = canonical_q(values.get("high_support_I_count"), "shard high I")
    low = canonical_q(values.get("low_support_I_count"), "shard low I")
    band = canonical_q(values.get("band_I_count"), "shard band I")
    unscaled = canonical_q(
        values.get("unscaled_band_I_count"), "shard unscaled band I"
    )
    high_volume = canonical_q(
        values.get("high_support_volume_count"), "shard high volume"
    )
    low_volume = canonical_q(
        values.get("low_support_volume_count"), "shard low volume"
    )
    band_volume = canonical_q(
        values.get("band_volume_count"), "shard band volume"
    )
    if (not high > low > 0 or band != high - low or band <= 0 or
            unscaled != band / SCALE**2 or
            not high_volume > low_volume > 0 or
            band_volume != high_volume - low_volume):
        raise ArithmeticError(f"A-v2 internal exact relation failed in {path}")
    return high, low, band


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("shards", nargs="*", type=Path)
    parser.add_argument(
        "--prepare-only", action="store_true",
        help="validate sources and reconstruct the D14 square, but no shard",
    )
    parser.add_argument(
        "--metadata-only", action="store_true",
        help="validate shard schemas/exact internal relations without radializing",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args()
    if args.prepare_only and (args.metadata_only or args.shards):
        parser.error("--prepare-only cannot be combined with shards/options")

    self_data = FILE.read_bytes()
    if sha256(self_data) != args.expected_self_sha256:
        raise RuntimeError("externally pinned independent checker hash mismatch")
    producer_data = PRODUCER.read_bytes()
    source_snapshots = {path: path.read_bytes() for path in PINNED}
    for path, expected in PINNED.items():
        actual = sha256(source_snapshots[path])
        if actual != expected:
            raise RuntimeError(
                f"frozen radial source changed: {path}: {actual} != {expected}"
            )
    if sha256(producer_data) != PRODUCER_SHA256:
        raise RuntimeError("frozen A-v2 producer changed")

    started = time.monotonic()
    frontier = load_snapshot(
        "hostile_a_v2_radial_frontier", FRONTIER, source_snapshots[FRONTIER]
    )
    radial = load_snapshot(
        "hostile_a_v2_radial_backend", RADIAL, source_snapshots[RADIAL]
    )
    engine = load_snapshot(
        "hostile_a_v2_radial_engine", ENGINE, source_snapshots[ENGINE]
    )
    outer = strict_json(source_snapshots[OUTER], str(OUTER))
    support = strict_json(source_snapshots[SUPPORT], str(SUPPORT))
    basis, scaled = validate_inputs(frontier, outer, support)
    dilated = local_natural_dilation(basis, scaled)
    if set(dilated) - set(basis):
        raise ArithmeticError("natural dilation escaped the D14 basis")
    square = local_orbit_square(frontier.ei, dilated)
    term_count = sum(len(row) for row in square.values())
    if len(square) != 508 or term_count != 3034:
        raise ArithmeticError(
            f"independent D14 square inventory mismatch: {len(square)}, "
            f"{term_count}"
        )

    if not args.shards and not args.prepare_only:
        parser.error("supply at least one shard or use --prepare-only")

    rows = []
    seen = set()
    sum_band = Q(0)
    for path in args.shards:
        payload = path.read_bytes()
        raw = strict_json(payload, str(path))
        count = raw.get("count")
        if type(count) is not int or not 0 <= count <= 12 or count in seen:
            raise ValueError(f"invalid or repeated shard count in {path}")
        seen.add(count)
        expected_high, expected_low, expected_band = validate_shard(
            raw, path, count
        )
        sum_band += expected_band
        row = {
            "count": count,
            "shard_sha256": sha256(payload),
            "high_support_I_count": str(expected_high),
            "low_support_I_count": str(expected_low),
            "band_I_count": str(expected_band),
        }
        if not args.metadata_only:
            value, diagnostics = engine.radialized_band_i_r(
                radial, square, k=K, alpha_high=ALPHA2, alpha_low=ALPHA1,
                delta=DELTA, schedule=SCHEDULE_HEAD, number_large=count,
            )
            high, low = diagnostics["high"], diagnostics["low"]
            if high != expected_high:
                raise ArithmeticError(f"exact high mismatch for count {count}")
            if low != expected_low:
                raise ArithmeticError(f"exact low mismatch for count {count}")
            if value != expected_band or value != high - low:
                raise ArithmeticError(f"exact band mismatch for count {count}")
            row.update({
                "exact_high_equal": True,
                "exact_low_equal": True,
                "exact_band_equal": True,
            })
        else:
            row["independent_radial_reconstruction"] = False
        rows.append(row)

    if (FILE.read_bytes() != self_data or PRODUCER.read_bytes() != producer_data or
            any(path.read_bytes() != data
                for path, data in source_snapshots.items())):
        raise RuntimeError("frozen radial source closure changed during checking")
    result = {
        "status": (
            "INDEPENDENT EXACT RADIAL A-v2 PREPARATION PASS"
            if not rows else
            "A-v2 SHARD METADATA/INTERNAL-ARITHMETIC CHECK PASS"
            if args.metadata_only else
            "INDEPENDENT EXACT RADIAL A-v2 SHARD CHECK PASS"
        ),
        "rigorous": True,
        "arithmetic": "fractions.Fraction only",
        "serialized_matrix_entries_read": False,
        "producer_imported": False,
        "independent_natural_dilation": True,
        "independent_orbit_square": True,
        "square_orbit_groups": len(square),
        "square_residual_terms": term_count,
        "source_hashes": {
            str(path.relative_to(REPO)): digest
            for path, digest in PINNED.items()
        },
        "producer_sha256": PRODUCER_SHA256,
        "checker_sha256": args.expected_self_sha256,
        "rows": sorted(rows, key=lambda row: row["count"]),
        "checked_counts": sorted(seen),
        "sum_scaled_band_I": str(sum_band),
        "sum_unscaled_band_I": str(sum_band / SCALE**2),
        "elapsed_seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    payload = (json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ) + "\n").encode("ascii")
    if args.output is None:
        sys.stdout.buffer.write(payload)
        return
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with args.output.open("xb") as handle:
            created = True
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        if created and args.output.exists():
            args.output.unlink()
        raise
    print(json.dumps({
        "status": result["status"],
        "checked_counts": result["checked_counts"],
        "elapsed_seconds": result["elapsed_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
        "output": str(args.output),
        "output_sha256": sha256(payload),
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
