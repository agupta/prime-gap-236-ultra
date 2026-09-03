#!/usr/bin/env python3
"""Memory-light exact tests for the H6 scalar-line package."""

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from fractions import Fraction as F
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
GENERATOR = HERE / "build_h6_scalar_line.py"
RECOVER = HERE / "recover_h6_scalar_line.py"
SOURCE = PROJECT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
BANDS = PROJECT / "agents/structural-basis/results/c10_D12_degree_bands.json"
RECOVERY = PROJECT / "agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json"
RAW = PROJECT / "agents/structural-basis/results/c10_D12_band_sparse_gradient_mp100.json"
MANIFEST = HERE / "results/c10_D12_h6_scalar_line_manifest.json"
DIRECTION = HERE / "results/h6_scalar_line/c10_D12_h6_direction_11.json"
SELF_RESULT = HERE / "results/h6_scalar_line/c10_D12_h6_self_mp100.json"


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def run_generator(directory):
    out = Path(directory) / "out"
    manifest = Path(directory) / "manifest.json"
    command = [sys.executable, str(GENERATOR), "--source", str(SOURCE),
               "--bands", str(BANDS), "--recovery", str(RECOVERY),
               "--raw", str(RAW), "--output-dir", str(out),
               "--manifest", str(manifest)]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
    return command, manifest, out


