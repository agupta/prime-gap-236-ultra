#!/usr/bin/env python3
"""Support-independent algebra kernel for one symmetric fixed vector.

This module is discovery infrastructure, not a certificate checker.  It
separates the exact orbit/coefficient contractions from support-dependent face
geometry.  The resulting in-memory kernel can therefore be replayed at several
rational supports without rebuilding the same products.  No target D12 kernel
is compiled merely by importing or testing this file.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from math import comb
from pathlib import Path
from typing import Iterable


HERE = Path(__file__).resolve().parent
EXACT_DIR = HERE.parents[1] / "exact-integrator"
SRC_DIR = EXACT_DIR / "src"
if str(EXACT_DIR) not in sys.path:
    sys.path.insert(0, str(EXACT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import exact_integrator as ei  # noqa: E402
import grouped_fixed_vector as grouped  # noqa: E402


RATIONAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json_bytes(data: bytes):
    """Reject duplicate keys and JSON floating-point tokens."""

    def object_pairs(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key!r}")
            out[key] = value
        return out

    def reject_float(token):
        raise ValueError(f"JSON float forbidden: {token!r}")

    return json.loads(data, object_pairs_hook=object_pairs,
                      parse_float=reject_float,
                      parse_constant=reject_float)


def canonical_fraction(token: object) -> Fraction:
    if not isinstance(token, str) or RATIONAL.fullmatch(token) is None:
        raise ValueError("coefficient is not a canonical rational string")
    value = Fraction(token)
    if str(value) != token:
        raise ValueError(f"noncanonical rational: {token!r}")
    return value


def exact_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def parse_source_bytes(data: bytes):
    raw = strict_json_bytes(data)
    if not isinstance(raw, dict):
        raise ValueError("source must be a JSON object")
    required = {"k", "degree", "basis_dimension", "basis", "rational_vector"}
    if not required <= set(raw):
        raise ValueError(f"source missing keys {sorted(required-set(raw))}")
    k = exact_int(raw["k"], "k")
    degree = exact_int(raw["degree"], "degree")
    dimension = exact_int(raw["basis_dimension"], "basis_dimension")
    if k < 1 or degree < 0 or dimension < 1:
        raise ValueError("invalid k/degree/dimension")
    if (not isinstance(raw["basis"], list) or
            not isinstance(raw["rational_vector"], list) or
            len(raw["basis"]) != dimension or
            len(raw["rational_vector"]) != dimension):
        raise ValueError("basis/vector dimension mismatch")
    labels = []
    for index, entry in enumerate(raw["basis"]):
        if not isinstance(entry, list) or len(entry) != 2:
            raise ValueError(f"bad basis entry {index}")
        a = exact_int(entry[0], f"basis[{index}].a")
        lam_raw = entry[1]
        if a < 0 or not isinstance(lam_raw, list):
            raise ValueError(f"bad basis entry {index}")
        lam = tuple(exact_int(x, f"basis[{index}].lambda") for x in lam_raw)
        if (any(x <= 0 for x in lam) or
                any(lam[i] < lam[i + 1] for i in range(len(lam) - 1)) or
                len(lam) > k or a + sum(lam) > degree):
            raise ValueError(f"invalid partition/slack in basis entry {index}")
        labels.append((a, lam))
    if len(set(labels)) != len(labels):
        raise ValueError("duplicate basis labels")
    coefficients = [canonical_fraction(x) for x in raw["rational_vector"]]
    return k, degree, tuple(labels), tuple(coefficients)


def canonical_pair(left: tuple[int, ...], right: tuple[int, ...]):
    return (left, right) if left <= right else (right, left)


def required_orbit_pairs(labels, k):
    pairs = set()
    for _, lam in labels:
        for _, mu in labels:
            pairs.add(canonical_pair(lam, mu))
            for _, lr in ei.OneStratumSupport.split_at_distinguished(lam, k):
                for _, mr in ei.OneStratumSupport.split_at_distinguished(mu, k):
                    pairs.add(canonical_pair(lr, mr))
    return tuple(sorted(pairs))


@dataclass(frozen=True)
class FixedVectorKernel:
    k: int
    degree: int
    labels: tuple
    source_sha256: str
    orbit_products: dict
    i_raw: dict
    marginal_raw: dict

    def orbit_lookup(self, left, right):
        return self.orbit_products[canonical_pair(tuple(left), tuple(right))]

    def i_grouped(self, alpha, scalar=Fraction):
        """Translate the support-independent I kernel to one alpha."""
        zero, one = scalar(0), scalar(1)
        answer = defaultdict(lambda: defaultdict(lambda: zero))
        for (nu, total), raw in self.i_raw.items():
            value = scalar(raw.numerator) / scalar(raw.denominator)
            for c in range(total + 1):
                answer[nu][c] += (value * scalar(comb(total, c)) *
                                  (one - alpha) ** (total - c))
        return {nu: {c: x for c, x in by_c.items() if x}
                for nu, by_c in answer.items()
                if any(by_c.values())}

    def marginal_components(self, scalar=Fraction):
        answer = {}
        for key, value in self.marginal_raw.items():
            answer[key] = scalar(value.numerator) / scalar(value.denominator)
        return answer


def compile_kernel_bytes(data: bytes) -> FixedVectorKernel:
    k, degree, labels, coefficients = parse_source_bytes(data)
    orbit_products = {}
    for left, right in required_orbit_pairs(labels, k):
        orbit_products[(left, right)] = tuple(
            (tuple(nu), int(multiplicity))
            for nu, multiplicity in ei.multiply_monomial_orbits(left, right))

    i_raw = defaultdict(Fraction)
    for i, (a, lam) in enumerate(labels):
        for j in range(i + 1):
            b, mu = labels[j]
            factor = coefficients[i] * coefficients[j]
            if i != j:
                factor *= 2
            for nu, multiplicity in orbit_products[canonical_pair(lam, mu)]:
                i_raw[(nu, a + b)] += factor * multiplicity

    marginal = defaultdict(Fraction)
    for coefficient, (a, lam) in zip(coefficients, labels):
        for exponent, remaining in ei.OneStratumSupport.split_at_distinguished(
                lam, k):
            marginal[(remaining, exponent, a)] += coefficient

    return FixedVectorKernel(
        k=k,
        degree=degree,
        labels=labels,
        source_sha256=sha256_bytes(data),
        orbit_products=orbit_products,
        i_raw={key: value for key, value in i_raw.items() if value},
        marginal_raw={key: value for key, value in marginal.items() if value},
    )


class KernelEvaluator(grouped.GroupedEvaluator):
    """Grouped evaluator with support-independent contractions injected."""

    def __init__(self, support, kernel: FixedVectorKernel, scalar=Fraction):
        if support.k != kernel.k:
            raise ValueError("support/kernel k mismatch")
        super().__init__(support, (), (), scalar)
        self.kernel = kernel
        self._i_grouped = kernel.i_grouped(support.alpha, scalar)
        self._marginals = kernel.marginal_components(scalar)

    def square_residual_terms(self):
        return self._i_grouped

    def marginal_components(self):
        return self._marginals

    def branch_orbit_product(self, left, right, same_branch):
        combined = {}
        if same_branch:
            keys = list(left)
            for i, lr in enumerate(keys):
                for j in range(i + 1):
                    mr = keys[j]
                    product = ei._poly_mul(left[lr], left[mr])
                    factor = self.scalar(2 if i != j else 1)
                    for nu, multiplicity in self.kernel.orbit_lookup(lr, mr):
                        target = combined.setdefault(nu, defaultdict(self.scalar))
                        grouped.add_poly(target, product,
                                         factor * multiplicity)
        else:
            for lr, left_poly in left.items():
                for mr, right_poly in right.items():
                    product = ei._poly_mul(left_poly, right_poly)
                    for nu, multiplicity in self.kernel.orbit_lookup(lr, mr):
                        target = combined.setdefault(nu, defaultdict(self.scalar))
                        grouped.add_poly(target, product,
                                         self.scalar(2 * multiplicity))
        return {nu: dict(poly) for nu, poly in combined.items() if poly}


def evaluate_kernel(support, kernel, scalar=Fraction, workers=1):
    evaluator = KernelEvaluator(support, kernel, scalar)
    denominator, groups, faces = evaluator.evaluate_i(False, workers)
    j_value, components, integrals = evaluator.evaluate_j(False, workers)
    return {
        "denominator": denominator,
        "j_value": j_value,
        "numerator": scalar(support.k) * j_value,
        "i_orbit_groups": groups,
        "i_faces": faces,
        "marginal_components": components,
        "j_branch_integrals": integrals,
    }


def kernel_summary(kernel: FixedVectorKernel):
    return {
        "status": "support-independent-fixed-vector-kernel-summary",
        "rigorous": False,
        "theorem_ready": False,
        "k": kernel.k,
        "degree": kernel.degree,
        "basis_dimension": len(kernel.labels),
        "source_sha256": kernel.source_sha256,
        "orbit_product_pairs": len(kernel.orbit_products),
        "i_raw_terms": len(kernel.i_raw),
        "marginal_raw_terms": len(kernel.marginal_raw),
    }


def main(argv: Iterable[str] | None = None):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source_json")
    args = parser.parse_args(argv)
    data = Path(args.source_json).read_bytes()
    kernel = compile_kernel_bytes(data)
    print(json.dumps(kernel_summary(kernel), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
