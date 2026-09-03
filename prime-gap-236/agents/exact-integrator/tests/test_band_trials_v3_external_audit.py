#!/usr/bin/env python3
"""Independent exact audit of the frozen v3 H12-near20 band trial.

This deliberately reconstructs the 20-to-272 ownership map from the JSON
schema instead of importing the trial producer or its ``BandMap.expand``.
"""

import hashlib
import json
import sys
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
PG = HERE.parents[2]
SB = PG / "agents/structural-basis"
EA = PG / "agents/exact-integrator"
sys.path[:0] = [str(SB / "code"), str(EA), str(EA / "src")]

from band_operator import (BandMap, full_simplex_i_preconditioner,  # noqa: E402
                           matvec)


PATHS = {
    "raw": SB / "results/c10_D12_band_sparse_gradient_mp100.json",
    "recovery": SB / "results/c10_D12_band_sparse_gradient_recovered_v2.json",
    "source": EA / "results/hb_c10_fullsimplex_noones_D12.json",
    "bands": SB / "results/c10_D12_degree_bands.json",
    "manifest": SB / "results/c10_D12_band_trials_manifest_v3.json",
    "near20": SB / "results/c10_D12_h12_near_20pct_v3.json",
}
HASHES = {
    "raw": "0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d",
    "recovery": "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43",
    "source": "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87",
    "bands": "29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9",
    "manifest": "c16b960004b42e0c66fd2255fd6002eed1cbcf049167fe88f1f18c124e7686e5",
    "near20": "88c1d26f6cf46bbdd12dc000eb802cac8efe91be0ad003d6827f2ccdc6c0ff47",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label(raw):
    return int(raw[0]), tuple(map(int, raw[1]))


def median(values):
    values = sorted(values)
    n = len(values)
    return values[n // 2] if n % 2 else \
        (values[n // 2 - 1] + values[n // 2]) / 2


def all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_keys(child)


class FrozenBandTrialV3Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for key, path in PATHS.items():
            if sha(path) != HASHES[key]:
                raise AssertionError(f"{key} SHA mismatch")
        cls.data = {key: json.loads(path.read_bytes())
                    for key, path in PATHS.items()}

    def test_exact_near20_gauge_expansion_and_derivatives(self):
        raw, recovery = self.data["raw"], self.data["recovery"]
        source, bands = self.data["source"], self.data["bands"]
        manifest, trial = self.data["manifest"], self.data["near20"]

        source_labels = [label(item) for item in source["basis"]]
        owner, weight = {}, {}
        coordinate = 0
        for item in bands["core"]:
            owner[label(item["label"])] = coordinate
            weight[label(item["label"])] = Fraction(1)
            coordinate += 1
        for degree in sorted(bands["bands"], key=int):
            for item in bands["bands"][degree]:
                key = label(item["label"])
                self.assertNotIn(key, owner)
                owner[key] = coordinate
                weight[key] = Fraction(item["coefficient"])
            coordinate += 1
        self.assertEqual(coordinate, 20)
        self.assertEqual(set(owner), set(source_labels))
        self.assertEqual([label(item) for item in trial["basis"]], source_labels)

        theta0 = list(map(Fraction, raw["theta"]))
        direction = list(map(Fraction,
                             manifest["base_action_diagnostics"]["direction"]))
        theta1 = list(map(Fraction, trial["compressed_theta"]))
        detail = trial["trial"]
        step = Fraction(detail["exact_step_t"])
        scale = Fraction(detail["exact_H12_gauge_scale"])
        self.assertEqual(theta0[19], 1)
        self.assertEqual(scale, 1 / (theta0[19] + step * direction[19]))
        self.assertEqual(theta1,
                         [scale * (x + step * d)
                          for x, d in zip(theta0, direction)])
        self.assertEqual(theta1[19], 1)

        expanded0 = [weight[key] * theta0[owner[key]] for key in source_labels]
        expanded1 = [weight[key] * theta1[owner[key]] for key in source_labels]
        self.assertEqual(expanded1, list(map(Fraction, trial["rational_vector"])))
        self.assertTrue(all(expanded0))
        raw_changes = [abs(step * direction[owner[key]] /
                           theta0[owner[key]]) for key in source_labels]
        normalized = [abs(x / y - 1) for x, y in zip(expanded1, expanded0)]
        compressed = [abs(x / y - 1) for x, y in zip(theta1, theta0)]
        self.assertEqual(max(normalized), Fraction(1, 5))
        self.assertEqual(Fraction(detail[
            "raw_path_max_relative_coefficient_change"]), max(raw_changes))
        self.assertEqual(Fraction(detail[
            "raw_path_median_relative_coefficient_change"]), median(raw_changes))
        self.assertEqual(Fraction(detail[
            "normalized_max_relative_coefficient_change"]), max(normalized))
        self.assertEqual(Fraction(detail[
            "normalized_median_relative_coefficient_change"]), median(normalized))
        self.assertEqual(Fraction(detail[
            "compressed_max_relative_coordinate_change"]), max(compressed))
        self.assertEqual(Fraction(detail[
            "compressed_median_relative_coordinate_change"]), median(compressed))

        denominator, numerator = Fraction(raw["denominator"]), Fraction(raw["numerator"])
        quotient = numerator / denominator
        a_theta = list(map(Fraction, recovery["a_theta_exact_fraction_half"]))
        b_theta = list(map(Fraction, recovery["b_theta_exact_fraction_half"]))
        self.assertEqual(a_theta,
                         [Fraction(x) / 2 for x in raw["grad_denominator"]])
        self.assertEqual(b_theta,
                         [Fraction(x) / 2 for x in raw["grad_numerator"]])
        residual = [b - quotient * a for a, b in zip(a_theta, b_theta)]
        displacement = [x - y for x, y in zip(theta1, theta0)]
        derivative = 2 * sum((x * r for x, r in
                              zip(displacement, residual)), Fraction(0)) / denominator
        dprime = 2 * sum((d * a for d, a in zip(direction, a_theta)), Fraction(0))
        nprime = 2 * sum((d * b for d, b in zip(direction, b_theta)), Fraction(0))
        qprime = (nprime * denominator - numerator * dprime) / denominator**2
        diagnostics = manifest["base_action_diagnostics"]
        self.assertEqual(Fraction(diagnostics["denominator_first_derivative_exact"]),
                         dprime)
        self.assertEqual(Fraction(diagnostics["numerator_first_derivative_exact"]),
                         nprime)
        self.assertEqual(Fraction(diagnostics["rayleigh_first_derivative_exact"]),
                         qprime)
        self.assertEqual(Fraction(detail["normalized_trial_first_derivative_exact"]),
                         derivative)
        self.assertEqual(Fraction(detail["scaled_raw_path_first_derivative_exact"]),
                         scale * step * qprime)
        self.assertGreater(derivative, 0)
        self.assertGreater(qprime, 0)

        keys = set(all_keys(trial))
        self.assertFalse({"denominator", "numerator", "quotient"} & keys)
        self.assertFalse(trial["finite_form_value_claimed"])
        self.assertTrue(trial["fresh_scalar_reevaluation_required"])
        near20_row = next(row for row in manifest["trials"]
                          if row["name"] == "h12_near_20pct")
        self.assertEqual(near20_row["sha256"], HASHES["near20"])

    def test_full_simplex_p_tangent_direction(self):
        """Cross-check the serialized direction against a fresh P rebuild."""
        raw, manifest = self.data["raw"], self.data["manifest"]
        band_map = BandMap.from_source_and_bands(PATHS["source"], PATHS["bands"])
        with localcontext() as context:
            # Match the producer's first solve precision; the P-orthogonality
            # is a cancellation at roughly 190 digits and is invisible in a
            # merely 100-digit rebuild.
            context.prec = 230
            alpha_q = Fraction(raw["parameters"]["alpha"])
            alpha = Decimal(alpha_q.numerator) / Decimal(alpha_q.denominator)
            p = full_simplex_i_preconditioner(band_map, 48, alpha, Decimal)
            theta = [Decimal(Fraction(x).numerator) / Decimal(Fraction(x).denominator)
                     for x in raw["theta"]]
            direction = [Decimal(Fraction(x).numerator) /
                         Decimal(Fraction(x).denominator) for x in
                         manifest["base_action_diagnostics"]["direction"]]
            ptheta = matvec(p, theta, Decimal(0))
            pdirection = matvec(p, direction, Decimal(0))
            theta_p_d = sum((x * y for x, y in zip(theta, pdirection)), Decimal(0))
            d_p_d = sum((x * y for x, y in zip(direction, pdirection)), Decimal(0))
            theta_p_theta = sum((x * y for x, y in zip(theta, ptheta)), Decimal(0))
            self.assertLess(abs(theta_p_d) / theta_p_theta.sqrt(), Decimal("1e-180"))
            self.assertLess(abs(d_p_d - 1), Decimal("1e-180"))


if __name__ == "__main__":
    unittest.main()
