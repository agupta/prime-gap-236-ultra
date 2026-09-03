#!/usr/bin/env python3
"""Independent exact/static audit of the three recovered-action band trials.

No capped support integral is evaluated.  The full-simplex preconditioner is
rebuilt with Fraction arithmetic from the independently audited monomial
orbit product, rather than importing the producer's Decimal solver or band
trial code.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from fractions import Fraction as Q
from pathlib import Path

HERE = Path(__file__).resolve().parent
PG = HERE.parents[1]
sys.path.insert(0, str(PG))

from verify.exact_capped_certificate import monomial_product, orbit_size  # noqa: E402


SB = PG / "agents/structural-basis"
EI = PG / "agents/exact-integrator"
PATHS = {
    "source": EI / "results/hb_c10_fullsimplex_noones_D12.json",
    "bands": SB / "results/c10_D12_degree_bands.json",
    "raw": SB / "results/c10_D12_band_sparse_gradient_mp100.json",
    "recovery": SB / "results/c10_D12_band_sparse_gradient_recovered_v2.json",
    "manifest": SB / "results/c10_D12_band_trials_manifest_v2.json",
    "near5": SB / "results/c10_D12_h12_near_5pct_v2.json",
    "near10": SB / "results/c10_D12_h12_near_10pct_v2.json",
    "near20": SB / "results/c10_D12_h12_near_20pct_v2.json",
    "producer": SB / "code/propose_band_trials.py",
    "recovery_code": SB / "code/recover_band_gradient.py",
    "line_search": SB / "code/band_line_search.py",
    "exact_geometry": PG / "verify/exact_capped_certificate.py",
}
SHAS = {
    "source": "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
    "bands": "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9",
    "raw": "0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d",
    "recovery": "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43",
    "manifest": "2a14bfc229ca56e279006c7fb3ee11b0663b5558f0f02aa7c46f8e26e5fcfc87",
    "near5": "c43fe29367311383dceda07103fa87ebb2168f53793f1ed6a24a79e6144314c5",
    "near10": "5cc0d13fc4d549983badca22e0c04b5177b77c3ce65b72527e04f9092256bc94",
    "near20": "ada77e63b32c3eb3e80708543acfc7bf709f0e3cab03a5bc68d313d94ed4c3dc",
    "producer": "c330855d0c42e5be55be7759714322149b4fa1fdde263ca7d7160315397a704e",
    "recovery_code": "9342fa3f6d8157a4d9b8603a20bb0527b7f47087a5aa3c9d39aebef892f9fee5",
    "line_search": "f5acf5f3b5a0c87f65175b724acafaf805dee40f43039e5b9300d2b0b6758f09",
    "exact_geometry": "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
}
TARGETS = {
    "h12_near_5pct": Q(1, 20),
    "h12_near_10pct": Q(1, 10),
    "h12_near_20pct": Q(1, 5),
}


def fail(message):
    raise RuntimeError(message)


def require(condition, message):
    if not condition:
        fail(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def duplicate_object(pairs):
    answer = {}
    for key, value in pairs:
        require(key not in answer, f"duplicate JSON key {key!r}")
        answer[key] = value
    return answer


def reject_constant(token):
    fail(f"nonfinite JSON constant {token}")


def load(name):
    path = PATHS[name]
    require(digest(path) == SHAS[name], f"SHA mismatch at {name}")
    return json.loads(path.read_bytes(), object_pairs_hook=duplicate_object,
                      parse_constant=reject_constant)


def label(value):
    require(isinstance(value, list) and len(value) == 2 and
            type(value[0]) is int and isinstance(value[1], list) and
            all(type(x) is int for x in value[1]), "malformed basis label")
    return value[0], tuple(value[1])


def exact_median(values):
    ordered = sorted(values)
    n = len(ordered)
    return ordered[n // 2] if n % 2 else \
        (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def build_band_map(source, bands):
    labels = [label(x) for x in source["basis"]]
    coefficients = [Q(x) for x in source["rational_vector"]]
    require(len(labels) == len(coefficients) == 272 and
            len(set(labels)) == 272, "source label/vector dimension")
    require(bands.get("source_sha256") == SHAS["source"] and
            bands.get("compressed_basis_dimension") == 20 and
            bands.get("expanded_term_count") == 272,
            "band provenance/dimension")
    blocks = []
    theta0 = []
    for item in bands["core"]:
        blocks.append({label(item["label"]): Q(1)})
        theta0.append(Q(item["coefficient"]))
    for degree in sorted(bands["bands"], key=int):
        block = {label(item["label"]): Q(item["coefficient"])
                 for item in bands["bands"][degree]}
        require(len(block) == len(bands["bands"][degree]),
                "duplicate band label")
        blocks.append(block)
        theta0.append(Q(1))
    require(len(blocks) == len(theta0) == 20, "compressed map dimension")
    by_label = {}
    for owner, block in enumerate(blocks):
        for basis_label, weight in block.items():
            require(basis_label not in by_label, "overlapping band ownership")
            by_label[basis_label] = (owner, weight)
    require(set(by_label) == set(labels), "band map is not a partition")
    owners = [by_label[x][0] for x in labels]
    weights = [by_label[x][1] for x in labels]
    require([weights[i] * theta0[owners[i]] for i in range(272)] == coefficients,
            "band map does not reconstruct source")
    return labels, coefficients, owners, weights, theta0


def expand(theta, owners, weights):
    require(len(theta) == 20, "compressed vector length")
    return [weights[i] * theta[owners[i]] for i in range(272)]


def build_exact_preconditioner(labels, owners, weights):
    """Independent Fraction reconstruction of the 20x20 full-simplex I."""
    k = 48
    alpha = Q(79247, 300000)
    matrix = [[Q(0) for _ in range(20)] for _ in range(20)]
    moments = {}

    def moment(part, residual):
        key = (part, residual)
        if key in moments:
            return moments[key]
        angular = math.prod(math.factorial(x) for x in part)
        degree0 = sum(part) + k
        value = Q(0)
        for c in range(residual + 1):
            value += (Q(math.comb(residual, c) * math.factorial(c) * angular,
                        math.factorial(degree0 + c)) *
                      (1 - alpha) ** (residual - c) *
                      alpha ** (degree0 + c))
        value *= orbit_size(k, part)
        moments[key] = value
        return value

    for i, (a, left) in enumerate(labels):
        oi, wi = owners[i], weights[i]
        for j in range(i + 1):
            b, right = labels[j]
            oj, wj = owners[j], weights[j]
            value = sum((multiplicity * moment(part, a + b)
                         for part, multiplicity in
                         monomial_product(left, right, k).items()), Q(0))
            value *= wi * wj
            if i == j:
                matrix[oi][oi] += value
            elif oi == oj:
                matrix[oi][oi] += 2 * value
            else:
                matrix[oi][oj] += value
                matrix[oj][oi] += value
    require(matrix == [list(row) for row in zip(*matrix)],
            "preconditioner is not symmetric")
    return matrix


def dot(left, right):
    return sum((x * y for x, y in zip(left, right)), Q(0))


def matvec(matrix, vector):
    return [dot(row, vector) for row in matrix]


def recursive_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from recursive_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from recursive_keys(item)


def main():
    for name in PATHS:
        require(digest(PATHS[name]) == SHAS[name], f"initial SHA {name}")
    source, bands, raw = load("source"), load("bands"), load("raw")
    recovery, manifest = load("recovery"), load("manifest")
    labels, _, owners, weights, theta0 = build_band_map(source, bands)
    require(raw["source_sha256"] == SHAS["source"] and
            raw["bands_sha256"] == SHAS["bands"] and
            raw["status"] == "rejected-degree-band-gradient-discovery" and
            raw["rigorous"] is False and raw["complete"] is True,
            "raw discovery bindings")
    require(recovery["raw_sha256"] == SHAS["raw"] and
            recovery["recovery_script_sha256"] == SHAS["recovery_code"] and
            recovery["rigorous"] is False and
            recovery["no_projected_trial_emitted"] is True,
            "recovery bindings")
    require([Q(x) for x in recovery["a_theta_exact_fraction_half"]] ==
            [Q(x) / 2 for x in raw["grad_denominator"]] and
            [Q(x) for x in recovery["b_theta_exact_fraction_half"]] ==
            [Q(x) / 2 for x in raw["grad_numerator"]],
            "recovered action halves")

    theta = [Q(x) for x in raw["theta"]]
    require(len(theta) == 20 and theta[19] == 1 and theta != theta0,
            "serialized-action base semantics")
    a_theta = [Q(x) for x in recovery["a_theta_exact_fraction_half"]]
    b_theta = [Q(x) for x in recovery["b_theta_exact_fraction_half"]]
    denominator, numerator = Q(raw["denominator"]), Q(raw["numerator"])
    quotient = numerator / denominator
    residual = [b - quotient * a for a, b in zip(a_theta, b_theta)]

    diag = manifest["base_action_diagnostics"]
    require(diag["precision"] == 230 and diag["second_precision"] == 270,
            "direction precision metadata")
    direction = [Q(x) for x in diag["direction"]]
    require(len(direction) == 20, "direction dimension")
    direction_pairing = dot(direction, residual)
    d_prime = 2 * dot(direction, a_theta)
    n_prime = 2 * dot(direction, b_theta)
    rayleigh_prime = (n_prime * denominator - numerator * d_prime) / \
        denominator ** 2
    euler_residual = dot(theta, residual)
    require(Q(diag["direction_dot_residual_exact"]) == direction_pairing > 0,
            "direction/residual pairing")
    require(Q(diag["denominator_first_derivative_exact"]) == d_prime and
            Q(diag["numerator_first_derivative_exact"]) == n_prime and
            Q(diag["rayleigh_first_derivative_exact"]) == rayleigh_prime > 0,
            "base derivative diagnostics")
    require(Q(diag["theta_dot_rayleigh_residual_exact"]) == euler_residual and
            Q(diag["theta_dot_residual_relative_to_numerator"]) ==
            abs(euler_residual / numerator), "Euler-residual diagnostics")

    p = build_exact_preconditioner(labels, owners, weights)
    ptheta, pdirection = matvec(p, theta), matvec(p, direction)
    theta_norm = dot(theta, ptheta)
    direction_norm = dot(direction, pdirection)
    orthogonality = abs(dot(theta, pdirection))
    projection = dot(theta, residual) / theta_norm
    projected_residual = [r - projection * pt
                          for r, pt in zip(residual, ptheta)]
    direction_scale = dot(direction, projected_residual) / direction_norm
    solve_error = max(abs(r - direction_scale * pd)
                      for r, pd in zip(projected_residual, pdirection)) / \
        max(abs(r) for r in projected_residual)
    normalized_orthogonality = orthogonality * orthogonality / theta_norm
    require(abs(direction_norm - 1) < Q(1, 10**175),
            "exact P norm check")
    require(normalized_orthogonality < Q(1, 10**350),
            "exact P orthogonality check")
    require(direction_scale > 0 and solve_error < Q(1, 10**175),
            "exact P-preconditioned residual check")

    ratios = [direction[i] / theta[i] for i in range(20)]
    c = -ratios[19]
    spread = max(abs(x - ratios[19]) for x in ratios)
    pole = 1 / c
    require(c > 0 and Q(diag["negative_H12_relative_direction"]) == c and
            Q(diag["relative_direction_spread"]) == spread and
            Q(diag["H12_projective_pole_step"]) == pole,
            "projective pole diagnostics")

    provenance = {
        "raw_gradient_sha256": SHAS["raw"],
        "recovery_artifact_sha256": SHAS["recovery"],
        "recovery_script_sha256": SHAS["recovery_code"],
        "trial_script_sha256": SHAS["producer"],
        "line_search_dependency_sha256": SHAS["line_search"],
        "source_sha256": SHAS["source"],
        "bands_sha256": SHAS["bands"],
        "no_finite_form_evaluation": True,
    }
    require(manifest["status"] ==
            "three-rational-band-trials-awaiting-scalar-selection" and
            manifest["rigorous"] is False and
            manifest["fresh_scalar_reevaluation_required"] is True and
            manifest["trial_count"] == 3 and
            manifest["provenance"] == provenance and
            manifest["statement"] ==
            "No finite-step denominator, numerator, or Rayleigh value has been computed for these trials.",
            "manifest status/provenance")

    expected_order = (("near5", "h12_near_5pct"),
                      ("near10", "h12_near_10pct"),
                      ("near20", "h12_near_20pct"))
    for manifest_row, (path_key, name) in zip(
            manifest["trials"], expected_order, strict=True):
        trial = load(path_key)
        target = TARGETS[name]
        detail = trial["trial"]
        require(manifest_row["name"] == name and
                manifest_row["sha256"] == SHAS[path_key] and
                Path(manifest_row["path"]).name == PATHS[path_key].name,
                f"manifest row {name}")
        require(trial["status"] == "recovered-action-rational-band-trial" and
                trial["rigorous"] is False and
                trial["fresh_scalar_reevaluation_required"] is True and
                trial["finite_form_value_claimed"] is False and
                trial["k"] == 48 and trial["provenance"] == provenance,
                f"trial gates {name}")
        require([label(x) for x in trial["basis"]] == labels,
                f"basis {name}")
        step = target / (spread + target * c)
        require(0 < step < pole and Q(detail["exact_step_t"]) == step and
                detail["projective_pole_side"] == "near",
                f"near-side step {name}")
        unscaled = [theta[i] + step * direction[i] for i in range(20)]
        scale = 1 / unscaled[19]
        compressed = [scale * x for x in unscaled]
        expanded = expand(compressed, owners, weights)
        require(Q(detail["exact_H12_gauge_scale"]) == scale and
                compressed[19] == 1 and detail["H12_coordinate"] == "1",
                f"gauge {name}")
        require([Q(x) for x in trial["compressed_theta"]] == compressed and
                [Q(x) for x in trial["rational_vector"]] == expanded,
                f"exact expansion {name}")
        base_expanded = expand(theta, owners, weights)
        raw_changes = [abs((unscaled[owners[i]] - theta[owners[i]]) /
                           theta[owners[i]]) for i in range(272)]
        normalized_changes = [abs((expanded[i] - base_expanded[i]) /
                                  base_expanded[i]) for i in range(272)]
        compressed_changes = [abs((compressed[i] - theta[i]) / theta[i])
                              for i in range(20)]
        exact_stats = {
            "raw_path_max_relative_coefficient_change": max(raw_changes),
            "raw_path_median_relative_coefficient_change":
                exact_median(raw_changes),
            "normalized_max_relative_coefficient_change":
                max(normalized_changes),
            "normalized_median_relative_coefficient_change":
                exact_median(normalized_changes),
            "compressed_max_relative_coordinate_change":
                max(compressed_changes),
            "compressed_median_relative_coordinate_change":
                exact_median(compressed_changes),
        }
        require(max(normalized_changes) == max(compressed_changes) == target,
                f"attained target {name}")
        for key, value in exact_stats.items():
            require(Q(detail[key]) == value, f"statistic {key} at {name}")
        displacement = [x - y for x, y in zip(compressed, theta)]
        actual_derivative = 2 * dot(displacement, residual) / denominator
        raw_derivative = scale * step * rayleigh_prime
        require(Q(detail["normalized_trial_first_derivative_exact"]) ==
                actual_derivative > 0 and
                Q(detail["scaled_raw_path_first_derivative_exact"]) ==
                raw_derivative > 0, f"trial derivatives {name}")
        keys = set(recursive_keys(trial))
        require(not {"denominator", "numerator", "quotient", "margin"} & keys,
                f"finite form field leaked into {name}")
        require("first-order changes" in detail["note"] and
                "not finite-step form evaluations" in detail["note"],
                f"derivative caveat {name}")

    for name in PATHS:
        require(digest(PATHS[name]) == SHAS[name], f"ending SHA {name}")
    print("BAND TRIAL V2 AUDIT PASS (discovery-only; no finite form value)")
    print(f"exact_P_norm_error={abs(direction_norm-1)}")
    print(f"exact_P_orthogonality_squared_over_theta_norm={normalized_orthogonality}")
    print(f"exact_preconditioned_residual_relative_error={solve_error}")
    print(f"rayleigh_first_derivative={rayleigh_prime}")
    print(f"exact_P_norm_error_float={float(abs(direction_norm-1)):.6e}")
    print("exact_P_orthogonality_squared_over_theta_norm_float="
          f"{float(normalized_orthogonality):.6e}")
    print("exact_preconditioned_residual_relative_error_float="
          f"{float(solve_error):.6e}")


if __name__ == "__main__":
    main()