def test_reproducible_bytes_and_fail_closed_existing():
    actual = load(MANIFEST)
    with tempfile.TemporaryDirectory(prefix="h6-package-test.") as directory:
        command, manifest, out = run_generator(directory)
        generated = load(manifest)
        # Artifact payloads contain no output path and must be byte-identical.
        expected = {x["name"]: x["sha256"] for x in actual["artifacts"]}
        observed = {x["name"]: x["sha256"] for x in generated["artifacts"]}
        require(observed == expected, "generated artifact SHAs")
        second = subprocess.run(command, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        require(second.returncode != 0, "existing outputs were overwritten")


def test_literal_h6_and_candidate_normalizations():
    manifest = load(MANIFEST)
    entries = {x["name"]: x for x in manifest["artifacts"]}
    for item in entries.values():
        require(sha(item["path"]) == item["sha256"], "manifest byte binding")
    direction = load(entries["H6_direction"]["path"])
    bands = load(BANDS)
    expected_labels = [x["label"] for x in bands["bands"]["6"]]
    expected_coefficients = [F(x["coefficient"]) for x in bands["bands"]["6"]]
    require(direction["basis"] == expected_labels and
            list(map(F, direction["rational_vector"])) == expected_coefficients,
            "11-label direction is not literal H6")
    require(direction["compressed_direction"] == ["0"]*13+["1"]+["0"]*6,
            "compressed H6 direction")

    source_labels = load(SOURCE)["basis"]
    base_theta = list(map(F, load(RECOVERY)["theta"]))
    # Rebuild owner/weight from the published band data, independently of the
    # generator's implementation.
    owner, weight = {}, {}
    for i, item in enumerate(bands["core"]):
        owner[json.dumps(item["label"])] = i
        weight[json.dumps(item["label"])] = F(1)
    for degree in range(5, 13):
        for item in bands["bands"][str(degree)]:
            owner[json.dumps(item["label"])] = degree + 7
            weight[json.dumps(item["label"])] = F(item["coefficient"])
    base = [weight[json.dumps(x)]*base_theta[owner[json.dumps(x)]]
            for x in source_labels]
    for name, tau in (("h6_5pct", F(1,20)), ("h6_10pct", F(1,10)),
                      ("h6_20pct", F(1,5))):
        candidate = load(entries[name]["path"])
        vector = list(map(F, candidate["rational_vector"]))
        changes = [abs((x-y)/y) for x,y in zip(vector,base)]
        require(max(changes) == tau and sum(x != 0 for x in changes) == 11,
                f"{name} normalization")
        require(candidate["compressed_theta"][19] == "1",
                f"{name} H12 gauge")


def test_action_factors_and_line_algebra():
    manifest = load(MANIFEST)
    action = manifest["base_action"]
    D0, N0 = F(action["denominator_D0"]), F(action["numerator_N0"])
    a, b = F(action["A_cross_a01"]), F(action["B48_cross_b01"])
    R = D0*b-N0*a
    require(R == F(action["ascent_residual_R"]) > 0 and
            F(action["quotient_first_derivative"]) == 2*R/D0**2,
            "stored action/factor-two identities")
    raw = load(RAW)
    require(F(raw["grad_denominator"][13])/2 == a and
            F(raw["grad_numerator"][13])/2 == b,
            "sparse producer half-gradient semantics")
    require(raw["grouped_evaluator_sha256"] ==
            manifest["provenance"]["grouped_self_form_evaluator_sha256"],
            "grouped self-form semantic binding")

    spec = importlib.util.spec_from_file_location("h6_recover", RECOVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Exact synthetic endpoint recovers both self forms and threshold.
    D0, N0, a, b, A11, B11, tau = map(
        F, ("7/3", "2", "1/5", "3/7", "11/13", "17/19", "1/10"))
    Dt = D0+2*tau*a+tau*tau*A11
    Nt = N0+2*tau*b+tau*tau*B11
    require(module.recover_A11(D0,a,tau,Dt) == A11,
            "one-endpoint A11 recovery")
    recovered_B = (Nt-N0-2*tau*b)/tau**2
    require(recovered_B == B11, "one-endpoint B11 recovery")
    _, determinant, threshold = module.endpoint_threshold(
        D0,N0,a,b,tau,Dt)
    # At equality q_tau=threshold, N-D has a double real root; perturbing the
    # endpoint quotient across it flips the exact max>1 criterion.
    h0,h1=N0-D0,b-a
    h2_equal=h1*h1/h0
    q_equal=(N0+2*tau*b+tau*tau*(A11+h2_equal))/Dt
    require(q_equal == threshold and determinant > 0,
            "endpoint threshold identity")


def test_decimal100_self_result_replay_and_mutation():
    spec = importlib.util.spec_from_file_location("h6_recover_decimal", RECOVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = load(SELF_RESULT)
    direction_sha = sha(DIRECTION)
    A11, B11 = module.validate_self_result(result, direction_sha)
    require(A11 == F(result["denominator"]) and
            B11 == F(result["numerator"]), "accepted self forms")
    # The producer independently rounds each derived Decimal100 field.  One
    # final-ulp mutation must nevertheless fail the replay gate.
    mutated = json.loads(json.dumps(result))
    final = mutated["numerator"][-1]
    mutated["numerator"] = mutated["numerator"][:-1] + str((int(final)+1) % 10)
    try:
        module.validate_self_result(mutated, direction_sha)
    except ValueError:
        pass
    else:
        raise AssertionError("one-final-ulp numerator mutation accepted")

    manifest = load(MANIFEST)
    D0, N0, a, b = module.manifest_action(manifest)
    line = module.line_reconstruction(D0, N0, a, b, A11, B11)
    require(F(line["projective_generalized_eigen_polynomial"]["lambda2"]) > 0,
            "projective pencil leading coefficient")
    require(len(line["stationary_roots_decimal100"]) == 2 and
            line["line_max_strictly_above_one"] is False and
            F(line["projective_maximum_decimal100"]) < 1,
            "complete H6 line maximum")


def main():
    tests = [test_reproducible_bytes_and_fail_closed_existing,
             test_literal_h6_and_candidate_normalizations,
             test_action_factors_and_line_algebra,
             test_decimal100_self_result_replay_and_mutation]
    for test in tests:
        test()
        print("PASS", test.__name__)
    print(f"PASS all {len(tests)} tests")
    print("generator_sha256", sha(GENERATOR))
    print("recovery_sha256", sha(RECOVER))


if __name__ == "__main__":
    main()
