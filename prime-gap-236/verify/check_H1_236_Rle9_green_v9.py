#!/usr/bin/env python3
"""Standalone source reconstruction of the Green-v9 R<=9 certificate.

The large replay logic is imported from its frozen fixed-polygon-v8 version.
This small adapter replaces only the mixed-shard producer, result checker and
aggregate wrapper.  It also translates the Green checker's two backend-name
fields for the already-audited generic replay logic; the raw shard bytes are
still parsed independently for the final exact scalar reconstruction.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
BASE_PATH = FILE.with_name("check_H1_236_Rle9.py")
BASE_SHA256 = \
    "4179aeda84fef4d6712e62e7b02c0738bd277e69cb0e8d71f81de77863e324cb"
GREEN_AGGREGATOR_PATH = FILE.with_name(
    "assemble_one_band_236_green_v9_r09.py")
GREEN_AGGREGATOR_SHA256 = \
    "4762573e5f699f2641bb0081f571a3c34f23b47d70386f49626f9af1eef2de29"
GREEN_AGGREGATOR_TEST_PATH = FILE.with_name(
    "test_assemble_one_band_236_green_v9_r09.py")
GREEN_AGGREGATOR_TEST_SHA256 = \
    "3dfc7afc7bafd20daa94e8a43d0d8e27e1a06ebce86a6777a8a8bd57c12c1300"
SELF_TEST_PATH = FILE.with_name("test_check_H1_236_Rle9_green_v9.py")
SELF_TEST_SHA256 = \
    "72f4b78be5bdc089184a460b77cd969cad98d1658136b1f38530fc83fa16f2a9"
DEFAULT_CERTIFICATE = REPO / "certificate/H1_236_one_band_Rle9_green_v9.json"


def sha256(data_or_path) -> str:
    data = (data_or_path if isinstance(data_or_path, bytes)
            else Path(data_or_path).read_bytes())
    return hashlib.sha256(data).hexdigest()


def load_pinned(name, path, expected):
    data = path.read_bytes()
    if sha256(data) != expected:
        raise RuntimeError(f"pinned {name} changed")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_pinned(
    "H1_236_green_v9_pinned_Rle9_replay", BASE_PATH, BASE_SHA256)
GREEN = load_pinned(
    "H1_236_green_v9_pinned_aggregator",
    GREEN_AGGREGATOR_PATH, GREEN_AGGREGATOR_SHA256)

_OLD_AGG = BASE.AGG
_OLD_AGGREGATOR_PATH = BASE.ASSEMBLER
_OLD_AGGREGATOR_SHA256 = BASE.ASSEMBLER_SHA256
_OLD_COMPARE_CERTIFICATE = BASE.compare_certificate
_OLD_STRICT_LOADS = BASE.BASE.strict_loads
_V8_FORMAT = "H1-236-one-band-fixed-polygon-v8-Rle9-exact-aggregate-v1"
_V8_ENGINE = "fixed-polygon-v8-with-Rle9-branch-projection"
_GREEN_FORMAT = "H1-236-one-band-green-v9-Rle9-exact-aggregate-v1"
_GREEN_ENGINE = "green-v9-with-Rle9-branch-projection"


def adapt_b_audit(value, label):
    """Validate and translate only backend-name fields used by BASE.verify."""
    fields = {
        "status", "input_sha256", "common_r", "scaled_b_shard",
        "recombined_exactly", "maximum_active_shift",
        "active_branch_families", "fixed_denominator_relation_verified",
        "cache_inventory_semantics_verified",
        "green_boundary_denominator_proof_pinned", "convexity_fail_closed",
        "source_closure_verified", "reference_exact_fields_bit_equal",
        "reference_sha256", "total_scalar_products",
        "total_surviving_product_monomials",
    }
    if (type(value) is not dict or set(value) != fields or
            value.get("status") !=
                "GREEN-V9 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS" or
            type(value.get("common_r")) is not int or
            not 0 <= value["common_r"] <= 9 or
            type(value.get("maximum_active_shift")) is not int or
            value["maximum_active_shift"] != 14 - value["common_r"] or
            value.get("active_branch_families") !=
                ["large", "small", "small_total"] or
            type(value.get("input_sha256")) is not str or
            BASE.HEX64.fullmatch(value["input_sha256"]) is None or
            type(value.get("total_scalar_products")) is not int or
            value["total_scalar_products"] <= 0 or
            type(value.get("total_surviving_product_monomials")) is not int or
            value["total_surviving_product_monomials"] <= 0 or
            value.get("recombined_exactly") is not True or
            value.get("fixed_denominator_relation_verified") is not True or
            value.get("cache_inventory_semantics_verified") is not True or
            value.get("green_boundary_denominator_proof_pinned") is not True or
            value.get("convexity_fail_closed") is not True or
            value.get("source_closure_verified") is not True or
            value.get("reference_exact_fields_bit_equal") is not None or
            value.get("reference_sha256") is not None):
        raise BASE.VerificationError(f"malformed Green-v9 audit: {label}")
    BASE.rational(value.get("scaled_b_shard"), f"{label}.scaled_b_shard")
    translated = copy.deepcopy(value)
    translated["status"] = (
        "FIXED-POLYGON-V8 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS")
    translated["fixed_polygon_denominator_proof_pinned"] = \
        translated.pop("green_boundary_denominator_proof_pinned")
    return translated


def strict_loads_for_green(data, label):
    value = _OLD_STRICT_LOADS(data, label)
    if label.startswith("b audit stdout r="):
        return adapt_b_audit(value, label)
    return value


def compare_green_certificate(certificate, aggregate, reconstructed):
    """Reuse exact comparison after checking and renaming backend metadata."""
    if (type(certificate) is not dict or type(aggregate) is not dict or
            certificate.get("format") != _GREEN_FORMAT or
            aggregate.get("format") != _GREEN_FORMAT or
            certificate.get("b_engine") != _GREEN_ENGINE or
            aggregate.get("b_engine") != _GREEN_ENGINE):
        raise BASE.VerificationError(
            "compact/fresh aggregate is not the Green-v9 contract")
    compatible_certificate = copy.deepcopy(certificate)
    compatible_aggregate = copy.deepcopy(aggregate)
    for record in (compatible_certificate, compatible_aggregate):
        record["format"] = _V8_FORMAT
        record["b_engine"] = _V8_ENGINE
    return _OLD_COMPARE_CERTIFICATE(
        compatible_certificate, compatible_aggregate, reconstructed)


# Remove the v8-only wrapper closure, retain the common R<=9/base closure,
# then add the complete Green wrapper closure.  The Green aggregator itself
# flat-pins both the Green and normalized-v8 checker source maps.
PINS = dict(BASE.PINS)
for path in set(_OLD_AGG.PINS) - set(_OLD_AGG.R09.PINS):
    PINS.pop(path, None)
PINS.pop(BASE.ASSEMBLER, None)
PINS.pop(BASE.ASSEMBLER_TEST, None)
for path, expected in GREEN.PINS.items():
    previous = PINS.get(path)
    if previous is not None and previous != expected:
        raise RuntimeError(f"inconsistent Green replay pin: {path}")
    PINS[path] = expected
PINS.update({
    _OLD_AGGREGATOR_PATH: _OLD_AGGREGATOR_SHA256,
    BASE_PATH: BASE_SHA256,
    GREEN_AGGREGATOR_PATH: GREEN_AGGREGATOR_SHA256,
    GREEN_AGGREGATOR_TEST_PATH: GREEN_AGGREGATOR_TEST_SHA256,
    SELF_TEST_PATH: SELF_TEST_SHA256,
})

# Configure the frozen replay module.  Its exact reconstruction, byte-binding,
# support, tuple and inner-form code is otherwise untouched.
BASE.FILE = FILE
BASE.AGG = GREEN
BASE.ASSEMBLER = GREEN_AGGREGATOR_PATH
BASE.ASSEMBLER_SHA256 = GREEN_AGGREGATOR_SHA256
BASE.ASSEMBLER_TEST = GREEN_AGGREGATOR_TEST_PATH
BASE.ASSEMBLER_TEST_SHA256 = GREEN_AGGREGATOR_TEST_SHA256
BASE.B_PRODUCER = GREEN.GREEN_RUNNER
BASE.B_RESULT_CHECKER = GREEN.GREEN_CHECKER
BASE.DEFAULT_CERTIFICATE = DEFAULT_CERTIFICATE
BASE.PINS = PINS
BASE.compare_certificate = compare_green_certificate
BASE.BASE.strict_loads = strict_loads_for_green


def main():
    return BASE.main()


if __name__ == "__main__":
    raise SystemExit(main())
