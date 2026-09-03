#!/usr/bin/env python3
"""Source-bound unmultiplied D12 target for the v6 multiplier screen.

This module supplies only discovery infrastructure.  It binds the exact
272-label polynomial (and its integer-scaled computational copy), evaluates
the frozen v6 transformed multiplier features directly, and validates the
Decimal100 per-stratum base normalizers.  It neither runs chains nor accepts
a sampled quotient.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from importance_whitening_v6 import WhitenedC10ImportanceDensity


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]

D12_SOURCE_RELATIVE = \
    "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
D12_INTEGER_RELATIVE = \
    "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12_integer_scaled.json"
D4_ORACLE_RELATIVE = \
    "agents/exact-integrator/results/c10_stratum_quadratic_cappedopt_D4_exact.json"
RAW_NORMALIZER_RELATIVE = \
    "agents/structural-basis/results/c10_D12_band_sparse_gradient_mp100.json"
RECOVERED_NORMALIZER_RELATIVE = \
    "agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json"
BASELINE_RELATIVE = \
    "agents/exact-integrator/results/c10_capped_fullD12_vector_grouped_mp100.json"
RECOVERY_CODE_RELATIVE = \
    "agents/structural-basis/code/recover_band_gradient.py"
RECOVERY_TEST_RELATIVE = \
    "agents/structural-basis/tests/test_recover_band_gradient.py"
RECOVERY_AUDIT_RELATIVE = \
    "agents/small-delta-frontier/RECOVERED-BAND-GRADIENT-AUDIT.md"
NEGATIVE_TRANSFER_RELATIVE = \
    "agents/exact-integrator/results/c10_D12_quadratic_transfer_decimal100.json"

EXPECTED_HASHES = {
    D12_SOURCE_RELATIVE:
        "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
    D12_INTEGER_RELATIVE:
        "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93",
    D4_ORACLE_RELATIVE:
        "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86",
    RAW_NORMALIZER_RELATIVE:
        "0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d",
    RECOVERED_NORMALIZER_RELATIVE:
        "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43",
    BASELINE_RELATIVE:
        "02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9",
    RECOVERY_CODE_RELATIVE:
        "9342fa3f6d8157a4d9b8603a20bb0527b7f47087a5aa3c9d39aebef892f9fee5",
    RECOVERY_TEST_RELATIVE:
        "a9926cefa7ed92b30abeac3801a8866fac4ffe97b593b28b898e9579c9c1a716",
    RECOVERY_AUDIT_RELATIVE:
        "502441909f2f83b78cc80538d1518ee4d7856da5929ba6e39ba67c5c247d3100",
    NEGATIVE_TRANSFER_RELATIVE:
        "7e9f62fd5fa0040c2e9c184319f90e5278ec9f21912bd9198610bc7823544978",
}

SUPPORT_PARAMETERS = {
    "alpha": "79247/300000", "delta": "1/100",
    "eta": "76247/300000", "beta1": "3/20", "beta2": "3/20",
    "beta3plus": "97/625",
}
SUM_INTERNAL_RELATIVE_TOLERANCE = Decimal("1e-98")
BASELINE_RELATIVE_TOLERANCE = Decimal("1e-50")
NEGATIVE_TRANSFER_MAXIMUM_QUOTIENT = Decimal("0.96")
_CANONICAL_RATIONAL = re.compile(r"^(?:0|-?[1-9][0-9]*)(?:/[1-9][0-9]*)?$")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def strict_metadata_json(data, name):
    """Reject duplicate/nonfinite JSON while retaining benign float metadata."""
    if not isinstance(data, bytes) or len(data) > 128_000_000:
        raise ValueError(f"{name} must be bounded JSON bytes")

    def pairs_hook(pairs):
        answer = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in answer:
                raise ValueError(f"duplicate/non-string key in {name}")
            answer[key] = value
        return answer

    def reject_constant(_value):
        raise ValueError(f"nonfinite JSON token in {name}")

    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs_hook,
                      parse_float=Decimal, parse_constant=reject_constant)


def exact_fraction(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} is Boolean")
    if isinstance(value, int):
        return Fraction(value)
    if (not isinstance(value, str) or len(value) > 1_000_000 or
            not _CANONICAL_RATIONAL.fullmatch(value)):
        raise ValueError(f"{name} is not a canonical rational")
    answer = Fraction(value)
    if value.startswith("-") and answer == 0:
        raise ValueError(f"{name} is negative zero")
    if "/" in value and str(answer) != value:
        raise ValueError(f"{name} fraction is not reduced")
    return answer


def positive_decimal(value, name):
    if not isinstance(value, str) or len(value) > 1000:
        raise ValueError(f"{name} must be a finite Decimal string")
    answer = Decimal(value)
    if not answer.is_finite() or answer <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return answer


def _relative_error(observed, expected):
    if expected == 0:
        raise ZeroDivisionError("relative-error reference is zero")
    return abs(observed / expected - 1)


def validate_source_equivalence(repo_root=REPO_ROOT):
    repo_root = Path(repo_root).resolve()
    for relative, expected in EXPECTED_HASHES.items():
        if sha256_file(repo_root / relative) != expected:
            raise ValueError(f"D12 target dependency changed: {relative}")
    source = strict_metadata_json(
        (repo_root / D12_SOURCE_RELATIVE).read_bytes(), "D12 source")
    integer = strict_metadata_json(
        (repo_root / D12_INTEGER_RELATIVE).read_bytes(),
        "D12 integer-scaled source")
    if (source.get("k") != 48 or source.get("degree") != 12 or
            source.get("basis_dimension") != 272 or
            integer.get("status") != "exact-integer-scaled-fixed-vector-input" or
            integer.get("k") != 48 or integer.get("degree") != 12 or
            integer.get("basis_dimension") != 272 or
            source.get("basis") != integer.get("basis") or
            not isinstance(source.get("rational_vector"), list) or
            not isinstance(integer.get("rational_vector"), list) or
            len(source["basis"]) != 272 or
            len(source["rational_vector"]) != 272 or
            len(integer["rational_vector"]) != 272):
        raise ValueError("D12 source dimensions/basis differ")
    scaling = integer.get("integer_scaling")
    if (not isinstance(scaling, dict) or set(scaling) != {
            "source_json", "source_sha256", "least_common_denominator",
            "form_scale", "quotient_and_margin_sign_preserved"} or
            scaling["source_sha256"] != EXPECTED_HASHES[D12_SOURCE_RELATIVE] or
            scaling["form_scale"] != "least_common_denominator^2" or
            scaling["quotient_and_margin_sign_preserved"] is not True):
        raise ValueError("integer scaling provenance changed")
    denominator = exact_fraction(
        scaling["least_common_denominator"], "least common denominator")
    if denominator.denominator != 1 or denominator <= 0:
        raise ValueError("least common denominator is not positive integer")
    for index, (raw, scaled) in enumerate(zip(
            source["rational_vector"], integer["rational_vector"])):
        if exact_fraction(raw, f"source coefficient {index}") * denominator != \
                exact_fraction(scaled, f"integer coefficient {index}"):
            raise ArithmeticError(
                f"integer source is not common-scale equivalent at {index}")
    return {"source": source, "integer": integer,
            "least_common_denominator": denominator}


def load_d12_normalizers(repo_root=REPO_ROOT):
    """Validate and normalize the 16 raw C10 D12 I/J stratum masses."""
    repo_root = Path(repo_root).resolve()
    validate_source_equivalence(repo_root)
    raw = strict_metadata_json(
        (repo_root / RAW_NORMALIZER_RELATIVE).read_bytes(), "raw normalizers")
    recovered = strict_metadata_json(
        (repo_root / RECOVERED_NORMALIZER_RELATIVE).read_bytes(),
        "recovered gradient")
    baseline = strict_metadata_json(
        (repo_root / BASELINE_RELATIVE).read_bytes(), "grouped baseline")
    negative = strict_metadata_json(
        (repo_root / NEGATIVE_TRANSFER_RELATIVE).read_bytes(),
        "negative transfer regression")
    expected_gate_keys = {
        "decimal_dps_at_least_90", "source_sha_pinned", "bands_sha_pinned",
        "operator_unchanged_during_run", "band_dependency_sha_pinned_and_unchanged",
        "grouped_sha_pinned_and_unchanged", "integrator_sha_pinned_and_unchanged",
        "source_k48_dim272_banddim20", "parameters_exact_c10",
        "all_vectors_length20", "all_numbers_finite", "gradient_halves_match",
        "denominator_positive", "quotient_recomputed",
        "euler_relative_below_1e50", "complete_traversal_counts",
        "stratum_buckets_sum", "baseline_artifact_sha_pinned",
        "baseline_dependencies_match", "baseline_forms_50_digits"}
    if (raw.get("status") != "rejected-degree-band-gradient-discovery" or
            raw.get("rigorous") is not False or raw.get("complete") is not True or
            raw.get("decimal_dps") != 100 or raw.get("workers") != 2 or
            raw.get("source_sha256") != EXPECTED_HASHES[D12_SOURCE_RELATIVE] or
            raw.get("baseline_sha256") != EXPECTED_HASHES[BASELINE_RELATIVE] or
            raw.get("parameters") != SUPPORT_PARAMETERS or
            raw.get("gates_passed") is not False or
            not isinstance(raw.get("gates"), dict) or
            set(raw["gates"]) != expected_gate_keys or
            raw["gates"].get("gradient_halves_match") is not False or
            any(value is not True for key, value in raw["gates"].items()
                if key != "gradient_halves_match")):
        raise ValueError("raw D12 normalizer trust gates changed")
    recovery_gates = {
        "raw_bytes_sha_pinned", "sole_raw_failure_is_redundant_halves",
        "substantive_producer_invariants_recomputed",
        "dependencies_and_parameters_pinned",
        "exact_half_mismatch_below_1e98_relative",
        "no_projected_trial_or_quotient_emitted"}
    if (recovered.get("status") !=
            "byte-pinned-recovered-degree-band-gradient-discovery" or
            recovered.get("rigorous") is not False or
            recovered.get("complete") is not True or
            recovered.get("raw_sha256") != EXPECTED_HASHES[
                RAW_NORMALIZER_RELATIVE] or
            recovered.get("recovery_script_sha256") != EXPECTED_HASHES[
                RECOVERY_CODE_RELATIVE] or
            recovered.get("source_sha256") != EXPECTED_HASHES[
                D12_SOURCE_RELATIVE] or
            recovered.get("parameters") != SUPPORT_PARAMETERS or
            not isinstance(recovered.get("validation_gates"), dict) or
            set(recovered["validation_gates"]) != recovery_gates or
            any(value is not True
                for value in recovered["validation_gates"].values()) or
            recovered.get("denominator") != raw.get("denominator") or
            recovered.get("numerator") != raw.get("numerator")):
        raise ValueError("recovered D12 normalizer trust chain changed")
    if (baseline.get("status") !=
            "multiprecision-grouped-fixed-vector-discovery" or
            baseline.get("rigorous") is not False or baseline.get("k") != 48 or
            baseline.get("basis_dimension") != 272 or
            baseline.get("input_sha256") != EXPECTED_HASHES[D12_SOURCE_RELATIVE] or
            baseline.get("parameters") != SUPPORT_PARAMETERS):
        raise ValueError("D12 grouped baseline identity changed")
    if (negative.get("status") !=
            "multiprecision-transferred-quadratic-candidate" or
            negative.get("rigorous") is not False or
            negative.get("input_sha256") != EXPECTED_HASHES[
                D12_INTEGER_RELATIVE] or
            positive_decimal(negative.get("quotient"),
                             "negative transfer quotient") >=
            NEGATIVE_TRANSFER_MAXIMUM_QUOTIENT):
        raise ValueError("negative-transfer exclusion regression changed")
    if (not isinstance(raw.get("i_value_by_r"), list) or
            len(raw["i_value_by_r"]) != 16 or
            not isinstance(raw.get("j_value_by_r"), list) or
            len(raw["j_value_by_r"]) != 16):
        raise ValueError("D12 raw normalizer stratum count changed")
    with localcontext() as context:
        context.prec = 180
        i_values = tuple(positive_decimal(value, f"I stratum {r}")
                         for r, value in enumerate(raw["i_value_by_r"]))
        j_values = tuple(positive_decimal(value, f"J stratum {r}")
                         for r, value in enumerate(raw["j_value_by_r"]))
        i_sum = sum(i_values, Decimal(0))
        j_sum = sum(j_values, Decimal(0))
        raw_i = positive_decimal(raw.get("denominator"), "raw denominator")
        raw_b = positive_decimal(raw.get("numerator"), "raw numerator")
        baseline_i = positive_decimal(
            baseline.get("denominator"), "baseline denominator")
        baseline_b = positive_decimal(
            baseline.get("numerator"), "baseline numerator")
        internal_i_error = _relative_error(i_sum, raw_i)
        internal_j_error = _relative_error(Decimal(48) * j_sum, raw_b)
        baseline_i_error = _relative_error(raw_i, baseline_i)
        baseline_b_error = _relative_error(raw_b, baseline_b)
        quotient = Decimal(48) * j_sum / i_sum
        recorded_quotient = positive_decimal(
            raw.get("quotient"), "raw quotient")
        quotient_error = _relative_error(quotient, recorded_quotient)
        if (internal_i_error > SUM_INTERNAL_RELATIVE_TOLERANCE or
                internal_j_error > SUM_INTERNAL_RELATIVE_TOLERANCE or
                quotient_error > SUM_INTERNAL_RELATIVE_TOLERANCE or
                baseline_i_error > BASELINE_RELATIVE_TOLERANCE or
                baseline_b_error > BASELINE_RELATIVE_TOLERANCE):
            raise ArithmeticError("D12 normalizer sums/base forms disagree")
        # Finite Decimal strings are exact rationals.  Store normalized
        # weights as Fractions so downstream recombination sums to one
        # identically, independent of ambient Decimal precision.
        i_fraction = tuple(Fraction(value) for value in raw["i_value_by_r"])
        j_fraction = tuple(Fraction(value) for value in raw["j_value_by_r"])
        i_fraction_sum = sum(i_fraction, Fraction(0))
        j_fraction_sum = sum(j_fraction, Fraction(0))
        return {
            "i_values": i_values, "j_values": j_values,
            "i_weights": tuple(value / i_fraction_sum for value in i_fraction),
            "j_weights": tuple(value / j_fraction_sum for value in j_fraction),
            "denominator": i_sum, "j_total_unscaled": j_sum,
            "numerator": Decimal(48) * j_sum, "base_quotient": quotient,
            "j_scale_to_numerator": 48,
            "relative_errors": {
                "sum_i_to_raw": internal_i_error,
                "48_sum_j_to_raw": internal_j_error,
                "quotient_to_raw": quotient_error,
                "raw_i_to_grouped_baseline": baseline_i_error,
                "raw_b_to_grouped_baseline": baseline_b_error,
            },
            "raw_sha256": EXPECTED_HASHES[RAW_NORMALIZER_RELATIVE],
            "recovered_sha256": EXPECTED_HASHES[RECOVERED_NORMALIZER_RELATIVE],
            "baseline_sha256": EXPECTED_HASHES[BASELINE_RELATIVE],
        }


class D12WhitenedMultiplierDensity(WhitenedC10ImportanceDensity):
    """Unmultiplied 272-term D12 base with direct v6 multiplier features."""

    def __init__(self, repo_root=REPO_ROOT):
        repo_root = Path(repo_root).resolve()
        provenance = validate_source_equivalence(repo_root)
        super().__init__(repo_root / D12_INTEGER_RELATIVE,
                         repo_root / D4_ORACLE_RELATIVE)
        if (self.vector_sha256 != EXPECTED_HASHES[D12_INTEGER_RELATIVE] or
                self.parameter_sha256 != EXPECTED_HASHES[D4_ORACLE_RELATIVE] or
                self.k != 48 or self.dimension != 96 or
                tuple(self.strata) != tuple(range(16))):
            raise ValueError("D12 transformed adapter provenance changed")
        self.d12_source_sha256 = EXPECTED_HASHES[D12_SOURCE_RELATIVE]
        self.d12_integer_sha256 = EXPECTED_HASHES[D12_INTEGER_RELATIVE]
        self.d12_basis_dimension = 272
        self.d12_degree = 12
        self.integer_scale = provenance["least_common_denominator"]

    def validate_constant_multiplier(self, point, *, tolerance=512):
        features = self.i_features(point)
        reconstructed = math.fsum(
            self.base_constant_weights[6 * r] * features[6 * r]
            for r in self.strata)
        bound = tolerance * math.ulp(1.0) * max(1.0, abs(reconstructed))
        if not math.isfinite(reconstructed) or abs(reconstructed - 1) > bound:
            raise ArithmeticError("D12 constant multiplier did not reconstruct")
        return reconstructed
