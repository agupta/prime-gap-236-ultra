#!/usr/bin/env python3
"""Fail-closed D18 inner-coordinate adapter for the active25 shell engine.

This module changes only the fixed inner polynomial.  The support objects,
right-count tagging, four cross channels, grouped recurrence, and common-r
sharding are delegated to the frozen D16/v2 implementation.  It has no target
execution CLI; the sole CLI action is a read-only preflight.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
V2 = HERE / "frontier_active25_inner_d16_staged_v2.py"
V2_TEST = HERE / "test_frontier_active25_inner_d16_staged_v2.py"
CERT = REPO / (
    "agents/exact-integrator/results/"
    "aquarter_fullsimplex_k48_B18_refined_exact.json")
RADIAL = REPO / "results/wide_c722_B18_inner_radial_two_amplitudes_exact.json"
BASELINE = REPO / "results/aquarter_B18_cachefree_baseline_check.json"
RUN_BASIS = REPO / "agents/exact-integrator/run_basis.py"
INTEGRATOR = REPO / "agents/exact-integrator/src/exact_integrator.py"
SCAN = HERE / "scan_bv_epsilon_fixed.py"

PINNED = {
    V2: "bb00675f722a843c0d87ef36e382aea812d6622c79da517e238b0146af9592dd",
    V2_TEST: "27fabdfa8e4f73820ca70af6189751d2e30acd7f699b580b9cd2cfdb625f10ed",
    CERT: "af6f1eb0d75bc59caf20cc82f79a3cb339be3ac7280af2afcad89eca0e31cf58",
    RADIAL: "d0e40966fc30dd4eb645b672f5b2aa631a50dbfbc4d60e02de48e9ef54e9ecb1",
    BASELINE: "44b7e97cca3134bf8594b24a6296e331b9b277991bce9777b7263ff216eba5fa",
    RUN_BASIS: "f660a30d8dd83f13459e0412ded1e28c7ec0864abb41ad04a396475a7905e1d4",
    INTEGRATOR: "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    SCAN: "96495079a18039a0a7b0522e83ac455cbe5ff144598fff6b382f2c2953958de9",
}

CERT_KEYS = {
    "basis", "cache_file_sha256", "cache_hits", "cache_misses", "degree",
    "denominator_positive", "discovery_rigorous", "exact_denominator",
    "exact_margin", "exact_numerator", "exact_quotient", "format",
    "integrator_sha256", "k", "margin_positive", "matrix_sha256",
    "parameters", "particular_vector_forms_rigorous", "power_trace",
    "rational_vector", "rationalization_significant_digits",
    "resume_iterations", "resume_precision", "run_basis_sha256",
    "seed_power_eigenvalue", "source_run_sha256",
}
RADIAL_KEYS = {
    "I_matrix", "R", "V", "baseline_RR_J_exact_match",
    "baseline_amplitudes_11_exact_match", "baseline_quotient_decimal",
    "basis_dimension", "certificate_sha256", "claim_scope",
    "decimal_discovery_eigenvalue", "decimal_precision",
    "denominator_positive", "exact_denominator", "exact_gain_decimal",
    "exact_margin", "exact_numerator", "exact_quotient",
    "exact_quotient_decimal", "format", "inner_I_fraction_decimal",
    "integrator_sha256", "k", "kJ_matrix", "margin_positive",
    "marginal_term_counts", "piecewise_function", "rational_amplitudes",
    "rationalization_significant_digits", "script_sha256",
}
BASELINE_KEYS = {
    "analytic_family", "analytic_note_sha256", "baseline_exact_match",
    "certificate_sha256", "claim_scope", "format", "integrator_sha256",
    "original_epsilon", "rows", "script_sha256", "winner_epsilon",
    "winner_exact_quotient", "winner_exact_quotient_decimal",
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def snapshots():
    result = {}
    for path, expected in PINNED.items():
        data = path.read_bytes()
        if sha256_bytes(data) != expected:
            raise RuntimeError(f"D18 adapter dependency changed: {path}")
        result[path] = data
    return result


_START = snapshots()
_SPEC = importlib.util.spec_from_file_location("active25_d18_adapter_v2", V2)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(V2)
v2 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = v2
_SPEC.loader.exec_module(v2)


def dependency_record():
    answer = {str(path.relative_to(REPO)): expected
              for path, expected in PINNED.items()}
    answer.update({str(path.relative_to(REPO)): expected
                   for path, expected in v2.PINNED.items()})
    answer.update(v2.core.require_pins())
    return dict(sorted(answer.items()))


def strict_sha(value, name):
    if (type(value) is not str or len(value) != 64 or
            any(c not in "0123456789abcdef" for c in value)):
        raise ValueError(f"{name} is not a canonical SHA-256")
    return value


def fraction(value, name):
    if type(value) is not str:
        raise ValueError(f"{name} is not a string Fraction")
    parsed = Q(value)
    if str(parsed) != value:
        raise ValueError(f"{name} is not canonical")
    return parsed


def finite_decimal(value, name):
    if type(value) is not str or not Decimal(value).is_finite():
        raise ValueError(f"{name} is not a finite Decimal string")
    return Decimal(value)


def strict_matrix(value, name):
    if (type(value) is not list or len(value) != 2 or
            any(type(row) is not list or len(row) != 2 for row in value)):
        raise ValueError(f"{name} is not a 2x2 matrix")
    return [[fraction(value[i][j], f"{name}[{i},{j}]")
             for j in range(2)] for i in range(2)]


def validate_payloads(cert, radial, baseline):
    if (type(cert) is not dict or set(cert) != CERT_KEYS or
            type(radial) is not dict or set(radial) != RADIAL_KEYS or
            type(baseline) is not dict or set(baseline) != BASELINE_KEYS):
        raise ValueError("D18 artifact top-level schema mismatch")

    expected_parameters = {
        "alpha": "103/400", "beta1": "103/400", "beta2": "103/400",
        "beta3plus": "103/400", "delta": "7/250", "eta": "97/400",
    }
    expected_basis = [[a, list(lam)]
                      for a, lam in v2.core.shell.ei.even_basis(18)]
    if (cert["format"] != "bv-even-exact-vector-v1" or cert["k"] != 48 or
            type(cert["k"]) is not int or cert["degree"] != 18 or
            type(cert["degree"]) is not int or
            cert["parameters"] != expected_parameters or
            cert["basis"] != expected_basis or len(expected_basis) != 471 or
            cert["integrator_sha256"] != PINNED[INTEGRATOR] or
            cert["run_basis_sha256"] != PINNED[RUN_BASIS] or
            cert["particular_vector_forms_rigorous"] is not True or
            cert["discovery_rigorous"] is not False or
            cert["denominator_positive"] is not True or
            cert["margin_positive"] is not False):
        raise ValueError("D18 certificate identity mismatch")
    for key in ("cache_file_sha256", "matrix_sha256", "source_run_sha256"):
        strict_sha(cert[key], f"certificate {key}")
    if (any(type(cert[key]) is not int or cert[key] < 0
            for key in ("cache_hits", "cache_misses", "resume_iterations",
                        "resume_precision", "rationalization_significant_digits")) or
            type(cert["rational_vector"]) is not list or
            len(cert["rational_vector"]) != 471):
        raise ValueError("D18 certificate count/vector mismatch")
    vector = tuple(fraction(x, f"D18 coefficient {i}")
                   for i, x in enumerate(cert["rational_vector"]))
    denominator = fraction(cert["exact_denominator"], "certificate denominator")
    numerator = fraction(cert["exact_numerator"], "certificate numerator")
    quotient = fraction(cert["exact_quotient"], "certificate quotient")
    margin = fraction(cert["exact_margin"], "certificate margin")
    finite_decimal(cert["seed_power_eigenvalue"], "seed eigenvalue")
    if (denominator <= 0 or quotient != numerator / denominator or
            margin != numerator - denominator or
            cert["margin_positive"] is not (margin > 0)):
        raise ValueError("D18 certificate exact forms mismatch")

    if (radial["format"] != "direct-bv-radial-two-amplitude-exact-v1" or
            radial["k"] != 48 or type(radial["k"]) is not int or
            radial["basis_dimension"] != 471 or
            type(radial["basis_dimension"]) is not int or
            radial["certificate_sha256"] != PINNED[CERT] or
            radial["integrator_sha256"] != PINNED[INTEGRATOR] or
            radial["R"] != "103/400" or radial["V"] != "97/400" or
            radial["piecewise_function"] !=
            "a*F0 for sum(t)<=V; b*F0 for V<sum(t)<R" or
            radial["baseline_RR_J_exact_match"] is not True or
            radial["baseline_amplitudes_11_exact_match"] is not True or
            radial["denominator_positive"] is not True or
            radial["margin_positive"] is not False or
            radial["claim_scope"] !=
            "Exact particular piecewise-vector forms; Decimal eigenvalue discovery is not itself a certificate."):
        raise ValueError("D18 radial artifact identity mismatch")
    strict_sha(radial["script_sha256"], "radial script SHA")
    amplitudes = tuple(fraction(x, f"radial amplitude {i}")
                       for i, x in enumerate(radial["rational_amplitudes"]))
    if len(amplitudes) != 2 or amplitudes[0] != 1:
        raise ValueError("D18 radial amplitudes mismatch")
    imat = strict_matrix(radial["I_matrix"], "radial I")
    bmat = strict_matrix(radial["kJ_matrix"], "radial 48J")
    if (imat[0][1] != 0 or imat[1][0] != 0 or
            any(imat[i][i] <= 0 for i in range(2)) or
            bmat[0][1] != bmat[1][0]):
        raise ValueError("D18 radial matrix structure mismatch")
    radial_denominator = sum(
        (amplitudes[i] * imat[i][j] * amplitudes[j]
         for i in range(2) for j in range(2)), Q(0))
    radial_numerator = sum(
        (amplitudes[i] * bmat[i][j] * amplitudes[j]
         for i in range(2) for j in range(2)), Q(0))
    if (radial_denominator != fraction(
            radial["exact_denominator"], "radial denominator") or
            radial_numerator != fraction(
                radial["exact_numerator"], "radial numerator") or
            fraction(radial["exact_quotient"], "radial quotient") !=
            radial_numerator / radial_denominator or
            fraction(radial["exact_margin"], "radial margin") !=
            radial_numerator - radial_denominator or
            radial["denominator_positive"] is not (radial_denominator > 0) or
            radial["margin_positive"] is not
            (radial_numerator > radial_denominator)):
        raise ValueError("D18 radial exact contraction mismatch")
    ones_denominator = sum((imat[i][j]
                            for i in range(2) for j in range(2)), Q(0))
    ones_numerator = sum((bmat[i][j]
                          for i in range(2) for j in range(2)), Q(0))
    if ones_denominator != denominator or ones_numerator != numerator:
        raise ValueError("D18 radial baseline does not reconstruct certificate")
    for key in ("baseline_quotient_decimal", "decimal_discovery_eigenvalue",
                "exact_gain_decimal", "exact_quotient_decimal",
                "inner_I_fraction_decimal"):
        finite_decimal(radial[key], f"radial {key}")
    expected_counts = {
        "difference": 471, "raw_R": 471, "raw_V": 471,
        "recentered_R": 568, "recentered_V": 471,
        "square_DD": 10761, "square_RR": 13955, "square_VV": 10761,
    }
    if (radial["marginal_term_counts"] != expected_counts or
            any(type(x) is not int for x in radial["marginal_term_counts"].values()) or
            type(radial["decimal_precision"]) is not int or
            radial["decimal_precision"] != 180 or
            type(radial["rationalization_significant_digits"]) is not int or
            radial["rationalization_significant_digits"] != 61):
        raise ValueError("D18 radial count/precision mismatch")

    expected_family = {
        "A": "1/4", "J_common_coordinate_cutoff": "1/4-epsilon",
        "beta": "1/2", "c1": 0, "c2": 0, "delta": "7/250",
        "range": "0<epsilon<1/4",
        "relevant_modulus_bound": "x^((1-epsilon0)/2)", "rho": "1_P",
        "support": "sum(t_i)<1/4+epsilon; B_m=1/4+epsilon",
    }
    if (baseline["format"] != "direct-bv-fixed-vector-epsilon-scan-v1" or
            baseline["certificate_sha256"] != PINNED[CERT] or
            baseline["integrator_sha256"] != PINNED[INTEGRATOR] or
            baseline["script_sha256"] != PINNED[SCAN] or
            baseline["analytic_family"] != expected_family or
            baseline["baseline_exact_match"] is not True or
            baseline["original_epsilon"] != "3/400" or
            baseline["winner_epsilon"] != "3/400" or
            baseline["winner_exact_quotient"] != cert["exact_quotient"] or
            type(baseline["rows"]) is not list or len(baseline["rows"]) != 1):
        raise ValueError("D18 baseline artifact identity mismatch")
    strict_sha(baseline["analytic_note_sha256"], "baseline analytic-note SHA")
    row = baseline["rows"][0]
    expected_row_keys = {
        "B_all", "alpha", "definition1_margins", "epsilon", "eta",
        "exact_denominator", "exact_margin", "exact_margin_positive",
        "exact_numerator", "exact_quotient", "exact_quotient_decimal",
        "relevant_modulus_exponent", "term_counts",
    }
    if (type(row) is not dict or set(row) != expected_row_keys or
            row["B_all"] != "103/400" or row["alpha"] != "103/400" or
            row["epsilon"] != "3/400" or row["eta"] != "97/400" or
            row["relevant_modulus_exponent"] != "1/2" or
            row["definition1_margins"] != {
                "B1_minus_delta": "459/2000", "beta_minus_B1": "97/400",
                "epsilon": "3/400",
                "one_half_minus_epsilon_minus_A": "97/400"} or
            row["term_counts"] != {
                "F_square": 10761, "marginal": 471,
                "marginal_square": 10761} or
            any(type(x) is not int for x in row["term_counts"].values()) or
            row["exact_denominator"] != cert["exact_denominator"] or
            row["exact_numerator"] != cert["exact_numerator"] or
            row["exact_quotient"] != cert["exact_quotient"] or
            row["exact_margin"] != cert["exact_margin"] or
            row["exact_margin_positive"] is not False):
        raise ValueError("D18 baseline row mismatch")
    finite_decimal(row["exact_quotient_decimal"], "baseline row quotient")
    finite_decimal(baseline["winner_exact_quotient_decimal"],
                   "baseline winning quotient")
    return (tuple((a, tuple(lam)) for a, lam in cert["basis"]), vector,
            amplitudes, radial_denominator, radial_numerator)


def load_inner_coordinate():
    core_start = v2.core.require_pins()
    cert = json.loads(_START[CERT])
    radial = json.loads(_START[RADIAL])
    baseline = json.loads(_START[BASELINE])
    answer = validate_payloads(cert, radial, baseline)
    if snapshots() != _START or v2.core.require_pins() != core_start:
        raise RuntimeError("D18 adapter closure changed while loading")
    return answer


def production_inputs():
    """Use the frozen degree-independent v2 shell construction unchanged."""
    return v2.production_inputs(inner_loader=load_inner_coordinate)


def exact_common_r_shard(common_r, *, progress=False):
    """Unlaunched D18 adapter to the frozen exact common-r recurrence."""
    return v2.exact_common_r_shard(
        common_r, inner_loader=load_inner_coordinate, progress=progress)


def low_k_inputs(k, basis, vector, amplitudes, inner_i=Q(1), inner_b=Q(1)):
    """Small-k fixture using exactly the production support/channel semantics."""
    if (type(k) is not int or not 1 <= k <= 3 or
            len(basis) != len(vector) or len(amplitudes) != 2):
        raise ValueError("malformed low-k adapter fixture")
    supports = v2.core.make_supports(k)
    components = v2.core.outer_core.components(basis, vector, k)
    one = (((), 0, 0, Q(1)),)
    named = {"R": (supports["R"], components),
             "V": (supports["V"], components),
             "H": (supports["H"], one),
             "L": (supports["L"], one)}
    catalog = (("rh", "R", "H"), ("rl", "R", "L"),
               ("vh", "V", "H"), ("vl", "V", "L"))
    weights = v2.core.production_pair_weights(amplitudes)
    return named, catalog, weights, inner_i, inner_b, len(basis)


def preflight():
    basis, vector, amplitudes, inner_i, inner_b = load_inner_coordinate()
    named, catalog, weights, check_i, check_b, dimension = production_inputs()
    if (dimension != 471 or check_i != inner_i or check_b != inner_b or
            tuple(named) != ("R", "V", "H", "L") or
            tuple(tag for tag, _, _ in catalog) != ("rh", "rl", "vh", "vl") or
            weights != v2.core.production_pair_weights(amplitudes)):
        raise ArithmeticError("D18 production adapter changed shell semantics")
    return {
        "active_outer_counts": list(range(26)),
        "basis_dimension": len(basis),
        "coefficient_count": len(vector),
        "dependency_sha256": dependency_record(),
        "driver_sha256": sha256(FILE),
        "inner_48J": str(inner_b),
        "inner_I": str(inner_i),
        "radial_amplitudes": [str(x) for x in amplitudes],
        "shell_traversal": "frozen D16/v2 common-r recurrence unchanged",
        "status": "frontier-active25-inner-D18-adapter-preflight",
        "target_started": False,
        "theorem_ready": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if not args.preflight_only:
        parser.error("this adapter revision exposes preflight only")
    print(json.dumps(preflight(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
