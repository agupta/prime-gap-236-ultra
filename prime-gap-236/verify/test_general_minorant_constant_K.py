import importlib.util
import pathlib
import unittest
from fractions import Fraction


PATH = pathlib.Path(__file__).with_name("general_minorant_constant_K.py")
SPEC = importlib.util.spec_from_file_location("general_minorant_constant_K", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ConstantKTests(unittest.TestCase):
    def test_k2_direct_integral(self):
        # For a triangle, K = (alpha-eta)^2/2 and I=alpha^2/2.
        A = Fraction(7, 10)
        epsilon = Fraction(1, 10)
        alpha = A + epsilon
        eta = A - epsilon
        expected = (alpha - eta) ** 2 / alpha**2
        self.assertEqual(MODULE.ratio(2, A, epsilon), expected)

    def test_zero_width_limit(self):
        A = Fraction(1, 4)
        values = [MODULE.ratio(48, A, Fraction(1, 10**n)) for n in (3, 4, 5)]
        self.assertGreater(values[0], values[1])
        self.assertGreater(values[1], values[2])
        self.assertGreater(values[2], 0)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            MODULE.ratio(1, Fraction(1, 4), Fraction(1, 100))
        with self.assertRaises(ValueError):
            MODULE.ratio(48, Fraction(1, 100), Fraction(1, 100))

    def test_proposition3_first_ii_envelope(self):
        # Combining xi_2 < 7/17 from Proposition 2 with the first scalar
        # condition (II) of Proposition 3 gives the limiting ceiling 143/544.
        self.assertEqual(
            MODULE.prop3_first_ii_A_upper(
                Fraction(7, 17), Fraction(0), Fraction(0)),
            Fraction(143, 544))

        xi2 = Fraction(2, 5)
        delta = Fraction(1, 100)
        h = Fraction(1, 10**10)
        A = MODULE.prop3_first_ii_A_upper(xi2, delta, h)
        self.assertEqual(
            xi2 / 10 - Fraction(32, 10) * A + Fraction(8, 10) - 2*h,
            delta)


if __name__ == "__main__":
    unittest.main()
