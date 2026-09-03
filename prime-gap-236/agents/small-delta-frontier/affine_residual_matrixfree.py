#!/usr/bin/env python3
"""Matrix-free affine Rayleigh-residual screen for one fixed base polynomial.

For H_(r,p)=1_{R=r} phi_p F0, with phi=(1,L,Z), and a fixed affine
multiplier c, this reconstructs only

    a_j = I(F0*c, H_j),       b_j = k J(F0*c, H_j),
    d_j = I(H_j,H_j),         e_j = k J(H_j,H_j).

No multiplier Gram matrix is built.  On each aggregate face all requested
channels are packed into one vector-valued polynomial, so each geometric
domain is integrated once.  A restricted coordinate list is a genuine finite
subspace screen: a positive two-vector improvement in any listed direction is
valid, although a negative screen is not an upper bound for omitted directions.

The target use is discovery, not certification.  Fraction mode plus an exact
stored D4 matrix is the regression oracle; Decimal mode is intended only for a
possible later D12 screen after the fixed-candidate baseline has completed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import resource
import sys
import time
from collections import defaultdict
from decimal import Decimal, getcontext
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "exact-integrator"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "src"))

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import install_decimal, precompute_orbits  # noqa: E402
from stratum_linear import StratumLinearEvaluator  # noqa: E402


CHANNEL_NAMES = ("1", "L", "Z")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed_label(label, cutoff):
    r, p = label
    return not (label == (0, 1) or (p != 0 and r > cutoff))


def parse_coordinate_spec(token):
    """Parse `all`, `boundary`, or comma-separated `r:1|L|Z` labels."""
    if token in ("all", "boundary"):
        return token
    answer = []
    for item in token.split(","):
        fields = item.split(":")
        if len(fields) != 2 or fields[1] not in CHANNEL_NAMES:
            raise argparse.ArgumentTypeError(f"malformed coordinate {item!r}")
        label = (int(fields[0]), CHANNEL_NAMES.index(fields[1]))
        if label in answer:
            raise argparse.ArgumentTypeError(f"duplicate coordinate {item!r}")
        answer.append(label)
    if not answer:
        raise argparse.ArgumentTypeError("empty coordinate list")
    return tuple(answer)


class MatrixFreeAffineResidual(StratumLinearEvaluator):
    """Packed exact/multiprecision cross and diagonal-form evaluator."""

    @staticmethod
    def _new_vector(width, zero):
        return [zero for _ in range(width)]

    def _pack_blocks(self, channels, indices):
        """Pack selected scalar orbit blocks into a local vector block."""
        width = len(indices)
        answer = {}
        for position, p in enumerate(indices):
            for lr, polynomial in channels[p].items():
                target_poly = answer.setdefault(lr, {})
                for monomial, value in polynomial.items():
                    target = target_poly.setdefault(
                        monomial, self._new_vector(width, self.zero))
                    target[position] += value
        return answer

    def _pack_polynomials(self, polynomials, indices):
        width = len(indices)
        answer = {}
        for position, p in enumerate(indices):
            for monomial, value in polynomials[p].items():
                target = answer.setdefault(
                    monomial, self._new_vector(width, self.zero))
                target[position] += value
        return answer

    def _add_vector(self, destination, source, offset):
        for nu, polynomial in source.items():
            target_poly = destination.setdefault(nu, {})
            for monomial, vector in polynomial.items():
                target = target_poly.setdefault(
                    monomial,
                    self._new_vector(offset + len(vector), self.zero))
                if len(target) < offset + len(vector):
                    target.extend(self._new_vector(
                        offset + len(vector) - len(target), self.zero))
                for i, value in enumerate(vector):
                    target[offset + i] += value

    def _packed_orbit_product(self, packed, scalar_block):
        """Ordinary bilinear orbit product: packed left times scalar right."""
        if not packed or not scalar_block:
            return {}
        width = len(next(iter(next(iter(packed.values())).values())))
        combined = {}
        for lr, left_poly in packed.items():
            for mr, right_poly in scalar_block.items():
                orbit_products = ei.multiply_monomial_orbits(lr, mr)
                for (li, lj), left_vector in left_poly.items():
                    for (ri, rj), right_value in right_poly.items():
                        monomial = (li + ri, lj + rj)
                        for nu, multiplicity in orbit_products:
                            target_poly = combined.setdefault(nu, {})
                            target = target_poly.setdefault(
                                monomial,
                                self._new_vector(width, self.zero))
                            factor = self.scalar(multiplicity) * right_value
                            for i, value in enumerate(left_vector):
                                target[i] += value * factor
        return combined

    def _packed_hadamard_orbit_square(self, packed):
        """Pack the ordinary orbit squares of each channel, without cross terms."""
        if not packed:
            return {}
        width = len(next(iter(next(iter(packed.values())).values())))
        combined = {}
        for lr, left_poly in packed.items():
            for mr, right_poly in packed.items():
                orbit_products = ei.multiply_monomial_orbits(lr, mr)
                for (li, lj), left_vector in left_poly.items():
                    for (ri, rj), right_vector in right_poly.items():
                        monomial = (li + ri, lj + rj)
                        for nu, multiplicity in orbit_products:
                            target_poly = combined.setdefault(nu, {})
                            target = target_poly.setdefault(
                                monomial,
                                self._new_vector(width, self.zero))
                            factor = self.scalar(multiplicity)
                            for i, (left, right) in enumerate(
                                    zip(left_vector, right_vector)):
                                target[i] += left * right * factor
        return combined

    def _packed_poly_product(self, packed, scalar_poly):
        if not packed or not scalar_poly:
            return {}
        width = len(next(iter(packed.values())))
        answer = {}
        for (li, lj), left_vector in packed.items():
            for (ri, rj), right in scalar_poly.items():
                target = answer.setdefault(
                    (li + ri, lj + rj),
                    self._new_vector(width, self.zero))
                for i, value in enumerate(left_vector):
                    target[i] += value * right
        return answer

    def _packed_poly_hadamard_square(self, packed):
        if not packed:
            return {}
        width = len(next(iter(packed.values())))
        answer = {}
        for (li, lj), left in packed.items():
            for (ri, rj), right in packed.items():
                target = answer.setdefault(
                    (li + ri, lj + rj),
                    self._new_vector(width, self.zero))
                for i, (a, b) in enumerate(zip(left, right)):
                    target[i] += a * b
        return answer

    def _packed_poly_add(self, destination, source, offset, width):
        for monomial, vector in source.items():
            target = destination.setdefault(
                monomial, self._new_vector(width, self.zero))
            for i, value in enumerate(vector):
                target[offset + i] += value

    def _integrate_vector_domain(self, polynomial, dimension, r, outer,
                                 constraints, width):
        zero_vector = self._new_vector(width, self.zero)
        if not polynomial or outer <= 0:
            return zero_vector
        if dimension == 0:
            if any(cap < 0 for _, _, cap in constraints):
                return zero_vector
            return list(polynomial.get((0, 0), zero_vector))
        s = dimension - r
        if r and s:
            domain = ei.polygon(outer, constraints)

            def moment(i, j):
                return ei.polygon_monomial(domain, i, j)
        elif r:
            lo, hi = self.zero, outer
            for az, aw, cap in constraints:
                if az > 0:
                    hi = min(hi, cap / az)
                elif az < 0:
                    lo = max(lo, cap / az)
                elif cap < 0:
                    return zero_vector

            def moment(i, j):
                if j or hi <= lo:
                    return self.zero
                return (hi ** (i + 1) - lo ** (i + 1)) / (i + 1)
        else:
            lo, hi = self.zero, outer
            for az, aw, cap in constraints:
                if aw > 0:
                    hi = min(hi, cap / aw)
                elif aw < 0:
                    lo = max(lo, cap / aw)
                elif cap < 0:
                    return zero_vector

            def moment(i, j):
                if i or hi <= lo:
                    return self.zero
                return (hi ** (j + 1) - lo ** (j + 1)) / (j + 1)
        answer = zero_vector
        for (i, j), vector in polynomial.items():
            weight = moment(i, j)
            for position, value in enumerate(vector):
                answer[position] += value * weight
        return answer

    def _integrate_packed_orbits(self, combined, dimension, r, h, outer,
                                 max_h, constraints, width):
        total = {}
        for nu, marginal in combined.items():
            density = self.orbit_density(dimension, nu, r, h, max_h)
            if not density:
                continue
            for (di, dj), density_value in density.items():
                for (mi, mj), vector in marginal.items():
                    target = total.setdefault(
                        (di + mi, dj + mj),
                        self._new_vector(width, self.zero))
                    for position, value in enumerate(vector):
                        target[position] += density_value * value
        return self._integrate_vector_domain(
            total, dimension, r, outer, constraints, width)

    def evaluate_i_cross_diagonal(self, coefficients, coordinate_set,
                                  progress=False):
        grouped = self.square_residual_terms()
        cross = {label: self.zero for label in coordinate_set}
        diagonal = {label: self.zero for label in coordinate_set}
        faces = lanes = 0
        dimension = self.support.k
        by_r = defaultdict(list)
        for label in coordinate_set:
            by_r[label[0]].append(label[1])
        for r in sorted(by_r):
            indices = sorted(by_r[r])
            max_h = int(self.support.alpha // self.support.delta) - r
            constraints = ()
            if r:
                cap = self.support.beta(r) - r * self.support.delta
                if cap <= 0:
                    continue
                constraints = ((self.one, self.zero, cap),)
            for h in range(max_h + 1):
                outer = self.support.alpha - (r + h) * self.support.delta
                if outer <= 0:
                    continue
                base = self._i_face_polynomial(
                    grouped, dimension, r, h, max_h, outer)
                phi = self._phi_polynomials(r, h)
                amplitude = defaultdict(self.scalar)
                for p in range(3):
                    factor = coefficients.get((r, p), self.zero)
                    if factor:
                        for monomial, value in phi[p].items():
                            amplitude[monomial] += factor * value
                packed_phi = self._pack_polynomials(phi, indices)
                cross_poly = self._packed_poly_product(
                    self._packed_poly_product(packed_phi, dict(amplitude)),
                    base)
                self_poly = self._packed_poly_product(
                    self._packed_poly_hadamard_square(packed_phi), base)
                width = 2 * len(indices)
                packed = {}
                self._packed_poly_add(packed, cross_poly, 0, width)
                self._packed_poly_add(
                    packed, self_poly, len(indices), width)
                values = self._integrate_vector_domain(
                    packed, dimension, r, outer, constraints, width)
                for position, p in enumerate(indices):
                    cross[(r, p)] += values[position]
                    diagonal[(r, p)] += values[len(indices) + position]
                faces += 1
                lanes += width
                if progress:
                    print(f"residual I r={r} h={h} faces={faces}",
                          flush=True)
                self.clear_face_caches()
            self.clear_radial_caches()
        return cross, diagonal, len(grouped), faces, lanes

    def evaluate_j_cross_diagonal(self, coefficients, coordinate_set,
                                  progress=False):
        _, lrs, by_lr = self._j_component_data()
        cross = {label: self.zero for label in coordinate_set}
        diagonal = {label: self.zero for label in coordinate_set}
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        dimension = self.support.k - 1
        common_r = sorted({label[0] for label in coordinate_set} |
                          {label[0] - 1 for label in coordinate_set
                           if label[0] > 0})
        domains = lanes = 0
        for r in common_r:
            max_h = int(self.support.eta // self.support.delta) - r
            if max_h < 0:
                continue
            for h in range(max_h + 1):
                outer = self.support.eta - (r + h) * self.support.delta
                if outer <= 0:
                    continue
                channels = self._channel_branch_blocks(
                    lrs, by_lr, r, h, dimension, outer)
                combined_candidate = {}
                branch_indices = {}
                for branch in branches:
                    total_r = (r if branch in self.SMALL_BRANCHES else r + 1)
                    vector = tuple(coefficients.get(
                        (total_r, p), self.zero) for p in range(3))
                    combined_candidate[branch] = self._combine_channel_blocks(
                        channels[branch], vector)
                    branch_indices[branch] = sorted(
                        p for rr, p in coordinate_set if rr == total_r)
                for i, left in enumerate(branches):
                    for right in branches[:i + 1]:
                        constraints = self._active_branch_pair(
                            channels, left, right, dimension, r, h, outer)
                        if constraints is None:
                            continue
                        left_indices = branch_indices[left]
                        right_indices = branch_indices[right]
                        if left == right:
                            if not left_indices:
                                continue
                            packed_channels = self._pack_blocks(
                                channels[left], left_indices)
                            cross_product = self._packed_orbit_product(
                                packed_channels, combined_candidate[left])
                            self_product = \
                                self._packed_hadamard_orbit_square(
                                    packed_channels)
                            width = 2 * len(left_indices)
                            packed = {}
                            self._add_vector(packed, cross_product, 0)
                            self._add_vector(
                                packed, self_product, len(left_indices))
                            values = self._integrate_packed_orbits(
                                packed, dimension, r, h, outer, max_h,
                                constraints, width)
                            total_r = (r if left in self.SMALL_BRANCHES
                                       else r + 1)
                            for position, p in enumerate(left_indices):
                                cross[(total_r, p)] += values[position]
                                diagonal[(total_r, p)] += \
                                    values[len(left_indices) + position]
                        else:
                            if not left_indices and not right_indices:
                                continue
                            packed = {}
                            width = len(left_indices) + len(right_indices)
                            if left_indices:
                                product = self._packed_orbit_product(
                                    self._pack_blocks(
                                        channels[left], left_indices),
                                    combined_candidate[right])
                                self._add_vector(packed, product, 0)
                            if right_indices:
                                product = self._packed_orbit_product(
                                    self._pack_blocks(
                                        channels[right], right_indices),
                                    combined_candidate[left])
                                self._add_vector(
                                    packed, product, len(left_indices))
                            values = self._integrate_packed_orbits(
                                packed, dimension, r, h, outer, max_h,
                                constraints, width)
                            left_r = (r if left in self.SMALL_BRANCHES
                                      else r + 1)
                            right_r = (r if right in self.SMALL_BRANCHES
                                       else r + 1)
                            for position, p in enumerate(left_indices):
                                cross[(left_r, p)] += values[position]
                            for position, p in enumerate(right_indices):
                                cross[(right_r, p)] += \
                                    values[len(left_indices) + position]
                        domains += 1
                        lanes += width
                if progress:
                    print(f"residual J r={r} h={h} domains={domains}",
                          flush=True)
                self.clear_face_caches(clear_marginals=True)
            self.clear_radial_caches()
        k = self.scalar(self.support.k)
        return ({label: k * value for label, value in cross.items()},
                {label: k * value for label, value in diagonal.items()},
                len(self.marginal_components()), domains, lanes,
                common_r)

    def evaluate_residual_data(self, coefficients, coordinate_set,
                               progress=False):
        start = time.perf_counter()
        i = self.evaluate_i_cross_diagonal(
            coefficients, coordinate_set, progress)
        i_seconds = time.perf_counter() - start
        j_start = time.perf_counter()
        j = self.evaluate_j_cross_diagonal(
            coefficients, coordinate_set, progress)
        j_seconds = time.perf_counter() - j_start
        return {
            "i_cross": i[0], "i_diagonal": i[1],
            "j_cross": j[0], "j_diagonal": j[1],
            "i_orbit_groups": i[2], "i_faces": i[3],
            "i_scalar_lanes": i[4],
            "marginal_components": j[2], "j_branch_domains": j[3],
            "j_scalar_lanes": j[4], "j_common_r": j[5],
            "i_seconds": i_seconds, "j_seconds": j_seconds,
            "total_seconds": time.perf_counter() - start,
        }


def parse_multiplier(raw, cutoff, scalar):
    labels = [(int(r), CHANNEL_NAMES.index(channel))
              for r, channel in raw["linear_labels"]]
    if labels != [(r, p) for r in range(16) for p in range(3)]:
        raise ValueError("multiplier labels are not the canonical 48 labels")
    vector = [Q(x) for x in raw["rational_vector"]]
    if len(vector) != 48:
        raise ValueError("multiplier vector has wrong dimension")
    answer = {}
    for label, value in zip(labels, vector):
        if not allowed_label(label, cutoff):
            value = Q(0)
        answer[label] = scalar(value.numerator, value.denominator)
    return labels, vector, answer


def oracle_forms(raw, rational_coefficients, cutoff):
    labels = [(int(r), CHANNEL_NAMES.index(channel))
              for r, channel in raw["linear_labels"]]
    position = {label: i for i, label in enumerate(labels)}
    coefficients = list(rational_coefficients)
    for i, label in enumerate(labels):
        if not allowed_label(label, cutoff):
            coefficients[i] = Q(0)
    blocks = {int(r): [[Q(x) for x in row] for row in block]
              for r, block in raw["i_blocks"].items()}
    i_cross = {}
    i_diagonal = {}
    for label in labels:
        r, p = label
        i_cross[label] = sum(
            blocks[r][p][q] * coefficients[position[(r, q)]]
            for q in range(3))
        i_diagonal[label] = blocks[r][p][p]
    j_cross = {label: Q(0) for label in labels}
    j_diagonal = {label: Q(0) for label in labels}
    for key, token in raw["j_entries"].items():
        left, right = ast.literal_eval(key)
        value = Q(token) * int(raw["k"])
        if left == right:
            j_cross[left] += value * coefficients[position[left]]
            j_diagonal[left] += value
        else:
            j_cross[left] += value * coefficients[position[right]]
            j_cross[right] += value * coefficients[position[left]]
    denominator = sum(coefficients[position[label]] * i_cross[label]
                      for label in labels)
    numerator = sum(coefficients[position[label]] * j_cross[label]
                    for label in labels)
    return i_cross, i_diagonal, j_cross, j_diagonal, denominator, numerator


def decimal_text(value, digits=60):
    if isinstance(value, Q):
        getcontext().prec = digits
        return str(Decimal(value.numerator) / Decimal(value.denominator))
    return str(value)


def form_matches(got, wanted, convert, decimal_dps):
    expected = convert(wanted)
    if decimal_dps is None:
        return got == expected
    scale = max(abs(got), abs(expected), Decimal(1).scaleb(-decimal_dps))
    # The grouped inclusion--exclusion faces can lose roughly 25--30 decimal
    # digits before cancellation.  Decimal mode is discovery only; retaining
    # dps-40 relative digits is the explicit D4 regression gate.
    return abs(got - expected) <= scale * Decimal(1).scaleb(-decimal_dps + 40)


def two_vector_eigenvalue(denominator, numerator, cross_i, cross_j,
                          diagonal_i, diagonal_j, digits=100):
    """Discovery maximum in span{baseline, direction}; never a rigor claim."""
    old_precision = getcontext().prec
    getcontext().prec = max(old_precision, digits)

    def dec(value):
        if isinstance(value, Q):
            return Decimal(value.numerator) / Decimal(value.denominator)
        return Decimal(value)

    D, N, a, b, d, e = map(
        dec, (denominator, numerator, cross_i, cross_j,
              diagonal_i, diagonal_j))
    gram = D * d - a * a
    if D <= 0 or d <= 0 or gram <= 0:
        getcontext().prec = old_precision
        return None
    qa = gram
    qb = -N * d - e * D + 2 * a * b
    qc = N * e - b * b
    discriminant = qb * qb - 4 * qa * qc
    if discriminant < 0:
        # A tiny negative from Decimal cancellation is not rounded upward.
        getcontext().prec = old_precision
        return None
    answer = (-qb + discriminant.sqrt()) / (2 * qa)
    getcontext().prec = old_precision
    return answer


def load_baseline_result(path, expected_sha, args, input_sha, multiplier_sha):
    if file_sha(path) != expected_sha:
        raise SystemExit("baseline result SHA mismatch")
    raw = json.loads(path.read_bytes())
    required = {
        "status": "multiprecision-transferred-affine-candidate",
        "complete": True,
        "rigorous": False,
        "theorem_ready": False,
        "linear_cutoff": args.linear_cutoff,
        "input_sha256": input_sha,
        "multiplier_sha256": multiplier_sha,
        "decimal_dps": args.decimal_dps,
        "gates_passed": True,
    }
    for key, value in required.items():
        if raw.get(key) != value:
            raise SystemExit(f"baseline result field {key!r} mismatch")
    if (raw.get("fixed_basis_dimension"), raw.get("multiplier_dimension"),
            raw.get("marginal_components"), raw.get("j_branch_domains")) != \
            (272, 48, 695, 1200):
        raise SystemExit("baseline traversal dimensions/counts mismatch")
    parameters = {key: str(getattr(args, key)) for key in (
        "alpha", "delta", "eta", "beta1", "beta2", "beta3plus")}
    if raw.get("parameters") != parameters:
        raise SystemExit("baseline support parameters mismatch")
    denominator = Decimal(raw["denominator"])
    numerator = Decimal(raw["numerator"])
    serialized_q = Decimal(raw["quotient"])
    if denominator <= 0 or not all(
            x.is_finite() for x in (denominator, numerator, serialized_q)):
        raise SystemExit("baseline forms are invalid")
    computed_q = numerator / denominator
    scale = max(abs(computed_q), abs(serialized_q), Decimal(1))
    if abs(computed_q - serialized_q) > \
            scale * Decimal(1).scaleb(-args.decimal_dps + 10):
        raise SystemExit("baseline quotient does not match its forms")
    return raw, denominator, numerator, computed_q


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json", type=Path)
    parser.add_argument("multiplier_json", type=Path)
    parser.add_argument("--expect-input-sha256", required=True)
    parser.add_argument("--expect-multiplier-sha256", required=True)
    parser.add_argument("--alpha", type=Q, required=True)
    parser.add_argument("--delta", type=Q, required=True)
    parser.add_argument("--eta", type=Q, required=True)
    parser.add_argument("--beta1", type=Q, required=True)
    parser.add_argument("--beta2", type=Q, required=True)
    parser.add_argument("--beta3plus", type=Q, required=True)
    parser.add_argument("--linear-cutoff", type=int, default=11)
    parser.add_argument("--coordinates", type=parse_coordinate_spec,
                        default="boundary")
    parser.add_argument("--decimal-dps", type=int)
    parser.add_argument("--oracle-affine-json", type=Path)
    parser.add_argument("--baseline-quotient", type=Q)
    parser.add_argument("--baseline-result-json", type=Path)
    parser.add_argument("--expect-baseline-sha256")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 0 <= args.linear_cutoff <= 15:
        parser.error("linear cutoff must be in 0..15")
    if args.decimal_dps is not None and args.decimal_dps < 60:
        parser.error("Decimal discovery requires at least 60 digits")
    baseline_choices = sum(value is not None for value in (
        args.oracle_affine_json, args.baseline_quotient,
        args.baseline_result_json))
    if baseline_choices != 1:
        parser.error("select exactly one oracle/baseline source")
    if (args.baseline_result_json is None) != \
            (args.expect_baseline_sha256 is None):
        parser.error("baseline result path and expected SHA are paired")
    if args.baseline_result_json is not None and args.decimal_dps is None:
        parser.error("a Decimal baseline result requires --decimal-dps")

    protected = {args.input_json.resolve(), args.multiplier_json.resolve(),
                 Path(__file__).resolve()}
    if args.oracle_affine_json is not None:
        protected.add(args.oracle_affine_json.resolve())
    if args.baseline_result_json is not None:
        protected.add(args.baseline_result_json.resolve())
    if args.output.resolve() in protected:
        parser.error("output path collides with a protected input/source")

    input_bytes = args.input_json.read_bytes()
    multiplier_bytes = args.multiplier_json.read_bytes()
    if file_sha(args.input_json) != args.expect_input_sha256:
        raise SystemExit("input SHA mismatch")
    if file_sha(args.multiplier_json) != args.expect_multiplier_sha256:
        raise SystemExit("multiplier SHA mismatch")
    input_raw = json.loads(input_bytes)
    multiplier_raw = json.loads(multiplier_bytes)
    if int(input_raw.get("k", -1)) != 48 or int(multiplier_raw.get("k", -1)) != 48:
        raise SystemExit("this driver requires k=48")
    labels = [(int(a), tuple(int(x) for x in lam))
              for a, lam in input_raw["basis"]]
    rational_base = [Q(x) for x in input_raw["rational_vector"]]
    if len(labels) != len(rational_base):
        raise SystemExit("base basis/vector mismatch")

    orbit_table = precompute_orbits(labels, 48)
    if args.decimal_dps is None:
        scalar = Q
    else:
        getcontext().prec = args.decimal_dps
        scalar = install_decimal(orbit_table, args.decimal_dps)
    convert = lambda x: scalar(x.numerator, x.denominator)
    support = ei.OneStratumSupport(
        48, *[convert(x) for x in (
            args.alpha, args.delta, args.eta, args.beta1, args.beta2,
            args.beta3plus)])
    base = [convert(x) for x in rational_base]
    _, rational_multiplier, coefficients = parse_multiplier(
        multiplier_raw, args.linear_cutoff, scalar)
    all_coordinates = tuple(
        (r, p) for r in range(16) for p in range(3)
        if allowed_label((r, p), args.linear_cutoff))
    if args.coordinates == "all":
        coordinates = all_coordinates
    elif args.coordinates == "boundary":
        coordinates = ((11, 0), (11, 1), (11, 2), (12, 0), (13, 0))
    else:
        coordinates = args.coordinates
    if any(label not in all_coordinates for label in coordinates):
        raise SystemExit("requested coordinate is outside the effective span")

    preloaded_baseline = None
    if args.baseline_result_json is not None:
        preloaded_baseline = load_baseline_result(
            args.baseline_result_json, args.expect_baseline_sha256, args,
            args.expect_input_sha256, args.expect_multiplier_sha256)

    dependency_paths = {
        "script": Path(__file__),
        "stratum_linear": ENGINE / "stratum_linear.py",
        "stratum_amplitude": ENGINE / "stratum_amplitude.py",
        "grouped": ENGINE / "grouped_fixed_vector.py",
        "integrator": ENGINE / "src/exact_integrator.py",
    }
    if args.output.resolve() in {path.resolve()
                                for path in dependency_paths.values()}:
        raise SystemExit("output path collides with an arithmetic dependency")
    dependencies_start = {key: file_sha(path)
                          for key, path in dependency_paths.items()}
    evaluator = MatrixFreeAffineResidual(
        support, labels, base, scalar)
    forms = evaluator.evaluate_residual_data(
        coefficients, set(coordinates), args.progress)
    dependencies_end = {key: file_sha(path)
                        for key, path in dependency_paths.items()}
    if dependencies_start != dependencies_end or \
            file_sha(args.input_json) != args.expect_input_sha256 or \
            file_sha(args.multiplier_json) != args.expect_multiplier_sha256 or \
            (args.baseline_result_json is not None and
             file_sha(args.baseline_result_json) !=
             args.expect_baseline_sha256):
        raise SystemExit("an input or arithmetic dependency changed during run")

    oracle_status = "not-requested"
    baseline_result_sha = None
    denominator = numerator = quotient = None
    if args.oracle_affine_json is not None:
        oracle_bytes = args.oracle_affine_json.read_bytes()
        oracle = json.loads(oracle_bytes)
        expected = oracle_forms(
            oracle, rational_multiplier, args.linear_cutoff)
        for label in coordinates:
            comparisons = (
                (forms["i_cross"][label], expected[0][label], "I cross"),
                (forms["i_diagonal"][label], expected[1][label], "I diag"),
                (forms["j_cross"][label], expected[2][label], "kJ cross"),
                (forms["j_diagonal"][label], expected[3][label], "kJ diag"),
            )
            for got, wanted, name in comparisons:
                if not form_matches(got, wanted, convert, args.decimal_dps):
                    raise SystemExit(
                        f"oracle mismatch for {label} {name}: "
                        f"got={got}, expected={convert(wanted)}")
        denominator, numerator = expected[4], expected[5]
        quotient = numerator / denominator
        oracle_status = "exact-cross-and-diagonal-match"
    elif args.baseline_result_json is not None:
        _, denominator, numerator, quotient = preloaded_baseline
        baseline_result_sha = args.expect_baseline_sha256
        oracle_status = "pinned-completed-baseline-result"
    elif args.baseline_quotient is not None:
        quotient = args.baseline_quotient

    q_scalar = convert(quotient)
    rows = []
    for label in coordinates:
        a = forms["i_cross"][label]
        b = forms["j_cross"][label]
        d = forms["i_diagonal"][label]
        e = forms["j_diagonal"][label]
        residual = b - q_scalar * a
        two_vector = (two_vector_eigenvalue(
            denominator, numerator, a, b, d, e,
            digits=(args.decimal_dps or 100))
            if denominator is not None and numerator is not None else None)
        rows.append({
            "label": [label[0], CHANNEL_NAMES[label[1]]],
            "i_cross": str(a), "kj_cross": str(b),
            "i_diagonal": str(d), "kj_diagonal": str(e),
            "rayleigh_residual": str(residual),
            "two_vector_quotient_discovery": (str(two_vector)
                                                if two_vector is not None
                                                else None),
        })

    output = {
        "status": "matrix-free-affine-residual-screen",
        "rigorous_forms": args.decimal_dps is None,
        "claim_scope": ("cross and diagonal forms for the listed directions; "
                        "not a full affine matrix or omitted-space upper bound"),
        "input_json": str(args.input_json),
        "input_sha256": args.expect_input_sha256,
        "multiplier_json": str(args.multiplier_json),
        "multiplier_sha256": args.expect_multiplier_sha256,
        "oracle_json": (str(args.oracle_affine_json)
                        if args.oracle_affine_json else None),
        "oracle_status": oracle_status,
        "baseline_result_json": (str(args.baseline_result_json)
                                  if args.baseline_result_json else None),
        "baseline_result_sha256": baseline_result_sha,
        "k": 48,
        "parameters": {key: str(getattr(args, key)) for key in (
            "alpha", "delta", "eta", "beta1", "beta2", "beta3plus")},
        "linear_cutoff": args.linear_cutoff,
        "effective_dimension": len(all_coordinates),
        "screen_dimension": len(coordinates),
        "coordinates": [[r, CHANNEL_NAMES[p]] for r, p in coordinates],
        "decimal_dps": args.decimal_dps,
        "baseline_denominator": str(denominator) if denominator is not None else None,
        "baseline_numerator": str(numerator) if numerator is not None else None,
        "baseline_quotient": str(quotient),
        "rows": rows,
        "i_orbit_groups": forms["i_orbit_groups"],
        "i_faces": forms["i_faces"],
        "i_scalar_lanes": forms["i_scalar_lanes"],
        "marginal_components": forms["marginal_components"],
        "j_common_r": forms["j_common_r"],
        "j_branch_domains": forms["j_branch_domains"],
        "j_scalar_lanes": forms["j_scalar_lanes"],
        "i_seconds": forms["i_seconds"],
        "j_seconds": forms["j_seconds"],
        "total_seconds": forms["total_seconds"],
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "dependency_hashes": dependencies_start,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in (
        "status", "rigorous_forms", "oracle_status", "baseline_quotient",
        "effective_dimension", "screen_dimension", "i_faces",
        "j_common_r", "j_branch_domains", "i_seconds", "j_seconds",
        "total_seconds", "peak_rss_kib")}, indent=2))


if __name__ == "__main__":
    main()
