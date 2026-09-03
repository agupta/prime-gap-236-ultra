#!/usr/bin/env python3
"""Independent, no-import preflight for the C10 sparse-coordinate package.

This checker deliberately does not import the package generator, the grouped
evaluator, or exact_integrator.  It rebuilds the 20 disjoint coordinate blocks,
the 20-to-272 expansion, every signed direction and stored cross action, and
the static grouped-work counts from elementary Fraction arithmetic.

It certifies only package consistency.  The Decimal self-form evaluations are
discovery calculations and are outside this preflight.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache
from itertools import product
from math import comb, factorial
from pathlib import Path


SOURCE_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
BANDS_SHA = "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9"
RECOVERY_SHA = "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43"
MANIFEST_SHA = "967a004ed5f02dc08d07bd9ab8f5af1050b345427327935b96d0979ae531787f"
GENERATOR_SHA = "82ee455d319b770c114428fe98dfc5b76d0dd7ca1d3c095729c60ac2c23fb344"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
PARAMETERS = {
    "alpha": Fraction(79247, 300000),
    "delta": Fraction(1, 100),
    "eta": Fraction(76247, 300000),
    "beta1": Fraction(3, 20),
    "beta2": Fraction(3, 20),
    "beta3plus": Fraction(97, 625),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw: bytes, what: str):
    def pairs(items):
        out = {}
        for key, value in items:
            require(type(key) is str and key not in out,
                    f"{what}: duplicate or non-string key")
            out[key] = value
        return out

    return json.loads(
        raw,
        object_pairs_hook=pairs,
        # Pinned source metadata contains non-authoritative decimal diagnostics.
        # Keep them exact as Decimal; every field consumed below is type-checked
        # independently and all mathematical payloads must be rational strings.
        parse_float=Decimal,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"{what}: nonfinite token {token}")),
    )


def rational(value, what: str) -> Fraction:
    require(type(value) is str and value == value.strip() and value,
            f"{what}: canonical rational string required")
    try:
        answer = Fraction(value)
    except Exception as exc:
        raise ValueError(f"{what}: malformed rational") from exc
    fraction_form = re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?", value)
    decimal_form = re.fullmatch(r"-?(?:0|[1-9][0-9]*)\.[0-9]+", value)
    scientific_form = re.fullmatch(
        r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?E-?[0-9]+", value)
    require(fraction_form is not None or decimal_form is not None or
            scientific_form is not None,
            f"{what}: noncanonical rational syntax")
    if "/" in value:
        require(str(answer) == value, f"{what}: unreduced fraction")
    return answer


def label(value, what: str):
    require(type(value) is list and len(value) == 2 and
            type(value[0]) is int and value[0] >= 0 and
            type(value[1]) is list and
            all(type(x) is int and x >= 2 for x in value[1]) and
            value[1] == sorted(value[1], reverse=True),
            f"{what}: canonical no-ones label required")
    return value[0], tuple(value[1])


def load(path: Path, expected_sha: str, what: str):
    path = path.resolve()
    raw = path.read_bytes()
    require(digest(raw) == expected_sha, f"{what}: SHA mismatch")
    return path, raw, strict_json(raw, what)


def falling(n: int, r: int) -> int:
    return factorial(n) // factorial(n-r)


@lru_cache(maxsize=None)
def orbit_product(lam, mu):
    """Contingency-table derivation of P_lam P_mu structure constants."""
    lam, mu = tuple(sorted(lam, reverse=True)), tuple(sorted(mu, reverse=True))
    if not lam:
        return ((mu, 1),)
    if not mu:
        return ((lam, 1),)
    lc, mc = list(Counter(lam).items()), list(Counter(mu).items())
    lvals, lcnt = zip(*lc)
    mvals, mcnt = zip(*mc)
    aut_l = product_int(factorial(n) for n in lcnt)
    aut_m = product_int(factorial(n) for n in mcnt)
    table = [[0]*len(mvals) for _ in lvals]
    totals = defaultdict(Fraction)

    def rows(cap, caps, j=0, row=()):
        if j == len(caps):
            yield row
            return
        used = sum(row)
        for value in range(min(cap-used, caps[j])+1):
            yield from rows(cap, caps, j+1, row+(value,))

    def visit(i, remaining):
        if i < len(lvals):
            for row in rows(lcnt[i], remaining):
                table[i][:] = row
                visit(i+1, tuple(remaining[j]-row[j]
                                 for j in range(len(mvals))))
            return
        rs = [sum(row) for row in table]
        cs = [sum(table[i][j] for i in range(len(lvals)))
              for j in range(len(mvals))]
        parts = []
        for i, exponent in enumerate(lvals):
            parts += [exponent]*(lcnt[i]-rs[i])
        for j, exponent in enumerate(mvals):
            parts += [exponent]*(mcnt[j]-cs[j])
        for i, left in enumerate(lvals):
            for j, right in enumerate(mvals):
                parts += [left+right]*table[i][j]
        nu = tuple(sorted(parts, reverse=True))
        labeled = product_int(falling(n, used) for n, used in zip(lcnt, rs))
        labeled *= product_int(falling(n, used) for n, used in zip(mcnt, cs))
        cell_aut = product_int(factorial(n) for row in table for n in row)
        require(labeled % cell_aut == 0, "orbit product integrality I")
        labeled //= cell_aut
        aut_nu = product_int(factorial(n) for n in Counter(nu).values())
        coefficient = Fraction(aut_nu*labeled, aut_l*aut_m)
        require(coefficient.denominator == 1, "orbit product integrality II")
        totals[nu] += coefficient

    visit(0, tuple(mcnt))
    return tuple(sorted((nu, int(value)) for nu, value in totals.items()))


def product_int(values) -> int:
    answer = 1
    for value in values:
        answer *= value
    return answer


def split_distinguished(lam, k=48):
    out = []
    if len(lam) < k:
        out.append((0, lam))
    for exponent in sorted(set(lam)):
        rest = list(lam)
        rest.remove(exponent)
        out.append((exponent, tuple(rest)))
    return tuple(out)


def poly_add(target, source, scale=Fraction(1)):
    for monomial, value in source.items():
        target[monomial] += scale*value
        if target[monomial] == 0:
            del target[monomial]


def poly_mul(left, right):
    out = defaultdict(Fraction)
    for (i, j), x in left.items():
        for (u, v), y in right.items():
            out[i+u, j+v] += x*y
    return {key: value for key, value in out.items() if value}


def linear_power(c0, cz, cw, power):
    out = defaultdict(Fraction)
    for i in range(power+1):
        for j in range(power-i+1):
            h = power-i-j
            multinomial = Fraction(factorial(power),
                                   factorial(i)*factorial(j)*factorial(h))
            out[i, j] += multinomial*cz**i*cw**j*c0**h
    return dict(out)


def marginal_poly(r, h, branch, t_exp, residual):
    alpha, delta = PARAMETERS["alpha"], PARAMETERS["delta"]
    u0 = (r+h)*delta
    one_u = (1-u0, Fraction(-1), Fraction(-1))
    if branch == "Sdelta":
        upper, lower = (delta, Fraction(0), Fraction(0)), Fraction(0)
    elif branch in ("Stotal", "Ltotal"):
        upper = (alpha-u0, Fraction(-1), Fraction(-1))
        lower = delta if branch == "Ltotal" else Fraction(0)
    elif branch == "Lbig":
        upper = (beta(r+1)-r*delta, Fraction(-1), Fraction(0))
        lower = delta
    else:
        raise ValueError("unknown branch")
    out = defaultdict(Fraction)
    for j in range(residual+1):
        n = t_exp+j+1
        scale = Fraction((-1)**j*comb(residual, j), n)
        term = poly_mul(linear_power(*one_u, residual-j),
                        linear_power(*upper, n))
        if lower:
            poly_add(term, linear_power(*one_u, residual-j), -lower**n)
        poly_add(out, term, scale)
    return dict(out)


def beta(r):
    require(r > 0, "beta index")
    if r == 1:
        return PARAMETERS["beta1"]
    if r == 2:
        return PARAMETERS["beta2"]
    return PARAMETERS["beta3plus"]


def branch_constraints(r, h, branch):
    alpha, delta = PARAMETERS["alpha"], PARAMETERS["delta"]
    u0 = (r+h)*delta
    hp = []
    if branch.startswith("S") and r:
        cap = beta(r)-r*delta
        if cap <= 0:
            return None
        hp.append((Fraction(1), Fraction(0), cap))
    if branch == "Sdelta":
        hp.append((Fraction(1), Fraction(1), alpha-u0-delta))
    elif branch == "Stotal":
        hp += [(Fraction(-1), Fraction(-1), -(alpha-u0-delta)),
               (Fraction(1), Fraction(1), alpha-u0)]
    elif branch == "Ltotal":
        hp += [(Fraction(0), Fraction(-1),
                -(alpha-beta(r+1)-h*delta)),
               (Fraction(1), Fraction(1), alpha-u0-delta)]
    elif branch == "Lbig":
        if beta(r+1) == alpha and h == 0:
            return None
        hp += [(Fraction(0), Fraction(1), alpha-beta(r+1)-h*delta),
               (Fraction(1), Fraction(0), beta(r+1)-(r+1)*delta)]
    else:
        raise ValueError("unknown branch")
    return tuple(hp)


def clip_polygon(vertices, hp):
    if not vertices:
        return ()
    a, b, c = hp
    out = []
    previous = vertices[-1]
    fp = a*previous[0]+b*previous[1]-c
    previous_in = fp <= 0
    for current in vertices:
        fc = a*current[0]+b*current[1]-c
        current_in = fc <= 0
        if current_in != previous_in:
            t = fp/(fp-fc)
            out.append((previous[0]+t*(current[0]-previous[0]),
                        previous[1]+t*(current[1]-previous[1])))
        if current_in:
            out.append(current)
        previous, fp, previous_in = current, fc, current_in
    clean = []
    for point in out:
        if not clean or point != clean[-1]:
            clean.append(point)
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()
    return tuple(clean)


def positive_domain(r, outer, constraints):
    if r == 0:
        lo, hi = Fraction(0), outer
        for az, aw, cap in constraints:
            require(az == 0 or True, "unreachable")
            if aw > 0:
                hi = min(hi, cap/aw)
            elif aw < 0:
                lo = max(lo, cap/aw)
            elif cap < 0:
                return False
        return hi > lo
    polygon = ((Fraction(0), Fraction(0)),
               (outer, Fraction(0)), (Fraction(0), outer))
    for hp in constraints:
        polygon = clip_polygon(polygon, hp)
        if len(polygon) < 3:
            return False
    twice_area = sum(polygon[i][0]*polygon[(i+1) % len(polygon)][1] -
                     polygon[(i+1) % len(polygon)][0]*polygon[i][1]
                     for i in range(len(polygon)))
    return twice_area != 0


def max_large():
    delta = PARAMETERS["delta"]
    feasible = [r for r in range(1, 49) if r*delta < beta(r)]
    return max(feasible, default=0)


def static_counts(labels, coefficients):
    needed = set()
    for _, lam in labels:
        for _, mu in labels:
            needed.add((lam, mu))
            for _, lr in split_distinguished(lam):
                for _, mr in split_distinguished(mu):
                    needed.add((lr, mr))
    orbit_terms = sum(len(orbit_product(*key)) for key in needed)

    terms = defaultdict(Fraction)
    alpha = PARAMETERS["alpha"]
    for i, (a, lam) in enumerate(labels):
        for j in range(i+1):
            b, mu = labels[j]
            factor = coefficients[i]*coefficients[j]*(1 if i == j else 2)
            for nu, multiplicity in orbit_product(lam, mu):
                for c in range(a+b+1):
                    terms[nu, c] += (factor*multiplicity*comb(a+b, c)*
                                     (1-alpha)**(a+b-c))
    terms = {key: value for key, value in terms.items() if value}

    components = defaultdict(Fraction)
    for coefficient, (a, lam) in zip(coefficients, labels):
        for exponent, rest in split_distinguished(lam):
            components[rest, exponent, a] += coefficient
    components = {key: value for key, value in components.items() if value}
    marginal_orbits = sorted({rest for rest, _, _ in components})
    by_lr = {rest: [(e, a, value) for (lr, e, a), value in components.items()
                    if lr == rest] for rest in marginal_orbits}

    branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
    j_domains = 0
    eta, delta = PARAMETERS["eta"], PARAMETERS["delta"]
    for r in range(min(47, max_large())+1):
        for h in range(int(eta//delta)-r+1):
            outer = eta-(r+h)*delta
            if outer <= 0:
                continue
            nonempty = {}
            for branch in branches:
                constraints = branch_constraints(r, h, branch)
                if constraints is None or not positive_domain(r, outer, constraints):
                    nonempty[branch] = False
                    continue
                block_nonempty = False
                for lr in marginal_orbits:
                    polynomial = defaultdict(Fraction)
                    for e, a, value in by_lr[lr]:
                        poly_add(polynomial, marginal_poly(r, h, branch, e, a),
                                 value)
                    if polynomial:
                        block_nonempty = True
                        break
                nonempty[branch] = block_nonempty
            for i, left in enumerate(branches):
                if not nonempty[left]:
                    continue
                for right in branches[:i+1]:
                    if not nonempty[right]:
                        continue
                    if {left, right} in ({"Sdelta", "Stotal"},
                                        {"Ltotal", "Lbig"}):
                        continue
                    c1, c2 = branch_constraints(r, h, left), branch_constraints(r, h, right)
                    if c1 is not None and c2 is not None and positive_domain(
                            r, outer, c1+c2):
                        j_domains += 1

    alpha_faces = 0
    for r in range(min(48, max_large())+1):
        for h in range(int(PARAMETERS["alpha"]//delta)-r+1):
            if PARAMETERS["alpha"]-(r+h)*delta > 0:
                alpha_faces += 1
    return {
        "direction_labels": len(labels),
        "precomputed_orbit_keys": len(needed),
        "precomputed_orbit_terms": orbit_terms,
        "i_orbit_groups": len({nu for nu, _ in terms}),
        "i_grouped_residual_terms": len(terms),
        "i_faces": alpha_faces,
        "marginal_components": len(components),
        "distinct_marginal_orbits": len(marginal_orbits),
        "j_branch_integrals": j_domains,
    }


def parse_blocks(source, bands):
    labels = [label(value, f"source basis[{i}]")
              for i, value in enumerate(source["basis"])]
    vector = [rational(value, f"source vector[{i}]")
              for i, value in enumerate(source["rational_vector"])]
    require(source.get("k") == 48 and source.get("degree") == 12 and
            source.get("basis_dimension") == 272 and
            len(labels) == len(vector) == len(set(labels)) == 272,
            "source dimensions")
    require(bands.get("source_sha256") == SOURCE_SHA and
            bands.get("compressed_basis_dimension") == 20 and
            bands.get("expanded_term_count") == 272, "bands metadata")
    blocks, names, theta_source = [], [], []
    for i, item in enumerate(bands["core"]):
        item_label = label(item["label"], f"core[{i}]")
        blocks.append({item_label: Fraction(1)})
        names.append(f"core_{i}:{item_label}")
        theta_source.append(rational(item["coefficient"], f"core coefficient {i}"))
    require(len(blocks) == 12, "core count")
    require(set(bands["bands"]) == {str(d) for d in range(5, 13)},
            "band keys")
    for degree in range(5, 13):
        block = {}
        for j, item in enumerate(bands["bands"][str(degree)]):
            item_label = label(item["label"], f"H{degree}[{j}]")
            require(item_label not in block, f"duplicate H{degree} label")
            block[item_label] = rational(item["coefficient"],
                                         f"H{degree}[{j}] coefficient")
        blocks.append(block)
        names.append(f"H{degree}")
        theta_source.append(Fraction(1))
    owner = {}
    for coordinate, block in enumerate(blocks):
        for item_label in block:
            require(item_label not in owner, "overlapping compressed blocks")
            owner[item_label] = coordinate
    require(set(labels) == set(owner), "compressed blocks do not partition source")
    reconstructed = [blocks[owner[x]][x]*theta_source[owner[x]] for x in labels]
    require(reconstructed == vector, "20-to-272 expansion mismatch")
    return labels, blocks, names, theta_source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--bands", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--generator", required=True)
    parser.add_argument("--grouped", required=True)
    parser.add_argument("--integrator", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    paths = {}
    json_names = {"manifest", "source", "bands", "recovery"}
    for name, path, expected in (
        ("manifest", args.manifest, MANIFEST_SHA),
        ("source", args.source, SOURCE_SHA),
        ("bands", args.bands, BANDS_SHA),
        ("recovery", args.recovery, RECOVERY_SHA),
        ("generator", args.generator, GENERATOR_SHA),
        ("grouped", args.grouped, GROUPED_SHA),
        ("integrator", args.integrator, INTEGRATOR_SHA),
    ):
        resolved = Path(path).resolve()
        raw = resolved.read_bytes()
        require(digest(raw) == expected, f"{name}: SHA mismatch")
        paths[name] = (resolved, raw,
                       strict_json(raw, name) if name in json_names else None)
    manifest, source, bands, recovery = (paths[x][2] for x in
                                          ("manifest", "source", "bands", "recovery"))
    labels, blocks, names, theta_source = parse_blocks(source, bands)
    require(manifest.get("status") ==
            "c10-D12-19-coordinate-sparse-self-form-manifest" and
            manifest.get("rigorous") is False and
            manifest.get("theorem_ready") is False and
            manifest.get("no_self_form_values_claimed") is True and
            manifest.get("k") == 48 and manifest.get("degree") == 12 and
            manifest.get("coordinates_included") == list(range(19)),
            "manifest status/dimensions")
    require(manifest.get("parameters") == {key: str(value)
                                            for key, value in PARAMETERS.items()},
            "manifest parameters")
    expected_provenance = {
        "source_sha256": SOURCE_SHA, "bands_sha256": BANDS_SHA,
        "recovery_sha256": RECOVERY_SHA,
        "grouped_evaluator_sha256": GROUPED_SHA,
        "exact_integrator_sha256": INTEGRATOR_SHA,
        "generator_sha256": GENERATOR_SHA,
    }
    require(manifest.get("provenance") == expected_provenance,
            "manifest provenance")
    require(recovery.get("status") ==
            "byte-pinned-recovered-degree-band-gradient-discovery" and
            recovery.get("complete") is True and recovery.get("rigorous") is False and
            recovery.get("source_sha256") == SOURCE_SHA and
            recovery.get("bands_sha256") == BANDS_SHA and
            recovery.get("decimal_dps") == 100, "recovery status")
    theta = [rational(x, f"theta[{i}]") for i, x in enumerate(recovery["theta"])]
    action_a = [rational(x, f"action A[{i}]") for i, x in enumerate(
        recovery["a_theta_exact_fraction_half"])]
    action_b = [rational(x, f"action B[{i}]") for i, x in enumerate(
        recovery["b_theta_exact_fraction_half"])]
    # The producer's MP100 theta is the Decimal-rounded evaluation input;
    # the exact source coefficients above are independently checked through
    # the 20-to-272 identity, but are not byte-identical to those decimals.
    require(len(theta) == len(action_a) == len(action_b) == 20 and
            theta[12:] == [Fraction(1)]*8,
            "recovery compressed coordinates")
    D0 = rational(recovery["denominator"], "D0")
    N0 = rational(recovery["numerator"], "N0")
    require(D0 > N0 > 0, "base form signs")

    entries = manifest.get("full_ranking")
    require(type(entries) is list and len(entries) == 19, "full ranking length")
    require(manifest.get("post_H6_launch_queue") ==
            [entry for entry in entries if entry.get("name") != "H6"],
            "post-H6 queue")
    seen = set()
    report = []
    previous_score = None
    for rank, entry in enumerate(entries):
        require(type(entry) is dict, f"entry {rank} type")
        coordinate = entry.get("coordinate")
        require(type(coordinate) is int and 0 <= coordinate < 19 and
                coordinate not in seen, f"entry {rank} coordinate")
        seen.add(coordinate)
        orientation = entry.get("orientation")
        require(orientation in (-1, 1) and type(orientation) is int,
                f"coordinate {coordinate} orientation")
        raw_residual = D0*action_b[coordinate]-N0*action_a[coordinate]
        require(raw_residual != 0 and orientation == (1 if raw_residual > 0 else -1),
                f"coordinate {coordinate} orientation/residual")
        relative_scale = abs(theta[coordinate])
        score = 2*relative_scale*abs(raw_residual)/D0**2
        require(rational(entry.get("relative_first_order_score"),
                         f"coordinate {coordinate} score") == score,
                f"coordinate {coordinate} score mismatch")
        if previous_score is not None:
            require(previous_score >= score, "ranking not descending")
        previous_score = score
        direction_path = Path(entry.get("path", "")).resolve()
        require(direction_path.parent.name == "sparse_coordinate_scan_all",
                f"coordinate {coordinate} direction directory")
        direction_raw = direction_path.read_bytes()
        require(digest(direction_raw) == entry.get("sha256"),
                f"coordinate {coordinate} direction SHA")
        direction = strict_json(direction_raw, f"direction {coordinate}")
        require(direction.get("status") ==
                "c10-D12-sparse-coordinate-self-form-direction" and
                direction.get("rigorous") is False and
                direction.get("theorem_ready") is False and
                direction.get("fresh_scalar_reevaluation_required") is True and
                direction.get("finite_form_value_claimed") is False and
                direction.get("k") == 48 and direction.get("degree") == 12 and
                direction.get("coordinate") == coordinate and
                direction.get("coordinate_name") == names[coordinate] and
                direction.get("orientation") == orientation and
                direction.get("parameters") == manifest["parameters"] and
                direction.get("provenance") == expected_provenance,
                f"coordinate {coordinate} metadata")
        expected_labels = list(blocks[coordinate])
        got_labels = [label(x, f"direction {coordinate} basis[{i}]")
                      for i, x in enumerate(direction["basis"])]
        got_coefficients = [rational(x, f"direction {coordinate} vector[{i}]")
                            for i, x in enumerate(direction["rational_vector"])]
        expected_coefficients = [orientation*blocks[coordinate][x]
                                 for x in expected_labels]
        require(got_labels == expected_labels and
                got_coefficients == expected_coefficients and
                direction.get("basis_dimension") == len(expected_labels) ==
                entry.get("basis_dimension"),
                f"coordinate {coordinate} exact sparse expansion")
        compressed = [rational(x, f"direction {coordinate} compressed[{i}]")
                      for i, x in enumerate(direction["compressed_direction"])]
        require(compressed == [Fraction(orientation if i == coordinate else 0)
                               for i in range(20)],
                f"coordinate {coordinate} compressed direction")
        cross = direction.get("cross_action")
        require(type(cross) is dict and
                rational(cross.get("denominator_D0"), "cross D0") == D0 and
                rational(cross.get("numerator_N0"), "cross N0") == N0 and
                rational(cross.get("A_cross_a01"), "cross A") ==
                orientation*action_a[coordinate] and
                rational(cross.get("B48_cross_b01"), "cross B") ==
                orientation*action_b[coordinate] and
                rational(cross.get("ascent_residual_R"), "cross R") ==
                abs(raw_residual) and
                rational(cross.get("quotient_first_derivative"), "cross dq") ==
                2*abs(raw_residual)/D0**2 and
                rational(cross.get("relative_coordinate_scale"), "cross scale") ==
                relative_scale and
                rational(cross.get("relative_first_order_score"), "cross score") ==
                score, f"coordinate {coordinate} cross action")
        rebuilt_counts = static_counts(got_labels, got_coefficients)
        require(direction.get("expected_grouped_counts") == rebuilt_counts and
                entry.get("expected_grouped_counts") == rebuilt_counts,
                f"coordinate {coordinate} grouped counts")
        report.append({"rank": rank+1, "coordinate": coordinate,
                       "name": names[coordinate], "orientation": orientation,
                       "sha256": digest(direction_raw),
                       "score": str(score), "counts": rebuilt_counts})
    require(seen == set(range(19)), "coordinate coverage")

    answer = {
        "status": "AUDIT PASS",
        "scope": "independent static preflight; no integral or quotient claim",
        "manifest_sha256": MANIFEST_SHA,
        "generator_sha256": GENERATOR_SHA,
        "directions_checked": len(report),
        "coordinates": report,
    }
    rendered = json.dumps(answer, indent=2)+"\n"
    if args.output:
        output = Path(args.output).resolve()
        trusted = {item[0] for item in paths.values()}
        trusted.update(Path(item["path"]).resolve() for item in entries)
        require(output not in trusted and not output.exists(), "output collision")
        output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
