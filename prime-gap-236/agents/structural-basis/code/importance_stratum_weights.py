#!/usr/bin/env python3
"""Load pinned per-stratum discovery normalizers fail-closed.

These Decimal weights are used only to assemble conditional Monte Carlo
estimates.  They are never accepted by the exact sieve certificate checker.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal, localcontext
from pathlib import Path


EXPECTED_C10_PARAMETERS = {
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
    "beta1": "3/20",
    "beta2": "3/20",
    "beta3plus": "97/625",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PREFIX = re.compile(r"^[a-z0-9_]*$")
_DECIMAL_SCIENTIFIC = re.compile(
    r"^[1-9]\.[0-9]+E(?:0|[+-]?[1-9][0-9]*)$")


def _reject_json_constant(_value):
    raise ValueError("nonfinite JSON token in normalizer artifact")


def _finite_json_float(token):
    value = float(token)
    if not math.isfinite(value):
        raise ValueError("overflowed JSON float in normalizer metadata")
    return value


def _strict_json_bytes(data):
    if not isinstance(data, bytes) or len(data) > 64_000_000:
        raise ValueError("normalizer must be bounded JSON bytes")

    def pairs_hook(pairs):
        answer = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in answer:
                raise ValueError(
                    "duplicate or non-string key in normalizer artifact")
            answer[key] = value
        return answer

    # The pinned producer has benign timing metadata encoded as JSON floats;
    # exact mathematical fields receive a stricter gate below.
    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs_hook,
                      parse_float=_finite_json_float,
                      parse_constant=_reject_json_constant)


def _recorded_decimal(token, decimal_dps, name):
    if not isinstance(token, str) or not _DECIMAL_SCIENTIFIC.fullmatch(token):
        raise ValueError(f"{name} is not a canonical scientific Decimal")
    significand_digits = sum(
        character.isdigit() for character in token.split("E", 1)[0])
    # A few positive contractions can lose one leading digit to Decimal
    # normalization, while the discovery contract asks for at least 80
    # stable recorded digits rather than exactly `decimal_dps` characters.
    if significand_digits < 80:
        raise ValueError(f"{name} records fewer than 80 significant digits")
    value = Decimal(token)
    if str(value) != token:
        raise ValueError(f"{name} is not canonically serialized")
    return value


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_stratum_weights(path, expected_sha256, *, prefix,
                         j_scale_to_numerator):
    path = Path(path)
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(
            expected_sha256):
        raise ValueError("expected SHA-256 must be 64 lowercase hex digits")
    if not isinstance(prefix, str) or not _PREFIX.fullmatch(prefix):
        raise ValueError("normalizer prefix has invalid syntax")
    # Read once.  Hashing one path version and parsing a later version would
    # permit a concrete hash/parse TOCTOU provenance mismatch.
    data = path.read_bytes()
    observed_sha256 = hashlib.sha256(data).hexdigest()
    if observed_sha256 != expected_sha256:
        raise ValueError("stratum-normalizer artifact hash mismatch")
    raw = _strict_json_bytes(data)
    if not isinstance(raw, dict):
        raise ValueError("normalizer top level must be an object")
    decimal_dps = raw.get("decimal_dps")
    if (isinstance(decimal_dps, bool) or not isinstance(decimal_dps, int) or
            decimal_dps < 80):
        raise ValueError("at least 80 recorded decimal digits are required")
    if raw.get("complete") is not True or raw.get("gates_passed") is not True:
        raise ValueError("normalizer traversal is incomplete or failed its gates")
    if raw.get("parameters") != EXPECTED_C10_PARAMETERS:
        raise ValueError("normalizer is not the exact C10 parameter point")
    if (isinstance(j_scale_to_numerator, bool) or
            j_scale_to_numerator not in (1, 48)):
        raise ValueError("J convention must explicitly be 1 (48Jr) or 48 (Jr)")

    i_key = f"{prefix}i_by_r"
    j_key = f"{prefix}j_by_common_r"
    denominator_key = f"{prefix}denominator"
    numerator_key = f"{prefix}numerator"
    try:
        raw_i = raw[i_key]
        raw_j = raw[j_key]
        raw_denominator = raw[denominator_key]
        raw_numerator = raw[numerator_key]
    except KeyError as exc:
        raise ValueError(f"missing stratum-normalizer field: {exc}") from exc
    if (not isinstance(raw_i, list) or not isinstance(raw_j, list) or
            len(raw_i) != 16 or len(raw_j) != 16):
        raise ValueError("C10 normalizer artifact must contain all 16 strata")

    with localcontext() as context:
        context.prec = decimal_dps + 30
        try:
            i_values = tuple(
                _recorded_decimal(x, decimal_dps, f"I stratum {r}")
                for r, x in enumerate(raw_i))
            j_values = tuple(
                _recorded_decimal(x, decimal_dps, f"J stratum {r}")
                for r, x in enumerate(raw_j))
            denominator = _recorded_decimal(
                raw_denominator, decimal_dps, "denominator")
            numerator = _recorded_decimal(
                raw_numerator, decimal_dps, "numerator")
        except Exception as exc:
            raise ValueError("malformed Decimal normalizer") from exc
        if (not denominator.is_finite() or not numerator.is_finite() or
                denominator <= 0 or numerator <= 0):
            raise ValueError("base forms must be finite and positive")
        if any(not x.is_finite() or x <= 0 for x in i_values + j_values):
            raise ValueError("every active stratum normalizer must be positive")
        i_sum = sum(i_values)
        j_sum = sum(j_values)
        relative_i_residual = abs(i_sum / denominator - 1)
        relative_j_residual = abs(j_scale_to_numerator * j_sum / numerator - 1)
        # Each list contains 16 separately rounded Decimal contractions.  This
        # deliberately loose multiple of their recorded ulp is still dozens
        # of orders below any discovery uncertainty.
        residual_limit = Decimal(64).scaleb(-(decimal_dps - 2))
        if relative_i_residual > residual_limit:
            raise ArithmeticError("I stratum normalizers do not sum to I0")
        if relative_j_residual > residual_limit:
            raise ArithmeticError("J stratum normalizers do not sum to 48J0")
        i_weights = tuple(x / i_sum for x in i_values)
        j_weights = tuple(x / j_sum for x in j_values)
        return {
            "path": str(path),
            "sha256": observed_sha256,
            "decimal_dps": decimal_dps,
            "prefix": prefix,
            "j_scale_to_numerator": j_scale_to_numerator,
            "i_values": i_values,
            "j_values": j_values,
            "denominator": denominator,
            "numerator": numerator,
            "base_quotient": numerator / denominator,
            "relative_i_residual": relative_i_residual,
            "relative_j_residual": relative_j_residual,
            "residual_limit": residual_limit,
            "i_weights": i_weights,
            # Multiplying every J stratum by the same factor does not alter
            # its normalized conditional weight, but the factor is checked
            # above before normalization so incompatible producer schemas
            # cannot silently agree.
            "j_weights": j_weights,
        }
