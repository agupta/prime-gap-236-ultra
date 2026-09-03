#!/usr/bin/env python3
"""Exact D4 oracle matrices for importance-Ritz calibration.

This module only reads the independently reconstructed exact stratum-
quadratic artifact.  It converts its unnormalised ``1,L,Z,...`` forms into
the dimensionless expectation matrices appearing in equations (1)--(2) of
``IMPORTANCE-RITZ-DESIGN.md``.  It performs no stochastic calculation and
does not certify a D12 quotient.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from fractions import Fraction
from pathlib import Path


CHANNEL_POWERS = (
    (0, 0),
    (1, 0),
    (0, 1),
    (2, 0),
    (1, 1),
    (0, 2),
)

PINNED_ORACLE_SHA256 = \
    "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86"
EXPECTED_STRATA = 16
_CANONICAL_J_KEY = re.compile(
    r"^\(\(([0-9]+), ([0-9]+)\), \(([0-9]+), ([0-9]+)\)\)$")


def _reject_json_constant(_value):
    raise ValueError("nonfinite JSON token in exact oracle")


def _finite_json_float(token):
    value = float(token)
    if not math.isfinite(value):
        raise ValueError("overflowed JSON float in oracle metadata")
    return value


def _strict_json_bytes(data):
    if not isinstance(data, bytes) or len(data) > 64_000_000:
        raise ValueError("oracle must be bounded JSON bytes")

    def pairs_hook(pairs):
        answer = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in answer:
                raise ValueError("duplicate or non-string JSON key in oracle")
            answer[key] = value
        return answer

    return json.loads(
        data.decode("utf-8"), object_pairs_hook=pairs_hook,
        # The pinned producer records benign timing/solver metadata as JSON
        # floats.  Exact mathematical fields are separately required below
        # to be canonical rational strings.
        parse_float=_finite_json_float, parse_constant=_reject_json_constant)


def _fraction(value, name="oracle scalar"):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a canonical rational string")
    if len(value) > 100_000:
        raise ValueError(f"{name} is unreasonably large")
    try:
        answer = Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{name} is not a rational string") from error
    if str(answer) != value:
        raise ValueError(f"{name} is not canonical")
    return answer


def _zero_matrix(dimension):
    return [[Fraction(0) for _ in range(dimension)]
            for _ in range(dimension)]


def _expected_j_keys():
    answer = {}
    for r in range(EXPECTED_STRATA):
        for a in range(len(CHANNEL_POWERS)):
            for b in range(a, len(CHANNEL_POWERS)):
                key = f"(({r}, {a}), ({r}, {b}))"
                answer[key] = ((r, a), (r, b))
    for r in range(EXPECTED_STRATA - 1):
        for a in range(len(CHANNEL_POWERS)):
            for b in range(len(CHANNEL_POWERS)):
                key = f"(({r}, {a}), ({r + 1}, {b}))"
                answer[key] = ((r, a), (r + 1, b))
    return answer


EXPECTED_J_KEYS = _expected_j_keys()


def _parse_exact_expectation_oracle_bytes(data, source_path, source_sha256):
    """Validate oracle bytes and construct the exact normalized matrices.

    This private parser is exposed to the hostile test suite so semantic
    mutation tests do not have to forge the public byte pin.  Production
    callers must use :func:`load_exact_expectation_oracle`.  The source
    stores I as one 6-by-6 block per stratum and the unscaled J upper
    triangle.  We insert factor 48 and divide channels by alpha powers.
    """
    raw = _strict_json_bytes(data)
    if not isinstance(raw, dict):
        raise ValueError("oracle top level must be an object")
    if raw.get("rigorous_forms") is not True:
        raise ValueError("oracle artifact does not assert rigorous forms")
    if isinstance(raw.get("k"), bool) or raw.get("k") != 48:
        raise ValueError("oracle artifact is not the k=48 calculation")
    raw_powers = raw.get("channel_powers")
    if (not isinstance(raw_powers, list) or
            any(not isinstance(pair, list) or len(pair) != 2 or
                any(isinstance(x, bool) or not isinstance(x, int)
                    for x in pair) for pair in raw_powers) or
            raw_powers != [list(x) for x in CHANNEL_POWERS]):
        raise ValueError("unexpected channel order")

    parameters = raw.get("parameters")
    parameter_keys = {
        "alpha", "delta", "eta", "beta1", "beta2", "beta3plus"}
    if not isinstance(parameters, dict) or set(parameters) != parameter_keys:
        raise ValueError("unexpected parameter schema")
    exact_parameters = {
        key: _fraction(parameters[key], f"parameter {key}")
        for key in sorted(parameter_keys)
    }
    alpha = exact_parameters["alpha"]
    delta = exact_parameters["delta"]
    eta = exact_parameters["eta"]
    betas = (exact_parameters["beta1"], exact_parameters["beta2"],
             exact_parameters["beta3plus"])
    if not (alpha > 0 and 0 <= eta <= alpha and delta >= 0 and
            all(beta > 0 for beta in betas)):
        raise ValueError("invalid exact support parameters")

    raw_i_blocks = raw.get("i_blocks")
    expected_stratum_keys = {str(r) for r in range(EXPECTED_STRATA)}
    if not isinstance(raw_i_blocks, dict) or \
            set(raw_i_blocks) != expected_stratum_keys:
        raise ValueError("I blocks must contain exactly strata 0 through 15")
    strata = list(range(EXPECTED_STRATA))
    channel_count = len(CHANNEL_POWERS)
    dimension = len(strata) * channel_count
    i_matrix = _zero_matrix(dimension)
    b48_matrix = _zero_matrix(dimension)

    for r in strata:
        block = raw_i_blocks[str(r)]
        if (not isinstance(block, list) or len(block) != channel_count or
                any(not isinstance(row, list) or len(row) != channel_count
                    for row in block)):
            raise ValueError("malformed I block")
        for a in range(channel_count):
            da = sum(CHANNEL_POWERS[a])
            for b in range(channel_count):
                db = sum(CHANNEL_POWERS[b])
                i_matrix[r * channel_count + a][r * channel_count + b] = \
                    _fraction(block[a][b], f"I[{r},{a},{b}]") / \
                    alpha ** (da + db)
        for a in range(channel_count):
            for b in range(channel_count):
                if block[a][b] != block[b][a]:
                    raise ValueError("I block is not exactly symmetric")

    raw_j_entries = raw.get("j_entries")
    if not isinstance(raw_j_entries, dict) or \
            set(raw_j_entries) != set(EXPECTED_J_KEYS):
        raise ValueError(
            "J entries must be the complete canonical diagonal/adjacent set")
    for encoded, ((r, a), (s, b)) in EXPECTED_J_KEYS.items():
        if _CANONICAL_J_KEY.fullmatch(encoded) is None:
            raise AssertionError("internal noncanonical J key")
        value = raw_j_entries[encoded]
        i = r * channel_count + a
        j = s * channel_count + b
        scale_degree = sum(CHANNEL_POWERS[a]) + sum(CHANNEL_POWERS[b])
        entry = 48 * _fraction(value, f"J {encoded}") / alpha ** scale_degree
        b48_matrix[i][j] = entry
        b48_matrix[j][i] = entry

    # The unmultiplied F is the sum of the constant channel over all strata.
    constant_indices = [r * channel_count for r in strata]
    i0 = sum(i_matrix[i][i] for i in constant_indices)
    b0 = sum(b48_matrix[i][j]
             for i in constant_indices for j in constant_indices)
    if i0 <= 0 or b0 <= 0:
        raise ArithmeticError("base normalizers must be positive")

    e_i = [[entry / i0 for entry in row] for row in i_matrix]
    e_j = [[entry / b0 for entry in row] for row in b48_matrix]
    return {
        "path": str(source_path),
        "source_sha256": source_sha256,
        "k": 48,
        "alpha": alpha,
        "parameters": exact_parameters,
        "strata": tuple(strata),
        "channel_powers": CHANNEL_POWERS,
        "dimension": dimension,
        "I0": i0,
        "B0": b0,
        "base_quotient": b0 / i0,
        "I": i_matrix,
        "B48": b48_matrix,
        "E_I": e_i,
        "E_J": e_j,
    }


def load_exact_expectation_oracle(path):
    """Load the single byte-pinned exact C10 D4 oracle artifact."""
    path = Path(path)
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != PINNED_ORACLE_SHA256:
        raise ValueError("exact oracle SHA-256 mismatch")
    return _parse_exact_expectation_oracle_bytes(data, path, digest)


def principal_indices(strata, total_degree):
    """Indices for all requested strata and channels of degree at most D."""
    if isinstance(total_degree, bool) or not isinstance(total_degree, int) or \
            total_degree not in (0, 1, 2):
        raise ValueError("D4 calibration degree must be 0, 1, or 2")
    strata = tuple(strata)
    if any(isinstance(r, bool) or not isinstance(r, int) or
           not 0 <= r < EXPECTED_STRATA for r in strata):
        raise ValueError("strata must be exact integers from 0 through 15")
    if len(set(strata)) != len(strata):
        raise ValueError("strata must not repeat")
    channels = [i for i, powers in enumerate(CHANNEL_POWERS)
                if sum(powers) <= total_degree]
    return tuple(r * len(CHANNEL_POWERS) + channel
                 for r in strata for channel in channels)


def principal_submatrix(matrix, indices):
    return [[matrix[i][j] for j in indices] for i in indices]
