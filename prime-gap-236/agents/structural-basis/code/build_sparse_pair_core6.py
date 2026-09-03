#!/usr/bin/env python3
"""Build the audited six-core polarization tier; never evaluates an integral."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


MANIFEST_SHA = "967a004ed5f02dc08d07bd9ab8f5af1050b345427327935b96d0979ae531787f"
PREFLIGHT_SHA = "38a5963fa24827fbe83593fc1dd663666cf9cc43363e74704969c138be588c25"
PREFLIGHT_CODE_SHA = "511d2c0ec21a26cba30f08bcecc8f2ac6856609db0cf44457f7b58e814d265db"
CORE_AUDIT_SHA = "88bdbf0de9c4cac7ce0a81cda7978f21e15d36d52c7df12bd80a294943114077"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
SELECTED = (10, 9, 6, 8, 5, 11)
# Nested cliques: after batches 1,2,4,5 the first 3,4,5,6 directions are complete.
BATCHES = (
    ((10, 9), (10, 6), (9, 6)),
    ((10, 8), (9, 8), (6, 8)),
    ((10, 5), (9, 5), (6, 5)),
    ((8, 5), (10, 11), (9, 11)),
    ((6, 11), (8, 11), (5, 11)),
)
PARAMETERS = {"alpha": "79247/300000", "delta": "1/100",
              "eta": "76247/300000", "beta1": "3/20",
              "beta2": "3/20", "beta3plus": "97/625"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, what):
    def pairs(items):
        out = {}
        for key, value in items:
            require(type(key) is str and key not in out,
                    f"{what}: duplicate/non-string key")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"{what}: nonfinite {token}")))


def load(path, expected, what):
    path = Path(path).resolve()
    raw = path.read_bytes()
    require(sha(raw) == expected, f"{what}: SHA mismatch")
    return path, raw, strict_json(raw, what)


def import_preflight(path):
    spec = importlib.util.spec_from_file_location("core6_static_preflight", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def units(counts):
    # A transparent monotone proxy, used only to estimate wall time.
    return (counts["precomputed_orbit_terms"] +
            4*counts["i_grouped_residual_terms"] +
            20*counts["marginal_components"])


def publish(rendered, trusted):
    destinations = list(rendered)
    require(len(destinations) == len(set(destinations)) and
            not set(destinations) & set(trusted), "output alias")
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    handles = {}
    try:
        for path in destinations:
            path.parent.mkdir(parents=True, exist_ok=True)
            handles[path] = os.open(path, flags, 0o600)
            require(stat.S_ISREG(os.fstat(handles[path]).st_mode),
                    "reserved output is not regular")
        for path, fd in handles.items():
            raw = rendered[path]
            offset = 0
            while offset < len(raw):
                wrote = os.write(fd, raw[offset:])
                require(wrote > 0, "short write")
                offset += wrote
            os.fsync(fd)
        for path, fd in handles.items():
            fs, ps = os.fstat(fd), os.stat(path, follow_symlinks=False)
            require((fs.st_dev, fs.st_ino) == (ps.st_dev, ps.st_ino),
                    "reserved output inode changed")
            require(path.read_bytes() == rendered[path], "output bytes changed")
        for path, raw in trusted.items():
            require(path.read_bytes() == raw, f"trusted bytes changed: {path}")
    except Exception as exc:
        rejection = (json.dumps({"status": "REJECTED", "error": str(exc)})+"\n").encode()
        for fd in handles.values():
            try:
                os.ftruncate(fd, 0)
                os.lseek(fd, 0, os.SEEK_SET)
                os.write(fd, rejection)
                os.fsync(fd)
            except Exception:
                pass
        raise
    finally:
        for fd in handles.values():
            os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--preflight-code", required=True)
    parser.add_argument("--core-audit", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output-manifest", required=True)
    args = parser.parse_args()
    manifest_path, manifest_raw, manifest = load(
        args.manifest, MANIFEST_SHA, "coordinate manifest")
    preflight_path, preflight_raw, preflight = load(
        args.preflight, PREFLIGHT_SHA, "independent preflight")
    core_path, core_raw, core = load(args.core_audit, CORE_AUDIT_SHA, "core audit")
    preflight_code_path = Path(args.preflight_code).resolve()
    preflight_code_raw = preflight_code_path.read_bytes()
    require(sha(preflight_code_raw) == PREFLIGHT_CODE_SHA, "preflight code SHA")
    self_path, self_raw = Path(__file__).resolve(), Path(__file__).read_bytes()
    require(preflight.get("status") == core.get("status") == "AUDIT PASS" and
            preflight.get("manifest_sha256") == core.get("manifest_sha256") == MANIFEST_SHA and
            core.get("preflight_sha256") == PREFLIGHT_SHA and
            core.get("rigorous") is False and len(core.get("records", [])) == 12,
            "input audit verdicts")
    entries = {item["coordinate"]: item for item in manifest["full_ranking"]}
    diagonal = {item["coordinate"]: item for item in core["records"]}
    require(set(diagonal) == set(range(12)) and all(i in entries for i in SELECTED),
            "selected diagonal coverage")
    trusted = {manifest_path: manifest_raw, preflight_path: preflight_raw,
               preflight_code_path: preflight_code_raw, core_path: core_raw,
               self_path: self_raw}
    directions = {}
    for coordinate in SELECTED:
        entry = entries[coordinate]
        path = Path(entry["path"]).resolve()
        raw = path.read_bytes()
        require(sha(raw) == entry["sha256"], f"c{coordinate}: input SHA")
        direction = strict_json(raw, f"c{coordinate} direction")
        require(direction["coordinate"] == coordinate and
                direction["basis_dimension"] == 1 and
                len(direction["basis"]) == len(direction["rational_vector"]) == 1 and
                direction["parameters"] == PARAMETERS,
                f"c{coordinate}: singleton direction")
        trusted[path] = raw
        directions[coordinate] = direction
    static = import_preflight(preflight_code_path)
    output_dir = Path(args.output_dir).resolve()
    manifest_output = Path(args.output_manifest).resolve()
    rendered, pair_entries = {}, []
    batch_lookup = {pair: batch for batch, pairs in enumerate(BATCHES, 1)
                    for pair in pairs}
    require({tuple(sorted(pair)) for pairs in BATCHES for pair in pairs} ==
            {tuple(sorted((SELECTED[i], SELECTED[j])))
             for i in range(len(SELECTED)) for j in range(i)},
            "batch schedule is not the complete selected clique")
    with localcontext() as context:
        context.prec = 60
        for batch, pairs in enumerate(BATCHES, 1):
            for left, right in pairs:
                dl, dr = directions[left], directions[right]
                labels = dl["basis"]+dr["basis"]
                vectors = dl["rational_vector"]+dr["rational_vector"]
                typed_labels = [(a, tuple(parts)) for a, parts in labels]
                typed_vectors = [Fraction(value) for value in vectors]
                counts = static.static_counts(typed_labels, typed_vectors)
                require(counts["direction_labels"] == 2 and
                        counts["i_faces"] == 312 and
                        counts["marginal_components"] == 4 and
                        counts["j_branch_integrals"] == 1200,
                        f"pair {left},{right}: static-count gate")
                cl, cr = (entries[left]["expected_grouped_counts"],
                          entries[right]["expected_grouped_counts"])
                tl = Decimal(str(diagonal[left]["total_seconds"]))
                tr = Decimal(str(diagonal[right]["total_seconds"]))
                ul, ur, up = map(Decimal, (units(cl), units(cr), units(counts)))
                central = up*(tl+tr)/(ul+ur)
                lower = max(tl, tr, up*min(tl/ul, tr/ur))
                upper = 2*up*max(tl/ul, tr/ur)
                compressed = [str(Fraction(dl["orientation"] if i == left else
                                           dr["orientation"] if i == right else 0))
                              for i in range(20)]
                payload = {
                    "status": "c10-D12-sparse-core6-pair-sum-direction",
                    "rigorous": False, "theorem_ready": False,
                    "finite_form_value_claimed": False,
                    "fresh_scalar_reevaluation_required": True,
                    "k": 48, "degree": 12, "basis_dimension": 2,
                    "coordinates": [left, right],
                    "coordinate_names": [entries[left]["name"], entries[right]["name"]],
                    "orientations": [dl["orientation"], dr["orientation"]],
                    "combination": "unscaled signed sum d_i+d_j",
                    "basis": labels, "rational_vector": vectors,
                    "compressed_direction": compressed,
                    "expected_grouped_counts": counts,
                    "polarization": {
                        "Aij": "(A_sum-Aii-Ajj)/2",
                        "Bij": "(B48_sum-B48ii-B48jj)/2",
                        "B_convention": "B48=48*J; factor 48 is applied exactly once by evaluator",
                        "diagonal_i_result_sha256": diagonal[left]["result_sha256"],
                        "diagonal_j_result_sha256": diagonal[right]["result_sha256"],
                    },
                    "parameters": PARAMETERS,
                    "provenance": {
                        "coordinate_manifest_sha256": MANIFEST_SHA,
                        "independent_preflight_sha256": PREFLIGHT_SHA,
                        "independent_preflight_code_sha256": PREFLIGHT_CODE_SHA,
                        "core_diagonal_audit_sha256": CORE_AUDIT_SHA,
                        "grouped_evaluator_sha256": GROUPED_SHA,
                        "exact_integrator_sha256": INTEGRATOR_SHA,
                        "builder_sha256": sha(self_raw),
                    },
                }
                filename = f"c10_D12_pair_c{left:02d}_c{right:02d}_sum_direction.json"
                path = output_dir/filename
                stem = filename.removesuffix("_direction.json")
                stage_path = output_dir/f"{stem}_self_mp100.I-stage.json"
                result_path = output_dir/f"{stem}_self_mp100.json"
                raw = (json.dumps(payload, indent=2)+"\n").encode()
                rendered[path] = raw
                pair_entries.append({
                    "batch": batch, "i": left, "j": right,
                    "coordinates": [left, right],
                    "input_path": str(path), "input_sha256": sha(raw),
                    "i_stage_path": str(stage_path),
                    "result_path": str(result_path),
                    "expected_grouped_counts": counts,
                    "estimated_worker1_seconds": {
                        "lower": str(lower), "central": str(central),
                        "upper_conservative": str(upper),
                        "model": "monotone static units; calibrated only on the two audited singleton runs",
                        "units": counts["precomputed_orbit_terms"]+
                                 4*counts["i_grouped_residual_terms"]+
                                 20*counts["marginal_components"],
                    },
                    "diagonal_result_sha256": [diagonal[left]["result_sha256"],
                                                diagonal[right]["result_sha256"]],
                })
    pair_entries.sort(key=lambda item: (item["batch"],
                                        BATCHES[item["batch"]-1].index(tuple(item["coordinates"]))))
    selected_diagonal_gain = sum(Decimal(diagonal[i]["line_gain"]) for i in SELECTED)
    central_total = sum(Decimal(item["estimated_worker1_seconds"]["central"])
                        for item in pair_entries)
    pair_manifest = {
        "status": "c10-D12-sparse-core6-polarization-tier",
        "rigorous": False, "theorem_ready": False,
        "no_pair_form_values_claimed": True,
        "k": 48, "degree": 12,
        "basis_order": ["base"]+[f"d{coordinate}" for coordinate in SELECTED],
        "coordinates": list(SELECTED),
        "selected_coordinates": list(SELECTED),
        "pair_semantics": "unscaled_sum",
        "selection_rule": "six highest audited core-only individual line gains",
        "selected_diagonal_gain_sum_not_a_ritz_bound": str(selected_diagonal_gain),
        "pairs": pair_entries,
        "batches": [[list(pair) for pair in pairs] for pairs in BATCHES],
        "concurrency": {"jobs": 3, "workers_per_job": 1,
                        "reason": "reserve one CPU core and cap memory"},
        "estimated_serial_worker1_seconds_central": str(central_total),
        "polarization": {
            "input": "unscaled signed sum d_i+d_j",
            "Aij": "(A_sum-Aii-Ajj)/2",
            "Bij": "(B48_sum-B48ii-B48jj)/2",
        },
        "ritz": {
            "space": "span{base,d10,d9,d6,d8,d5,d11}",
            "matrix_dimension": 7,
            "acceptance": "particular-vector quotient only; never assume A positive definite",
            "continuation_gate": "add H8/H7 rows only if discovery Ritz gain >= 1e-4",
            "continuation_gate_value": "1/10000",
        },
        "parameters": PARAMETERS,
        "launch_template": (
            "python3 agents/exact-integrator/grouped_fixed_vector.py INPUT "
            "--alpha 79247/300000 --delta 1/100 --eta 76247/300000 "
            "--beta1 3/20 --beta2 3/20 --beta3plus 97/625 "
            "--decimal-dps 100 --workers 1 --progress --i-stage STAGE --output OUTPUT"
        ),
        "provenance": {
            "coordinate_manifest_sha256": MANIFEST_SHA,
            "independent_preflight_sha256": PREFLIGHT_SHA,
            "independent_preflight_code_sha256": PREFLIGHT_CODE_SHA,
            "core_diagonal_audit_sha256": CORE_AUDIT_SHA,
            "grouped_evaluator_sha256": GROUPED_SHA,
            "exact_integrator_sha256": INTEGRATOR_SHA,
            "builder_sha256": sha(self_raw),
        },
    }
    manifest_bytes = (json.dumps(pair_manifest, indent=2)+"\n").encode()
    rendered[manifest_output] = manifest_bytes
    publish(rendered, trusted)
    print(json.dumps({"status": pair_manifest["status"],
                      "builder_sha256": sha(self_raw),
                      "manifest_sha256": sha(manifest_bytes),
                      "pair_count": len(pair_entries),
                      "central_serial_seconds": str(central_total)}, indent=2))


if __name__ == "__main__":
    main()
