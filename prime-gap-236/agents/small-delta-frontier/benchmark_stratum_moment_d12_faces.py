#!/usr/bin/env python3
"""Source-bound exact D12 face benchmark for fused/unfused moment products.

This is deliberately a *face sample*, not a target matrix builder.  A fresh
process performs the expensive fixed-base setup once and evaluates the same
three I and three J faces.  Exact tagged tables are serialized so a separate
consumer can require bit-for-bit equality between the fused and unfused
implementations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import resource
import stat
import sys
import time
from collections import defaultdict
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
EI = HERE.parent / "exact-integrator"
sys.path[:0] = [str(HERE), str(EI), str(EI / "src")]

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import add_poly  # noqa: E402
from stratum_moment_table import (  # noqa: E402
    BRANCHES, StratumMomentTableEvaluator, aggregate_powers,
)
from stratum_moment_table_fused import (  # noqa: E402
    FusedStratumMomentTableEvaluator, canonical_schema_sha256,
    moment_tag_schema, validate_moment_tag_schema,
)


ORIGINAL = EI / "results/hb_c10_fullsimplex_noones_D12.json"
ORIGINAL_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
SCALED = EI / "results/hb_c10_fullsimplex_noones_D12_integer_scaled.json"
SCALED_SHA = "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93"
SOURCE_METADATA_PATH = "results/hb_c10_fullsimplex_noones_D12.json"
DEGREE = 3
I_FACES = ((0, 0), (7, 9), (15, 0))
J_FACES = ((0, 0), (7, 9), (15, 0))
PARAMETERS = {
    "alpha": Q(79247, 300000), "delta": Q(1, 100),
    "eta": Q(76247, 300000), "beta1": Q(3, 20),
    "beta2": Q(3, 20), "beta3plus": Q(97, 625),
}
EXPECTED_SCHEMA_SHA = \
    "320272a9dfb08ab6d12396127de3ff35ffe35c47b4715e4035bc985e67981aad"
MINIMUM_AVAILABLE_MIB = 1844


class BenchmarkError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise BenchmarkError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def available_memory_mib():
    """Read the Linux MemAvailable gate without a shell or subprocess."""
    fields = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        pieces = line.split()
        if len(pieces) >= 2 and pieces[0].endswith(":"):
            fields[pieces[0][:-1]] = pieces[1:]
    raw = fields.get("MemAvailable")
    require(raw is not None and len(raw) == 2 and raw[1] == "kB" and
            re.fullmatch(r"[1-9][0-9]*", raw[0]) is not None,
            "cannot parse /proc/meminfo MemAvailable")
    return int(raw[0]) // 1024


def parse_canonical_fraction(value, label):
    require(type(value) is str and re.fullmatch(
        r"(?:0|-?[1-9][0-9]*)(?:/[1-9][0-9]*)?", value) is not None,
        f"noncanonical rational token: {label}")
    answer = Q(value)
    require(str(answer) == value, f"unreduced rational token: {label}")
    return answer


def parse_label(item, index):
    require(type(item) is list and len(item) == 2 and
            type(item[0]) is int and item[0] >= 0 and
            type(item[1]) is list,
            f"malformed D12 basis label {index}")
    residual, raw_partition = item
    require(all(type(x) is int and x >= 2 for x in raw_partition),
            f"noninteger/small partition part {index}")
    partition = tuple(raw_partition)
    require(tuple(sorted(partition, reverse=True)) == partition and
            residual + sum(partition) <= 12,
            f"noncanonical D12 basis label {index}")
    return residual, partition


def load_source_bound_inputs():
    """Reconstruct and validate the pinned 714-bit integer scaling."""
    original_raw, scaled_raw = ORIGINAL.read_bytes(), SCALED.read_bytes()
    require(sha256(original_raw) == ORIGINAL_SHA, "D12 original SHA mismatch")
    require(sha256(scaled_raw) == SCALED_SHA, "D12 scaled SHA mismatch")
    original, scaled = json.loads(original_raw), json.loads(scaled_raw)
    require(type(scaled) is dict and set(scaled) == {
        "status", "k", "degree", "basis_dimension", "basis",
        "rational_vector", "integer_scaling"},
        "D12 scaled top-level schema")
    require(scaled["status"] == "exact-integer-scaled-fixed-vector-input" and
            scaled["k"] == 48 and scaled["degree"] == 12 and
            scaled["basis_dimension"] == 272,
            "D12 scaled identity")
    require(original.get("k") == 48 and original.get("degree") == 12 and
            original.get("basis_dimension") == 272 and
            scaled["basis"] == original.get("basis"),
            "D12 original/scaled basis identity")
    require(type(scaled["basis"]) is list and
            type(scaled["rational_vector"]) is list and
            len(scaled["basis"]) == len(scaled["rational_vector"]) == 272,
            "D12 basis/vector dimensions")
    labels = [parse_label(item, i)
              for i, item in enumerate(scaled["basis"])]
    require(len(set(labels)) == 272, "duplicate D12 label")
    original_vector = original.get("rational_vector")
    require(type(original_vector) is list and len(original_vector) == 272,
            "D12 original vector dimension")
    rationals = [parse_canonical_fraction(value, f"original[{i}]")
                 for i, value in enumerate(original_vector)]
    raw_integers = scaled["rational_vector"]
    require(all(type(x) is str and
                re.fullmatch(r"(?:0|-?[1-9][0-9]*)", x) is not None
                for x in raw_integers), "D12 scaled coefficient token")
    integers = [int(x) for x in raw_integers]
    meta = scaled["integer_scaling"]
    require(type(meta) is dict and set(meta) == {
        "source_json", "source_sha256", "least_common_denominator",
        "form_scale", "quotient_and_margin_sign_preserved"},
        "D12 scaling metadata schema")
    require(meta["source_json"] == SOURCE_METADATA_PATH and
            meta["source_sha256"] == ORIGINAL_SHA and
            meta["form_scale"] == "least_common_denominator^2" and
            meta["quotient_and_margin_sign_preserved"] is True,
            "D12 scaling metadata identity")
    raw_lcm = meta["least_common_denominator"]
    require(type(raw_lcm) is str and
            re.fullmatch(r"[1-9][0-9]*", raw_lcm) is not None,
            "D12 LCM token")
    claimed_lcm = int(raw_lcm)
    reconstructed_lcm = 1
    for value in rationals:
        reconstructed_lcm = math.lcm(reconstructed_lcm, value.denominator)
    require(claimed_lcm == reconstructed_lcm and
            claimed_lcm.bit_length() == 714,
            "D12 LCM reconstruction")
    require(all(value * claimed_lcm == integer
                for value, integer in zip(rationals, integers)),
            "D12 integer scaling changed a coefficient")
    require(math.gcd(*integers) == 1, "D12 integer vector not primitive")
    return labels, integers, claimed_lcm, original_raw, scaled_raw


def canonical_i_table(table):
    return [[u, v, str(value)]
            for (u, v), value in sorted(table.items()) if value]


def canonical_j_table(table):
    return [[*key, str(value)]
            for key, value in sorted(table.items()) if value]


def table_sha(table):
    raw = json.dumps(table, separators=(",", ":")).encode("ascii")
    return sha256(raw)


def evaluate_i_face(evaluator, grouped, r, h):
    require(type(r) is int and type(h) is int and r >= 0 and h >= 0,
            "invalid I face tag")
    dimension = evaluator.support.k
    max_h = int(evaluator.support.alpha // evaluator.support.delta) - r
    require(h <= max_h, "I face outside alpha support")
    outer = evaluator.support.alpha - (r + h) * evaluator.support.delta
    require(outer > 0, "empty I face")
    constraints = ()
    if r:
        cap = evaluator.support.beta(r) - r * evaluator.support.delta
        require(cap > 0, "empty I cap")
        constraints = ((evaluator.one, evaluator.zero, cap),)
    start = time.perf_counter()
    base = evaluator._i_face_polynomial(
        grouped, dimension, r, h, max_h, outer)
    setup_seconds = time.perf_counter() - start
    answer = {}
    start = time.perf_counter()
    for u, v in evaluator.aggregate_moments:
        weighted = ei._poly_mul(
            base, evaluator._aggregate_polynomial(r, h, u, v))
        value = evaluator.integrate_domain(
            weighted, dimension, r, outer, constraints)
        if value:
            answer[(u, v)] = value
    integrate_seconds = time.perf_counter() - start
    evaluator.clear_face_caches()
    evaluator.clear_radial_caches()
    return answer, {
        "face_polynomial_seconds": setup_seconds,
        "aggregate_integral_seconds": integrate_seconds,
        "scalar_integrals": len(evaluator.aggregate_moments),
    }


def _moment_pairs(degree, same_branch):
    if same_branch:
        return tuple((j, k) for j in range(degree + 1)
                     for k in range(j + 1))
    return tuple((j, k) for j in range(degree + 1)
                 for k in range(degree + 1))


def evaluate_j_face(evaluator, lrs, by_lr, r, h, fused):
    require(type(r) is int and type(h) is int and r >= 0 and h >= 0,
            "invalid J face tag")
    dimension = evaluator.support.k - 1
    max_h = int(evaluator.support.eta // evaluator.support.delta) - r
    require(h <= max_h, "J face outside eta support")
    outer = evaluator.support.eta - (r + h) * evaluator.support.delta
    require(outer > 0, "empty J face")
    start = time.perf_counter()
    blocks = evaluator._moment_branch_blocks(
        lrs, by_lr, r, h, dimension, outer)
    blocks_seconds = time.perf_counter() - start
    aggregate = {power: evaluator._aggregate_polynomial(r, h, *power)
                 for power in evaluator.aggregate_moments}
    answer = defaultdict(evaluator.scalar)
    counters = {
        "branch_domains": 0, "fused_traversals": 0,
        "logical_moment_products": 0, "scalar_integrals": 0,
        "orbit_pair_visits": 0, "tagged_polynomial_multiplies": 0,
        "density_visits": 0, "density_tag_contractions": 0,
    }
    start = time.perf_counter()
    for left_index, left_branch in enumerate(BRANCHES):
        for right_branch in BRANCHES[:left_index + 1]:
            constraints = evaluator._active_branch_pair(
                blocks, left_branch, right_branch,
                dimension, r, h, outer)
            if constraints is None:
                continue
            counters["branch_domains"] += 1
            same_branch = left_branch == right_branch
            pairs = _moment_pairs(evaluator.degree, same_branch)
            if fused:
                bases, local = evaluator._fused_density_product_polynomials(
                    blocks[left_branch], blocks[right_branch], pairs,
                    dimension, r, h, max_h)
                counters["fused_traversals"] += 1
                counters["logical_moment_products"] += len(bases)
                for key in ("orbit_pair_visits",
                            "tagged_polynomial_multiplies",
                            "density_visits", "density_tag_contractions"):
                    counters[key] += local[key]
                base_items = sorted(bases.items())
            else:
                base_items = []
                for j, k in pairs:
                    if (not blocks[left_branch][j] or
                            not blocks[right_branch][k]):
                        continue
                    base = evaluator._density_product_polynomial(
                        blocks[left_branch][j], blocks[right_branch][k],
                        dimension, r, h, max_h)
                    if base:
                        base_items.append(((j, k), base))
                counters["logical_moment_products"] += len(base_items)
            left_class = evaluator._class(left_branch)
            right_class = evaluator._class(right_branch)
            for (j, k), base in base_items:
                for u, v in aggregate_powers(2 * evaluator.degree - j - k):
                    value = evaluator.integrate_domain(
                        ei._poly_mul(base, aggregate[(u, v)]),
                        dimension, r, outer, constraints)
                    key = (left_class, right_class, j, k, u, v)
                    evaluator._add_j_value(answer, key, value)
                    if not same_branch:
                        evaluator._add_j_value(
                            answer, (right_class, left_class,
                                     k, j, u, v), value)
                    elif j != k:
                        evaluator._add_j_value(
                            answer, (left_class, right_class,
                                     k, j, u, v), value)
                    counters["scalar_integrals"] += 1
    product_integral_seconds = time.perf_counter() - start
    evaluator.clear_face_caches(clear_marginals=True)
    evaluator.clear_radial_caches()
    counters["branch_blocks_seconds"] = blocks_seconds
    counters["product_integral_seconds"] = product_integral_seconds
    return dict(answer), counters


def dependency_paths():
    return (
        ORIGINAL, SCALED, Path(__file__),
        HERE / "stratum_moment_table.py",
        HERE / "stratum_moment_table_fused.py",
        EI / "stratum_quadratic.py", EI / "stratum_linear.py",
        EI / "stratum_amplitude.py", EI / "grouped_fixed_vector.py",
        Path(ei.__file__),
    )


def snapshot_dependencies():
    answer = {}
    for path in dependency_paths():
        resolved = path.resolve()
        require(resolved not in answer, "benchmark dependency path alias")
        raw = resolved.read_bytes()
        require(len(raw) <= 20_000_000, "benchmark dependency too large")
        answer[resolved] = raw
    return answer


def publish_owned(path_text, payload, trusted):
    path = Path(path_text).resolve()
    require(path not in trusted, "benchmark output aliases dependency")
    raw = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode),
                "benchmark output is not regular")
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            require(count > 0, "benchmark short output write")
            offset += count
        os.fsync(fd)
        fs, ps = os.fstat(fd), os.stat(path, follow_symlinks=False)
        require((fs.st_dev, fs.st_ino) == (ps.st_dev, ps.st_ino) and
                path.read_bytes() == raw,
                "benchmark output ownership/bytes")
        for trusted_path, original in trusted.items():
            require(trusted_path.read_bytes() == original,
                    f"benchmark dependency changed: {trusted_path}")
    finally:
        os.close(fd)
    print(json.dumps({"status": payload["status"],
                      "output_sha256": sha256(raw)}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fused", "unfused"), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prelaunch_available_mib = available_memory_mib()
    require(prelaunch_available_mib >= MINIMUM_AVAILABLE_MIB,
            "shared-memory launch gate failed: "
            f"{prelaunch_available_mib} MiB < {MINIMUM_AVAILABLE_MIB} MiB")
    trusted = snapshot_dependencies()
    labels, integers, base_lcm, original_raw, scaled_raw = \
        load_source_bound_inputs()
    support = ei.OneStratumSupport(
        48, PARAMETERS["alpha"], PARAMETERS["delta"], PARAMETERS["eta"],
        PARAMETERS["beta1"], PARAMETERS["beta2"],
        PARAMETERS["beta3plus"])
    evaluator_class = (FusedStratumMomentTableEvaluator
                       if args.mode == "fused" else
                       StratumMomentTableEvaluator)
    evaluator = evaluator_class(
        support, labels, integers, Q, degree=DEGREE)
    schema = moment_tag_schema(DEGREE)
    validate_moment_tag_schema(schema, DEGREE)
    require(canonical_schema_sha256(DEGREE) == EXPECTED_SCHEMA_SHA,
            "degree-three schema SHA mismatch")

    total_start = time.perf_counter()
    start = time.perf_counter()
    grouped = evaluator.square_residual_terms()
    i_setup_seconds = time.perf_counter() - start
    start = time.perf_counter()
    components, lrs, by_lr = evaluator._j_component_data()
    j_setup_seconds = time.perf_counter() - start

    i_results = []
    for r, h in I_FACES:
        table, counters = evaluate_i_face(evaluator, grouped, r, h)
        canonical = canonical_i_table(table)
        i_results.append({
            "face": [r, h], "table": canonical,
            "table_sha256": table_sha(canonical), **counters,
        })
        print(f"{args.mode} D12 I face r={r} h={h} "
              f"seconds={counters['face_polynomial_seconds'] + counters['aggregate_integral_seconds']:.6f}",
              flush=True)

    j_results = []
    for r, h in J_FACES:
        table, counters = evaluate_j_face(
            evaluator, lrs, by_lr, r, h, args.mode == "fused")
        canonical = canonical_j_table(table)
        j_results.append({
            "face": [r, h], "table": canonical,
            "table_sha256": table_sha(canonical), **counters,
        })
        print(f"{args.mode} D12 J face r={r} h={h} "
              f"seconds={counters['branch_blocks_seconds'] + counters['product_integral_seconds']:.6f}",
              flush=True)

    elapsed = time.perf_counter() - total_start
    payload = {
        "status": "exact-D12-degree3-fused-face-benchmark-pass",
        "rigorous_sample_forms": True,
        "theorem_ready": False,
        "scope": "three exact I and three exact J faces only; no full matrix",
        "mode": args.mode,
        "k": 48, "base_degree": 12, "multiplier_degree": DEGREE,
        "parameters": {key: str(value) for key, value in PARAMETERS.items()},
        "original_input_sha256": ORIGINAL_SHA,
        "scaled_input_sha256": SCALED_SHA,
        "base_lcm_bits": base_lcm.bit_length(),
        "basis_dimension": len(labels),
        "integer_vector_content": 1,
        "prelaunch_available_memory_mib": prelaunch_available_mib,
        "required_prelaunch_available_memory_mib": MINIMUM_AVAILABLE_MIB,
        "tag_schema": schema,
        "tag_schema_sha256": EXPECTED_SCHEMA_SHA,
        "selected_i_faces": [list(x) for x in I_FACES],
        "selected_j_faces": [list(x) for x in J_FACES],
        "i_orbit_groups": len(grouped),
        "marginal_components": len(components),
        "i_setup_seconds": i_setup_seconds,
        "j_setup_seconds": j_setup_seconds,
        "i_results": i_results,
        "j_results": j_results,
        "total_seconds": elapsed,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "dependency_hashes": {
            str(path): sha256(raw) for path, raw in trusted.items()
        },
    }
    require(ORIGINAL.read_bytes() == original_raw and
            SCALED.read_bytes() == scaled_raw,
            "D12 source bytes changed")
    publish_owned(args.output, payload, trusted)


if __name__ == "__main__":
    main()
