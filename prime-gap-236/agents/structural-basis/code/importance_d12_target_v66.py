#!/usr/bin/env python3
"""V6.6-bound unmultiplied D12 target, identity dry-run only.

This module binds the 272-label D12 base and proves the exact multiplier-one
identity for the v6.6 transform.  It cannot create a launch gate until an
independent v6.6 calibration audit pass is pinned.  It runs no chain and
computes no new sieve quotient.
"""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path

import importance_d12_target_v6 as core
import importance_d4_calibration_v66 as d4


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
CHANNEL_LABELS = ("1", "L", "Z", "L^2", "LZ", "Z^2")

# Filled only after a separately frozen independent v6.6 AUDIT PASS.  An
# empty map deliberately blocks target-gate generation and every screen.
V66_AUDIT_ARTIFACT_HASHES = {}


def sha256_canonical(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode()).hexdigest()


def validate_v66_audit_artifacts():
    if not V66_AUDIT_ARTIFACT_HASHES:
        raise ValueError("independent v6.6 PASS artifacts are not pinned")
    for relative, expected in V66_AUDIT_ARTIFACT_HASHES.items():
        if core.sha256_file(REPO_ROOT / relative) != expected:
            raise ValueError(f"v6.6 audit artifact changed: {relative}")
    return True


def exact_identity_package(repo_root=REPO_ROOT):
    """Prove exactly that transformed base coefficients give multiplier one."""
    repo_root = Path(repo_root).resolve()
    source = core.validate_source_equivalence(repo_root)
    normalizers = core.load_d12_normalizers(repo_root)
    adapter = core.D12WhitenedMultiplierDensity(repo_root)
    transform_sha = d4.v65.v64.v63.v62.v61.v6.TRANSFORM_SHA256
    if (adapter.whitening_transform_sha256 != transform_sha or
            adapter.dimension != 96 or adapter.k != 48 or
            tuple(adapter.strata) != tuple(range(16))):
        raise ValueError("D12 adapter transform/dimension differs from v6.6")
    transform = adapter.whitening_transform_exact
    transformed = tuple(adapter.base_constant_weights_exact)
    if len(transform) != 96 or len(transformed) != 96 or any(
            len(row) != 96 for row in transform):
        raise ValueError("D12 exact transform has wrong dimensions")
    old = tuple(sum(transform[i][j] * transformed[j] for j in range(96))
                for i in range(96))
    wanted = tuple(Fraction(int(i % 6 == 0)) for i in range(96))
    if old != wanted:
        raise ArithmeticError("T times transformed base is not multiplier one")
    if (sum(normalizers["i_weights"], Fraction(0)) != 1 or
            sum(normalizers["j_weights"], Fraction(0)) != 1):
        raise ArithmeticError("D12 stratum normalizers do not sum exactly")
    labels = [[r, channel] for r in range(16)
              for channel in CHANNEL_LABELS]
    identity = {
        "labels": labels,
        "transformed_rational_vector": [str(value) for value in transformed],
        "old_rational_vector": [str(value) for value in old],
        "old_vector_is_16_tagged_constants": True,
        "exact_transform_sha256": adapter.whitening_transform_sha256,
    }
    return {
        "identity": identity,
        "identity_sha256": sha256_canonical(identity),
        "normalizers": normalizers,
        "source": source,
        "adapter": adapter,
    }


D12WhitenedMultiplierDensity = core.D12WhitenedMultiplierDensity
load_d12_normalizers = core.load_d12_normalizers
validate_source_equivalence = core.validate_source_equivalence
EXPECTED_HASHES = core.EXPECTED_HASHES
