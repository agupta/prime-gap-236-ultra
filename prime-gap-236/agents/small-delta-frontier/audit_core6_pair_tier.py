#!/usr/bin/env python3
"""Independent hostile preflight and 7D solver for the six-core pair tier.

This file imports only the frozen primary grouped evaluator/integrator.  It
never imports the pair producer or either of its audit helpers.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
FULL_MANIFEST_SHA = "967a004ed5f02dc08d07bd9ab8f5af1050b345427327935b96d0979ae531787f"
PAIR_BUILDER_SHA = "ac8186bd7d6e3b569e0b02b4385f8b55f9e5abb4b96cd89f68cef217fe9d2667"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
COORDINATES = (10, 9, 6, 8, 5, 11)
PARAMETERS = {"alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
              "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
              "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625)}


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


def read(path_text, expected, description):
    path = Path(path_text).resolve(); raw = path.read_bytes()
    require(len(raw) <= 20_000_000 and sha(raw) == expected,
            f"{description}: size/SHA mismatch")
    return path, raw, strict_json(raw, description)


def frac(value, description):
    require(type(value) is str and value and value == value.strip(),
            f"{description}: rational string")
    try:
        return Fraction(value)
    except Exception as exc:
        raise ValueError(f"{description}: malformed rational") from exc


def typed_label(value, description):
    require(type(value) is list and len(value) == 2 and
            type(value[0]) is int and value[0] >= 0 and
            type(value[1]) is list and
            all(type(x) is int and x >= 2 for x in value[1]) and
            tuple(value[1]) == tuple(sorted(value[1], reverse=True)),
            f"{description}: canonical label")
    return value[0], tuple(value[1])


def import_grouped(path):
    spec = importlib.util.spec_from_file_location("pair_audit_grouped", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def count_j_domains(grouped, evaluator):
    components = evaluator.marginal_components()
    lrs = sorted({lr for lr, _, _ in components})
    by_lr = {lr: [(e, a, value) for (x, e, a), value in components.items()
                  if x == lr] for lr in lrs}
    branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
    dimension = 47; count = 0
    for r in range(min(dimension, evaluator.support.max_large())+1):
        max_h = int(evaluator.support.eta//evaluator.support.delta)-r
        for h in range(max_h+1):
            outer = evaluator.support.eta-(r+h)*evaluator.support.delta
            if outer <= 0:
                continue
            active = {}
            for branch in branches:
                constraints = evaluator.support._branch_constraints(r, h, branch)
                geometry = constraints is not None and evaluator.integrate_domain(
                    {(0, 0): Fraction(1)}, dimension, r, outer, constraints) > 0
                nonempty = False
                if geometry:
                    for lr in lrs:
                        poly = defaultdict(Fraction)
                        for e, a, value in by_lr[lr]:
                            grouped.add_poly(poly, dict(evaluator.support._marginal_poly(
                                r, h, branch, e, a)), value)
                        if poly:
                            nonempty = True; break
                active[branch] = nonempty
            for x, left in enumerate(branches):
                if not active[left]:
                    continue
                for y in range(x+1):
                    right = branches[y]
                    if not active[right] or {left, right} in (
                            {"Sdelta", "Stotal"}, {"Ltotal", "Lbig"}):
                        continue
                    constraints = evaluator.branch_domain(r, h, left, right)
                    if constraints is not None and evaluator.integrate_domain(
                            {(0, 0): Fraction(1)}, dimension, r, outer,
                            constraints) > 0:
                        count += 1
            evaluator.clear_face_caches(clear_marginals=True)
        evaluator.clear_radial_caches()
    return len(components), len(lrs), count


def static_counts(grouped, labels, coefficients):
    table = grouped.precompute_orbits(labels, 48)
    support = grouped.ei.OneStratumSupport(
        48, PARAMETERS["alpha"], PARAMETERS["delta"], PARAMETERS["eta"],
        PARAMETERS["beta1"], PARAMETERS["beta2"], PARAMETERS["beta3plus"])
    evaluator = grouped.GroupedEvaluator(support, labels, coefficients, Fraction)
    squares = evaluator.square_residual_terms()
    components, marginal_orbits, domains = count_j_domains(grouped, evaluator)
    faces = sum(1 for r in range(min(48, support.max_large())+1)
                for h in range(int(support.alpha//support.delta)-r+1)
                if support.alpha-(r+h)*support.delta > 0)
    return {"direction_labels": len(labels),
            "precomputed_orbit_keys": len(table),
            "precomputed_orbit_terms": sum(len(x) for x in table.values()),
            "i_orbit_groups": len(squares),
            "i_grouped_residual_terms": sum(len(x) for x in squares.values()),
            "i_faces": faces, "marginal_components": components,
            "distinct_marginal_orbits": marginal_orbits,
            "j_branch_integrals": domains}


def validate_parameters(value, description):
    require(type(value) is dict and set(value) == set(PARAMETERS) and
            all(frac(value[k], f"{description}.{k}") == v
                for k, v in PARAMETERS.items()), f"{description}: C10")


def load_manifests(args):
    full_path, full_raw, full = read(
        args.coordinate_manifest, FULL_MANIFEST_SHA, "coordinate manifest")
    pair_path, pair_raw, pair = read(
        args.pair_manifest, args.expect_pair_manifest_sha256, "pair manifest")
    builder = PROJECT/"agents/structural-basis/code/build_sparse_pair_core6.py"
    grouped_path = PROJECT/"agents/exact-integrator/grouped_fixed_vector.py"
    integrator_path = PROJECT/"agents/exact-integrator/src/exact_integrator.py"
    require(sha(builder.read_bytes()) == PAIR_BUILDER_SHA and
            sha(grouped_path.read_bytes()) == GROUPED_SHA and
            sha(integrator_path.read_bytes()) == INTEGRATOR_SHA,
            "live arithmetic/source closure")
    provenance = pair.get("provenance", {})
    require(pair.get("status") == "c10-D12-sparse-core6-polarization-tier" and
            pair.get("rigorous") is False and pair.get("theorem_ready") is False and
            pair.get("no_pair_form_values_claimed") is True and
            pair.get("k") == 48 and pair.get("degree") == 12 and
            pair.get("coordinates") == list(COORDINATES) and
            pair.get("selected_coordinates") == list(COORDINATES) and
            pair.get("basis_order") == ["base"]+[f"d{x}" for x in COORDINATES] and
            pair.get("pair_semantics") == "unscaled_sum" and
            provenance.get("coordinate_manifest_sha256") == FULL_MANIFEST_SHA and
            provenance.get("builder_sha256") == PAIR_BUILDER_SHA and
            provenance.get("grouped_evaluator_sha256") == GROUPED_SHA and
            provenance.get("exact_integrator_sha256") == INTEGRATOR_SHA,
            "pair manifest schema/provenance")
    validate_parameters(pair.get("parameters"), "pair manifest parameters")
    require(pair.get("polarization") == {
        "input": "unscaled signed sum d_i+d_j",
        "Aij": "(A_sum-Aii-Ajj)/2",
        "Bij": "(B48_sum-B48ii-B48jj)/2"}, "manifest polarization")
    trusted = {full_path: full_raw, pair_path: pair_raw,
               builder.resolve(): builder.read_bytes(),
               grouped_path.resolve(): grouped_path.read_bytes(),
               integrator_path.resolve(): integrator_path.read_bytes(),
               Path(__file__).resolve(): Path(__file__).read_bytes()}
    return full, pair, trusted, import_grouped(grouped_path)


def audit_inputs(args):
    full, pair, trusted, grouped = load_manifests(args)
    entries = {x.get("coordinate"): x for x in full.get("full_ranking", [])}
    require(set(entries) == set(range(19)), "coordinate coverage")
    directions = {}
    for coordinate in COORDINATES:
        entry = entries[coordinate]
        path, raw, direction = read(entry["path"], entry["sha256"],
                                    f"direction c{coordinate}")
        require(direction.get("coordinate") == coordinate and
                direction.get("basis_dimension") == 1 and
                len(direction.get("basis", [])) ==
                len(direction.get("rational_vector", [])) == 1 and
                direction.get("expected_grouped_counts") ==
                entry.get("expected_grouped_counts"), f"direction c{coordinate}")
        trusted[path] = raw; directions[coordinate] = direction
    expected_pairs = {(COORDINATES[i], COORDINATES[j])
                      for i in range(len(COORDINATES)) for j in range(i+1, len(COORDINATES))}
    records = pair.get("pairs")
    require(type(records) is list and len(records) == 15 and
            {(x.get("i"), x.get("j")) for x in records} == expected_pairs,
            "complete six-coordinate clique")
    protected = set(trusted)
    audited = []
    for record in records:
        i, j = record["i"], record["j"]
        require(record.get("coordinates") == [i, j], f"pair c{i},c{j} ordering")
        path, raw, value = read(record["input_path"], record["input_sha256"],
                                f"pair input c{i},c{j}")
        require(path not in protected, "pair input path alias"); protected.add(path)
        trusted[path] = raw
        left, right = directions[i], directions[j]
        expected_basis = left["basis"]+right["basis"]
        expected_vector = left["rational_vector"]+right["rational_vector"]
        expected_compressed = [str(frac(left["compressed_direction"][k], "left")+
                                   frac(right["compressed_direction"][k], "right"))
                               for k in range(20)]
        labels = [typed_label(x, "pair label") for x in expected_basis]
        coefficients = [frac(x, "pair coefficient") for x in expected_vector]
        counts = static_counts(grouped, labels, coefficients)
        require(value.get("status") == "c10-D12-sparse-core6-pair-sum-direction" and
                value.get("rigorous") is False and value.get("theorem_ready") is False and
                value.get("finite_form_value_claimed") is False and
                value.get("fresh_scalar_reevaluation_required") is True and
                value.get("k") == 48 and value.get("degree") == 12 and
                value.get("basis_dimension") == 2 and
                value.get("coordinates") == [i, j] and
                value.get("coordinate_names") == [entries[i]["name"], entries[j]["name"]] and
                value.get("orientations") == [left["orientation"], right["orientation"]] and
                value.get("combination") == "unscaled signed sum d_i+d_j" and
                value.get("basis") == expected_basis and
                value.get("rational_vector") == expected_vector and
                value.get("compressed_direction") == expected_compressed and
                value.get("expected_grouped_counts") == counts ==
                record.get("expected_grouped_counts") and
                value.get("provenance") == pair.get("provenance"),
                f"pair identity/counts c{i},c{j}")
        validate_parameters(value.get("parameters"), f"pair c{i},c{j} parameters")
        pol = value.get("polarization", {})
        require(pol.get("Aij") == "(A_sum-Aii-Ajj)/2" and
                pol.get("Bij") == "(B48_sum-B48ii-B48jj)/2" and
                pol.get("B_convention") ==
                "B48=48*J; factor 48 is applied exactly once by evaluator" and
                record.get("diagonal_result_sha256") ==
                [pol.get("diagonal_i_result_sha256"),
                 pol.get("diagonal_j_result_sha256")],
                f"pair polarization c{i},c{j}")
        stage_path, result_path = map(lambda x: Path(x).resolve(),
                                      (record["i_stage_path"], record["result_path"]))
        require(stage_path not in protected and result_path not in protected and
                stage_path != result_path, "stage/result path alias")
        protected.update((stage_path, result_path))
        audited.append({"i": i, "j": j, "input_sha256": sha(raw),
                        "expected_grouped_counts": counts,
                        "i_stage_path": str(stage_path),
                        "result_path": str(result_path),
                        "outputs_present_at_audit": stage_path.exists() or result_path.exists()})
    require(not any(x["outputs_present_at_audit"] for x in audited),
            "pair output existed at prelaunch audit")
    for path, raw in trusted.items():
        require(path.read_bytes() == raw, f"trusted bytes changed: {path}")
    value = {"status": "AUDIT PASS", "scope": "six-core-pair-input-prelaunch",
            "rigorous": False, "theorem_ready": False,
            "coordinate_manifest_sha256": FULL_MANIFEST_SHA,
            "pair_manifest_sha256": args.expect_pair_manifest_sha256,
            "pair_builder_sha256": PAIR_BUILDER_SHA,
            "pair_count": len(audited), "coordinates": list(COORDINATES),
            "polarization": {"Aij": "(A_sum-Aii-Ajj)/2",
                             "Bij": "(B48_sum-B48ii-B48jj)/2",
                             "B48_factor": 48},
            "pairs": audited, "no_integration_launched": True,
            "no_ritz_value_claimed": True}
    return value, trusted


def publish(path_text, value, trusted):
    path = Path(path_text).resolve(); require(path not in trusted, "output alias")
    payload = (json.dumps(value, indent=2)+"\n").encode(); path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT|os.O_EXCL|os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"): flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "output regular")
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:]); require(written > 0, "short write"); offset += written
        os.fsync(fd); fs, ps = os.fstat(fd), os.stat(path, follow_symlinks=False)
        require((fs.st_dev, fs.st_ino) == (ps.st_dev, ps.st_ino) and
                path.read_bytes() == payload, "output ownership/bytes")
        for trusted_path, raw in trusted.items():
            require(trusted_path.read_bytes() == raw,
                    f"trusted bytes changed: {trusted_path}")
    except Exception as exc:
        rejection = (json.dumps({"status": "REJECTED", "error": str(exc)})+"\n").encode()
        try:
            os.ftruncate(fd, 0); os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, rejection); os.fsync(fd)
        except Exception:
            pass
        raise
    finally:
        os.close(fd)
    print(json.dumps({"status": value["status"], "output_sha256": sha(payload)}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coordinate-manifest", required=True)
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--expect-pair-manifest-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    value, trusted = audit_inputs(args)
    publish(args.output, value, trusted)


if __name__ == "__main__":
    main()
