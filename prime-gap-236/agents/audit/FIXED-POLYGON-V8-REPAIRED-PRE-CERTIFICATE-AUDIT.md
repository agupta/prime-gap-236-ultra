# Repaired fixed-polygon v8 hostile pre-certificate audit

## Verdict and exact scope

**PRE-CERTIFICATE AUDIT PASS** for the repaired, unlaunched fixed-polygon-v8
source and structural/result-checker bundle:

```text
agents/exact-projection-engine/fixed_polygon_moments.py
4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb

agents/exact-projection-engine/test_fixed_polygon_moments.py
165bacf0b02778e35151327112832898f6c40870ac68d8de3d349ac52e6ffd36

agents/exact-projection-engine/d14_grid38_scaled_b_shard_fixed_polygon_v8.py
36a8e027c83cabb272aa28a5d542dc571793cbcf90c5ca48787bc20092a55b72

agents/audit/verify_fixed_polygon_v8_cross_shard.py
ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c

agents/audit/test_verify_fixed_polygon_v8_cross_shard.py
91e827601235c6b08bf65a1f2cf2608954d6e26849171b4edd8ff55ab970e3f3
```

The earlier runner `649c...` was an executable fatal failure and remains
documented separately in `FIXED-POLYGON-V8-PRELAUNCH-AUDIT.md`.  No verdict
from that retired snapshot is inherited here.

This repaired verdict authorizes a target computation and later strict
result audit.  No target v8 shard was available during this audit, so it does
not certify any shard value, aggregate sign, quotient, or prime-gap theorem.

## Fixed-denominator derivation

Let a triangle have rational vertices whose coordinate denominators divide
`L`.  After multiplying the vertex coordinates by `L`, its affine
parameterization over the standard simplex is

```text
x = X(u,v)/L,  y = Y(u,v)/L,
dx dy = |det(P,Q)| du dv / L^2,
```

where `X,Y` have integer coefficients.  For a requested monomial of total
degree `d=a+b<=E`, expand

```text
X(u,v)^a Y(u,v)^b = sum c[i,j] u^i v^j
```

with integer coefficients and `i+j<=d`.  Since

```text
integral_simplex u^i v^j = i! j!/(i+j+2)!,
```

multiplication by

```text
D = L^(E+2) (E+2)!
```

gives the integer

```text
|det| L^(E-d) sum c[i,j] i! j! (E+2)!/(i+j+2)!.
```

Both divisibilities are literal: `E-d>=0` and `(i+j+2)!` divides
`(E+2)!`.  The implementation constructs precisely these factors, sums the
integer numerators over the convex fan, and creates one final `Fraction` per
requested moment.  No favorable rounding or intermediate rational
normalization is present.

The D19 inner marginal has total polynomial degree at most 20 after its one
fiber integration, while the D14 outer marginal has degree at most 15, so
their polynomial product contributes at most 35.  This is not yet the final
polygon degree.  On a two-dimensional common face there are `r` large and
`s=47-r` small shared coordinates; their aggregate-simplex densities add
baseline powers `(r-1)+(s-1)=45`.  Radialization preserves the remaining
polynomial degree, and the affine expansions only distribute it between the
two aggregate variables.  Hence every requested target polygon moment has
total degree at most

```text
E = 35 + 45 = 80.
```

The initial audit incorrectly stopped at 35; authorization was explicitly
withdrawn, and the entire independent suite was rerun at the corrected
ceiling 80 before this report was frozen.

## Independent polygon and target-domain reconstruction

The independent oracle does not call the pinned reference triangulator.  It
constructs each polygon by enumerating exact pairwise intersections of the
half-planes

```text
x>=0, y>=0, x+y<=T,
x<=x_bound, y<=y_upper, y>=y_lower, x+y>=total_lower
```

when the optional constraints are present, then takes an exact monotone
convex hull.  Moments are computed from Green's theorem,

```text
integral_P x^a y^b dxdy
 = 1/(a+1) integral_boundary(P) x^(a+1) y^b dy,
```

by an exact binomial expansion on every oriented edge.  This representation
shares neither fan triangulation nor the simplex beta-moment recurrence with
v8.

The oracle matched v8 exactly on:

- closed-form unit-simplex moments through total degree 80;
- a rational triangle crossing negative coordinates, in forward, reverse,
  and cyclically rotated vertex order;
- empty, point, segment, and collinear degenerate polygons;
- a dense set of all 666 target-shaped moments
  `x^(8+a)y^(37+b)`, `a+b<=35`, on a clipped polygon.  These are exactly the
  `r=9` radial-density offsets and reach total degree 80;
- every positive-total target high/low branch and inclusion-exclusion shift
  for common counts `r=1..12`: 804 exact domain/shift cases, of which 711
  have nonempty two-dimensional interiors.  For every `r`, sparse probes use
  the actual offsets `x^(r-1)y^(46-r)` and add pure and mixed polynomial
  powers summing to 35, so every case reaches total degree 80.

