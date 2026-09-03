#!/usr/bin/env python3
"""Rigorous grouped dyadic reconstruction for the C10 D12 affine candidate.

Every scalar operation is enclosed by integer-directed fixed-point interval
arithmetic.  The driver consumes only the pinned 272-term integer-scaled base
polynomial and the pinned exact rational affine multiplier.  It recomputes I
and J from the finite orbit/face recurrences; it never reads a matrix,
eigenvalue, Decimal integral, or persistent moment cache.

This is a staged result driver.  A positive run is not theorem-ready until
the driver itself and its output receive an independent hostile audit and a
second reconstruction.  Resume of the J stage requires the byte SHA of the I
stage and exact agreement of every dependency/configuration field.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import resource
import sys
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ENGINE = ROOT / "agents/exact-integrator"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "src"))

import exact_integrator as ei  # noqa: E402
from dyadic_backend import install_dyadic  # noqa: E402
from grouped_fixed_vector import add_poly, precompute_orbits  # noqa: E402
from stratum_linear_transfer_decimal import TransferEvaluator  # noqa: E402
from verify.dyadic_interval import DyadicInterval  # noqa: E402
from verify.exact_affine_multiplier import (  # noqa: E402
    AffineMultipliers,
    load_exact_affine_multiplier,
)
from verify.exact_capped_certificate import (  # noqa: E402
    CertificateError,
    TARGET_C10_D12,
    TARGET_ORDERED_PAYLOAD_SHA256,
    _reject_constant,
    _reject_duplicate_object,
    expected_labels,
    ordered_payload_sha256,
    parse_fraction,
    validate_parameters,
)


BASE_PATH = (ROOT / "agents/exact-integrator/results/"
             "hb_c10_fullsimplex_noones_D12_integer_scaled.json")
SOURCE_PATH = (ROOT / "agents/exact-integrator/results/"
               "hb_c10_fullsimplex_noones_D12.json")
AFFINE_PATH = (ROOT / "agents/exact-integrator/results/"
               "c10_stratum_linear_cappedopt_D4_exact.json")
BASE_SHA256 = "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93"
AFFINE_SHA256 = "ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158"
SOURCE_VECTOR_SHA256 = \
    "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
SOURCE_METADATA_PATH = "results/hb_c10_fullsimplex_noones_D12.json"
LINEAR_CUTOFF = 11
EXPECTED_I_GROUPS = 1575
EXPECTED_I_FACES = 312
EXPECTED_MARGINAL_COMPONENTS = 695
EXPECTED_J_DOMAINS = 1200
EXPECTED_ORBIT_PRODUCT_PAIRS = 5929
DEPENDENCY_SHAS = {
    ROOT / "verify/dyadic_interval.py":
        "f6f1730f77ba490f04326338e7b3bfe5ab2e5c6438f10892bdf3f5bfe6fc875d",
    ENGINE / "dyadic_backend.py":
        "1dae20016b5fcbde5f56cf222ce92b45899f14bd5ff07fd3c70b7b10ce4ce608",
    ENGINE / "src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    ENGINE / "grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    ENGINE / "stratum_amplitude.py":
        "d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887",
    ENGINE / "stratum_linear.py":
        "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
    ENGINE / "stratum_linear_transfer_decimal.py":
        "91d1b4ad0c675ccfe36100166bee20bb4007af49e1d0cfe618c8c82c8857f354",
    ROOT / "verify/exact_affine_multiplier.py":
        "9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e",
    ROOT / "verify/exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
}
_INTEGER_RE = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")
_POSITIVE_INTEGER_RE = re.compile(r"[1-9][0-9]*\Z")


class DyadicCertificateError(RuntimeError):
    pass


class DyadicTransferEvaluator(TransferEvaluator):
    """Expose the direct-I half of the grouped affine traversal."""

    def evaluate_i_transfer(self, amplitudes, progress=False):
        grouped = self.square_residual_terms()
        denominator = self.zero
        faces = 0
        dimension = self.support.k
        for r in self._r_values_i():
            max_h = int(self.support.alpha // self.support.delta) - r
            constraints = ()
            if r:
                cap = self.support.beta(r) - r * self.support.delta
                if cap <= 0:
                    continue
                constraints = ((self.one, self.zero, cap),)
            for h in range(max_h + 1):
                outer = self.support.alpha - (r + h) * self.support.delta
                if outer <= 0:
                    continue
                base = self._i_face_polynomial(
                    grouped, dimension, r, h, max_h, outer)
                amplitude = defaultdict(self.scalar)
                coefficients = amplitudes.get(
                    r, (self.zero, self.zero, self.zero))
                for channel, phi in enumerate(self._phi_polynomials(r, h)):
                    add_poly(amplitude, phi, coefficients[channel])
                integrand = ei._poly_mul(
                    base, ei._poly_mul(dict(amplitude), dict(amplitude)))
                denominator += self.integrate_domain(
                    integrand, dimension, r, outer, constraints)
                faces += 1
                if progress:
                    print(f"dyadic I r={r} h={h} faces={faces}", flush=True)
                self.clear_face_caches()
            self.clear_radial_caches()
        return denominator, len(grouped), faces

    def evaluate_j_transfer(self, amplitudes, progress=False):
        components, lrs, by_lr = self._j_component_data()
        j_value = self.zero
        domains = 0
        for r in self._r_values_j():
            value, count = self.evaluate_j_r_transfer(
                lrs, by_lr, amplitudes, r, progress)
            j_value += value
            domains += count
        return self.scalar(self.support.k) * j_value, len(components), domains


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_pinned(path: Path, expected: str, description: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DyadicCertificateError(
            f"cannot read {description}: {exc}") from exc
    if len(raw) > 20_000_000:
        raise DyadicCertificateError(f"{description} exceeds 20 MB")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise DyadicCertificateError(
            f"{description} SHA mismatch: expected {expected}, got {actual}")
    return raw


def strict_json(raw: bytes, description: str) -> dict:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError, CertificateError) as exc:
        raise DyadicCertificateError(
            f"malformed {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise DyadicCertificateError(f"{description} is not an object")
    return value


def dependency_snapshot() -> dict[str, str]:
    answer = {}
    for path, expected in DEPENDENCY_SHAS.items():
        read_pinned(path, expected, str(path.relative_to(ROOT)))
        answer[str(path.relative_to(ROOT))] = expected
    return answer


def parse_labels(raw_labels) -> list[tuple[int, tuple[int, ...]]]:
    if not isinstance(raw_labels, list):
        raise DyadicCertificateError("base basis is not a list")
    labels = []
    for index, label in enumerate(raw_labels):
        if (not isinstance(label, list) or len(label) != 2 or
                isinstance(label[0], bool) or not isinstance(label[0], int) or
                not isinstance(label[1], list) or
                any(isinstance(value, bool) or not isinstance(value, int)
                    for value in label[1])):
            raise DyadicCertificateError(f"malformed basis label {index}")
        residual = label[0]
        part = tuple(label[1])
        if (residual < 0 or tuple(sorted(part, reverse=True)) != part or
                any(value < 2 for value in part) or
                residual + sum(part) > TARGET_C10_D12.degree):
            raise DyadicCertificateError(
                f"noncanonical/out-of-degree basis label {index}")
        labels.append((residual, part))
    if len(labels) != 272 or len(set(labels)) != len(labels):
        raise DyadicCertificateError("base basis dimension/uniqueness failed")
    if set(labels) != expected_labels(12, 48):
        raise DyadicCertificateError("base basis is not complete through D12")
    return labels


def lcm_denominators(values) -> int:
    answer = 1
    for value in values:
        if not isinstance(value, Fraction):
            raise DyadicCertificateError("LCM input is not exact")
        answer = math.lcm(answer, value.denominator)
    return answer


def load_exact_inputs():
    validate_parameters(TARGET_C10_D12)
    source = strict_json(
        read_pinned(SOURCE_PATH, SOURCE_VECTOR_SHA256, "original D12 source"),
        "original D12 source")
    required_source = {"k", "degree", "basis_dimension", "basis",
                       "rational_vector"}
    if not required_source.issubset(source):
        raise DyadicCertificateError("original D12 source fields are incomplete")
    if (source.get("k") != 48 or source.get("degree") != 12 or
            source.get("basis_dimension") != 272):
        raise DyadicCertificateError("original D12 source metadata mismatch")
    if ordered_payload_sha256(source) != TARGET_ORDERED_PAYLOAD_SHA256:
        raise DyadicCertificateError(
            "original ordered D12 label/vector payload mismatch")
    source_labels = parse_labels(source.get("basis"))
    raw_source_coefficients = source.get("rational_vector")
    if (not isinstance(raw_source_coefficients, list) or
            len(raw_source_coefficients) != 272):
        raise DyadicCertificateError("original D12 vector length mismatch")
    source_coefficients = [
        parse_fraction(value, f"source rational_vector[{index}]")
        for index, value in enumerate(raw_source_coefficients)
    ]

    base = strict_json(read_pinned(BASE_PATH, BASE_SHA256, "D12 base"),
                       "D12 base")
    if (set(base) != {"status", "k", "degree", "basis_dimension",
                     "basis", "rational_vector", "integer_scaling"} or
            base.get("status") != "exact-integer-scaled-fixed-vector-input" or
            base.get("k") != 48 or base.get("degree") != 12 or
            base.get("basis_dimension") != 272):
        raise DyadicCertificateError("D12 base metadata mismatch")
    scaling = base.get("integer_scaling")
    expected_scaling_keys = {
        "source_json", "source_sha256", "least_common_denominator",
        "form_scale", "quotient_and_margin_sign_preserved",
    }
    if (not isinstance(scaling, dict) or set(scaling) != expected_scaling_keys or
            scaling.get("source_json") != SOURCE_METADATA_PATH or
            scaling.get("source_sha256") != SOURCE_VECTOR_SHA256 or
            scaling.get("form_scale") != "least_common_denominator^2" or
            scaling.get("quotient_and_margin_sign_preserved") is not True):
        raise DyadicCertificateError("D12 base scaling metadata mismatch")
    labels = parse_labels(base.get("basis"))
    if labels != source_labels:
        raise DyadicCertificateError("scaled/source ordered basis mismatch")
    raw_coefficients = base.get("rational_vector")
    if not isinstance(raw_coefficients, list) or len(raw_coefficients) != 272:
        raise DyadicCertificateError("D12 base vector length mismatch")
    coefficients = [
        parse_fraction(value, f"base rational_vector[{index}]")
        for index, value in enumerate(raw_coefficients)
    ]
    if any(value.denominator != 1 for value in coefficients):
        raise DyadicCertificateError("D12 base coefficients are not integers")
    if not any(coefficients):
        raise DyadicCertificateError("D12 base polynomial is zero")
    raw_lcm = scaling.get("least_common_denominator")
    if (not isinstance(raw_lcm, str) or
            _POSITIVE_INTEGER_RE.fullmatch(raw_lcm) is None):
        raise DyadicCertificateError("noncanonical base-vector LCM")
    claimed_lcm = int(raw_lcm)
    reconstructed_lcm = lcm_denominators(source_coefficients)
    if claimed_lcm != reconstructed_lcm:
        raise DyadicCertificateError("base-vector LCM was not reconstructed")
    for index, (source_value, scaled_value) in enumerate(
            zip(source_coefficients, coefficients, strict=True)):
        if source_value * reconstructed_lcm != scaled_value:
            raise DyadicCertificateError(
                f"scaled base coefficient mismatch at index {index}")
    content = 0
    for value in coefficients:
        content = math.gcd(content, abs(value.numerator))
    if content != 1:
        raise DyadicCertificateError(
            f"scaled base vector is not primitive (content {content})")

    affine = load_exact_affine_multiplier(
        AFFINE_PATH, TARGET_C10_D12, AFFINE_SHA256,
        linear_cutoff=LINEAR_CUTOFF)
    affine_lcm = lcm_denominators(
        value for triple in affine.coefficients for value in triple)
    integer_triples = tuple(
        tuple(value * affine_lcm for value in triple)
        for triple in affine.coefficients)
    if any(value.denominator != 1
           for triple in integer_triples for value in triple):
        raise DyadicCertificateError("affine LCM scaling failed")
    integer_affine = AffineMultipliers(
        integer_triples, source_sha256=AFFINE_SHA256,
        linear_cutoff=LINEAR_CUTOFF)
    integer_affine.validate_for(TARGET_C10_D12)
    return (labels, coefficients, integer_affine, affine_lcm,
            reconstructed_lcm)


def prepare(precision: int, shadow_bits: int):
    labels, coefficients, affine, affine_lcm, base_lcm = load_exact_inputs()
    # Structure constants are ordinary integers and must be frozen before the
    # exact-integrator scalar hooks are replaced by intervals.
    orbit_table = precompute_orbits(labels, TARGET_C10_D12.k)
    if len(orbit_table) != EXPECTED_ORBIT_PRODUCT_PAIRS:
        raise DyadicCertificateError(
            "orbit-product table is incomplete: "
            f"expected {EXPECTED_ORBIT_PRODUCT_PAIRS}, got {len(orbit_table)}")
    scalar = install_dyadic(
        orbit_table, precision=precision, shadow_bits=shadow_bits)
    support_values = [
        TARGET_C10_D12.alpha,
        TARGET_C10_D12.delta,
        TARGET_C10_D12.eta,
        TARGET_C10_D12.beta1,
        TARGET_C10_D12.beta2,
        TARGET_C10_D12.beta3plus,
    ]
    support = ei.OneStratumSupport(
        TARGET_C10_D12.k,
        *(scalar(value.numerator, value.denominator)
          for value in support_values),
    )
    base = [scalar(value.numerator, value.denominator)
            for value in coefficients]
    evaluator = DyadicTransferEvaluator(support, labels, base, scalar)
    amplitudes = {
        r: tuple(scalar(value.numerator, value.denominator)
                 for value in affine.at(r))
        for r in range(len(affine.coefficients))
    }
    return evaluator, amplitudes, affine_lcm, base_lcm, len(orbit_table)


def interval_data(value: DyadicInterval) -> dict:
    if not isinstance(value, DyadicInterval):
        raise DyadicCertificateError("result is not a dyadic interval")
    return {
        "precision_bits": DyadicInterval.PRECISION,
        "lo_integer": str(value.lo),
        "hi_integer": str(value.hi),
        "lower_fraction": str(value.lower_fraction()),
        "upper_fraction": str(value.upper_fraction()),
        "width_units": value.width_units(),
    }


def parse_canonical_integer(token, description: str) -> int:
    if not isinstance(token, str) or _INTEGER_RE.fullmatch(token) is None:
        raise DyadicCertificateError(f"malformed {description}")
    value = int(token)
    if str(value) != token:
        raise DyadicCertificateError(f"noncanonical {description}")
    return value


def interval_from_data(raw, description: str, precision: int):
    if not isinstance(raw, dict) or set(raw) != {
            "precision_bits", "lo_integer", "hi_integer",
            "lower_fraction", "upper_fraction", "width_units"}:
        raise DyadicCertificateError(f"malformed staged {description}")
    if raw.get("precision_bits") != precision:
        raise DyadicCertificateError(
            f"staged {description} precision mismatch")
    lo = parse_canonical_integer(raw.get("lo_integer"),
                                 f"{description} lower integer")
    hi = parse_canonical_integer(raw.get("hi_integer"),
                                 f"{description} upper integer")
    width = raw.get("width_units")
    if (isinstance(width, bool) or not isinstance(width, int) or width < 0 or
            lo > hi or width != hi - lo):
        raise DyadicCertificateError(f"staged {description} bounds reversed")
    value = DyadicInterval._from_bounds(lo, hi)
    if (raw.get("lower_fraction") != str(value.lower_fraction()) or
            raw.get("upper_fraction") != str(value.upper_fraction())):
        raise DyadicCertificateError(
            f"staged {description} rational endpoints mismatch")
    return value


def common_metadata(dependencies, precision, shadow_bits, affine_lcm,
                    base_lcm, reverse_counts, orbit_pairs):
    return {
        "scope": "rigorous C10 D12 transferred-affine dyadic enclosure",
        "k": 48,
        "degree_of_base": 12,
        "base_dimension": 272,
        "linear_cutoff": LINEAR_CUTOFF,
        "base_path": str(BASE_PATH.relative_to(ROOT)),
        "base_sha256": BASE_SHA256,
        "original_source_path": str(SOURCE_PATH.relative_to(ROOT)),
        "original_source_sha256": SOURCE_VECTOR_SHA256,
        "original_ordered_payload_sha256": TARGET_ORDERED_PAYLOAD_SHA256,
        "source_vector_sha256": SOURCE_VECTOR_SHA256,
        "reconstructed_base_lcm": str(base_lcm),
        "reconstructed_base_lcm_bits": base_lcm.bit_length(),
        "affine_path": str(AFFINE_PATH.relative_to(ROOT)),
        "affine_sha256": AFFINE_SHA256,
        "effective_affine_lcm": str(affine_lcm),
        "effective_affine_lcm_bits": affine_lcm.bit_length(),
        "global_scaling_preserves_quotient_and_margin_sign": True,
        "precision_bits": precision,
        "shadow_bits": shadow_bits,
        "count_order": "reverse" if reverse_counts else "forward",
        "orbit_product_pairs": orbit_pairs,
        "parameters": {
            "alpha": str(TARGET_C10_D12.alpha),
            "eta": str(TARGET_C10_D12.eta),
            "delta": str(TARGET_C10_D12.delta),
            "beta1": str(TARGET_C10_D12.beta1),
            "beta2": str(TARGET_C10_D12.beta2),
            "beta3plus": str(TARGET_C10_D12.beta3plus),
        },
        "dependency_sha256": dependencies,
    }


def atomic_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    os.replace(temporary, path)
    return sha256(path)


def rss_kib() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def reverse_count_methods(evaluator):
    original_i = evaluator._r_values_i
    original_j = evaluator._r_values_j
    evaluator._r_values_i = lambda: list(reversed(original_i()))
    evaluator._r_values_j = lambda: list(reversed(original_j()))


def run_i(evaluator, amplitudes, common, stage_path, progress):
    self_hash = sha256(Path(__file__))
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    denominator, groups, faces = evaluator.evaluate_i_transfer(
        amplitudes, progress=progress)
    wall = time.perf_counter() - started_wall
    cpu = time.process_time() - started_cpu
    if groups != EXPECTED_I_GROUPS or faces != EXPECTED_I_FACES:
        raise DyadicCertificateError(
            f"I traversal incomplete: groups={groups}, faces={faces}")
    if denominator.lo <= 0:
        raise DyadicCertificateError(
            "I interval does not prove strict positivity")
    if sha256(Path(__file__)) != self_hash:
        raise DyadicCertificateError("driver changed during I stage")
    if dependency_snapshot() != common["dependency_sha256"]:
        raise DyadicCertificateError("dependency changed during I stage")
    read_pinned(BASE_PATH, BASE_SHA256, "D12 base")
    read_pinned(SOURCE_PATH, SOURCE_VECTOR_SHA256, "original D12 source")
    read_pinned(AFFINE_PATH, AFFINE_SHA256, "affine multiplier")
    payload = {
        "status": "c10-d12-affine-rigorous-dyadic-i-stage",
        **common,
        "driver_sha256": self_hash,
        "I": interval_data(denominator),
        "I_strictly_positive": True,
        "i_orbit_groups": groups,
        "i_faces": faces,
        "i_wall_seconds": wall,
        "i_cpu_seconds": cpu,
        "i_peak_rss_kib_linux": rss_kib(),
    }
    return payload, atomic_json(stage_path, payload)


def load_stage(stage_path, expected_sha, common):
    if (not isinstance(expected_sha, str) or len(expected_sha) != 64 or
            any(character not in "0123456789abcdef"
                for character in expected_sha)):
        raise DyadicCertificateError(
            "J phase requires a lowercase 64-hex I-stage SHA")
    stage = strict_json(read_pinned(stage_path, expected_sha, "I stage"),
                        "I stage")
    expected_keys = {
        "status", *common.keys(), "driver_sha256", "I",
        "I_strictly_positive", "i_orbit_groups", "i_faces",
        "i_wall_seconds", "i_cpu_seconds", "i_peak_rss_kib_linux",
    }
    if set(stage) != expected_keys:
        missing = sorted(expected_keys.difference(stage))
        extra = sorted(set(stage).difference(expected_keys))
        raise DyadicCertificateError(
            f"I-stage field set mismatch: missing={missing}, extra={extra}")
    if stage.get("status") != "c10-d12-affine-rigorous-dyadic-i-stage":
        raise DyadicCertificateError("I-stage status mismatch")
    for key, value in common.items():
        if stage.get(key) != value:
            raise DyadicCertificateError(
                f"I-stage metadata mismatch at {key}")
    if stage.get("driver_sha256") != sha256(Path(__file__)):
        raise DyadicCertificateError("I-stage driver SHA mismatch")
    if (stage.get("I_strictly_positive") is not True or
            stage.get("i_orbit_groups") != EXPECTED_I_GROUPS or
            stage.get("i_faces") != EXPECTED_I_FACES):
        raise DyadicCertificateError("I-stage completeness gates failed")
    denominator = interval_from_data(
        stage.get("I"), "I", common["precision_bits"])
    if denominator.lo <= 0:
        raise DyadicCertificateError("staged I is not strictly positive")
    return stage, denominator


def run_j(evaluator, amplitudes, common, stage_path, expected_stage_sha,
          output_path, progress):
    self_hash = sha256(Path(__file__))
    stage, denominator = load_stage(
        stage_path, expected_stage_sha, common)
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    numerator, components, domains = evaluator.evaluate_j_transfer(
        amplitudes, progress=progress)
    wall = time.perf_counter() - started_wall
    cpu = time.process_time() - started_cpu
    if (components != EXPECTED_MARGINAL_COMPONENTS or
            domains != EXPECTED_J_DOMAINS):
        raise DyadicCertificateError(
            f"J traversal incomplete: components={components}, domains={domains}")
    margin = numerator - denominator
    quotient = numerator / denominator
    positive = margin.lo > 0
    if sha256(Path(__file__)) != self_hash:
        raise DyadicCertificateError("driver changed during J stage")
    if dependency_snapshot() != common["dependency_sha256"]:
        raise DyadicCertificateError("dependency changed during J stage")
    read_pinned(stage_path, expected_stage_sha, "I stage")
    read_pinned(BASE_PATH, BASE_SHA256, "D12 base")
    read_pinned(SOURCE_PATH, SOURCE_VECTOR_SHA256, "original D12 source")
    read_pinned(AFFINE_PATH, AFFINE_SHA256, "affine multiplier")
    payload = {
        "status": ("c10-d12-affine-rigorous-dyadic-positive-candidate"
                   if positive else
                   "c10-d12-affine-rigorous-dyadic-nonpositive-result"),
        **common,
        "driver_sha256": self_hash,
        "i_stage_path": str(stage_path),
        "i_stage_sha256": expected_stage_sha,
        "I": interval_data(denominator),
        "M2": interval_data(numerator),
        "M2_minus_M1": interval_data(margin),
        "quotient": interval_data(quotient),
        "I_strictly_positive": denominator.lo > 0,
        "margin_strictly_positive": positive,
        "acceptance_rule": "I.lo > 0 and (M2-M1).lo > 0",
        "integer_directed_outward_rounding": True,
        "matrix_entries_consumed": False,
        "persistent_moment_cache_consumed": False,
        "marginal_components": components,
        "j_branch_domains": domains,
        "j_wall_seconds": wall,
        "j_cpu_seconds": cpu,
        "j_peak_rss_kib_linux": rss_kib(),
        "i_wall_seconds": stage["i_wall_seconds"],
        "theorem_ready": False,
        "theorem_ready_reason": (
            "result-driver audit, independent reconstruction, and final "
            "end-to-end analytic audit remain mandatory"
        ),
    }
    atomic_json(output_path, payload)
    return payload, positive


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("i", "j", "all"), default="all")
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-stage-sha256")
    parser.add_argument("--precision", type=int, default=512)
    parser.add_argument("--shadow-bits", type=int, default=96)
    parser.add_argument("--reverse-counts", action="store_true")
    parser.add_argument("--progress", action="store_true")
    return parser.parse_args()


def validate_output_paths(stage: Path, output: Path) -> None:
    stage_resolved = stage.resolve(strict=False)
    output_resolved = output.resolve(strict=False)
    protected = {
        Path(__file__).resolve(),
        BASE_PATH.resolve(),
        SOURCE_PATH.resolve(),
        AFFINE_PATH.resolve(),
        *(path.resolve() for path in DEPENDENCY_SHAS),
    }
    if stage_resolved == output_resolved:
        raise DyadicCertificateError("stage and output paths must differ")
    if stage_resolved in protected or output_resolved in protected:
        raise DyadicCertificateError(
            "stage/output path collides with a pinned input or dependency")


def main():
    args = parse_args()
    if not 256 <= args.precision <= 4096:
        raise DyadicCertificateError(
            "certificate precision must be in [256,4096]")
    if not 32 <= args.shadow_bits <= 512:
        raise DyadicCertificateError(
            "shadow precision must be in [32,512]")
    validate_output_paths(args.stage, args.output)
    self_hash = sha256(Path(__file__))
    dependencies = dependency_snapshot()
    evaluator, amplitudes, affine_lcm, base_lcm, orbit_pairs = prepare(
        args.precision, args.shadow_bits)
    if args.reverse_counts:
        reverse_count_methods(evaluator)
    common = common_metadata(
        dependencies, args.precision, args.shadow_bits, affine_lcm,
        base_lcm,
        args.reverse_counts, orbit_pairs)
    if sha256(Path(__file__)) != self_hash:
        raise DyadicCertificateError("driver changed during preparation")

    expected_stage_sha = args.expected_stage_sha256
    if args.phase in ("i", "all"):
        stage, expected_stage_sha = run_i(
            evaluator, amplitudes, common, args.stage, args.progress)
        print(json.dumps({
            "phase": "I complete",
            "I_lower": stage["I"]["lower_fraction"],
            "I_upper": stage["I"]["upper_fraction"],
            "stage": str(args.stage),
            "stage_sha256": expected_stage_sha,
            "wall_seconds": stage["i_wall_seconds"],
            "peak_rss_kib_linux": stage["i_peak_rss_kib_linux"],
        }, sort_keys=True), flush=True)
    if args.phase in ("j", "all"):
        if expected_stage_sha is None:
            raise DyadicCertificateError(
                "J phase requires --expected-stage-sha256")
        result, positive = run_j(
            evaluator, amplitudes, common, args.stage,
            expected_stage_sha, args.output, args.progress)
        print(json.dumps({
            "phase": "J complete",
            "output": str(args.output),
            "output_sha256": sha256(args.output),
            "quotient_lower": result["quotient"]["lower_fraction"],
            "quotient_upper": result["quotient"]["upper_fraction"],
            "margin_lower": result["M2_minus_M1"]["lower_fraction"],
            "margin_upper": result["M2_minus_M1"]["upper_fraction"],
            "margin_strictly_positive": positive,
            "wall_seconds": result["j_wall_seconds"],
            "peak_rss_kib_linux": result["j_peak_rss_kib_linux"],
        }, sort_keys=True), flush=True)
        if not positive:
            return 4
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DyadicCertificateError, CertificateError, ValueError,
            ArithmeticError, OSError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)},
                         sort_keys=True), file=sys.stderr)
        raise SystemExit(3) from exc
