#!/usr/bin/env python3
"""Hostile tests for sparse-coordinate result and line reconstruction."""

import hashlib
import json
import subprocess
import sys
import tempfile
from fractions import Fraction as F
from pathlib import Path


HERE = Path(__file__).resolve().parent
RECOVER = HERE/"recover_sparse_coordinate_line.py"
MANIFEST = HERE/"results/c10_D12_sparse_coordinate_scan_manifest.json"
MANIFEST_SHA = "967a004ed5f02dc08d07bd9ab8f5af1050b345427327935b96d0979ae531787f"
DATA = {
    "H7": ("22f643231c8c44a22674622371ff84ba164e923ad57090afd1ac89157c2cde84",
           "0ac25784d7028f4bcf14a49486ead4deca9d942a4b580e1b9bbe280f596d5c81",
           "4b47730d890ddf5977c10cdbd999cf48012ac072835e7c43c7ef237bc6a69b4d", 14),
    "H5": ("f6aec9b2fae2a3edce726c95582019a6b1481dfe0146b39f1cbc83e69d3674d1",
           "ced65a774fc06f726190e5c7c4593baba5c765cf2dfd50b2a1cdeaaf032d9bb3",
           "0aa727396459d10990a5aa17b61c4492645a42e047fa406a94bb415aa069519c", 12),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def paths(name, coordinate):
    directory = HERE/"results/sparse_coordinate_tranche_h7_h5"
    direction = HERE/"results/sparse_coordinate_scan_all"/f"c10_D12_sparse_c{coordinate:02d}_{name}_direction.json"
    prefix = directory/f"c10_D12_sparse_c{coordinate:02d}_{name}_direction_self_mp100"
    return direction, Path(str(prefix)+".I-stage.json"), Path(str(prefix)+".json")


def command(name, output, stage_override=None, result_override=None,
            stage_sha=None, result_sha=None):
    direction_sha, expected_stage, expected_result, coordinate = DATA[name]
    direction, stage, result = paths(name, coordinate)
    stage = stage_override or stage; result = result_override or result
    return [sys.executable, str(RECOVER), "--manifest", str(MANIFEST),
            "--expect-manifest-sha256", MANIFEST_SHA,
            "--direction", str(direction), "--expect-direction-sha256", direction_sha,
            "--i-stage", str(stage), "--expect-i-stage-sha256", stage_sha or expected_stage,
            "--self-result", str(result), "--expect-self-result-sha256", result_sha or expected_result,
            "--output", str(output)]


def test_both_lines_and_frozen_values():
    expected = {
        "H7": F("0.9709699455402759047905961341880612885081298891942384788793368862154712367664225831774939720833746299"),
        "H5": F("0.9709699354783650309824573762640711682572175896008681917183993511987828060034653410290766443083974454"),
    }
    with tempfile.TemporaryDirectory(prefix="coordinate-line-test.") as directory:
        for name in ("H7", "H5"):
            output = Path(directory)/f"{name}.json"
            subprocess.run(command(name, output), check=True,
                           stdout=subprocess.DEVNULL)
            value = json.loads(output.read_bytes())
            if (value["coordinate_name"] != name or
                    value["line_max_strictly_above_one"] is not False or
                    F(value["projective_maximum_decimal100"]) != expected[name] or
                    len(value["stationary_roots_decimal100"]) != 2):
                raise AssertionError(f"{name} full line")


def test_decimal_final_unit_and_count_mutations():
    with tempfile.TemporaryDirectory(prefix="coordinate-mutation.") as directory:
        directory = Path(directory)
        _, _, result_path = paths("H7", 14)
        result = json.loads(result_path.read_bytes())
        result["numerator"] = result["numerator"][:-1] + str((int(result["numerator"][-1])+1)%10)
        mutated = directory/"mutated-result.json"
        mutated.write_text(json.dumps(result)+"\n")
        output = directory/"bad-output.json"
        run = subprocess.run(command("H7", output, result_override=mutated,
                                     result_sha=sha(mutated)),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if run.returncode == 0 or output.exists():
            raise AssertionError("final Decimal unit mutation accepted")

        result = json.loads(result_path.read_bytes()); result["i_orbit_groups"] += 1
        mutated2 = directory/"mutated-count.json"; mutated2.write_text(json.dumps(result)+"\n")
        run = subprocess.run(command("H7", directory/"bad-count-output.json",
                                     result_override=mutated2, result_sha=sha(mutated2)),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if run.returncode == 0:
            raise AssertionError("wrong grouped count accepted")


def test_stage_result_and_alias_gates():
    with tempfile.TemporaryDirectory(prefix="coordinate-stage.") as directory:
        directory = Path(directory)
        _, stage_path, _ = paths("H5", 12)
        stage = json.loads(stage_path.read_bytes())
        stage["denominator"] = str(F(stage["denominator"])+F(1,10)**250)
        mutated = directory/"stage.json"; mutated.write_text(json.dumps(stage)+"\n")
        run = subprocess.run(command("H5", directory/"bad-stage-output.json",
                                     stage_override=mutated, stage_sha=sha(mutated)),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if run.returncode == 0:
            raise AssertionError("stage/result denominator mismatch accepted")
        before = MANIFEST.read_bytes()
        run = subprocess.run(command("H5", MANIFEST), stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        if run.returncode == 0 or MANIFEST.read_bytes() != before:
            raise AssertionError("trusted output alias accepted/modified")


def test_worker1_core_and_boolean_rejection():
    manifest = json.loads(MANIFEST.read_bytes())
    entry = next(x for x in manifest["full_ranking"] if x["coordinate"] == 10)
    directory = HERE/"results/sparse_coordinate_scan_all"
    stage = directory/"c10_D12_sparse_c10_self_mp100.I-stage.json"
    result = directory/"c10_D12_sparse_c10_self_mp100.json"
    with tempfile.TemporaryDirectory(prefix="coordinate-core-test.") as temp:
        temp = Path(temp); output = temp/"core10.json"
        base = [sys.executable, str(RECOVER), "--manifest", str(MANIFEST),
                "--expect-manifest-sha256", MANIFEST_SHA,
                "--direction", entry["path"],
                "--expect-direction-sha256", entry["sha256"],
                "--i-stage", str(stage), "--expect-i-stage-sha256", sha(stage),
                "--self-result", str(result), "--expect-self-result-sha256", sha(result),
                "--output", str(output)]
        subprocess.run(base, check=True, stdout=subprocess.DEVNULL)
        value = json.loads(output.read_bytes())
        if F(value["projective_maximum_decimal100"]) != F(
                "0.9709703739244089091355617994205784053338124720882514260927954722577601376784527726961530504713255729"):
            raise AssertionError("worker1 core10 line")
        mutated_value = json.loads(result.read_bytes()); mutated_value["workers"] = True
        mutated = temp/"bool-worker.json"; mutated.write_text(json.dumps(mutated_value)+"\n")
        bad = list(base)
        bad[bad.index(str(result))] = str(mutated)
        bad[bad.index(sha(result))] = sha(mutated)
        bad[bad.index(str(output))] = str(temp/"bad-worker-output.json")
        run = subprocess.run(bad, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if run.returncode == 0:
            raise AssertionError("Boolean worker count accepted")


def main():
    tests = [test_both_lines_and_frozen_values,
             test_decimal_final_unit_and_count_mutations,
             test_stage_result_and_alias_gates,
             test_worker1_core_and_boolean_rejection]
    for test in tests:
        test(); print("PASS", test.__name__)
    print("PASS all", len(tests), "tests")
    print("recover_sha256", sha(RECOVER))


if __name__ == "__main__":
    main()
