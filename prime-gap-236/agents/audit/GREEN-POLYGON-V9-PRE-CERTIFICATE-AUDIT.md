# Green-polygon-v9 hostile pre-certificate audit

## Verdict and frozen bytes

**PRE-CERTIFICATE AUDIT PASS** for the repaired Green-v9 source/checker
bundle:

```text
agents/exact-projection-engine/green_polygon_moments.py
019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c

agents/exact-projection-engine/test_green_polygon_moments.py
05684adf3d1bfef537718819372525e97dd72cfc24b88e0a697a269a44cd9bfe

agents/exact-projection-engine/benchmark_green_polygon_target.py
480f8c2e4bc67d270a4739df2bc2c048203c27fdc0b580dca140f0a09bc14217

agents/exact-projection-engine/d14_grid38_scaled_b_shard_green_v9.py
ad38951dadecdb5a5c51d1221b0a078bc9f804e9c4ec8d434706fca55a11935a

agents/audit/verify_green_v9_cross_shard.py
7dbb352011d840a5bddf8f6f101f864d0a1b1e436ff4ebb5533ef1137217b4a7

agents/audit/test_verify_green_v9_cross_shard.py
6510af2c6705bd9ad1efde5ecd802547fda93243d361e3edc6c82502a96e4c4c
```

Independent audit suites:

```text
agents/audit/test_green_polygon_v9_independent.py
17232d337c945063be0e26fbb6e4141badf0d20faadbd03032ab8422e8209957

agents/audit/test_green_v9_checker_independent.py
a03d9d4d09e6414b354125bbc5911064618517702ca9190661ae47af39f013c3
```

This authorizes theorem-scale shard computation and later result comparison.
It does not certify any future v9 result, scalar aggregate, sign, quotient, or
prime-gap theorem.

## Failures found and repaired

The initial core `5ae1...` accepted a triangle boundary traversed twice: all
local turns and its signed area had the same orientation, so it returned area
`1` and first moments `1/3` instead of the geometric triangle's area `1/2`
and moments `1/6`.  It likewise accepted a five-vertex pentagram with all
vertices distinct.  Thus its advertised convex-cyclic fail-close was false.

The first repair added distinctness and a global supporting-half-plane test.
During optimized audit, that nominally frozen source was changed again after
a separate zero-shoelace noncollinear example was found.  The old runner
correctly failed its local source pin, so no verdict was issued.  The final
snapshot above additionally rejects zero signed area whenever any consecutive
turn is nonzero.  Both earlier snapshots are retired; no audit conclusion is
inherited from them.

## Exact Green denominator proof

Let `P` be a rational convex polygon with counterclockwise vertices and let
`L` clear every vertex-coordinate denominator.  Green's theorem gives

```text
integral_P x^a y^b dxdy
  = 1/(a+1) sum_edges integral_0^1
      x(t)^(a+1) y(t)^b y'(t) dt.
```

After replacing each coordinate by an integer affine form divided by `L`, an
edge term of a degree-`d=a+b` moment has coordinate denominator `L^(d+2)`:
`a+1` powers of `x`, `b` powers of `y`, and one `dy`.  Expanding the two
one-variable powers leaves terms `c_ij t^(i+j)`, whose integral has divisor
`i+j+1`.  For every requested `d<=E`, set `T=(E+2)!`.  Then

```text
L^(E+2) T^2
```

clears every edge contribution because `L^(E-d)` is integral, both
`a+1<=E+1` and `i+j+1<=E+1` divide `T`, and the two divisors are cleared by
independent copies of `T`.  The implementation performs precisely this
integer accumulation and constructs one final `Fraction` per requested
moment.  Clockwise input reverses the boundary sign and is corrected by the
exact orientation factor.

The D19 fiber marginal and D14 outer component contribute at most polynomial
degree 35.  On a two-dimensional shared face, the aggregate-simplex density
adds `(r-1)+(47-r-1)=45`; therefore the actual target request ceiling is 80,
not 35.  The audit tests and denominator checks use `E=80` throughout the
target path.

## Convexity and degeneracy proof

For nonzero signed area the core chooses its exact orientation `o`.  It
requires all vertices to be distinct and, for every directed boundary edge
`v_i v_{i+1}`, requires

```text
o * cross(v_{i+1}-v_i, v_j-v_i) >= 0
```

