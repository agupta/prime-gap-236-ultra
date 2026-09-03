#!/usr/bin/env python3
"""Heuristic falsifier for the omitted omega=0 mixed Type-IIb packing.

This is not a proof checker.  It searches continuous tuples and reports the
first tuple for which no exact bin assignment exists at floating precision.
"""

from bisect import bisect_left
import math
import random


DELTA = 361 / 50000
C1 = 875449999 / 2500000000
C2 = 224729999 / 2500000000
C3 = DELTA
INNER_B = 103 / 400


def subset_sums(values):
    out = [0.0]
    for value in values:
        out += [old + value for old in out]
    return sorted(out)


def interval_subset(values, lower, upper):
    split = len(values) // 2
    left = subset_sums(values[:split])
    right = subset_sums(values[split:])
    for a in left:
        at = bisect_left(right, lower - a - 1e-15)
        if at < len(right) and a + right[at] <= upper + 1e-15:
            return True
    return False


def packable(values):
    total = math.fsum(values)
    if total <= C1:
        return True
    # Assign no item, or one item that fits, to the third bin; the remaining
    # problem is whether bin 2 can take a subset leaving at most C1 in bin 1.
    choices = [-1] + [i for i, value in enumerate(values) if value <= C3 + 1e-15]
    for removed in choices:
        residual = values if removed < 0 else values[:removed] + values[removed + 1:]
        lower = math.fsum(residual) - C1
        if interval_subset(residual, lower, C2):
            return True
    return False


def random_group(count, bound, rng):
    mandatory = count * DELTA
    spare = bound - mandatory
    raw = [rng.expovariate(1.0) for _ in range(count + 1)]
    scale = spare / math.fsum(raw)
    return [DELTA + scale * raw[i] for i in range(count)]


def main():
    rng = random.Random(0xC722)
    tested = 0
    for inner_count, outer_count in ((1, 17), (1, 18), (2, 17), (3, 18), (16, 1)):
        outer_bound = min(11 / 200 + (outer_count - 1) * DELTA, 43 / 250)
        for _ in range(100_000):
            left = random_group(inner_count, INNER_B, rng)
            right = random_group(outer_count, outer_bound, rng)
            values = left + right
            tested += 1
            if not packable(values):
                print("HEURISTIC COUNTEREXAMPLE", inner_count, outer_count)
                print("values", [float.hex(value) for value in values])
                print("loads", math.fsum(left), math.fsum(right), math.fsum(values))
                return
    print("NO HEURISTIC COUNTEREXAMPLE", tested)


if __name__ == "__main__":
    main()
