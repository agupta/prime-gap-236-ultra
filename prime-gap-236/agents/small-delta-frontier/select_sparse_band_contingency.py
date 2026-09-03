#!/usr/bin/env python3
"""Select one sparse 20-band ascent direction from existing first-order data.

No integral is evaluated.  All ranking arithmetic is exact relative to the
serialized recovered Decimal100 action.  The result is a trial direction,
not a finite-step quotient or an optimization claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


SOURCE_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
BANDS_SHA = "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9"
RECOVERY_SHA = "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43"
RAW_SHA = "0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d"
PARAMETERS = {
    "alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
    "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
    "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, label):
    def pairs(items):
        answer = {}
        for key, value in items:
            require(key not in answer, f"{label}: duplicate key {key}")
            answer[key] = value
        return answer

    def constant(value):
        raise ValueError(f"{label}: nonfinite constant {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def label(value):
    require(type(value) is list and len(value) == 2 and
            type(value[0]) is int and type(value[1]) is list and
            all(type(x) is int for x in value[1]), "malformed basis label")
    return (value[0], tuple(value[1]))


def q(value, description):
    require(type(value) is str and value and value.strip() == value,
            f"{description}: rational string")
    answer = Fraction(value)
    require(str(answer) == value or any(character in value for character in ".eE"),
            f"{description}: noncanonical rational")
    return answer


def dot(left, right):
    return sum((x * y for x, y in zip(left, right)), Fraction(0))


def decimal_string(value, digits=60):
    with localcontext() as context:
        context.prec = digits
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def decimal100_fraction(value):
    """The exact rational represented by Decimal100(value).

    This is the scalar conversion used by the sparse producer: its ``theta``
    is not the much longer source Fraction, but this correctly rounded
    Decimal100 value serialized as a decimal string.
    """
    with localcontext() as context:
        context.prec = 100
        rounded = Decimal(value.numerator) / Decimal(value.denominator)
    return Fraction(str(rounded))


def write_exclusive(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        encoded = payload.encode("utf-8")
        offset = 0
        while offset < len(encoded):
            written = os.write(descriptor, encoded[offset:])
            require(written > 0, "short contingency output write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--bands", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    paths = {name: Path(value).resolve() for name, value in
             (("source", args.source), ("bands", args.bands),
              ("recovery", args.recovery), ("self", __file__))}
    output_path = Path(args.output).resolve()
    require(output_path not in set(paths.values()), "output aliases trusted input")
    require(len(set(paths.values())) == len(paths), "trusted input alias")
    start = {name: path.read_bytes() for name, path in paths.items()}
    require(sha(start["source"]) == SOURCE_SHA, "source SHA")
    require(sha(start["bands"]) == BANDS_SHA, "bands SHA")
    require(sha(start["recovery"]) == RECOVERY_SHA, "recovery SHA")
    source = json.loads(start["source"])
    bands = strict_json(start["bands"], "bands")
    recovery = strict_json(start["recovery"], "recovery")
    require(source.get("k") == 48 and source.get("degree") == 12 and
            source.get("basis_dimension") == 272, "source dimensions")
    labels = [label(value) for value in source["basis"]]
    coefficients = [q(value, f"source coefficient {index}")
                    for index, value in enumerate(source["rational_vector"])]
    require(len(labels) == len(coefficients) == 272 and
            len(set(labels)) == 272, "source basis/vector")
    require(bands.get("source_sha256") == SOURCE_SHA and
            bands.get("compressed_basis_dimension") == 20 and
            bands.get("expanded_term_count") == 272, "bands provenance/dimensions")

    blocks = []
    theta0 = []
    names = []
    for index, item in enumerate(bands["core"]):
        item_label = label(item["label"])
        blocks.append({item_label: Fraction(1)})
        theta0.append(q(item["coefficient"], f"core {index}"))
        names.append(f"core_{index}:{item_label}")
    for degree in sorted(bands["bands"], key=int):
        block = {}
        for index, item in enumerate(bands["bands"][degree]):
            item_label = label(item["label"])
            require(item_label not in block, "duplicate label within degree band")
            block[item_label] = q(item["coefficient"],
                                  f"H{degree} coefficient {index}")
        blocks.append(block)
        theta0.append(Fraction(1))
        names.append(f"H{degree}")
    require(len(blocks) == len(theta0) == len(names) == 20, "compressed dimension")
    owner = {}
    weight = {}
    for coordinate, block in enumerate(blocks):
        for item_label, item_weight in block.items():
            require(item_label not in owner, "label has two compressed owners")
            owner[item_label] = coordinate
            weight[item_label] = item_weight
    require(set(owner) == set(labels), "compressed blocks do not partition basis")
    require([weight[item_label] * theta0[owner[item_label]] for item_label in labels]
            == coefficients, "20-to-272 source reconstruction")

    require(recovery.get("status") ==
            "byte-pinned-recovered-degree-band-gradient-discovery" and
            recovery.get("complete") is True and recovery.get("rigorous") is False and
            recovery.get("decimal_dps") == 100 and
            recovery.get("raw_sha256") == RAW_SHA and
            recovery.get("source_sha256") == SOURCE_SHA and
            recovery.get("bands_sha256") == BANDS_SHA,
            "recovery status/provenance")
    require(set(recovery.get("parameters", {})) == set(PARAMETERS) and
            all(Fraction(recovery["parameters"][key]) == value
                for key, value in PARAMETERS.items()), "recovery C10 parameters")
    theta = [Fraction(value) for value in recovery["theta"]]
    a_theta = [Fraction(value) for value in
               recovery["a_theta_exact_fraction_half"]]
    b_theta = [Fraction(value) for value in
               recovery["b_theta_exact_fraction_half"]]
    grad_a = [Fraction(value) for value in recovery["grad_denominator"]]
    grad_b = [Fraction(value) for value in recovery["grad_numerator"]]
    require(all(len(values) == 20 for values in
                (theta, a_theta, b_theta, grad_a, grad_b)), "action dimensions")
    theta0_decimal100 = [decimal100_fraction(value) for value in theta0]
    require(theta == theta0_decimal100,
            "recovery/source Decimal100 compressed base mismatch")
    require(all(2 * x == y for x, y in zip(a_theta, grad_a)) and
            all(2 * x == y for x, y in zip(b_theta, grad_b)),
            "recovered actions are not exact gradient halves")
    denominator = Fraction(recovery["denominator"])
    numerator = Fraction(recovery["numerator"])
    require(denominator > 0 and numerator > 0, "base forms positive")

    residuals = [denominator * b - numerator * a
                 for a, b in zip(a_theta, b_theta)]
    ranking = []
    # Coordinate 19 is H12, fixed at one by the current gauge.  A direction
    # there can be represented projectively by the other 19 coordinates, so
    # exclude it to obtain a genuinely gauge-preserving sparse candidate.
    for index in range(19):
        product = theta[index] * residuals[index]
        require(product != 0, f"zero relative derivative at coordinate {index}")
        sign = 1 if product > 0 else -1
        coordinate_step = sign * theta[index]
        ascent = residuals[index] * coordinate_step
        require(ascent > 0, "direction orientation is not ascent")
        ranking.append((ascent, index, coordinate_step))
    ranking.sort(reverse=True)
    best_ascent, best, best_step = ranking[0]
    direction20 = [Fraction(0)] * 20
    direction20[best] = best_step
    direction272 = [weight[item_label] * direction20[owner[item_label]]
                    for item_label in labels]
    nonzero = [index for index, value in enumerate(direction272) if value]
    require(nonzero and all(owner[labels[index]] == best for index in nonzero),
            "expanded sparse direction support")
    r_direction = dot(direction20, residuals)
    require(r_direction == best_ascent > 0, "exact ascent residual")
    derivative = 2 * r_direction / (denominator * denominator)

    # These action-consistent values display the tiny independent rounding of
    # the stored base forms.  Even granting exact consistency, PSD completions
    # can make the missing self-curvature arbitrarily positive or negative.
    action_denominator = dot(theta, a_theta)
    action_numerator = dot(theta, b_theta)
    require(action_denominator > 0 and action_numerator > 0,
            "action-consistent base forms positive")
    a01_action = dot(direction20, a_theta)
    b01_action = dot(direction20, b_theta)

    result = {
        "status": "exact-first-order-sparse-band-contingency",
        "rigorous": False,
        "finite_form_value_claimed": False,
        "fresh_scalar_reevaluation_required": True,
        "k": 48,
        "parameters": {key: str(value) for key, value in PARAMETERS.items()},
        "bindings": {
            "source_sha256": SOURCE_SHA, "bands_sha256": BANDS_SHA,
            "recovery_sha256": RECOVERY_SHA, "raw_gradient_sha256": RAW_SHA,
            "selector_sha256": sha(start["self"]),
        },
        "selection_rule": (
            "among gauge-preserving coordinates j<19, maximize "
            "abs(theta_j*(D0*(Btheta)_j-N0*(Atheta)_j)); orient d_j so R(d)>0"
        ),
        "base_semantics": (
            "theta is the exact Fraction represented by the producer's "
            "Decimal100 rounding of the source compressed vector; the exact "
            "source fractions are used only to verify the 20-to-272 map"
        ),
        "selected_coordinate": best,
        "selected_name": names[best],
        "compressed_direction": [str(value) for value in direction20],
        "expanded_direction": [str(value) for value in direction272],
        "expanded_nonzero_count": len(nonzero),
        "exact_ascent_residual_R": str(r_direction),
        "exact_directional_derivative": str(derivative),
        "directional_derivative_decimal": decimal_string(derivative),
        "ranking": [{
            "coordinate": index, "name": names[index],
            "relative_step": str(step), "R": str(ascent),
            "directional_derivative": str(2 * ascent / denominator**2),
        } for ascent, index, step in ranking],
        "finite_step_falsification": {
            "formula": (
                "Delta(tau)=N(theta+tau*d)*D0-D(theta+tau*d)*N0="
                "2*tau*R(d)+tau^2*C(d)"
            ),
            "missing_curvature": "C(d)=D0*B11-N0*A11",
            "strict_improvement_criterion_for_tau_positive":
                "C(d)>-2*R(d)/tau",
            "statement": (
                "Existing action data determine R(d) but not A11 or B11. "
                "For action-consistent PSD completions, adding arbitrary M>=0 "
                "to B11 makes C arbitrarily positive, while adding M to A11 "
                "makes C arbitrarily negative. Thus no nonzero finite-step "
                "sign follows without a new scalar/self-form evaluation."
            ),
        },
        "serialized_euler_residuals": {
            "D": str(action_denominator - denominator),
            "N": str(action_numerator - numerator),
        },
        "action_consistent_cross_forms": {
            "A01": str(a01_action), "B01": str(b01_action),
        },
    }

    for name, path in paths.items():
        require(path.read_bytes() == start[name], f"trusted byte changed: {name}")
    rendered = json.dumps(result, indent=2) + "\n"
    write_exclusive(output_path, rendered)
    # Rebind output and every trusted byte after publication.
    require(output_path.read_bytes() == rendered.encode(), "output bytes changed")
    for name, path in paths.items():
        require(path.read_bytes() == start[name],
                f"trusted byte changed after publication: {name}")
    print(json.dumps({
        "status": result["status"], "rigorous": False,
        "output_sha256": sha(output_path.read_bytes()),
        "selected_coordinate": best, "selected_name": names[best],
        "expanded_nonzero_count": len(nonzero),
        "directional_derivative_decimal": decimal_string(derivative),
        "finite_form_value_claimed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
