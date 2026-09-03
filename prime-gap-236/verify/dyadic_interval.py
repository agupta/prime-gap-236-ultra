#!/usr/bin/env python3
"""Small fixed-point interval ring with integer-directed rounding.

An interval is stored as two integers ``lo, hi`` and denotes
``[lo/2**P, hi/2**P]``.  No hardware or Decimal rounding mode enters the
arithmetic.  This module is intended for a future rigorous reconstruction of
the scalar C10 integrals; it is not itself a sieve certificate.

The optional tiny exact shadow exists only to make support-geometry branch
decisions exact.  It is deliberately discarded once its numerator or
denominator grows beyond ``SHADOW_BITS``.  Arithmetic validity never depends
on the shadow: the integer endpoints alone are outward rounded.
"""

from __future__ import annotations

from fractions import Fraction
from typing import ClassVar


class IndeterminateComparison(ArithmeticError):
    """Raised rather than guessing when two enclosures overlap."""


class DyadicInterval:
    """A fixed-precision closed interval with rigorous integer endpoints."""

    PRECISION: ClassVar[int] = 512
    SCALE: ClassVar[int] = 1 << PRECISION
    SHADOW_BITS: ClassVar[int] = 96
    _LOCKED: ClassVar[bool] = False
    __slots__ = ("lo", "hi", "exact")

    def __init__(self, numerator=0, denominator=None):
        type(self)._LOCKED = True
        if isinstance(numerator, DyadicInterval):
            if denominator is not None:
                raise TypeError("denominator supplied with interval")
            self.lo = numerator.lo
            self.hi = numerator.hi
            self.exact = numerator.exact
            return
        if denominator is None:
            value = numerator if isinstance(numerator, Fraction) \
                else Fraction(numerator)
        else:
            value = Fraction(numerator, denominator)
        scaled = value.numerator * self.SCALE
        self.lo = scaled // value.denominator
        self.hi = -((-scaled) // value.denominator)
        self.exact = self._small_shadow(value)

    @classmethod
    def configure(cls, precision: int, shadow_bits: int = 96) -> None:
        if not isinstance(precision, int) or precision < 16:
            raise ValueError("precision must be an integer at least 16")
        if not isinstance(shadow_bits, int) or shadow_bits < 8:
            raise ValueError("shadow_bits must be an integer at least 8")
        if cls._LOCKED:
            if precision == cls.PRECISION and shadow_bits == cls.SHADOW_BITS:
                return
            raise RuntimeError(
                "dyadic precision is immutable after the first interval")
        cls.PRECISION = precision
        cls.SCALE = 1 << precision
        cls.SHADOW_BITS = shadow_bits

    @classmethod
    def _small_shadow(cls, value: Fraction):
        if value == 0:
            return value
        if (abs(value.numerator).bit_length() <= cls.SHADOW_BITS and
                value.denominator.bit_length() <= cls.SHADOW_BITS):
            return value
        return None

    @classmethod
    def _from_bounds(cls, lo: int, hi: int, exact=None):
        if lo > hi:
            raise ArithmeticError("reversed interval")
        answer = object.__new__(cls)
        cls._LOCKED = True
        answer.lo = int(lo)
        answer.hi = int(hi)
        answer.exact = (cls._small_shadow(exact)
                        if isinstance(exact, Fraction) else None)
        return answer

    @classmethod
    def _coerce(cls, other):
        return other if isinstance(other, cls) else cls(other)

    @staticmethod
    def _floor_ratio(numerator: int, denominator: int) -> int:
        if denominator == 0:
            raise ZeroDivisionError
        return numerator // denominator

    @staticmethod
    def _ceil_ratio(numerator: int, denominator: int) -> int:
        if denominator == 0:
            raise ZeroDivisionError
        return -((-numerator) // denominator)

    @classmethod
    def _shadow_binary(cls, left, right, operation):
        if left.exact is None or right.exact is None:
            return None
        return operation(left.exact, right.exact)

    def __neg__(self):
        exact = None if self.exact is None else -self.exact
        return self._from_bounds(-self.hi, -self.lo, exact)

    def __pos__(self):
        return self

    def __add__(self, other):
        other = self._coerce(other)
        exact = self._shadow_binary(self, other, lambda x, y: x + y)
        return self._from_bounds(self.lo + other.lo, self.hi + other.hi,
                                 exact)

    __radd__ = __add__

    def __sub__(self, other):
        return self + (-self._coerce(other))

    def __rsub__(self, other):
        return self._coerce(other) - self

    def __mul__(self, other):
        other = self._coerce(other)
        products = (self.lo * other.lo, self.lo * other.hi,
                    self.hi * other.lo, self.hi * other.hi)
        smallest, largest = min(products), max(products)
        lo = smallest // self.SCALE
        hi = -((-largest) // self.SCALE)
        exact = self._shadow_binary(self, other, lambda x, y: x * y)
        return self._from_bounds(lo, hi, exact)

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = self._coerce(other)
        if other.lo <= 0 <= other.hi:
            raise ZeroDivisionError("interval denominator contains zero")
        endpoint_pairs = ((self.lo, other.lo), (self.lo, other.hi),
                          (self.hi, other.lo), (self.hi, other.hi))
        lo = min(self._floor_ratio(n * self.SCALE, d)
                 for n, d in endpoint_pairs)
        hi = max(self._ceil_ratio(n * self.SCALE, d)
                 for n, d in endpoint_pairs)
        exact = self._shadow_binary(self, other, lambda x, y: x / y)
        return self._from_bounds(lo, hi, exact)

    def __rtruediv__(self, other):
        return self._coerce(other) / self

    def __floordiv__(self, other):
        other = self._coerce(other)
        if self.exact is not None and other.exact is not None:
            if other.exact == 0:
                raise ZeroDivisionError
            return self.exact // other.exact
        quotient = self / other
        lower_floor = quotient.lo // self.SCALE
        upper_floor = quotient.hi // self.SCALE
        if lower_floor != upper_floor:
            raise IndeterminateComparison(
                "interval quotient does not determine a unique floor")
        return lower_floor

    def __pow__(self, exponent: int):
        if not isinstance(exponent, int):
            raise TypeError("only integer powers are supported")
        if exponent < 0:
            return self._coerce(1) / (self ** (-exponent))
        answer = self._coerce(1)
        base = self
        power = exponent
        while power:
            if power & 1:
                answer = answer * base
            power >>= 1
            if power:
                base = base * base
        return answer

    def __abs__(self):
        if self.lo >= 0:
            return self
        if self.hi <= 0:
            return -self
        exact = None if self.exact is None else abs(self.exact)
        return self._from_bounds(0, max(-self.lo, self.hi), exact)

    def _ordered(self, other, weak: bool) -> bool:
        other = self._coerce(other)
        if self.exact is not None and other.exact is not None:
            return (self.exact <= other.exact if weak
                    else self.exact < other.exact)
        if weak:
            if self.hi <= other.lo:
                return True
            if self.lo > other.hi:
                return False
        else:
            if self.hi < other.lo:
                return True
            if self.lo >= other.hi:
                return False
        raise IndeterminateComparison(
            f"overlapping intervals in {'<=' if weak else '<'} comparison")

    def __lt__(self, other):
        return self._ordered(other, False)

    def __le__(self, other):
        return self._ordered(other, True)

    def __gt__(self, other):
        return self._coerce(other)._ordered(self, False)

    def __ge__(self, other):
        return self._coerce(other)._ordered(self, True)

    def __eq__(self, other):
        if self is other:
            return True
        try:
            other = self._coerce(other)
        except (TypeError, ValueError, ZeroDivisionError):
            return False
        if self.exact is not None and other.exact is not None:
            return self.exact == other.exact
        if self.exact is None and other.exact is None:
            # Equal *enclosures* do not prove equal represented numbers.
            # Only a common zero-width dyadic interval is a proved value.
            return (self.lo == self.hi == other.lo == other.hi)
        return False

    def __hash__(self):
        if self.exact is not None:
            # Python numeric equality requires equal hashes across numeric
            # types: Fraction(1), 1, and an exact-shadow interval for 1 are
            # equal.  This also prevents bifurcated lru_cache entries.
            return hash(self.exact)
        if self.lo == self.hi:
            # A zero-width dyadic enclosure is also a proved rational value.
            return hash(Fraction(self.lo, self.SCALE))
        return hash((DyadicInterval, self.lo, self.hi))

    def __bool__(self):
        return not ((self.exact == 0 if self.exact is not None else False) or
                    (self.lo == 0 and self.hi == 0))

    def contains(self, value) -> bool:
        value = value if isinstance(value, Fraction) else Fraction(value)
        scaled = value.numerator * self.SCALE
        return (self.lo * value.denominator <= scaled <=
                self.hi * value.denominator)

    def width_units(self) -> int:
        return self.hi - self.lo

    def lower_fraction(self) -> Fraction:
        return Fraction(self.lo, self.SCALE)

    def upper_fraction(self) -> Fraction:
        return Fraction(self.hi, self.SCALE)

    def midpoint_fraction(self) -> Fraction:
        return Fraction(self.lo + self.hi, 2 * self.SCALE)

    def is_finite(self) -> bool:
        return True

    def __repr__(self):
        return (f"DyadicInterval(lo={self.lo}, hi={self.hi}, "
                f"precision={self.PRECISION})")

    def __str__(self):
        if self.exact is not None:
            return f"[{self.exact},{self.exact}]~dyadic"
        return f"[{self.lo}/2^{self.PRECISION},{self.hi}/2^{self.PRECISION}]"


__all__ = ["DyadicInterval", "IndeterminateComparison"]