For every target case, each reduced output denominator was also checked to
divide `L^82 82!` exactly.  The `r=0`, `s=0`, and one-sided aggregate faces
were separately sent through the frozen scalar domain dispatcher with a
polygon routine that raises if called; all three zero-dimensional paths
returned their independently calculated point/interval moments without
touching the v8 routine.

Independent core/runtime tests:

```text
agents/audit/test_fixed_polygon_v8_independent.py
25c35d41f666e14b6a6b090c1aa981dc9b2d01331d56832b6bd078767b26dabd
```

They pass `5/5` in normal and optimized mode.  The corrected full runs took
355.413 and 350.760 seconds respectively.

## Runtime substitution and source closure

The repaired runner does not assign an attribute to the path `base.RADIAL`.
It saves the pinned `base.import_snapshot`, wraps it, and after the original
loader has instantiated the exact module for that path, replaces only that
module's `_polygon_monomial_batch`.  The module is the same object passed by
`v2.build` into the cached-v7 scalar backend.  All other snapshot loads are
returned unchanged.

An independent runner probe intercepts only the expensive `v2.build` call;
inside that call it invokes the runner-installed loader on the exact pinned
radial bytes and verifies by object identity that the live radial module
contains the exact fixed-moment function.  It also checks the repaired
algorithm flag, producer hash, format, source snapshots, and exclusive
publication.  Separately, a real hash-pinned `common-r=12` runner invocation
was allowed to execute for 15 seconds.  It passed the former crash point and
entered the true build, printing the exact 568-by-462 kernel inventory and
104,902 output terms before an intentional `SIGINT` cap.  It published no
partial result.

The runner snapshots and checks the v8 core/test, then recursively snapshots
the frozen v7/v6/v5/v3/v2/base closure and all candidate/support inputs.  It
rechecks its own bytes and every dependency snapshot after computation.  The
v8 producer is externally self-pinned and serialized as `producer_sha256`;
the inherited exclusive publisher prevents overwrite or partial final-name
publication.

## Structural/result checker

The repaired checker requires the exact v8 format/status/algorithm, producer
hash, and serialized/live source closure.  It normalizes exactly five
identity fields—format, status, producer, source map, and algorithm—to the
audited cached-v7 wire contract and submits the result to checker `80ec...`.
That inherited chain reconstructs exact branch values, factor 48, `H=14-r`,
active families, fixed radial denominators, cache inventories, geometry, and
scales.

An optional same-count cached-v7 reference is independently audited.  The
comparison excludes only top-level and nested timing fields and peak RSS; it
requires bit equality of the exact scalar, high/low branches, branch work
statistics, integer radial metadata, kernel/family inventories, geometry,
candidate, and scaling.  A consistent mutation of a branch together with
its factor-48 scalar was rejected by this comparison.

Independent checker tests:

```text
agents/audit/test_fixed_polygon_v8_checker_independent.py
3fe18751e60b8933398f22a049dc2a192e7956fb93956d44d993f2b5a22c42cc
```

They pass `5/5` in normal and optimized mode and cover exact normalization,
timing/RSS variation, byte-hash binding, consistent branch mutation, schema,
source, type, cache-work mutations, external self pinning, and exclusive
audit-output publication.  The production checker tests now use explicit
raises rather than optimization-elided assertions and pass `4/4` in both
modes.  The production core passes `3/3` in both modes.

## Reproduction

```bash
cd prime-gap-236
python3 -B -I -X pycache_prefix=/tmp/v8-core-prod-normal \
  agents/exact-projection-engine/test_fixed_polygon_moments.py
python3 -B -O -I -X pycache_prefix=/tmp/v8-core-prod-opt \
  agents/exact-projection-engine/test_fixed_polygon_moments.py
python3 -B -I -X pycache_prefix=/tmp/v8-core-audit-normal \
  agents/audit/test_fixed_polygon_v8_independent.py
python3 -B -O -I -X pycache_prefix=/tmp/v8-core-audit-opt \
  agents/audit/test_fixed_polygon_v8_independent.py
python3 -B -I -X pycache_prefix=/tmp/v8-check-prod-normal \
  agents/audit/test_verify_fixed_polygon_v8_cross_shard.py
python3 -B -O -I -X pycache_prefix=/tmp/v8-check-prod-opt \
  agents/audit/test_verify_fixed_polygon_v8_cross_shard.py
python3 -B -I -X pycache_prefix=/tmp/v8-check-audit-normal \
  agents/audit/test_fixed_polygon_v8_checker_independent.py
python3 -B -O -I -X pycache_prefix=/tmp/v8-check-audit-opt \
  agents/audit/test_fixed_polygon_v8_checker_independent.py
```

## Result-level gate

Every future v8 shard must be checked afresh with checker `ec0162a7...` in
normal and optimized mode, with exact input SHA recorded.  A same-count v7
reference should be supplied whenever one exists.  This source PASS cannot
be promoted to a result PASS or theorem claim without those checks and the
independent aggregate/replay/analytic gates.
