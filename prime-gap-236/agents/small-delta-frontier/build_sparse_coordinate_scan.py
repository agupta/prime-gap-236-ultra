#!/usr/bin/env python3
"""Build all 19 gauge-preserving sparse coordinate self-form inputs.

No integral is evaluated.  Each input is one signed compressed-coordinate
direction expanded through the pinned 20-to-272 band map.  Static grouped
cost/count metadata is reconstructed from the frozen grouped evaluator.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
from collections import defaultdict
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SOURCE_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
BANDS_SHA = "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9"
RECOVERY_SHA = "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
PARAMETERS = {
    "alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
    "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
    "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, description):
    def pairs(items):
        answer = {}
        for key, value in items:
            require(type(key) is str and key not in answer,
                    f"{description}: duplicate/non-string key")
            answer[key] = value
        return answer
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(
                          ValueError(f"{description}: nonfinite {x}")))


def rational(value, description):
    require(type(value) is str and value and value == value.strip(),
            f"{description}: rational string")
    try:
        return Fraction(value)
    except Exception as exc:
        raise ValueError(f"{description}: malformed rational") from exc


def label(value, description):
    require(type(value) is list and len(value) == 2 and
            type(value[0]) is int and value[0] >= 0 and
            type(value[1]) is list and
            all(type(x) is int and x >= 2 for x in value[1]) and
            tuple(value[1]) == tuple(sorted(value[1], reverse=True)),
            f"{description}: canonical no-ones label")
    return value[0], tuple(value[1])


def load(path_text, expected_sha, description):
    path = Path(path_text).resolve()
    raw = path.read_bytes()
    require(sha(raw) == expected_sha, f"{description}: SHA mismatch")
    return path, raw, strict_json(raw, description)


def import_grouped(path):
    spec = importlib.util.spec_from_file_location("sparse_scan_grouped", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_blocks(source, bands):
    labels = [label(x, f"source basis[{i}]")
              for i, x in enumerate(source.get("basis", []))]
    vector = [rational(x, f"source vector[{i}]")
              for i, x in enumerate(source.get("rational_vector", []))]
    require(source.get("k") == 48 and source.get("degree") == 12 and
            source.get("basis_dimension") == 272 and
            len(labels) == len(vector) == len(set(labels)) == 272,
            "source dimensions")
    require(bands.get("source_sha256") == SOURCE_SHA and
            bands.get("compressed_basis_dimension") == 20 and
            bands.get("expanded_term_count") == 272, "band metadata")
    blocks, names, theta_source = [], [], []
    for i, item in enumerate(bands.get("core", [])):
        item_label = label(item.get("label"), f"core[{i}]")
        blocks.append({item_label: Fraction(1)})
        names.append(f"core_{i}:{item_label}")
        theta_source.append(rational(item.get("coefficient"),
                                     f"core[{i}] coefficient"))
    require(len(blocks) == 12, "core count")
    require(type(bands.get("bands")) is dict and
            set(bands["bands"]) == {str(x) for x in range(5, 13)},
            "degree band keys")
    for degree in range(5, 13):
        block = {}
        for j, item in enumerate(bands["bands"][str(degree)]):
            item_label = label(item.get("label"), f"H{degree}[{j}]")
            require(item_label not in block, f"duplicate H{degree} label")
            block[item_label] = rational(item.get("coefficient"),
                                         f"H{degree}[{j}] coefficient")
        blocks.append(block)
        names.append(f"H{degree}")
        theta_source.append(Fraction(1))
    require(len(blocks) == 20 and names[12:15] == ["H5", "H6", "H7"] and
            names[19] == "H12", "compressed coordinate convention")
    owner, weight = {}, {}
    for coordinate, block in enumerate(blocks):
        for item_label, coefficient in block.items():
            require(item_label not in owner, "overlapping blocks")
            owner[item_label], weight[item_label] = coordinate, coefficient
    require(set(owner) == set(labels) and
            [weight[x]*theta_source[owner[x]] for x in labels] == vector,
            "exact 20-to-272 expansion")
    return labels, blocks, names, theta_source


def count_j_domains(grouped, evaluator):
    """Replay exactly the grouped evaluator's branch-count gates, no forms."""
    components = evaluator.marginal_components()
    lrs = sorted({lr for lr, _, _ in components})
    by_lr = {lr: [(e, a, value) for (x, e, a), value in components.items()
                  if x == lr] for lr in lrs}
    branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
    dimension = evaluator.support.k - 1
    count = 0
    max_r = min(dimension, evaluator.support.max_large())
    for r in range(max_r + 1):
        max_h = int(evaluator.support.eta // evaluator.support.delta) - r
        for h in range(max_h + 1):
            outer = evaluator.support.eta - (r+h)*evaluator.support.delta
            if outer <= 0:
                continue
            active_blocks = {}
            for branch in branches:
                constraints = evaluator.support._branch_constraints(r, h, branch)
                active = (constraints is not None and evaluator.integrate_domain(
                    {(0, 0): Fraction(1)}, dimension, r, outer, constraints) > 0)
                if not active:
                    active_blocks[branch] = False
                    continue
                nonempty = False
                for lr in lrs:
                    poly = defaultdict(Fraction)
                    for e, a, value in by_lr[lr]:
                        grouped.add_poly(poly, dict(evaluator.support._marginal_poly(
                            r, h, branch, e, a)), value)
                    if poly:
                        nonempty = True
                        break
                active_blocks[branch] = nonempty
            for i, left in enumerate(branches):
                if not active_blocks[left]:
                    continue
                for j in range(i+1):
                    right = branches[j]
                    if not active_blocks[right]:
                        continue
                    if {left, right} in ({"Sdelta", "Stotal"},
                                        {"Ltotal", "Lbig"}):
                        continue
                    constraints = evaluator.branch_domain(r, h, left, right)
                    if constraints is not None and evaluator.integrate_domain(
                            {(0, 0): Fraction(1)}, dimension, r, outer,
                            constraints) > 0:
                        count += 1
            evaluator.clear_face_caches(clear_marginals=True)
        evaluator.clear_radial_caches()
    return len(components), len(lrs), count


def static_costs(grouped, labels, coefficients):
    orbit_table = grouped.precompute_orbits(labels, 48)
    support = grouped.ei.OneStratumSupport(
        48, PARAMETERS["alpha"], PARAMETERS["delta"], PARAMETERS["eta"],
        PARAMETERS["beta1"], PARAMETERS["beta2"], PARAMETERS["beta3plus"])
    evaluator = grouped.GroupedEvaluator(support, labels, coefficients, Fraction)
    residuals = evaluator.square_residual_terms()
    components, marginal_orbits, domains = count_j_domains(grouped, evaluator)
    # The evaluator increments I faces solely from this support geometry.
    faces = 0
    for r in range(min(48, support.max_large())+1):
        max_h = int(support.alpha // support.delta)-r
        for h in range(max_h+1):
            if support.alpha-(r+h)*support.delta > 0:
                faces += 1
    return {
        "direction_labels": len(labels),
        "precomputed_orbit_keys": len(orbit_table),
        "precomputed_orbit_terms": sum(len(x) for x in orbit_table.values()),
        "i_orbit_groups": len(residuals),
        "i_grouped_residual_terms": sum(len(x) for x in residuals.values()),
        "i_faces": faces,
        "marginal_components": components,
        "distinct_marginal_orbits": marginal_orbits,
        "j_branch_integrals": domains,
    }


def publish(rendered, trusted):
    destinations = list(rendered)
    require(len(destinations) == len(set(destinations)) and
            not set(destinations) & set(trusted), "output path alias")
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fds = {}
    try:
        for path in destinations:
            path.parent.mkdir(parents=True, exist_ok=True)
            fds[path] = os.open(path, flags, 0o600)
            require(stat.S_ISREG(os.fstat(fds[path]).st_mode), "output regular")
        for path, fd in fds.items():
            payload = rendered[path]
            offset = 0
            while offset < len(payload):
                written = os.write(fd, payload[offset:])
                require(written > 0, "short write")
                offset += written
            os.fsync(fd)
        for path, fd in fds.items():
            fs, ps = os.fstat(fd), os.stat(path, follow_symlinks=False)
            require((fs.st_dev, fs.st_ino) == (ps.st_dev, ps.st_ino),
                    "output inode changed")
            require(path.read_bytes() == rendered[path], "output bytes changed")
        for path, raw in trusted.items():
            require(path.read_bytes() == raw, f"trusted bytes changed: {path}")
    except Exception as exc:
        rejection = (json.dumps({"status": "REJECTED", "error": str(exc)})+"\n").encode()
        for fd in fds.values():
            try:
                os.ftruncate(fd, 0); os.lseek(fd, 0, os.SEEK_SET); os.write(fd, rejection); os.fsync(fd)
            except Exception:
                pass
        raise
    finally:
        for fd in fds.values():
            os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--bands", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--coordinates", default="0-18",
                        help="0-18, or a comma-separated ordered subset")
    args = parser.parse_args()
    grouped_path = PROJECT / "agents/exact-integrator/grouped_fixed_vector.py"
    integrator_path = PROJECT / "agents/exact-integrator/src/exact_integrator.py"
    specs = {
        "source": (args.source, SOURCE_SHA), "bands": (args.bands, BANDS_SHA),
        "recovery": (args.recovery, RECOVERY_SHA),
        "grouped": (grouped_path, GROUPED_SHA),
        "integrator": (integrator_path, INTEGRATOR_SHA),
    }
    loaded, trusted = {}, {}
    for name, (path, expected) in specs.items():
        resolved = Path(path).resolve(); raw = resolved.read_bytes()
        require(sha(raw) == expected, f"{name}: SHA mismatch")
        require(resolved not in trusted, "trusted path alias")
        trusted[resolved] = raw
        if name in ("source", "bands", "recovery"):
            loaded[name] = strict_json(raw, name)
    self_path = Path(__file__).resolve(); self_raw = self_path.read_bytes()
    trusted[self_path] = self_raw
    grouped = import_grouped(grouped_path)
    labels, blocks, names, theta_source = parse_blocks(
        loaded["source"], loaded["bands"])
    recovery = loaded["recovery"]
    require(recovery.get("status") ==
            "byte-pinned-recovered-degree-band-gradient-discovery" and
            recovery.get("complete") is True and recovery.get("rigorous") is False and
            recovery.get("source_sha256") == SOURCE_SHA and
            recovery.get("bands_sha256") == BANDS_SHA and
            recovery.get("decimal_dps") == 100, "recovery status")
    theta = [rational(x, f"theta[{i}]") for i, x in enumerate(recovery["theta"])]
    action_a = [rational(x, f"a[{i}]") for i, x in enumerate(
        recovery["a_theta_exact_fraction_half"])]
    action_b = [rational(x, f"b[{i}]") for i, x in enumerate(
        recovery["b_theta_exact_fraction_half"])]
    require(len(theta) == len(action_a) == len(action_b) == 20 and
            theta[12:] == [Fraction(1)]*8, "action dimensions/gauge")
    D0, N0 = rational(recovery["denominator"], "D0"), rational(recovery["numerator"], "N0")
    require(D0 > N0 > 0, "base form signs")

    if args.coordinates == "0-18":
        requested = list(range(19))
    else:
        try:
            requested = [int(x) for x in args.coordinates.split(",")]
        except ValueError as exc:
            raise ValueError("malformed coordinate subset") from exc
        require(requested and len(requested) == len(set(requested)) and
                all(0 <= x < 19 for x in requested), "coordinate subset")
    entries = []
    objects = []
    for coordinate in requested:
        raw_R = D0*action_b[coordinate]-N0*action_a[coordinate]
        require(raw_R != 0, f"zero first-order residual coordinate {coordinate}")
        orientation = 1 if raw_R > 0 else -1
        direction_labels = list(blocks[coordinate])
        coefficients = [orientation*blocks[coordinate][x] for x in direction_labels]
        costs = static_costs(grouped, direction_labels, coefficients)
        a01, b01 = orientation*action_a[coordinate], orientation*action_b[coordinate]
        R = D0*b01-N0*a01
        relative_scale = abs(theta[coordinate])
        score = 2*relative_scale*R/D0**2
        common_name = names[coordinate].replace(" ", "")
        payload = {
            "status": "c10-D12-sparse-coordinate-self-form-direction",
            "rigorous": False, "theorem_ready": False,
            "fresh_scalar_reevaluation_required": True,
            "finite_form_value_claimed": False,
            "k": 48, "degree": 12, "coordinate": coordinate,
            "coordinate_name": names[coordinate], "orientation": orientation,
            "basis_dimension": len(direction_labels),
            "basis": [[a, list(parts)] for a, parts in direction_labels],
            "rational_vector": [str(x) for x in coefficients],
            "compressed_direction": [str(Fraction(orientation) if i == coordinate else Fraction(0))
                                     for i in range(20)],
            "cross_action": {
                "denominator_D0": str(D0), "numerator_N0": str(N0),
                "A_cross_a01": str(a01), "B48_cross_b01": str(b01),
                "ascent_residual_R": str(R),
                "quotient_first_derivative": str(2*R/D0**2),
                "relative_coordinate_scale": str(relative_scale),
                "relative_first_order_score": str(score),
                "self_form_semantics": "A11=I(d,d), B11=48*J(d,d)",
                "line_formula": "q(s)=(N0+2*s*b01+s^2*B11)/(D0+2*s*a01+s^2*A11)",
                "stationary_polynomial": "R+(D0*B11-N0*A11)*s+(B11*a01-A11*b01)*s^2",
                "crossing_test": "max q>1 iff N-D is positive somewhere, after A11/B11 reconstruction",
            },
            "expected_grouped_counts": costs,
            "parameters": {k: str(v) for k, v in PARAMETERS.items()},
            "provenance": {
                "source_sha256": SOURCE_SHA, "bands_sha256": BANDS_SHA,
                "recovery_sha256": RECOVERY_SHA,
                "grouped_evaluator_sha256": GROUPED_SHA,
                "exact_integrator_sha256": INTEGRATOR_SHA,
                "generator_sha256": sha(self_raw),
            },
        }
        filename = f"c10_D12_sparse_c{coordinate:02d}_{common_name}_direction.json"
        path = Path(args.output_dir).resolve()/filename
        raw = (json.dumps(payload, indent=2)+"\n").encode()
        objects.append((path, raw))
        entries.append({
            "coordinate": coordinate, "name": names[coordinate],
            "orientation": orientation, "relative_first_order_score": str(score),
            "path": str(path), "sha256": sha(raw),
            "basis_dimension": len(direction_labels),
            "expected_grouped_counts": costs,
        })
    entries.sort(key=lambda x: Fraction(x["relative_first_order_score"]), reverse=True)
    if requested == list(range(19)):
        require([x["name"] for x in entries[:3]] == ["H6", "H7", "H5"],
                "exact relative residual ranking top three")
    launch_queue = [x for x in entries if x["name"] != "H6"]
    if {12, 14}.issubset(requested):
        require([x["name"] for x in launch_queue[:2]] == ["H7", "H5"],
                "post-H6 launch order")
    manifest = {
        "status": "c10-D12-19-coordinate-sparse-self-form-manifest",
        "rigorous": False, "theorem_ready": False,
        "no_self_form_values_claimed": True, "k": 48, "degree": 12,
        "coordinates_included": requested,
        "gauge": "H12 coordinate 19 is held fixed; directions cover coordinates 0..18",
        "ranking_semantics": "descending exact derivative for an oriented relative coordinate step abs(theta_i)",
        "full_ranking": entries, "post_H6_launch_queue": launch_queue,
        "parameters": {k: str(v) for k, v in PARAMETERS.items()},
        "provenance": {
            "source_sha256": SOURCE_SHA, "bands_sha256": BANDS_SHA,
            "recovery_sha256": RECOVERY_SHA,
            "grouped_evaluator_sha256": GROUPED_SHA,
            "exact_integrator_sha256": INTEGRATOR_SHA,
            "generator_sha256": sha(self_raw),
        },
        "launch_template": (
            "python3 agents/exact-integrator/grouped_fixed_vector.py INPUT "
            "--alpha 79247/300000 --delta 1/100 --eta 76247/300000 "
            "--beta1 3/20 --beta2 3/20 --beta3plus 97/625 "
            "--decimal-dps 100 --workers 2 --i-stage STAGE --output OUTPUT"
        ),
    }
    manifest_path = Path(args.manifest).resolve()
    manifest_raw = (json.dumps(manifest, indent=2)+"\n").encode()
    rendered = {path: raw for path, raw in objects}; rendered[manifest_path] = manifest_raw
    publish(rendered, trusted)
    print(json.dumps({"status": manifest["status"],
                      "manifest_sha256": sha(manifest_raw),
                      "generator_sha256": sha(self_raw),
                      "post_H6_first": launch_queue[:2]}, indent=2))


if __name__ == "__main__":
    main()
