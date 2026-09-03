#!/usr/bin/env python3
"""Build three explicit C10 D12 trials on the sparse H6 band line.

This script performs no integration.  It consumes the byte-pinned recovered
Decimal100 action, independently reconstructs its 20-to-272 band map, and
publishes three exact rational vectors plus the 11-label H6 direction.  Every
output remains discovery-only until a fresh scalar/self-form evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SOURCE_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
BANDS_SHA = "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9"
RECOVERY_SHA = "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43"
RAW_SHA = "0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d"
OPERATOR_SHA = "e1545435f0c7ad22a17115ac46c291436c1ead5101fd3de6d2a80ab65bc9c257"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
PARAMETERS = {
    "alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
    "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
    "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625),
}
STEPS = (("h6_5pct", Fraction(1, 20)),
         ("h6_10pct", Fraction(1, 10)),
         ("h6_20pct", Fraction(1, 5)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, description):
    def pairs(items):
        answer = {}
        for key, value in items:
            require(type(key) is str and key not in answer,
                    f"{description}: duplicate/non-string key {key!r}")
            answer[key] = value
        return answer

    def constant(value):
        raise ValueError(f"{description}: nonfinite constant {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def parse_fraction(value, description):
    require(type(value) is str and value and value == value.strip(),
            f"{description}: expected rational string")
    try:
        answer = Fraction(value)
    except Exception as exc:
        raise ValueError(f"{description}: malformed rational") from exc
    return answer


def parse_label(value, description):
    require(type(value) is list and len(value) == 2 and
            type(value[0]) is int and value[0] >= 0 and
            type(value[1]) is list and
            all(type(x) is int and x >= 2 for x in value[1]),
            f"{description}: malformed no-ones label")
    return value[0], tuple(value[1])


def decimal100_fraction(value):
    with localcontext() as context:
        context.prec = 100
        rounded = Decimal(value.numerator) / Decimal(value.denominator)
    return Fraction(str(rounded))


def decimal_display(value, digits=70):
    with localcontext() as context:
        context.prec = digits
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def write_all_through_owned_fds(rendered, trusted):
    """Publish only through held O_EXCL fds, then rebind every byte/inode."""
    destinations = list(rendered)
    require(len(set(destinations)) == len(destinations), "output path alias")
    require(not set(destinations) & set(trusted), "output aliases trusted byte")
    for path in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
    descriptors = {}
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        for path in destinations:
            descriptor = os.open(path, flags, 0o600)
            descriptors[path] = descriptor
            mode = os.fstat(descriptor).st_mode
            require(stat.S_ISREG(mode), f"non-regular reserved output {path}")
        for path, descriptor in descriptors.items():
            payload = rendered[path]
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                require(written > 0, f"short write {path}")
                offset += written
            os.fsync(descriptor)
        for path, descriptor in descriptors.items():
            fd_stat = os.fstat(descriptor)
            path_stat = os.stat(path, follow_symlinks=False)
            require((fd_stat.st_dev, fd_stat.st_ino) ==
                    (path_stat.st_dev, path_stat.st_ino),
                    f"output inode ownership changed {path}")
            os.lseek(descriptor, 0, os.SEEK_SET)
            observed = b""
            while True:
                block = os.read(descriptor, 1 << 20)
                if not block:
                    break
                observed += block
            require(observed == rendered[path] == path.read_bytes(),
                    f"output bytes changed {path}")
        for path, expected in trusted.items():
            require(path.read_bytes() == expected,
                    f"trusted byte changed during publication: {path}")
    except Exception as exc:
        rejection = (json.dumps({"status": "REJECTED", "error": str(exc)},
                                sort_keys=True) + "\n").encode()
        # Never rename/unlink a pathname on failure.  Only overwrite the inode
        # which this process demonstrably owns through its still-held fd.
        for descriptor in descriptors.values():
            try:
                os.ftruncate(descriptor, 0)
                os.lseek(descriptor, 0, os.SEEK_SET)
                os.write(descriptor, rejection)
                os.fsync(descriptor)
            except Exception:
                pass
        raise
    finally:
        for descriptor in descriptors.values():
            os.close(descriptor)


def build(source, bands, recovery, raw, self_sha):
    require(source.get("k") == 48 and source.get("degree") == 12 and
            source.get("basis_dimension") == 272, "source dimensions")
    labels = [parse_label(x, f"source basis[{i}]")
              for i, x in enumerate(source.get("basis", []))]
    source_vector = [parse_fraction(x, f"source vector[{i}]")
                     for i, x in enumerate(source.get("rational_vector", []))]
    require(len(labels) == len(source_vector) == 272 and len(set(labels)) == 272,
            "source basis/vector")
    require(bands.get("source_sha256") == SOURCE_SHA and
            bands.get("compressed_basis_dimension") == 20 and
            bands.get("expanded_term_count") == 272, "bands metadata")

    blocks, theta_source, names = [], [], []
    for index, item in enumerate(bands.get("core", [])):
        item_label = parse_label(item.get("label"), f"core[{index}]")
        blocks.append({item_label: Fraction(1)})
        theta_source.append(parse_fraction(item.get("coefficient"),
                                           f"core[{index}] coefficient"))
        names.append(f"core_{index}")
    require(type(bands.get("bands")) is dict and
            sorted(bands["bands"], key=int) == [str(x) for x in range(5, 13)],
            "degree-band key set")
    for degree in range(5, 13):
        block = {}
        for index, item in enumerate(bands["bands"][str(degree)]):
            item_label = parse_label(item.get("label"),
                                     f"H{degree}[{index}]")
            require(item_label not in block, f"duplicate H{degree} label")
            block[item_label] = parse_fraction(
                item.get("coefficient"), f"H{degree}[{index}] coefficient")
        blocks.append(block)
        theta_source.append(Fraction(1))
        names.append(f"H{degree}")
    require(len(blocks) == 20 and names[13] == "H6" and names[19] == "H12",
            "compressed coordinate order")
    owner, weight = {}, {}
    for coordinate, block in enumerate(blocks):
        for item_label, item_weight in block.items():
            require(item_label not in owner, "two compressed owners")
            owner[item_label], weight[item_label] = coordinate, item_weight
    require(set(owner) == set(labels), "blocks do not partition source labels")
    require([weight[item] * theta_source[owner[item]] for item in labels] ==
            source_vector, "exact source expansion")

    require(raw.get("status") == "rejected-degree-band-gradient-discovery" and
            raw.get("rigorous") is False and raw.get("complete") is True and
            raw.get("gates_passed") is False and raw.get("decimal_dps") == 100,
            "raw status")
    gates = raw.get("gates")
    require(type(gates) is dict and
            {key for key, value in gates.items() if value is not True} ==
            {"gradient_halves_match"}, "raw sole rejection gate")
    require(raw.get("source_sha256") == SOURCE_SHA and
            raw.get("bands_sha256") == BANDS_SHA and
            raw.get("operator_sha256") == OPERATOR_SHA and
            raw.get("grouped_evaluator_sha256") == GROUPED_SHA and
            raw.get("integrator_sha256") == INTEGRATOR_SHA,
            "raw dependency bindings")
    require(set(raw.get("parameters", {})) == set(PARAMETERS) and
            all(parse_fraction(raw["parameters"][key], f"raw parameter {key}") == value
                for key, value in PARAMETERS.items()), "raw C10 parameters")

    require(recovery.get("status") ==
            "byte-pinned-recovered-degree-band-gradient-discovery" and
            recovery.get("rigorous") is False and recovery.get("complete") is True and
            recovery.get("no_projected_trial_emitted") is True and
            recovery.get("raw_sha256") == RAW_SHA and
            recovery.get("source_sha256") == SOURCE_SHA and
            recovery.get("bands_sha256") == BANDS_SHA and
            recovery.get("decimal_dps") == 100, "recovery status/provenance")
    for key in ("parameters", "theta", "denominator", "numerator",
                "grad_denominator", "grad_numerator"):
        require(recovery.get(key) == raw.get(key), f"recovery/raw field {key}")
    theta = [parse_fraction(x, f"theta[{i}]")
             for i, x in enumerate(recovery["theta"])]
    grad_a = [parse_fraction(x, f"grad denominator[{i}]")
              for i, x in enumerate(recovery["grad_denominator"])]
    grad_b = [parse_fraction(x, f"grad numerator[{i}]")
              for i, x in enumerate(recovery["grad_numerator"])]
    action_a = [parse_fraction(x, f"A theta[{i}]") for i, x in enumerate(
        recovery.get("a_theta_exact_fraction_half", []))]
    action_b = [parse_fraction(x, f"B theta[{i}]") for i, x in enumerate(
        recovery.get("b_theta_exact_fraction_half", []))]
    require(all(len(x) == 20 for x in (theta, grad_a, grad_b, action_a, action_b)),
            "recovery action dimensions")
    require(action_a == [x / 2 for x in grad_a] and
            action_b == [x / 2 for x in grad_b], "exact gradient halves")
    require(theta == [decimal100_fraction(x) for x in theta_source],
            "Decimal100 source-to-action base")
    D0 = parse_fraction(recovery["denominator"], "base denominator")
    N0 = parse_fraction(recovery["numerator"], "base numerator")
    require(D0 > 0 and N0 > 0 and N0 < D0, "base form signs")

    base_expanded = [weight[item] * theta[owner[item]] for item in labels]
    require(all(base_expanded), "relative normalization needs nonzero base")
    direction20 = [Fraction(0)] * 20
    direction20[13] = Fraction(1)
    direction272 = [weight[item] * direction20[owner[item]] for item in labels]
    nonzero = [i for i, x in enumerate(direction272) if x]
    require(len(nonzero) == 11 and
            all(owner[labels[i]] == 13 for i in nonzero), "literal H6 support")
    a01, b01 = action_a[13], action_b[13]
    R = D0 * b01 - N0 * a01
    derivative = 2 * R / D0**2
    require(R > 0 and derivative > 0, "H6 orientation")

    provenance = {
        "source_sha256": SOURCE_SHA, "bands_sha256": BANDS_SHA,
        "recovery_sha256": RECOVERY_SHA, "raw_gradient_sha256": RAW_SHA,
        "sparse_operator_sha256": OPERATOR_SHA,
        "grouped_self_form_evaluator_sha256": GROUPED_SHA,
        "exact_integrator_sha256": INTEGRATOR_SHA,
        "generator_sha256": self_sha,
    }
    common = {
        "rigorous": False, "fresh_scalar_reevaluation_required": True,
        "finite_form_value_claimed": False, "k": 48, "degree": 12,
        "parameters": {key: str(value) for key, value in PARAMETERS.items()},
        "provenance": provenance,
    }
    direction = {
        "status": "h6-sparse-self-form-direction",
        **common, "degree": 6, "basis_dimension": 11,
        "basis": [[a, list(lam)] for (a, lam), x in zip(labels, direction272) if x],
        "rational_vector": [str(x) for x in direction272 if x],
        "compressed_direction": [str(x) for x in direction20],
        "semantics": (
            "grouped denominator is A11=I(d,d); grouped numerator is "
            "B11=48*J(d,d), matching recovered half-gradients "
            "a=A*theta and b=(48J)*theta"
        ),
    }

    candidates = []
    for name, tau in STEPS:
        compressed = list(theta)
        compressed[13] += tau
        expanded = [x + tau * y for x, y in zip(base_expanded, direction272)]
        relative = [abs((x - y) / y) for x, y in zip(expanded, base_expanded)]
        require(max(relative) == tau and sum(x != 0 for x in relative) == 11,
                f"{name}: expanded relative normalization")
        candidates.append({
            "status": "h6-sparse-rational-band-trial", **common,
            "basis_dimension": 272,
            "basis": [[a, list(lam)] for a, lam in labels],
            "compressed_theta": [str(x) for x in compressed],
            "rational_vector": [str(x) for x in expanded],
            "trial": {
                "name": name, "exact_step_tau": str(tau),
                "H12_gauge_coordinate": "1",
                "finite_projective_pole": False,
                "normalization": (
                    "theta+tau*e_H6; max expanded-coordinate relative change"
                ),
                "exact_max_expanded_relative_change": str(max(relative)),
                "changed_expanded_coordinate_count": 11,
                "first_order_quotient_change_exact": str(tau * derivative),
                "first_order_quotient_change_decimal":
                    decimal_display(tau * derivative),
                "first_order_only": True,
            },
        })

    Dbar = sum((x * y for x, y in zip(theta, action_a)), Fraction(0))
    Nbar = sum((x * y for x, y in zip(theta, action_b)), Fraction(0))
    manifest_core = {
        "status": "h6-sparse-scalar-line-package",
        "rigorous": False, "fresh_scalar_reevaluation_required": True,
        "finite_form_value_claimed": False, "k": 48,
        "parameters": common["parameters"], "provenance": provenance,
        "base_semantics": (
            "exact fractions represented by the producer's serialized "
            "Decimal100 action base; not exact integral values"
        ),
        "base_action": {
            "denominator_D0": str(D0), "numerator_N0": str(N0),
            "A_cross_a01": str(a01), "B48_cross_b01": str(b01),
            "ascent_residual_R": str(R),
            "quotient_first_derivative": str(derivative),
            "quotient_first_derivative_decimal": decimal_display(derivative),
            "action_consistent_Dbar": str(Dbar),
            "action_consistent_Nbar": str(Nbar),
        },
        "line_algebra": {
            "forms": (
                "D(s)=D0+2*s*a01+s^2*A11; "
                "N(s)=N0+2*s*b01+s^2*B11"
            ),
            "one_endpoint_recovery": (
                "A11=(D_tau-D0-2*tau*a01)/tau^2; "
                "B11=(N_tau-N0-2*tau*b01)/tau^2"
            ),
            "stationary_polynomial": (
                "R+(D0*B11-N0*A11)*s+"
                "(B11*a01-A11*b01)*s^2"
            ),
            "endpoint_q_threshold_after_I_stage": (
                "q_tau_star=1+(h0+tau*h1)^2/(h0*D_tau), "
                "h0=N0-D0<0, h1=b01-a01"
            ),
            "threshold_scope": (
                "if recovered I-line determinant D0*A11-a01^2 is positive, "
                "max_s N(s)/D(s)>1 iff endpoint q_tau>q_tau_star"
            ),
        },
        "normalization_note": (
            "H12 stays exactly one, so this H6 line has no finite projective "
            "pole; tau=1/20,1/10,1/5 give literal 5%,10%,20% maxima"
        ),
        "cost_model": {
            "direction_labels": 11, "precomputed_orbit_keys": 121,
            "precomputed_orbit_terms": 293, "I_grouped_orbits": 77,
            "I_grouped_residual_terms": 272,
            "marginal_components": 23, "distinct_marginal_orbits": 11,
            "full_D12_orbit_keys_reference": 5929,
            "full_D12_orbit_terms_reference": 48867,
            "full_D12_marginal_components_reference": 695,
            "projected_two_worker_Decimal100_wall": "approximately 9 minutes; budget 20 minutes",
            "projected_peak_RSS": "below 0.2 GiB; abort gate 0.5 GiB",
            "projection_not_a_measurement": True,
        },
    }
    return direction, candidates, manifest_core


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--bands", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    dependencies = {
        "operator": PROJECT / "agents/structural-basis/code/band_operator_sparse.py",
        "grouped": PROJECT / "agents/exact-integrator/grouped_fixed_vector.py",
        "integrator": PROJECT / "agents/exact-integrator/src/exact_integrator.py",
    }
    paths = {
        "source": Path(args.source).resolve(), "bands": Path(args.bands).resolve(),
        "recovery": Path(args.recovery).resolve(), "raw": Path(args.raw).resolve(),
        "self": Path(__file__).resolve(),
        **{key: value.resolve() for key, value in dependencies.items()},
    }
    require(len(set(paths.values())) == len(paths), "trusted input path alias")
    trusted = {path: path.read_bytes() for path in paths.values()}
    expected = {"source": SOURCE_SHA, "bands": BANDS_SHA,
                "recovery": RECOVERY_SHA, "raw": RAW_SHA,
                "operator": OPERATOR_SHA, "grouped": GROUPED_SHA,
                "integrator": INTEGRATOR_SHA}
    for name, expected_sha in expected.items():
        require(digest(trusted[paths[name]]) == expected_sha, f"{name} SHA")
    parsed = {name: strict_json(trusted[paths[name]], name)
              for name in ("source", "bands", "recovery", "raw")}
    self_sha = digest(trusted[paths["self"]])
    direction, candidates, manifest = build(
        parsed["source"], parsed["bands"], parsed["recovery"], parsed["raw"],
        self_sha)

    output_dir = Path(args.output_dir).resolve()
    manifest_path = Path(args.manifest).resolve()
    direction_path = output_dir / "c10_D12_h6_direction_11.json"
    candidate_paths = [output_dir / f"c10_D12_{name}.json" for name, _ in STEPS]
    payload_objects = [(direction_path, direction)] + list(zip(candidate_paths,
                                                                candidates))
    rendered = {}
    entries = []
    for path, value in payload_objects:
        payload = (json.dumps(value, indent=2) + "\n").encode()
        rendered[path] = payload
        entries.append({"name": value.get("trial", {}).get("name", "H6_direction"),
                        "path": str(path), "sha256": digest(payload),
                        "kind": value["status"]})
    manifest["artifacts"] = entries
    manifest["launch_command_template"] = (
        "python3 agents/exact-integrator/grouped_fixed_vector.py "
        f"{direction_path} --alpha 79247/300000 --delta 1/100 "
        "--eta 76247/300000 --beta1 3/20 --beta2 3/20 "
        "--beta3plus 97/625 --decimal-dps 100 --workers 2 "
        "--i-stage H6_SELF.I-stage.json --output H6_SELF.json"
    )
    rendered[manifest_path] = (json.dumps(manifest, indent=2) + "\n").encode()
    write_all_through_owned_fds(rendered, trusted)
    print(json.dumps({
        "status": manifest["status"], "generator_sha256": self_sha,
        "manifest_sha256": digest(rendered[manifest_path]),
        "artifacts": entries, "finite_form_value_claimed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
