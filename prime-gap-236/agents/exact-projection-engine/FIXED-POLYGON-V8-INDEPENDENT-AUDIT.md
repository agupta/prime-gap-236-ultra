# Fixed-polygon v8 independent pre-certificate audit

Date: 2026-09-03 (Europe/Berlin)

Verdict: **SCOPED PRE-CERTIFICATE AUDIT PASS** for the repaired v8 snapshot
listed below.  This verdict authorizes a fresh target run from the source and
mathematics side only.  It is not a result audit and proves no value of a
target shard.  Every produced shard still requires the pinned result checker
in normal and optimized modes.

The earlier runner `649c5027...` is rejected and retired: it attempted to set
an attribute on the `Path` `base.RADIAL` and exited immediately with
`AttributeError`.  Nothing in this report transfers to that runner.

## Frozen scope

- repaired producer
  `d14_grid38_scaled_b_shard_fixed_polygon_v8.py`:
  `36a8e027c83cabb272aa28a5d542dc571793cbcf90c5ca48787bc20092a55b72`
- fixed polygon core `fixed_polygon_moments.py`:
  `4100a9eeb86563ae84bf02ed4df9a2a5b696b5cc9ff163d15ac482b242b637bb`
- producer-pinned core test `test_fixed_polygon_moments.py`:
  `165bacf0b02778e35151327112832898f6c40870ac68d8de3d349ac52e6ffd36`
- result checker `verify_fixed_polygon_v8_cross_shard.py`:
  `ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c`
- result-checker test `test_verify_fixed_polygon_v8_cross_shard.py`:
  `91e827601235c6b08bf65a1f2cf2608954d6e26849171b4edd8ff55ab970e3f3`
- independent hostile test `test_fixed_polygon_v8_independent.py`:
  `da0dab6479cd4c14767375ae7e78aa556b13d3cc6e1563a69f7daa0eb3ea1f81`
- original Fraction oracle `verify/exact_capped_certificate.py`:
  `1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c`

The independent test traverses and validates 29 producer pin entries across
the v8, v7, v6, v5, v2, and base closures.  A private-bytecode-cache run and
an optimized private-bytecode-cache run both import from the verified source
bytes and give the same mathematical verdict.

## Denominator theorem

Let a triangle have rational vertices and let `L` be the least common
multiple of all six coordinate denominators.  Under the standard simplex
map, write

```
x = X(u,v)/L,  y = Y(u,v)/L,
```

where `X,Y` are integer affine forms.  If the requested monomial is
`x^a y^b`, of total degree `d=a+b`, its affine expansion has integer
coefficients divided by `L^d`; the Jacobian is the absolute integer
determinant divided by `L^2`.  Every simplex term is then multiplied by

```
integral u^i v^j = i! j! / (i+j+2)!.
```

For every `d<=E`, multiplication by

```
D = L^(E+2) (E+2)!
```

leaves the integer factors
`L^(E-d)`, `i!`, `j!`, and `(E+2)!/(i+j+2)!`.  Thus `D` clears every
requested moment.  A convex polygon is triangulated from one vertex; all
triangles use the same `L,E,D`, so their sum has the same denominator.  This
is exactly the scaling implemented in the core.  Absolute determinants agree
with the old oracle on either orientation; the target polygons are convex
intersections returned by the pinned clipping routine.

For this target the polygon ceiling is 80, not 35.  The D19 marginal has
degree at most 20; the D14 outer polynomial and its distinguished-coordinate
primitive contribute at most another 15, and the two aggregate simplex
densities contribute

```
(r-1)+(s-1) = 45,  where r+s=47 and r,s>0.
```

Hence the polygon moment degree is at most `20+15+45=80`.  The `r=0`
one-dimensional interval path may have degree 81, but it does not call the
polygon batch.  Since the frozen target has `r<=12`, its other aggregate has
positive dimension in every polygon call.

## Independent exact comparisons

The hostile test enumerates the literal scheduled domains at both rational
endpoints for every `r=1,...,12`, every active Definition-5 shift, and every
one of `Sdelta`, `Stotal`, `Ltotal`, and `Lbig`.  This gives 804 target
domain/shift rows and 438 distinct exact polygons (including the empty
polygon): 119 triangles, 313 quadrilaterals, five pentagons, and one empty
polygon.

On every distinct polygon, the new core equals the original Fraction oracle
for eight moments including

```
(80,0), (0,80), (79,1), (1,79).
```

The reduced denominator of every returned moment was also checked to divide
the independently formed `L^82 82!`.  Eight seeded rational convex
quadrilaterals, and all eight reverse orientations, were compared at one
mixed/axis moment of every total degree 0 through 80.  A balanced maximum
case `(40,40)` was checked separately.  Negative vertex coordinates,
nonuniform denominators, and both orientations occur in this seeded set.

The independent dynamic wiring harness replaces the theorem-size `build`
with a small spy, while leaving the repaired producer's import and closure
logic intact.  It proves that the wrapper patches the actual module returned
when the pinned radial source path is imported, that the function object is
exactly `polygon_monomial_batch_fixed`, and that it is not installed on the
non-radial engine module.  The fake build publishes through the real
exclusive publisher, so the wiring is exercised past the source-closure
checks without launching a target calculation.

Observed independent runs:

```
PYTHONPYCACHEPREFIX=/tmp/fixed-v8-independent-normal \
  python3 agents/exact-projection-engine/test_fixed_polygon_v8_independent.py
# PASS; 804 rows, 438 polygons, degrees 0..80; 209.376 s

PYTHONPYCACHEPREFIX=/tmp/fixed-v8-independent-opt \
  python3 -O agents/exact-projection-engine/test_fixed_polygon_v8_independent.py
# PASS; 804 rows, 438 polygons, degrees 0..80; 216.872 s
```

The producer-pinned core test passed in normal, `-O`, no-bytecode/private
cache variants.  The repaired result-checker test passed 4/4 in normal,
`-O`, and two separate private bytecode caches.  Unlike the retired checker
test `7dad9c27...`, the repaired `91e82760...` contains no bare assertions
whose checks disappear under `-O`.

## Cost probe

For `r=8`, the full translated triangular request set

```
{(r-1+i, 47-r-1+j): i,j>=0 and i+j<=35}
```

has 666 moments and reaches total degree 80.  On the five-vertex target
polygon from the low-`Stotal`, shift-3 branch, the fixed core completed this
entire batch in 59.0484 seconds.  The old Fraction batch had not completed
after 270 seconds and was interrupted, giving a measured speedup lower bound
greater than 4.57 on this hard case.  No value from the interrupted cost
probe is used mathematically.

The complete `r=8` target has 56 branch/shift rows: six are empty, 21 are
triangles, 28 are quadrilaterals, and one is a pentagon.  A deliberately
conservative bound obtained by charging every nonempty row the measured
pentagon time is about 49 minutes for polygon moments; linear-in-triangle
count extrapolation is about 27 minutes.  Kernel/family construction adds
about 1.6 minutes in the frozen runs, while radialization remains separate.
Thus v8 is a material exact speedup, but the first target run should retain a
generous checkpoint and must report the actual split timings; a sub-30-minute
completion is plausible, not certified by this probe.

## Residual scope

- No theorem-size v8 shard was launched in this audit.
- No v8 result has been compared with a same-`r` v7 result.
- This is a source/formula/wiring verdict only.  A target result must be
  immutable, canonical, pass checker `ec0162a7...` in normal and optimized
  modes, and receive a separate result-level audit before aggregation.
