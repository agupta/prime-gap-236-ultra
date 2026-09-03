# Independent audit of the grouped fixed-vector evaluator

Date: 2026-09-01

Audited implementation:

- `../exact-integrator/grouped_fixed_vector.py`
- SHA-256 at the end of this audit: `47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a`
- imported `src/exact_integrator.py` SHA-256:
  `941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52`

The audit is deliberately limited to the finite-dimensional integration
implementation.  It does not establish the analytic admissibility of the C10
support and it is not a capped-D12 certificate.

## Symmetry-factor check

On a fixed face and branch `b`, write the marginal as

\[
M_b=\sum_\lambda p_{b,\lambda}(z,w)P_\lambda(u).
\]

The diagonal branch contribution `M_b^2` contains each equal orbit-label pair
once and each unequal pair twice.  For two different branches `b != c`, the
unordered branch pair in `(sum_b M_b)^2` represents both `M_b M_c` and
`M_c M_b`, hence every orbit-label pair receives a factor two.  The routine
`branch_orbit_product` has exactly these two, distinct factor-two rules.

The test `test_unordered_branch_and_orbit_factors` compares its output as a
complete dictionary of bivariate orbit polynomials against literal ordered
double sums.  It uses three left orbit labels, two right orbit labels, repeated
and unequal products, and nontrivial bivariate coefficients.  Equality is exact
over `Fraction`.

## Branch intersections

For the two small-coordinate branches, their common constraints imply

\[
z+w=\alpha-(r+h)\delta-\delta.
\]

For the two large-coordinate branches they imply

\[
w=\alpha-B_{r+1}-h\delta.
\]

Thus each complementary pair has zero two-dimensional measure.  When only one
aggregate variable exists it is a point and still has zero one-dimensional
measure.  The only exceptional degeneration is `s=0`, `h=0`, and
`B_{r+1}=alpha`: then `w=0` identically and the large-branch tie would occupy an
interval.  `_branch_constraints` explicitly returns `None` for `Lbig` in this
case, assigning the interval to `Ltotal` exactly once.

The C10 test enumerates every feasible `(r,h)` face and integrates the constant
polynomial over `Sdelta intersect Stotal` and `Ltotal intersect Lbig`.  Every
answer is the exact rational zero.  A separate `k=2` test constructs the
zero-dimensional-small-group tie and verifies both the one-branch convention
and the complete grouped/pairwise quadratic equality.

The same exact constant-polynomial test gives a useful pre-contraction filter.
C10 has 296 faces and 2960 raw unordered branch pairs, but only 1200 pair
intersections have positive aggregate measure.  Of 1184 branch-face domains,
only 748 are active: `Sdelta` on 296 faces, `Ltotal` on 285, `Lbig` on 167, and
`Stotal` on none.  The last fact is also immediate from
`alpha - eta = delta`.  Testing exact area/length before building marginal and
orbit-product polynomials can therefore remove about 59.5% of the raw pair
contractions without changing a summand.

## End-to-end small exact comparisons

Two additional tests reconstruct `I` and `kJ` by both routes:

1. a mixed odd-orbit `k=3` basis and signed integer vector;
2. a repeated-part `k=4` basis and rational signed vector.

The grouped results equal `exact_quadratic(support.matrices(...), vector)` as
exact fractions.  These cases exercise the one-dimensional `r=0` and `s=0`
faces as well as genuine two-dimensional faces.  The matrix path reconstructs
moments from basis pairs; no serialized matrix is read.

Hostile testing exposed two generic `k=1` bugs during the audit.  First, a
zero-dimensional `J` face was initially integrated over a fictitious `w`
interval.  The minimal constant-basis counterexample gave grouped
`J=2531/750000` instead of `9/400`.  After replacing this by evaluation at the
sole feasible 0-dimensional point, the boundary case
`alpha=delta=eta=1/10` still activated both `Sdelta` and `Stotal`, giving
`J=1/50` instead of `1/100`.  The repaired code uses the source integrator's
half-open interval convention to select active branches when the shared
dimension is zero.  Both counterexamples now agree exactly with the pairwise
reference.  They do not occur for C10 (`k=48`), but catching and repairing them
strengthens the independent checker.

## Cache and fork audit

The current implementation clears face-dependent orbit, marginal, linear-power,
polygon, and polygon-moment caches after each `(r,h)`.  It clears
`_large_shift_dp`, `_small_box_dp`, and `_selected_exponent_splits` after each
completed `r`, retaining their useful reuse across `h` without accumulating all
radial strata.  This resolves the earlier unbounded-cache hazard.  A dedicated
test runs complete grouped `I` and `J` passes and checks that all four density/DP
caches and the marginal cache have size zero afterward.

If parallelized, the safe representation is an explicit POSIX fork context
created only after the orbit table and fixed polynomial contraction have been
built.  Workers should inherit this state read-only and return one exact scalar
per work unit.  A spawn context is unsafe in Decimal mode because the installed
scalar and orbit lookup are local monkeypatched closures.  Grouping all `h`
faces of one `r` in a work unit preserves the radial-cache reuse.  Because the
complete face polynomial and worker caches become private copy-on-write pages,
two workers is the recommended initial cap under the observed 8 GiB machine.
The implemented fork-by-`r` path was compared directly with the serial path on
the signed repeated-part exact test: the complete `(I, group-count, face-count)`
and `(J, component-count, branch-count)` tuples are identical.

The stage and result artifacts now contain hashes of both the grouped script
and imported integrator source.  Resume validates both.  Adversarial CLI tests
show that a rigorous run rejects a false integrator hash and also rejects a
stale grouped-script hash even when the non-rigorous override flag explicitly
names that hash.  The legacy missing-dependency-hash escape hatch is restricted
to non-rigorous discovery runs.  Parent and maximum-child RSS are reported
separately, with an explicit note that neither is simultaneous aggregate RSS.

## Reproduction

```sh
python3 -m unittest \
  prime-gap-236/agents/structural-basis/tests/test_grouped_evaluator_audit.py -v
```

Result: `Ran 12 tests in 4.842s -- OK`, maximum RSS 25,464 KiB in the preceding
timed run.  Test SHA-256:
`8cb9de64b0059bad37eecb88569ad2c11343a5a92d891b620fdceab884b68e3c`.

## Verdict

`AUDIT PASS` for the tested grouped-contraction symmetry factors, complementary
branch intersections (including the exceptional zero-dimensional tie), cache
lifetime, fork/serial equality, dependency-hash fail-closed behavior, and small
exact end-to-end instances after the repairs above.  This pass does not cover a
completed C10 D12 evaluation; that large exact output must be checked again
against its recorded input, script, and integrator hashes.