for every vertex `v_j`.  Hence every listed edge is a supporting line of the
convex hull on the orientation-consistent side.  Distinctness prevents a
repeated traversal; the global edge condition rejects chords, stars,
interior-vertex excursions, and self-intersections.  Collinear boundary
vertices remain valid.  If signed area is zero, every consecutive turn must
also be zero; with distinct consecutive vertices this propagates one common
line through the whole cycle, so returning zero is valid.  A nonzero turn at
zero signed area raises.

The independent suite exhaustively permuted a strict five-vertex convex set:
exactly its five rotations in each of two orientations were accepted, while
the other 110 orders failed.  It separately rejected the repeated triangle,
the distinct pentagram, an interior-vertex excursion, and the exact
zero-shoelace noncollinear counterexample.

## Target and runtime evidence

The independent audit uses the already audited fixed-triangle integer engine,
not Green boundary integration, as its exact oracle.  It established:

- unit-simplex closed forms through degree 80, clockwise/reversed/cyclic
  orientation, rational negative-coordinate polygons, and collinear boundary
  points;
- exact equality on the hard 666-moment target batch
  `x^(8+a)y^(37+b)`, `a+b<=35`, including degree 80;
- divisibility of every reduced result denominator by
  `L^82*(82!)^2`;
- enumeration of all 804 scheduled positive-total high/low branch/shift
  cases for common `r=1..12`; all 711 positive-area polygons passed the
  convex guard and all low moments matched the independent triangle engine;
- exact interval handling on zero-dimensional aggregate faces without ever
  invoking the polygon routine; and
- actual runner wiring: the wrapper around the pinned snapshot loader changes
  only the freshly loaded radial module for `base.RADIAL`, and that exact
  object is the one passed to cached-v7.

The standalone hard-batch benchmark returned 666 moments of maximum degree
80 with exact content hash

```text
ca9b3fec5b0dccc20afbc8e0eb717e8fe00152287e9c4bf2311427dc13a163d8
```

in 1.007 seconds on the audit machine.  Performance is not used as evidence
of equality.

The runner recursively snapshots the cached-v7/v6/v5/v3/v2/base closure,
the Green core/test/benchmark, and all candidate/support inputs; it rechecks
all bytes after computation, binds its external self hash into the result,
and publishes through the audited exclusive publisher.

## Result checker

Checker `7dbb...` requires the exact Green format, producer, algorithm map,
canonical schema, and serialized/live source closure.  It normalizes exactly
the five proved identity fields to fixed-polygon-v8 and sends the record
through the complete `v8 -> v7 -> v6 -> v5 -> v3 -> v2` structural audit
cascade.  That cascade reconstructs factor 48, branch inventories, `H=14-r`,
active families, exact fixed-radial denominator relations, work counts,
geometry, candidates, and scales.

An optional same-count v8 reference is audited separately.  All exact
mathematical fields, branch values/statistics, integer-radial metadata,
geometry, candidate, and scale records must be bit-equal; only top/nested
timings and peak RSS may differ.  The independent suite changed a branch and
the final scalar consistently by the factor 48 and verified that the
reference comparison still rejected it.  It also attacked schema, source,
boolean count, work counters, external self pinning, and exclusive output.

## Test evidence and reproduction

Production core tests passed `3/3` and production checker tests `4/4` in both
normal and optimized modes.  Independent core/runtime tests passed `5/5` in
60.325 and 66.127 seconds; independent checker tests passed `5/5` in both
modes.

```bash
cd prime-gap-236
python3 -B -I -X pycache_prefix=/tmp/green-prod-normal \
  agents/exact-projection-engine/test_green_polygon_moments.py
python3 -B -O -I -X pycache_prefix=/tmp/green-prod-opt \
  agents/exact-projection-engine/test_green_polygon_moments.py
python3 -B -I -X pycache_prefix=/tmp/green-audit-normal \
  agents/audit/test_green_polygon_v9_independent.py
python3 -B -O -I -X pycache_prefix=/tmp/green-audit-opt \
  agents/audit/test_green_polygon_v9_independent.py
python3 -B -I -X pycache_prefix=/tmp/green-check-audit-normal \
  agents/audit/test_green_v9_checker_independent.py
python3 -B -O -I -X pycache_prefix=/tmp/green-check-audit-opt \
  agents/audit/test_green_v9_checker_independent.py
```

Every theorem-scale v9 shard remains a new result-level object.  It must be
checked under normal and optimized modes and compared with a same-count v8
result whenever one is available; this source verdict cannot be inherited as
a result verdict.
