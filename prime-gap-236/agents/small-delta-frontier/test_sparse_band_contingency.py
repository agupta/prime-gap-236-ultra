#!/usr/bin/env python3
"""Independent light tests for select_sparse_band_contingency.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from fractions import Fraction as F
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SELECTOR = HERE / "select_sparse_band_contingency.py"
SOURCE = PROJECT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
BANDS = PROJECT / "agents/structural-basis/results/c10_D12_degree_bands.json"
RECOVERY = PROJECT / "agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load(path):
    return json.loads(path.read_bytes())


def run_selector():
    with tempfile.TemporaryDirectory(prefix="sparse-contingency-test.") as directory:
        output = Path(directory) / "result.json"
        subprocess.run([
            sys.executable, str(SELECTOR), "--source", str(SOURCE),
            "--bands", str(BANDS), "--recovery", str(RECOVERY),
            "--output", str(output),
        ], check=True, stdout=subprocess.DEVNULL)
        return load(output)


def test_exact_ranking_and_expansion():
    result = run_selector()
    recovery = load(RECOVERY)
    bands = load(BANDS)
    D0, N0 = F(recovery["denominator"]), F(recovery["numerator"])
    theta = [F(x) for x in recovery["theta"]]
    action_a = [F(x) for x in recovery["a_theta_exact_fraction_half"]]
    action_b = [F(x) for x in recovery["b_theta_exact_fraction_half"]]
    scores = []
    for j in range(19):
        residual = D0 * action_b[j] - N0 * action_a[j]
        scores.append((abs(theta[j] * residual), j))
    scores.sort(reverse=True)
    require(scores[0][1] == result["selected_coordinate"] == 13,
            "H6 is not independently the exact top relative coordinate")
    require(result["selected_name"] == "H6", "selected band name")
    direction20 = [F(x) for x in result["compressed_direction"]]
    require(direction20 == [F(0)] * 13 + [F(1)] + [F(0)] * 6,
            "compressed direction is not exactly +H6")
    direction272 = [F(x) for x in result["expanded_direction"]]
    require(sum(x != 0 for x in direction272) == 11 ==
            result["expanded_nonzero_count"], "H6 expanded sparsity")

    # Reconstruct H6's weights without importing the production BandMap.
    h6 = {tuple([x["label"][0], *x["label"][1]]): F(x["coefficient"])
          for x in bands["bands"]["6"]}
    source_labels = [tuple([x[0], *x[1]]) for x in load(SOURCE)["basis"]]
    expected = [h6.get(item, F(0)) for item in source_labels]
    require(direction272 == expected, "272-vector is not the literal H6 block")

    residuals = [D0 * b - N0 * a for a, b in zip(action_a, action_b)]
    R = sum(x * y for x, y in zip(direction20, residuals))
    require(R == F(result["exact_ascent_residual_R"]) > 0,
            "serialized exact residual")
    require(F(result["exact_directional_derivative"]) == 2 * R / D0**2,
            "quotient derivative identity")


def test_finite_step_identity_and_falsification():
    # A signed exact toy checks every factor in
    # Delta(t)=N(theta+t d)D0-D(theta+t d)N0.
    D0, N0, a01, b01, A11, B11, tau = map(
        F, ("7/3", "5/2", "-4/7", "11/13", "17/19", "-23/29", "2/5"))
    Dtau = D0 + 2 * tau * a01 + tau**2 * A11
    Ntau = N0 + 2 * tau * b01 + tau**2 * B11
    R = D0 * b01 - N0 * a01
    C = D0 * B11 - N0 * A11
    require(Ntau * D0 - Dtau * N0 == 2 * tau * R + tau**2 * C,
            "finite-step cross-multiplication identity")
    require((Ntau / Dtau > N0 / D0) == (C > -2 * R / tau)
            if Dtau > 0 and R > 0 else True,
            "strict-improvement criterion")

    # Same positive base and cross action, two PSD diagonal completions.  The
    # unknown self entry can flip the sign at the same nonzero rational step.
    # This is the two-dimensional normal form after splitting off theta.
    D0, N0, a01, b01, tau = F(2), F(3), F(1), F(2), F(1, 10)
    R = D0 * b01 - N0 * a01
    require(R > 0, "toy first derivative")
    # PSD requires A11>=a01^2/D0 and B11>=b01^2/N0.
    low_A, low_B = a01**2 / D0, b01**2 / N0
    positive_C = D0 * (low_B + 100) - N0 * low_A
    negative_C = D0 * low_B - N0 * (low_A + 100)
    require(2 * tau * R + tau**2 * positive_C > 0 and
            2 * tau * R + tau**2 * negative_C < 0,
            "PSD completions with identical first-order action must flip sign")


def test_bytes_and_no_finite_claim():
    one, two = run_selector(), run_selector()
    require(one == two, "forward reruns are not deterministic")
    require(one["rigorous"] is False and
            one["finite_form_value_claimed"] is False and
            one["fresh_scalar_reevaluation_required"] is True,
            "discovery-only gates")
    require("C(d)>-2*R(d)/tau" == one["finite_step_falsification"]
            ["strict_improvement_criterion_for_tau_positive"],
            "serialized falsification criterion")


def main():
    tests = [test_exact_ranking_and_expansion,
             test_finite_step_identity_and_falsification,
             test_bytes_and_no_finite_claim]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS all {len(tests)} tests")
    print("selector_sha256", hashlib.sha256(SELECTOR.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
