#!/usr/bin/env python3
"""Exact global contraction for a capped one-band ``k J(F,H)``.

The ordinary marginal implementation expands and multiplies the orbit blocks
of ``m_F`` and ``m_H`` afresh on every ``(r,h,branch)`` face.  This module
uses Fubini before that multiplication.  If

    m_F(u) = sum q[p,lam] (alpha_F-sum(u))**p P_lam(u)

and ``H=sum c[a,mu](1-sum(t))**a P_mu(t)``, first split ``P_mu`` at the
distinguished coordinate and globally collect

    q[p,lam] c[a,mu] P_lam(u) P_(mu minus e)(u).

Only the resulting finite kernel is specialized to a support face.  The
Definition-5 cutoff ``sum(u) <= eta`` is retained literally: it is the outer
simplex in ``evaluate_cross_r``.  In particular, this is *not* the generally
false unconditional symmetrization of the marginal.

All arithmetic here is ``fractions.Fraction``.  The module contains no
floating-point or serialized-matrix path.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction as Q
from math import comb


Q0 = Q(0)
Q1 = Q(1)
BRANCHES = ("Sdelta", "Stotal", "Ltotal", "Lbig")


def scale_vector(vector, scale: int):
    """Return an exactly rescaled coefficient vector.

    The theorem certificate is homogeneous in both input directions.  Keeping
    this elementary operation here makes the common-denominator normalization
    explicit rather than an undocumented preprocessing step.
    """
    if type(scale) is not int or scale == 0:
        raise ValueError("scale must be a nonzero integer")
    return tuple(Q(value) * scale for value in vector)


def dilate_residual_terms(basis, vector, dilation: Q):
    """Return coefficients of ``F(dilation*t)`` in the residual basis.

    For ``L=1-sum(t)``, ``1-dilation*sum(t)=(1-dilation)+dilation*L`` and
    ``P_lam(dilation*t)=dilation**|lam| P_lam(t)``.  Thus this is a finite
    exact binomial transform and introduces no numerical interpolation.
    """
    if not isinstance(dilation, Q) or dilation <= 0:
        raise ValueError("dilation must be a positive Fraction")
    if len(basis) != len(vector):
        raise ValueError("basis/vector mismatch")
    out = defaultdict(Q)
    for coefficient, (a, lam) in zip(vector, basis):
        coefficient = Q(coefficient)
        if not coefficient:
            continue
        orbit_scale = dilation ** sum(lam)
        for b in range(a + 1):
            out[(b, lam)] += (
                coefficient * comb(a, b) *
                (Q1 - dilation) ** (a - b) *
                dilation ** b * orbit_scale)
    return {label: coefficient for label, coefficient in out.items()
            if coefficient}


def monomial_orbit_value(part, coordinates):
    """Evaluate the unnormalised monomial-symmetric orbit exactly.

    A dynamic program assigns each distinct exponent group to coordinate
    positions.  It avoids enumerating permutations (important for the k=48
    production dilation check) and counts every distinct monomial once.
    """
    coordinates = tuple(Q(value) for value in coordinates)
    groups = tuple(sorted(Counter(part).items(), reverse=True))
    target = tuple(count for _, count in groups)
    if sum(target) > len(coordinates):
        return Q0
    start = (0,) * len(groups)
    states = {start: Q1}
    for value in coordinates:
        following = dict(states)  # leave this coordinate unused
        powers = tuple(value ** exponent for exponent, _ in groups)
        for counts, coefficient in states.items():
            for index, needed in enumerate(target):
                if counts[index] >= needed:
                    continue
                updated = list(counts)
                updated[index] += 1
                updated = tuple(updated)
                following[updated] = following.get(updated, Q0) + (
                    coefficient * powers[index])
        states = following
    return states.get(target, Q0)


def evaluate_residual_terms(terms, coordinates):
    """Evaluate an exact residual-basis polynomial at one rational point."""
    coordinates = tuple(Q(value) for value in coordinates)
    residual = Q1 - sum(coordinates, Q0)
    orbit_values = {}
    answer = Q0
    for (power, part), coefficient in terms.items():
        if part not in orbit_values:
            orbit_values[part] = monomial_orbit_value(part, coordinates)
        answer += Q(coefficient) * residual ** power * orbit_values[part]
    return answer


def marginal_polynomial(ei, basis, vector, k: int, alpha: Q):
    """Reconstruct ``m_F`` as ``(power,orbit)->coefficient``.

    This independently states the elementary beta-integral used by the
    direct-full-simplex checker.  ``basis`` represents
    ``(1-sum(t))**a P_lam(t)`` and the distinguished fiber is
    ``0 <= t <= alpha-sum(u)``.
    """
    if type(k) is not int or k < 1 or not isinstance(alpha, Q):
        raise ValueError("invalid marginal parameters")
    if len(basis) != len(vector):
        raise ValueError("basis/vector mismatch")
    out = defaultdict(Q)
    for coefficient, label in zip(vector, basis):
        if not coefficient:
            continue
        a, lam = label
        if (type(a) is not int or a < 0 or type(lam) is not tuple or
                any(type(x) is not int or x <= 0 for x in lam)):
            raise ValueError("invalid polynomial label")
        coefficient = Q(coefficient)
        for exponent, rest in ei.OneStratumSupport.split_at_distinguished(
                lam, k):
            for c in range(a + 1):
                power = exponent + c + 1
                # Integral t^e (alpha-U-t)^c dt, followed by expansion
                # (1-alpha + alpha-U)^(a-c).
                factor = Q(comb(a, c), 1)
                # e! c!/(e+c+1)! = 1/((e+c+1) binom(e+c,e)).
                factor /= (power * comb(exponent + c, exponent))
                out[(power, rest)] += (
                    coefficient * factor * (Q1 - alpha) ** (a - c))
    return {key: value for key, value in out.items() if value}


def distinguished_components(ei, basis, vector, k: int):
    """Collect ``H`` after splitting only its distinguished monomial."""
    if type(k) is not int or k < 1 or len(basis) != len(vector):
        raise ValueError("invalid component input")
    out = defaultdict(Q)
    for coefficient, (a, lam) in zip(vector, basis):
        coefficient = Q(coefficient)
        if not coefficient:
            continue
        for exponent, rest in ei.OneStratumSupport.split_at_distinguished(
                lam, k):
            out[(rest, exponent, a)] += coefficient
    return {key: value for key, value in out.items() if value}


def global_cross_kernel(ei, marginal, components):
    """Collect all angular orbit products once.

    The output is ``orbit -> {(inner_power,t_exponent,H_residual): coeff}``.
    It is independent of the cap schedule, endpoint, face, and branch.
    """
    out = {}
    input_pairs = 0
    expanded_products = 0
    for (power, left_orbit), left_coefficient in marginal.items():
        for (right_orbit, exponent, residual), right_coefficient in \
                components.items():
            input_pairs += 1
            coefficient = Q(left_coefficient) * Q(right_coefficient)
            if not coefficient:
                continue
            key = (power, exponent, residual)
            for orbit, multiplicity in ei.multiply_monomial_orbits(
                    left_orbit, right_orbit):
                destination = out.setdefault(orbit, defaultdict(Q))
                destination[key] += coefficient * multiplicity
                if not destination[key]:
                    del destination[key]
                expanded_products += 1
    cleaned = {orbit: dict(block) for orbit, block in out.items() if block}
    return cleaned, {
        "marginal_terms": len(marginal),
        "distinguished_components": len(components),
        "input_pairs": input_pairs,
        "expanded_orbit_products": expanded_products,
        "output_orbits": len(cleaned),
        "output_kernel_terms": sum(map(len, cleaned.values())),
    }


def _add_poly(target, source, factor=Q1):
    if not factor:
        return
    for monomial, coefficient in source.items():
        target[monomial] += factor * coefficient
        if not target[monomial]:
            del target[monomial]


def _canonical_domain(frontier, dummy, dimension, r, outer, constraints):
    return frontier.canonical_domain_key(
        dummy, dimension, r, outer, constraints)


def evaluate_cross_r(frontier, kernel, *, support, alpha_f: Q, eta: Q,
                     common_r: int, progress=False):
    """Evaluate one exact common-large-count shard of ``J(F,H)``.

    ``support`` is one endpoint of the right-hand capped support.  The left
    marginal comes from a full simplex of radius ``alpha_f``.  The guard
    ``eta <= alpha_f`` makes its residual support constraint redundant, while
    the Definition-5 cutoff remains exactly ``sum(u)<=eta``.
    """
    if (not isinstance(alpha_f, Q) or not isinstance(eta, Q) or
            not Q0 < eta <= alpha_f or type(common_r) is not int or
            not 0 <= common_r < support.k):
        raise ValueError("invalid cross-shard parameters")
    k = support.k
    dimension = k - 1
    max_h = int(eta // support.delta) - common_r
    if max_h < 0:
        return Q0, {
            "faces": 0, "active_branches": 0, "geometric_groups": 0,
            "nonzero_integrals": 0, "max_integrand_monomials": 0,
        }
    dummy = frontier.GroupedEvaluator(support, [], [], Q)
    total = Q0
    faces = active_branches = geometric_groups = nonzero_integrals = 0
    max_integrand_monomials = 0
    # The angular density depends on (orbit,r,h), never on the t branch.
    for h in range(max_h + 1):
        outer = eta - (common_r + h) * support.delta
        if outer <= 0:
            continue
        u0 = (common_r + h) * support.delta
        inner_powers = {}
        marginal_primitives = {}
        densities = {}
        grouped = {}
        for branch in BRANCHES:
            constraints = support._branch_constraints(common_r, h, branch)
            if constraints is None:
                continue
            domain = _canonical_domain(
                frontier, dummy, dimension, common_r, outer, constraints)
            if domain is None:
                continue
            active_branches += 1
            integrand = grouped.setdefault(domain, defaultdict(Q))
            for orbit, block in kernel.items():
                density = densities.get(orbit)
                if density is None:
                    density = dummy.orbit_density(
                        dimension, orbit, common_r, h, max_h)
                    densities[orbit] = density
                if not density:
                    continue
                angular = defaultdict(Q)
                for (power, exponent, residual), coefficient in block.items():
                    if power not in inner_powers:
                        inner_powers[power] = dict(frontier.ei._linear_power(
                            alpha_f - u0, -Q1, -Q1, power))
                    primitive_key = (branch, exponent, residual)
                    if primitive_key not in marginal_primitives:
                        marginal_primitives[primitive_key] = dict(
                            support._marginal_poly(
                                common_r, h, branch, exponent, residual))
                    primitive = marginal_primitives[primitive_key]
                    if primitive:
                        _add_poly(
                            angular,
                            frontier.ei._poly_mul(
                                inner_powers[power], primitive),
                            coefficient)
                if angular:
                    _add_poly(
                        integrand,
                        frontier.ei._poly_mul(density, dict(angular)), Q1)
        geometric_groups += len(grouped)
        for domain, integrand in grouped.items():
            if integrand:
                nonzero_integrals += 1
                max_integrand_monomials = max(
                    max_integrand_monomials, len(integrand))
                total += frontier.integrate_canonical_domain(
                    dict(integrand), domain)
        faces += 1
        if progress:
            print(
                f"cross r={common_r} h={h}/{max_h} "
                f"branches={active_branches} groups={geometric_groups} "
                f"integrals={nonzero_integrals}",
                flush=True)
        dummy.clear_face_caches(clear_marginals=True)
    dummy.clear_radial_caches()
    return total, {
        "faces": faces,
        "active_branches": active_branches,
        "geometric_groups": geometric_groups,
        "nonzero_integrals": nonzero_integrals,
        "max_integrand_monomials": max_integrand_monomials,
    }


def evaluate_band_cross(frontier, kernel, *, high, low, alpha_f: Q,
                        eta: Q, common_strata=None, progress=False):
    """Return exact ``k*(J_high-J_low)`` and per-stratum diagnostics."""
    if (high.k != low.k or high.delta != low.delta or
            tuple(high.schedule) != tuple(low.schedule)):
        raise ValueError("band endpoint geometry mismatch")
    k = high.k
    selected = (range(min(k - 1, high.max_large(),
                          int(eta // high.delta)) + 1)
                if common_strata is None else tuple(common_strata))
    if any(type(r) is not int or not 0 <= r < k for r in selected):
        raise ValueError("invalid common stratum list")
    raw = Q0
    rows = []
    for r in selected:
        high_value, high_stats = evaluate_cross_r(
            frontier, kernel, support=high, alpha_f=alpha_f, eta=eta,
            common_r=r, progress=progress)
        low_value, low_stats = evaluate_cross_r(
            frontier, kernel, support=low, alpha_f=alpha_f, eta=eta,
            common_r=r, progress=progress)
        difference = high_value - low_value
        raw += difference
        rows.append({"common_r": r, "high_J": high_value,
                     "low_J": low_value, "band_J": difference,
                     "high_stats": high_stats, "low_stats": low_stats})
    return k * raw, rows


def square_residual_terms(ei, terms):
    """Globally collect a polynomial square in the residual-orbit basis."""
    items = [(key, Q(value)) for key, value in terms.items() if value]
    out = defaultdict(Q)
    for i, ((a, lam), left) in enumerate(items):
        for j in range(i + 1):
            (b, mu), right = items[j]
            coefficient = left * right * (1 if i == j else 2)
            for orbit, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                out[(a + b, orbit)] += coefficient * multiplicity
    grouped = defaultdict(dict)
    for (power, orbit), coefficient in out.items():
        if coefficient:
            grouped[orbit][power] = coefficient
    return dict(grouped)


def cross_residual_terms(ei, left, right):
    """Globally collect a polynomial product in the residual-orbit basis."""
    out = defaultdict(Q)
    for (a, lam), lc in left.items():
        if not lc:
            continue
        for (b, mu), rc in right.items():
            if not rc:
                continue
            for orbit, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                out[(a + b, orbit)] += Q(lc) * Q(rc) * multiplicity
    grouped = defaultdict(dict)
    for (power, orbit), coefficient in out.items():
        if coefficient:
            grouped[orbit][power] = coefficient
    return dict(grouped)


def primitive_tagged_families(kernel, *, alpha_f: Q, delta: Q,
                              coefficient_map=None):
    """Convert the global kernel to three exact antiderivative families.

    Tags are ``(fiber_power, inner_slack_power)`` and coefficients are
    symmetric polynomials in the shared variables.  The second affine factor
    is always ``alpha_f-U``.  This is possible because

        (1-U)^q = sum_s binom(q,s) (1-alpha_f)^(q-s)
                              (alpha_f-U)^s.

    ``small`` integrates ``0<=t<=delta``; ``small_total`` integrates
    ``0<=t<=alpha-U``; and ``large`` integrates ``delta<=t<=delta+q``
    with the first tagged affine equal to ``q``.
    """
    if not isinstance(alpha_f, Q) or not isinstance(delta, Q):
        raise ValueError("tagged primitive parameters must be Fractions")
    coefficient_map = (lambda value: value) if coefficient_map is None \
        else coefficient_map
    families = {
        "small": defaultdict(lambda: defaultdict(Q)),
        "small_total": defaultdict(lambda: defaultdict(Q)),
        "large": defaultdict(lambda: defaultdict(Q)),
    }
    source_terms = expanded_terms = 0
    for orbit, block in kernel.items():
        for (inner_power, exponent, residual), coefficient in block.items():
            source_terms += 1
            coefficient = coefficient_map(coefficient)
            for j in range(residual + 1):
                remaining = residual - j
                endpoint_power = exponent + j + 1
                base = (coefficient * ((-1) ** j) *
                        comb(residual, j) / endpoint_power)
                for s in range(remaining + 1):
                    slack_power = inner_power + s
                    common = (base * comb(remaining, s) *
                              (Q1 - alpha_f) ** (remaining - s))
                    families["small"][(0, slack_power)][orbit] += (
                        common * delta ** endpoint_power)
                    families["small_total"][
                        (endpoint_power, slack_power)][orbit] += common
                    for fiber_power in range(1, endpoint_power + 1):
                        families["large"][(fiber_power, slack_power)][
                            orbit] += (common * comb(endpoint_power, fiber_power) *
                                      delta ** (endpoint_power - fiber_power))
                    expanded_terms += endpoint_power + 2
    cleaned = {}
    for family, tagged in families.items():
        cleaned[family] = {
            tag: {orbit: value for orbit, value in polynomial.items() if value}
            for tag, polynomial in tagged.items()
        }
        cleaned[family] = {
            tag: polynomial for tag, polynomial in cleaned[family].items()
            if polynomial
        }
    return cleaned, {
        "source_kernel_terms": source_terms,
        "literal_antiderivative_expansions": expanded_terms,
        "family_tag_counts": {
            family: len(tagged) for family, tagged in cleaned.items()},
        "family_orbit_tag_entries": {
            family: sum(map(len, tagged.values()))
            for family, tagged in cleaned.items()},
    }


def radialize_tagged_families(radial_backend, families, *,
                              number_variables: int, number_large: int,
                              delta: Q, maximum_shift: int):
    """Radialize every family with one exact transform per angular orbit."""
    flat = {}
    for family, tagged in families.items():
        for (fiber_power, slack_power), polynomial in tagged.items():
            flat[(family, fiber_power, slack_power)] = polynomial
    transformed = radial_backend._radialize_tagged_targets(
        flat, number_variables, number_large, delta, maximum_shift)
    by_family = defaultdict(dict)
    for (family, fiber_power, slack_power), radial in transformed.items():
        by_family[family][(fiber_power, slack_power)] = radial
    return {
        family: radial_backend._pack_tagged_radials_by_shift(tagged)
        for family, tagged in by_family.items()
    }


def _positive_min(*values):
    return min(values)


def scheduled_cross_branch_jobs(radial_backend, *, k: int, alpha: Q,
                                eta: Q, delta: Q, schedule, common_r: int):
    """Literal four-branch domains for one right-hand support endpoint.

    The aggregate variables are the shifted sum of ``common_r`` large shared
    coordinates and the unshifted sum of the remaining shared coordinates.
    Inclusion--exclusion shifts of the latter are applied inside the radial
    integrator, which also translates ``y_lower/y_upper/total_lower``.
    """
    if (type(k) is not int or k < 1 or type(common_r) is not int or
            not 0 <= common_r < k or not Q0 < eta < alpha or
            not Q0 < delta or not schedule):
        raise ValueError("invalid scheduled cross geometry")
    schedule = tuple(schedule)

    def beta(r):
        if r <= 0:
            raise ValueError("positive cap index required")
        return schedule[min(r, len(schedule)) - 1]

    cutoff = eta - common_r * delta
    if cutoff <= 0:
        return []
    shared_cap = None if common_r == 0 else beta(common_r) - common_r * delta
    jobs = []
    # Distinguished coordinate is small and its whole [0,delta] interval is
    # available.  The total-bound minimum retains eta even away from the
    # historical special case alpha-eta=delta.
    small_total_bound = min(cutoff, alpha - (common_r + 1) * delta)
    if ((shared_cap is None or shared_cap > 0) and small_total_bound > 0):
        jobs.append((
            "Sdelta", "small",
            radial_backend.AggregateDomain(
                total_bound=small_total_bound, x_bound=shared_cap),
            (Q0, Q0, Q0)))

    # Truncated small fiber: alpha-delta <= U <= eta and 0<=t<=alpha-U.
    if ((shared_cap is None or shared_cap > 0) and
            cutoff > alpha - (common_r + 1) * delta):
        jobs.append((
            "Stotal", "small_total",
            radial_backend.AggregateDomain(
                total_bound=cutoff, x_bound=shared_cap,
                total_lower=alpha - (common_r + 1) * delta),
            (alpha - common_r * delta, -Q1, -Q1)))

    # A large distinguished coordinate exists only when the total-(r+1) cap
    # leaves positive translated mass q=t-delta.
    large_cap = beta(common_r + 1) - (common_r + 1) * delta
    if large_cap > 0:
        large_total_bound = min(cutoff, alpha - (common_r + 1) * delta)
        threshold = alpha - beta(common_r + 1)
        if large_total_bound > 0:
            jobs.append((
                "Ltotal", "large",
                radial_backend.AggregateDomain(
                    total_bound=large_total_bound, y_lower=threshold),
                (alpha - (common_r + 1) * delta, -Q1, -Q1)))
        jobs.append((
            "Lbig", "large",
            radial_backend.AggregateDomain(
                total_bound=cutoff, x_bound=large_cap,
                y_upper=threshold),
            (large_cap, -Q1, Q0)))
    return jobs


def evaluate_radialized_cross_endpoint_with_inner(
        radial_backend, packed_families, *, k: int, alpha: Q,
        alpha_f: Q, eta: Q, delta: Q, schedule, common_r: int):
    """Integrate one radialized exact cross shard at one endpoint."""
    jobs = scheduled_cross_branch_jobs(
        radial_backend, k=k, alpha=alpha, eta=eta, delta=delta,
        schedule=schedule, common_r=common_r)
    second_affine = (
        alpha_f - common_r * delta, -Q1, -Q1)
    values = {}
    for branch, family, domain, fiber_affine in jobs:
        values[branch] = radial_backend._integrate_tagged_radial_polynomials(
            None, common_r, (k - 1) - common_r, delta, domain,
            first_affine=fiber_affine, second_affine=second_affine,
            packed_by_shift=packed_families[family])
    return sum(values.values(), Q0), values


def radialized_band_cross_r(radial_backend, families, *, k: int,
                            alpha_high: Q, alpha_low: Q, alpha_f: Q,
                            eta: Q, delta: Q, schedule, common_r: int):
    """Exact ``k(J_high-J_low)`` for one common-large-count shard."""
    cutoff = eta - common_r * delta
    if cutoff <= 0:
        return Q0, {"high": {}, "low": {}, "radial_shift_count": 0}
    maximum_shift = radial_backend._maximum_active_shift(cutoff, delta)
    packed = radialize_tagged_families(
        radial_backend, families, number_variables=k - 1,
        number_large=common_r, delta=delta, maximum_shift=maximum_shift)
    high, high_branches = evaluate_radialized_cross_endpoint_with_inner(
        radial_backend, packed, k=k, alpha=alpha_high, alpha_f=alpha_f,
        eta=eta, delta=delta, schedule=schedule, common_r=common_r)
    low, low_branches = evaluate_radialized_cross_endpoint_with_inner(
        radial_backend, packed, k=k, alpha=alpha_low, alpha_f=alpha_f,
        eta=eta, delta=delta, schedule=schedule, common_r=common_r)
    return k * (high - low), {
        "high": high_branches, "low": low_branches,
        "radial_shift_count": len(set().union(*(
            set(block) for block in packed.values()))) if packed else 0,
    }


def radialized_band_i_r(radial_backend, square, *, k: int,
                        alpha_high: Q, alpha_low: Q, delta: Q, schedule,
                        number_large: int):
    """Exact band ``I`` shard for a globally collected residual square."""
    if not 0 <= number_large <= k:
        raise ValueError("I stratum outside dimension")
    schedule = tuple(schedule)

    def beta(r):
        return schedule[min(r, len(schedule)) - 1]

    maximum_total = alpha_high - number_large * delta
    if maximum_total <= 0:
        return Q0, {"high": Q0, "low": Q0}
    maximum_shift = radial_backend._maximum_active_shift(
        maximum_total, delta)
    tagged = {(0, power): {orbit: coefficient
                           for orbit, residuals in square.items()
                           if (coefficient := residuals.get(power)) is not None}
              for power in sorted({p for residuals in square.values()
                                   for p in residuals})}
    tagged = {tag: poly for tag, poly in tagged.items() if poly}
    radials = radial_backend._radialize_tagged_targets(
        tagged, k, number_large, delta, maximum_shift)
    packed = radial_backend._pack_tagged_radials_by_shift(radials)
    second_affine = (
        Q1 - number_large * delta, -Q1, -Q1)

    def endpoint(alpha):
        total_bound = alpha - number_large * delta
        if total_bound <= 0:
            return Q0
        cap = None if number_large == 0 else \
            beta(number_large) - number_large * delta
        if cap is not None and cap <= 0:
            return Q0
        return radial_backend._integrate_tagged_radial_polynomials(
            None, number_large, k - number_large, delta,
            radial_backend.AggregateDomain(
                total_bound=total_bound, x_bound=cap),
            first_affine=(Q0, Q0, Q0),
            second_affine=second_affine, packed_by_shift=packed)

    high, low = endpoint(alpha_high), endpoint(alpha_low)
    return high - low, {"high": high, "low": low}
