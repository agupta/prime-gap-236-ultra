#!/usr/bin/env python3
"""Exact deletion of the J-invisible core from a direct-BV polynomial.

For R=A+e and V=A-e define

  C = {t>=0: sum(t)<R and sum_{j!=i} t_j>V for every i}.

Every J_i fiber lies in sum_{j!=i}t_j<=V, so replacing F by F*1_{C^c}
preserves all J_i and removes exactly integral_C F^2 from I.  This script
computes that removed mass by slice inclusion-exclusion with Fractions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import defaultdict
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
EI_DIR = HERE.parent / "exact-integrator"
sys.path.insert(0, str(EI_DIR / "src"))
sys.path.insert(0, str(HERE))

import exact_integrator as ei
from scan_bv_epsilon_fixed import square_orbit_polynomial


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DeadCoreIntegrator:
    """Orbit moments over C, with x=sum(t)-V as slice variable."""

    def __init__(self, k: int, R: Q, V: Q):
        if not (k >= 2 and Q(0) < V < R < 1):
            raise ValueError("require k>=2 and 0<V<R<1")
        self.k, self.R, self.V = k, R, V
        self.width = R - V
        self.W = 1 - V

    @lru_cache(maxsize=None)
    def upper(self, m: int) -> Q:
        if not 0 <= m <= self.k:
            raise ValueError("bad inclusion-exclusion subset size")
        return (self.width if m <= 1
                else min(self.width, self.V / (m - 1)))

    @lru_cache(maxsize=None)
    def K(self, m: int, n: int, h: int) -> Q:
        """Integral_0^U x^h (V+(1-m)x)^n dx, exactly."""
        U = self.upper(m)
        if U <= 0:
            return Q(0)
        slope = 1 - m
        if slope == 0:
            return (self.V ** n) * (U ** (h + 1)) / (h + 1)
        # Expansion in x is stable in exact arithmetic and avoids negative
        # powers when the translated residual reaches zero at U.
        return sum(Q(math.comb(n, j)) * (self.V ** (n - j)) *
                   (slope ** j) * (U ** (h + j + 1)) / (h + j + 1)
                   for j in range(n + 1))

    @staticmethod
    @lru_cache(maxsize=None)
    def selected_subset_coefficients(k: int, nu):
        """[y^m z^g] (1+y)^(k-len(nu)) prod_i(1+y E_nu_i(z))."""
        # Selecting a positive-exponent coordinate r and expanding
        # (u+x)^r contributes sum_{g=0}^r z^g/g! after the common r! is
        # factored out.  y records the total selected-coordinate count.
        dp = {(0, 0): Q(1)}
        for r in nu:
            new = defaultdict(Q)
            inv_factorials = [Q(1, math.factorial(g)) for g in range(r + 1)]
            for (m, lost), value in dp.items():
                new[(m, lost)] += value
                for g, inv in enumerate(inv_factorials):
                    new[(m + 1, lost + g)] += value * inv
            dp = dict(new)
        zeros = k - len(nu)
        out = defaultdict(Q)
        for (m, lost), value in dp.items():
            for s in range(zeros + 1):
                out[(m + s, lost)] += value * math.comb(zeros, s)
        return tuple(sorted((m, g, value) for (m, g), value in out.items()
                            if value))

    def radial_standard_polynomial(self, by_a):
        """Collect sum_a c_a (1-V-x)^a in ordinary x powers."""
        out = defaultdict(Q)
        for a, coefficient in by_a.items():
            for r in range(a + 1):
                out[r] += (coefficient * math.comb(a, r) *
                           (self.W ** (a - r)) * ((-1) ** r))
        return {r: c for r, c in out.items() if c}

    def orbit_family_integral(self, nu, by_a) -> Q:
        """Integral_C P_nu(t) sum_a c_a(1-sum t)^a dt."""
        nu = tuple(sorted(nu, reverse=True))
        if len(nu) > self.k:
            return Q(0)
        degree = sum(nu)
        prod_factorials = math.prod(math.factorial(r) for r in nu)
        radial = self.radial_standard_polynomial(by_a)
        subtotal = Q(0)
        for m, lost, subset_coefficient in self.selected_subset_coefficients(
                self.k, nu):
            n = self.k - 1 + degree - lost
            if n < 0:
                raise AssertionError("negative slice exponent")
            integral = sum(coefficient * self.K(m, n, lost + r)
                           for r, coefficient in radial.items())
            term = subset_coefficient * integral / math.factorial(n)
            subtotal += term if m % 2 == 0 else -term
        return ei.orbit_size(self.k, nu) * prod_factorials * subtotal

    def polynomial_integral(self, square_terms, progress_every=50):
        grouped = defaultdict(dict)
        for (a, nu), coefficient in square_terms.items():
            grouped[nu][a] = coefficient
        answer = Q(0)
        started = time.perf_counter()
        for index, (nu, by_a) in enumerate(grouped.items(), 1):
            answer += self.orbit_family_integral(nu, by_a)
            if progress_every and index % progress_every == 0:
                print(f"dead-core orbit {index}/{len(grouped)} "
                      f"elapsed={time.perf_counter()-started:.1f}s "
                      f"Kcache={self.K.cache_info().currsize}",
                      file=sys.stderr, flush=True)
        return answer, len(grouped)


def hand_k2_moment(nu, a, R, V):
    """Independent shifted-triangle formula for k=2 sanity tests."""
    width = R - 2 * V
    if width <= 0:
        return Q(0)
    exponents = tuple(nu) + (0,) * (2 - len(nu))
    r, s = exponents
    canonical = Q(0)
    for i in range(r + 1):
        for j in range(s + 1):
            shift = (math.comb(r, i) * math.comb(s, j) *
                     (V ** (r - i + s - j)))
            for c in range(a + 1):
                residual = (math.comb(a, c) *
                            ((1 - R) ** (a - c)))
                canonical += (shift * residual *
                              Q(math.factorial(i) * math.factorial(j) *
                                math.factorial(c),
                                math.factorial(i + j + c + 2)) *
                              (width ** (i + j + c + 2)))
    return ei.orbit_size(2, tuple(nu)) * canonical


def self_test() -> None:
    core = DeadCoreIntegrator(2, Q(3, 5), Q(1, 5))
    # The constant core is the triangle t1,t2>V, t1+t2<R, of area 1/50.
    got = core.orbit_family_integral((), {0: Q(1)})
    if got != Q(1, 50):
        raise AssertionError(f"k=2 constant core mismatch: {got}")
    for nu in ((), (2,), (3,), (2, 2)):
        for a in range(4):
            got = core.orbit_family_integral(nu, {a: Q(1)})
            expected = hand_k2_moment(nu, a, Q(3, 5), Q(1, 5))
            if got != expected:
                raise AssertionError(f"k=2 moment mismatch {(nu,a)}")
    # Empty-core gate: for k=2, R<=2V makes t1>V,t2>V,sum<R impossible.
    empty = DeadCoreIntegrator(2, Q(2, 5), Q(1, 5))
    if empty.orbit_family_integral((), {0: Q(1)}) != 0:
        raise AssertionError("empty k=2 core did not cancel exactly")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("certificate", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--progress-every", type=int, default=25)
    args = ap.parse_args()
    self_test()

    cert_bytes = args.certificate.read_bytes()
    cert = json.loads(cert_bytes)
    source_path = EI_DIR / "src" / "exact_integrator.py"
    source_hash = sha(source_path)
    if cert.get("integrator_sha256") != source_hash:
        raise ValueError("certificate/integrator source mismatch")
    k = int(cert["k"])
    p = cert["parameters"]
    R, V = Q(p["alpha"]), Q(p["eta"])
    if not (Q(p["beta1"]) == Q(p["beta2"]) ==
            Q(p["beta3plus"]) == R):
        raise ValueError("dead-core preset requires a full simplex")
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in cert["basis"]]
    vector = [Q(x) for x in cert["rational_vector"]]
    if len(basis) != len(vector):
        raise ValueError("basis/vector length mismatch")
    f_terms = {(a, lam): coefficient
               for coefficient, (a, lam) in zip(vector, basis) if coefficient}
    square_terms = square_orbit_polynomial(f_terms)
    core = DeadCoreIntegrator(k, R, V)
    started = time.perf_counter()
    removed, orbit_count = core.polynomial_integral(
        square_terms, args.progress_every)
    elapsed = time.perf_counter() - started
    original_I, original_kJ = (Q(cert["exact_denominator"]),
                               Q(cert["exact_numerator"]))
    if not (Q(0) <= removed < original_I):
        raise ArithmeticError("dead-core mass is outside [0,I)")
    new_I = original_I - removed
    quotient = original_kJ / new_I
    removed_ratio = removed / original_I
    threshold = 1 - original_kJ / original_I
    # The J-invisibility statement is exact: a J_i point has the common
    # coordinate sum <=V, whereas C requires that same sum to be >V.
    output = {
        "format": "direct-bv-dead-core-exact-v1",
        "claim_scope": ("Exact rational-vector forms for the piecewise "
                        "function F*1_{C^c}; this is a valid non-polynomial "
                        "sieve test function up to standard L2 approximation."),
        "k": k, "R": str(R), "V": str(V), "width": str(R - V),
        "core_definition": ("sum(t)<R and sum_{j!=i}t_j>V for every i"),
        "J_invariance_reason": ("Every J_i integration domain has "
                                "sum_{j!=i}t_j<=V and is disjoint from C."),
        "integrator_sha256": source_hash,
        "script_sha256": sha(Path(__file__)),
        "certificate_sha256": hashlib.sha256(cert_bytes).hexdigest(),
        "basis_dimension": len(basis),
        "square_term_count": len(square_terms),
        "orbit_count": orbit_count,
        "exact_original_I": str(original_I),
        "exact_original_kJ": str(original_kJ),
        "exact_removed_I_core": str(removed),
        "exact_removed_ratio": str(removed_ratio),
        "exact_crossing_threshold": str(threshold),
        "crossing_condition_holds": removed_ratio > threshold,
        "exact_new_I": str(new_I),
        "exact_new_kJ": str(original_kJ),
        "exact_new_quotient": str(quotient),
        "exact_new_margin": str(original_kJ - new_I),
        "new_margin_positive": original_kJ > new_I,
        "removed_ratio_decimal": format(float(removed_ratio), ".17g"),
        "threshold_decimal": format(float(threshold), ".17g"),
        "new_quotient_decimal": format(float(quotient), ".17g"),
        "elapsed_seconds": elapsed,
        "K_cache": {"hits": core.K.cache_info().hits,
                    "misses": core.K.cache_info().misses,
                    "size": core.K.cache_info().currsize},
        "self_tests": ["k2 constant triangle", "k2 monomials",
                       "k2 empty-core exact cancellation"],
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    print("removed_ratio", output["removed_ratio_decimal"])
    print("threshold", output["threshold_decimal"])
    print("new_quotient", output["new_quotient_decimal"])
    print("new_margin_sign", "+" if original_kJ > new_I else "-")
    print("artifact_sha256", hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
