#!/usr/bin/env python3
"""Static identity audit for the transferred C10 D12 affine candidate.

This checker only parses pinned inputs and invokes the two target loaders.  It
does not construct orbit products, integrate a face, read a matrix, or consume
a discovery quotient.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from fractions import Fraction as Q
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import verify.check_c10_d12_affine_dyadic as grouped  # noqa: E402
import verify.check_c10_d12_affine_exact as exact  # noqa: E402
import verify.check_c10_d12_affine_independent_dyadic as independent  # noqa: E402
from verify.exact_affine_multiplier import (  # noqa: E402
    load_exact_affine_multiplier,
)
from verify.exact_capped_certificate import (  # noqa: E402
    TARGET_C10_D12,
    TARGET_ORDERED_PAYLOAD_SHA256,
    expected_labels,
    ordered_payload_sha256,
)


PROOF = ROOT / "agents/structural-basis/PROOF-DRAFT-C10.md"
SOURCE = (ROOT / "agents/exact-integrator/results/"
          "hb_c10_fullsimplex_noones_D12.json")
BASE = (ROOT / "agents/exact-integrator/results/"
        "hb_c10_fullsimplex_noones_D12_integer_scaled.json")
AFFINE = (ROOT / "agents/exact-integrator/results/"
          "c10_stratum_linear_cappedopt_D4_exact.json")
D12_STAGE = (ROOT / "agents/exact-integrator/results/"
             "c10_D12_stratum_linear_decimal100_cut11.json.I-stage.json")

PINNED = {
    PROOF:
        "30532156254193456faa6f8d1c9e6ac53395d7a46d633410bb749a0557773c2f",
    SOURCE:
        "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
    BASE:
        "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93",
    AFFINE:
        "ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158",
    ROOT / "verify/check_c10_d12_affine_dyadic.py":
        "bf0ad4b3c1288c1d2df67e92f9ebe9e63613b9dcd2892c3f96522217d920677b",
    ROOT / "verify/check_c10_d12_affine_exact.py":
        "5514f63159ad74e54142cf1db2d88a9c69f552cad3d253cd50ca66452cf2784e",
    ROOT / "verify/check_c10_d12_affine_independent_dyadic.py":
        "7e2ed20a68e3c3e95a9566b32cae3d403949a79a3a81adfa61b8dab833b640b9",
    ROOT / "verify/exact_affine_multiplier.py":
        "9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e",
    ROOT / "agents/exact-integrator/stratum_linear_transfer_decimal.py":
        "91d1b4ad0c675ccfe36100166bee20bb4007af49e1d0cfe618c8c82c8857f354",
    ROOT / "agents/exact-integrator/stratum_linear.py":
        "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
}


class IdentityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(payload) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IdentityError(message)


def lcm_denominators(values) -> int:
    answer = 1
    for value in values:
        answer = math.lcm(answer, value.denominator)
    return answer


def main() -> None:
    for path, expected in PINNED.items():
        require(sha256(path) == expected, f"byte SHA mismatch: {path}")

    proof = PROOF.read_text(encoding="utf-8")
    section = proof.split(
        "## 10. Named finite-dimensional placeholder `[CERT-C10-48]`", 1
    )[1].split("## 11.", 1)[0]
    for required in (
        "hb_c10_fullsimplex_noones_D12_integer_scaled.json",
        "c10_stratum_linear_cappedopt_D4_exact.json",
        "R(t)=\\#\\{i:t_i>\\delta\\}",
        "L(t)=\\sum_{t_i>\\delta}t_i",
        "Z(t)=\\sum_{t_i\\leq\\delta}t_i",
        "b_r=c_r=0$ for $r>11",
        "48J(F;\\delta,A,B,\\varepsilon_s)-I(F;\\delta,A,B,\\varepsilon_s)",
    ):
        require(required in section, f"proof Section 10 identity token absent: {required}")

    source_raw = json.loads(SOURCE.read_bytes())
    base_raw = json.loads(BASE.read_bytes())
    affine_raw = json.loads(AFFINE.read_bytes())
    stage_raw = json.loads(D12_STAGE.read_bytes())

    require(ordered_payload_sha256(source_raw) ==
            TARGET_ORDERED_PAYLOAD_SHA256,
            "original source ordered payload mismatch")
    require(source_raw["k"] == base_raw["k"] == affine_raw["k"] == 48,
            "candidate k is not uniformly 48")
    require(source_raw["degree"] == base_raw["degree"] == 12,
            "base degree mismatch")
    require(source_raw["basis_dimension"] ==
            base_raw["basis_dimension"] == 272,
            "base dimension mismatch")
    require(source_raw["basis"] == base_raw["basis"],
            "source/scaled ordered basis differs")
    require(len(source_raw["rational_vector"]) ==
            len(base_raw["rational_vector"]) == 272,
            "source/scaled vector dimension differs")

    labels = [(int(a), tuple(int(x) for x in partition))
              for a, partition in base_raw["basis"]]
    require(len(labels) == len(set(labels)) == 272,
            "base labels are not 272 distinct labels")
    require(set(labels) == expected_labels(12, 48),
            "base labels do not equal the complete no-ones D12 set")
    source_coefficients = [Q(value)
                           for value in source_raw["rational_vector"]]
    base_coefficients = [Q(value)
                         for value in base_raw["rational_vector"]]
    base_lcm = lcm_denominators(source_coefficients)
    require(str(base_lcm) == base_raw["integer_scaling"][
                "least_common_denominator"],
            "base LCM metadata differs from the 272 source coefficients")
    for index, (source_value, scaled_value) in enumerate(
            zip(source_coefficients, base_coefficients, strict=True)):
        require(source_value * base_lcm == scaled_value,
                f"base coefficient scaling mismatch at ordered index {index}")

    expected_affine_labels = [[r, channel]
                              for r in range(16)
                              for channel in ("1", "L", "Z")]
    require(affine_raw["linear_labels"] == expected_affine_labels,
            "raw affine labels are not 16 canonical 1/L/Z triples")
    raw_affine = [Q(value) for value in affine_raw["rational_vector"]]
    require(len(raw_affine) == 48, "raw affine vector does not have 48 entries")
    effective_triples = []
    overwritten = []
    for r in range(16):
        a, b, c = raw_affine[3 * r:3 * r + 3]
        if r > 11:
            if b:
                overwritten.append((r, "L", b))
            if c:
                overwritten.append((r, "Z", c))
            b = c = Q(0)
        effective_triples.append((a, b, c))
    require(len(overwritten) == 8,
            "cutoff 11 did not overwrite exactly eight nonzero raw channels")

    params = TARGET_C10_D12
    expected_support = {
        "alpha": "79247/300000",
        "delta": "1/100",
        "eta": "76247/300000",
        "beta1": "3/20",
        "beta2": "3/20",
        "beta3plus": "97/625",
    }
    actual_support = {
        "alpha": str(params.alpha), "delta": str(params.delta),
        "eta": str(params.eta), "beta1": str(params.beta1),
        "beta2": str(params.beta2), "beta3plus": str(params.beta3plus),
    }
    require(actual_support == expected_support,
            "target support parameters differ from C10")
    require(affine_raw["parameters"] == expected_support,
            "raw affine artifact support differs from C10")
    require(stage_raw["parameters"] == expected_support and
            stage_raw["linear_cutoff"] == 11 and
            stage_raw["input_sha256"] == grouped.BASE_SHA256,
            "D12 affine I-stage identity metadata differs")

    # The full-simplex source support is discovery metadata, not candidate
    # support.  Check that the target loaders do not accidentally import it.
    require(source_raw["parameters"]["beta1"] == "79247/300000",
            "unexpected discovery-source support metadata")
    require(source_raw["parameters"] != expected_support,
            "source unexpectedly ceased to be the documented full-simplex discovery")

    grouped_labels, grouped_coefficients, grouped_affine, grouped_affine_lcm, \
        grouped_base_lcm = grouped.load_exact_inputs()
    exact_terms, exact_affine, exact_affine_lcm, exact_base_lcm = \
        exact.load_scaled_inputs()

    independent_cutoff = independent.common_metadata(
        {}, 512, 96, 1, 1, False, (16, 16))["linear_cutoff"]
    require(grouped.LINEAR_CUTOFF == exact.LINEAR_CUTOFF ==
            independent_cutoff == 11,
            "target loader cutoff constants differ")
    for module in (grouped, exact, independent):
        require(module.BASE_PATH == BASE and module.AFFINE_PATH == AFFINE and
                module.SOURCE_PATH == SOURCE,
                f"target loader consumes different candidate files: {module.__name__}")
        require(module.BASE_SHA256 == PINNED[BASE] and
                module.AFFINE_SHA256 == PINNED[AFFINE] and
                module.SOURCE_VECTOR_SHA256 == PINNED[SOURCE],
                f"target loader input hashes differ: {module.__name__}")
    require(independent.load_scaled_inputs is exact.load_scaled_inputs,
            "independent dyadic driver no longer delegates to frozen exact loader")

    require(grouped_labels == labels == list(exact_terms),
            "272 ordered labels differ between target loaders")
    for index, label in enumerate(labels):
        require(grouped_coefficients[index] == base_coefficients[index] ==
                exact_terms[label],
                f"target loader coefficient mismatch at ordered index {index}")
    require(grouped_base_lcm == exact_base_lcm == base_lcm,
            "target loader base LCMs differ")

    effective = load_exact_affine_multiplier(
        AFFINE, params, PINNED[AFFINE], linear_cutoff=11)
    require(effective.coefficients == tuple(effective_triples),
            "effective cutoff table differs from the declared candidate")
    effective_lcm = lcm_denominators(
        value for triple in effective_triples for value in triple)
    require(grouped_affine_lcm == exact_affine_lcm == effective_lcm,
            "target loader affine LCMs differ")
    expected_integer_triples = tuple(
        tuple(value * effective_lcm for value in triple)
        for triple in effective_triples
    )
    require(grouped_affine.coefficients == exact_affine.coefficients ==
            expected_integer_triples,
            "target loader effective affine triples differ")
    require(all(grouped_affine.at(r)[1:] == (0, 0)
                for r in range(12, 16)),
            "a target loader retained an L/Z channel above cutoff 11")
    require(all(grouped_affine.at(r)[0] != 0 for r in range(12, 16)),
            "a target loader projected away a high-count constant channel")

    # Exact support feasibility: R=15 remains possible and R=16 does not.
    require(params.beta(15) - 15 * params.delta == Q(13, 2500),
            "R=15 cap reserve mismatch")
    require(params.beta(16) - 16 * params.delta == Q(-3, 625),
            "R=16 exclusion margin mismatch")

    payload = {
        "status": "AFFINE CANDIDATE IDENTITY AUDIT PASS",
        "k": 48,
        "support": expected_support,
        "base_dimension": 272,
        "base_ordered_payload_sha256": TARGET_ORDERED_PAYLOAD_SHA256,
        "scaled_base_file_sha256": PINNED[BASE],
        "scaled_base_identity_sha256": canonical_sha({
            "basis": base_raw["basis"],
            "rational_vector": base_raw["rational_vector"],
        }),
        "base_lcm_bits": base_lcm.bit_length(),
        "affine_source_file_sha256": PINNED[AFFINE],
        "raw_affine_identity_sha256": canonical_sha({
            "linear_labels": affine_raw["linear_labels"],
            "rational_vector": affine_raw["rational_vector"],
        }),
        "linear_cutoff": 11,
        "effective_affine_triples": 16,
        "effective_nominal_channels": 40,
        "effective_nonzero_channels": sum(
            value != 0 for triple in effective_triples for value in triple),
        "overwritten_raw_channels": [
            [r, channel, str(value)] for r, channel, value in overwritten
        ],
        "effective_affine_identity_sha256": canonical_sha([
            [str(value) for value in triple] for triple in effective_triples
        ]),
        "effective_affine_lcm_bits": effective_lcm.bit_length(),
        "grouped_and_independent_loaders_bitwise_identical": True,
        "target_integration_performed": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (IdentityError, AttributeError, KeyError, TypeError, ValueError,
            OSError) as exc:
        raise SystemExit(f"AFFINE CANDIDATE IDENTITY AUDIT FAIL: {exc}") from exc
