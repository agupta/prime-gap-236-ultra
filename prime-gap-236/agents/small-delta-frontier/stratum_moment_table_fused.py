#!/usr/bin/env python3
"""Fused SoA orbit products for fixed-base L/Z stratum moments.

The unfused prototype contracts each distinguished moment pair (j,k)
separately.  This module traverses every marginal-orbit-key pair once per
branch domain and carries all (j,k) payloads in a structure-of-arrays map.
The scalar aggregate integrations remain separate exact outputs.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from fractions import Fraction

from stratum_moment_table import (
    BRANCHES,
    StratumMomentTableEvaluator,
    aggregate_powers,
    channel_powers,
)

import exact_integrator as ei
from grouped_fixed_vector import add_poly


def moment_tag_schema(degree: int):
    """Canonical, JSON-safe tag inventory for one branch domain."""
    channels = [list(x) for x in channel_powers(degree)]
    i_tags = [list(x) for x in aggregate_powers(2 * degree)]
    same_products = [[j, k] for j in range(degree + 1)
                     for k in range(j + 1)]
    cross_products = [[j, k] for j in range(degree + 1)
                      for k in range(degree + 1)]
    same_moments = [[j, k, u, v]
                    for j, k in same_products
                    for u, v in aggregate_powers(2 * degree - j - k)]
    cross_moments = [[j, k, u, v]
                     for j, k in cross_products
                     for u, v in aggregate_powers(2 * degree - j - k)]
    return {
        "degree": degree,
        "channels": channels,
        "i_tags": i_tags,
        "same_branch_product_tags": same_products,
        "cross_branch_product_tags": cross_products,
        "same_branch_scalar_tags": same_moments,
        "cross_branch_scalar_tags": cross_moments,
    }


def canonical_schema_bytes(degree: int):
    return json.dumps(moment_tag_schema(degree), sort_keys=True,
                      separators=(",", ":")).encode()


def canonical_schema_sha256(degree: int):
    return hashlib.sha256(canonical_schema_bytes(degree)).hexdigest()


def validate_moment_tag_schema(value, degree: int):
    if type(degree) is not int or value != moment_tag_schema(degree):
        raise ValueError("noncanonical fused moment tag schema")
    # Equality already fixes order and values; these explicit type checks keep
    # Boolean integers and tuple/list coercions from being silently accepted.
    if type(value.get("degree")) is not int:
        raise ValueError("fused moment degree type")
    for key in ("channels", "i_tags", "same_branch_product_tags",
                "cross_branch_product_tags", "same_branch_scalar_tags",
                "cross_branch_scalar_tags"):
        if type(value.get(key)) is not list or any(type(row) is not list or
                                                   any(type(x) is not int
                                                       for x in row)
                                                   for row in value[key]):
            raise ValueError(f"fused moment tag types: {key}")
    return True


class FusedStratumMomentTableEvaluator(StratumMomentTableEvaluator):
    """Moment-table evaluator with one SoA orbit traversal per branch domain."""

    def _fused_density_product_polynomials(
            self, left_moments, right_moments, moment_pairs,
            dimension, r, h, max_h):
        """Return every tagged density product after one orbit-pair traversal.

        `combined[nu][(j,k)]` is an SoA payload.  The structure constants and
        density for `nu` are visited once, while polynomial multiplication is
        still performed for each nonzero tag carried by an orbit-key pair.
        """
        pairs = tuple(moment_pairs)
        left_by_orbit = defaultdict(list)
        right_by_orbit = defaultdict(list)
        used_left = {j for j, _ in pairs}
        used_right = {k for _, k in pairs}
        for j in sorted(used_left):
            for orbit, polynomial in left_moments[j].items():
                if polynomial:
                    left_by_orbit[orbit].append((j, polynomial))
        for k in sorted(used_right):
            for orbit, polynomial in right_moments[k].items():
                if polynomial:
                    right_by_orbit[orbit].append((k, polynomial))
        allowed = set(pairs)
        combined = {}
        orbit_pair_visits = tagged_polynomial_multiplies = 0
        for left_orbit in sorted(left_by_orbit):
            left_rows = left_by_orbit[left_orbit]
            for right_orbit in sorted(right_by_orbit):
                right_rows = right_by_orbit[right_orbit]
                active = [(j, k, p, q)
                          for j, p in left_rows for k, q in right_rows
                          if (j, k) in allowed]
                if not active:
                    continue
                orbit_pair_visits += 1
                expansions = ei.multiply_monomial_orbits(
                    left_orbit, right_orbit)
                for j, k, left_poly, right_poly in active:
                    product = ei._poly_mul(left_poly, right_poly)
                    tagged_polynomial_multiplies += 1
                    for nu, multiplicity in expansions:
                        tags = combined.setdefault(nu, {})
                        destination = tags.setdefault(
                            (j, k), defaultdict(self.scalar))
                        add_poly(destination, product,
                                 self.scalar(multiplicity))

        answer = {pair: defaultdict(self.scalar) for pair in pairs}
        density_visits = density_tag_contractions = 0
        for nu in sorted(combined):
            density = self.orbit_density(dimension, nu, r, h, max_h)
            if not density:
                continue
            density_visits += 1
            for pair in sorted(combined[nu]):
                marginal = dict(combined[nu][pair])
                add_poly(answer[pair], ei._poly_mul(density, marginal),
                         self.one)
                density_tag_contractions += 1
        result = {pair: dict(polynomial) for pair, polynomial in answer.items()
                  if polynomial}
        return result, {
            "orbit_pair_visits": orbit_pair_visits,
            "tagged_polynomial_multiplies": tagged_polynomial_multiplies,
            "density_visits": density_visits,
            "density_tag_contractions": density_tag_contractions,
        }

    def evaluate_j_r_moments(self, lrs, by_lr, r, progress=False):
        answer = defaultdict(self.scalar)
        dimension = self.support.k - 1
        branch_domains = fused_traversals = logical_products = 0
        scalar_integrals = orbit_pair_visits = tagged_multiplies = 0
        density_visits = density_tag_contractions = 0
        max_h = int(self.support.eta // self.support.delta) - r
        if max_h < 0:
            return {}, {
                "branch_domains": 0, "fused_traversals": 0,
                "logical_moment_products": 0, "scalar_integrals": 0,
                "orbit_pair_visits": 0, "tagged_polynomial_multiplies": 0,
                "density_visits": 0, "density_tag_contractions": 0,
            }
        for h in range(max_h + 1):
            if dimension == 0 and (r != 0 or h != 0):
                continue
            outer = self.support.eta - (r + h) * self.support.delta
            if outer <= 0:
                continue
            blocks = self._moment_branch_blocks(
                lrs, by_lr, r, h, dimension, outer)
            aggregate = {power: self._aggregate_polynomial(r, h, *power)
                         for power in self.aggregate_moments}
            for left_index, left_branch in enumerate(BRANCHES):
                for right_branch in BRANCHES[:left_index + 1]:
                    constraints = self._active_branch_pair(
                        blocks, left_branch, right_branch,
                        dimension, r, h, outer)
                    if constraints is None:
                        continue
                    branch_domains += 1
                    same_branch = left_branch == right_branch
                    moment_pairs = tuple(
                        ((j, k) for j in range(self.degree + 1)
                         for k in range(j + 1)) if same_branch else
                        ((j, k) for j in range(self.degree + 1)
                         for k in range(self.degree + 1)))
                    bases, counters = self._fused_density_product_polynomials(
                        blocks[left_branch], blocks[right_branch], moment_pairs,
                        dimension, r, h, max_h)
                    fused_traversals += 1
                    logical_products += len(bases)
                    orbit_pair_visits += counters["orbit_pair_visits"]
                    tagged_multiplies += counters[
                        "tagged_polynomial_multiplies"]
                    density_visits += counters["density_visits"]
                    density_tag_contractions += counters[
                        "density_tag_contractions"]
                    left_class = self._class(left_branch)
                    right_class = self._class(right_branch)
                    for (j, k), base in sorted(bases.items()):
                        maximum = 2 * self.degree - j - k
                        for u, v in aggregate_powers(maximum):
                            value = self.integrate_domain(
                                ei._poly_mul(base, aggregate[(u, v)]),
                                dimension, r, outer, constraints)
                            key = (left_class, right_class, j, k, u, v)
                            self._add_j_value(answer, key, value)
                            if not same_branch:
                                mirror = (right_class, left_class,
                                          k, j, u, v)
                                self._add_j_value(answer, mirror, value)
                            elif j != k:
                                mirror = (left_class, right_class,
                                          k, j, u, v)
                                self._add_j_value(answer, mirror, value)
                            scalar_integrals += 1
            if progress:
                print(f"fused J r={r} h={h} domains={branch_domains} "
                      f"traversals={fused_traversals} "
                      f"logical={logical_products} moments={scalar_integrals}",
                      flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        counters = {
            "branch_domains": branch_domains,
            "fused_traversals": fused_traversals,
            "logical_moment_products": logical_products,
            "scalar_integrals": scalar_integrals,
            "orbit_pair_visits": orbit_pair_visits,
            "tagged_polynomial_multiplies": tagged_multiplies,
            "density_visits": density_visits,
            "density_tag_contractions": density_tag_contractions,
        }
        return dict(answer), counters

    def evaluate_j_moments(self, progress=False):
        _, lrs, by_lr = self._j_component_data()
        values = {}
        totals = {
            "branch_domains": 0, "fused_traversals": 0,
            "logical_moment_products": 0, "scalar_integrals": 0,
            "orbit_pair_visits": 0, "tagged_polynomial_multiplies": 0,
            "density_visits": 0, "density_tag_contractions": 0,
        }
        for r in self._r_values_j():
            block, counters = self.evaluate_j_r_moments(
                lrs, by_lr, r, progress)
            values[r] = block
            for key in totals:
                totals[key] += counters[key]
        return values, len(self.marginal_components()), totals

    def evaluate_moment_forms(self, progress=False):
        i, groups, i_faces, i_scalar = self.evaluate_i_moments(progress)
        j, components, counters = self.evaluate_j_moments(progress)
        labels, a, b = self.assemble_dense_from_moments(i, j)
        return {
            "degree": self.degree,
            "tag_schema": moment_tag_schema(self.degree),
            "tag_schema_sha256": canonical_schema_sha256(self.degree),
            "channel_powers": self.moment_channels,
            "labels": labels,
            "a_matrix": a,
            "b_matrix": b,
            "i_moments": i,
            "j_moments": j,
            "i_orbit_groups": groups,
            "i_faces": i_faces,
            "i_scalar_moment_integrals": i_scalar,
            "marginal_components": components,
            "j_branch_domains": counters["branch_domains"],
            "j_fused_traversals": counters["fused_traversals"],
            "j_logical_moment_products": counters[
                "logical_moment_products"],
            "j_scalar_moment_integrals": counters["scalar_integrals"],
            "j_orbit_pair_visits": counters["orbit_pair_visits"],
            "j_tagged_polynomial_multiplies": counters[
                "tagged_polynomial_multiplies"],
            "j_density_visits": counters["density_visits"],
            "j_density_tag_contractions": counters[
                "density_tag_contractions"],
        }


__all__ = [
    "FusedStratumMomentTableEvaluator", "canonical_schema_bytes",
    "canonical_schema_sha256", "moment_tag_schema",
    "validate_moment_tag_schema",
]
