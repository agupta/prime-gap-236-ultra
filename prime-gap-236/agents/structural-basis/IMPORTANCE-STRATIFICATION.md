# Stratified repair of importance-Ritz discovery

## Why the original global-chain design fails

For the exact C10 D4 base polynomial, the `mu_I` probabilities of strata
`R=13,14,15` are approximately

```text
1.0250e-7, 7.3492e-11, 8.1604e-18.
```

Consequently, no feasible ordinary target chain can both use a realistic
sample count and validate every retained matrix entry.  Treating an unvisited
stratum as zero would silently change the finite-dimensional space.  The
global-chain version of `IMPORTANCE-RITZ-DESIGN.md` is therefore blocked for
full-matrix calibration.

This is a literal block, not merely an efficiency warning.  The pinned D12
Decimal100 traversal is at least as hostile in its tail: its I weights for
strata 13--15 are approximately `1.0650e-9`, `2.8220e-13`, and
`4.6325e-20`.  An ordinary eight-chain run cannot satisfy the frozen
missing-stratum rule at either base.

## Exact stratification identities

Write `D_r` for the subset of the I support with exactly `r` coordinates
strictly greater than `delta`, and put

```text
I_r = integral_{D_r} F_*(t)^2 dt,     w^I_r = I_r / I_*.
```

For the common 47-dimensional J variables, write `C_r` for the subset with
exactly `r` large common coordinates.  If

```text
m_*(u) = integral F_*(u,x) 1_D(u,x) dx,
J_r = integral_{C_r} m_*(u)^2 du,     w^J_r = J_r / J_*,
```

then the two matrix identities refine without approximation to

```text
E_muI[H H^T] = sum_r w^I_r E_muI,r[H H^T],
E_muJ[R R^T] = sum_r w^J_r E_muJ,r[R R^T].
```

Here `muI,r` and `muJ,r` are the corresponding conditional target laws.  This
is useful because each stratum can be sampled deliberately, regardless of its
global mass.  The weights are not estimated from visit counts.

There is a further necessary repair on the J side.  Directly estimating
`(m_i/m_*)(m_j/m_*)` under density `m_*^2` can have infinite variance at an
interior cancellation zero of `m_*`, even though the desired matrix entry is
finite.  For the finite retained marginal vector `m=(m_i)`, instead define on
each common stratum

```text
g(u) = sum_i m_i(u)^2,
y_ij(u) = m_i(u)m_j(u)/g(u),
z(u) = m_*(u)^2/g(u).
```

Sample the conditional envelope law `nu_r` with density proportional to `g`.
If `Z_r=integral_{C_r} g`, then

```text
E_nu,r[y_ij] = J_ij,r/Z_r,
E_nu,r[z]    = J_r/Z_r,
```

and therefore the exact normalized-matrix identity is

```text
J_ij/J_* = sum_r w^J_r E_nu,r[y_ij] / E_nu,r[z].
```

This does not require `Z_r`.  It also removes the cancellation singularity:
diagonal `y_ii` lies in `[0,1]`, off-diagonal `|y_ij|<=1/2`, and `z` is bounded
by Cauchy--Schwarz (in the tagged basis only the small and large constant
marginals can be nonzero at a fixed common point, giving `z<=2`).  A zero of
all retained marginals has zero envelope measure.  The chain target and the
batch diagnostics must use this envelope form; the earlier direct-ratio
`mu_J` implementation is retained only as an algebraic comparator and is not
authorized for confidence bands.

For D4 calibration, `I_r` is available exactly from the audited I blocks.
The independently completed Decimal160 affine traversal also records
`baseline_i_by_r` and `baseline_j_by_common_r`; their sums reproduce its base
denominator and numerator to the advertised precision.  The final exact D4
matrix oracle remains the acceptance standard, so a normalizer transcription
or factor-of-48 error is still exposed entry by entry.  Before a D12 screen,
the selected base traversal must serialize both `i_by_r` and
`j_by_common_r`, their totals, vector/multiplier hashes, and at least 80 stable
decimal digits.  These are discovery normalizers only; a winning vector still
goes through fresh exact reconstruction.

The producer convention is not uniform and must be bound explicitly.  The D4
Decimal160 baseline list stores `48 J_r` and therefore sums directly to its
numerator; the completed D12 transfer format stores unscaled `J_r` and its list
sums to `numerator/48`.  The pinned loader requires an explicit scale equal to
`1` or `48` and verifies the corresponding sum before normalizing.  Because
the common scale cancels from the weights, omitting this check could otherwise
hide exactly the factor error the calibration is meant to detect.

## Statistical status of the repair

The decompositions and envelope identities above are exact.  A finite
ordinary Metropolis run, however, is not a literally unbiased estimator:
burn-in leaves initialization bias, and the J reconstruction is a ratio of
two sample means.  Conditional chains are asymptotically consistent under
the usual ergodicity hypotheses, and the envelope makes every sampled
numerator and denominator observable bounded, but batch-CLT bands remain a
discovery heuristic rather than a mathematical confidence guarantee.  No
implemented finite-sample unbiased MCMC estimator is claimed.

Likewise, Decimal stratum weights are discovery normalizers, not exact
identities.  D4 I weights can be cross-checked against exact rational blocks;
the J weights and all D12 weights retain their pinned Decimal error.  Any
statistical interval must propagate that deterministic error.  Exact theorem
certification never consumes these matrices.

The cancellation repair is necessary for both pinned bases.  Direct
evaluation gives opposite signs of `m_*` along a segment inside one fixed
common stratum: for D4 take all 47 common coordinates from `0` to `1/200`
(stratum 0), and for D12 take one coordinate `101/10000` and the other 46
from `0` to `1/250` (stratum 1).  Thus neither base has a positivity invariant
that could justify the original `m_i/m_*` normal-band argument.

## Conditional reversible kernels

For stratum `r`, the existing pair-redistribution proposal is used with the
additional fail-closed support predicate `R(candidate)==r`.  The proposal is
still symmetric: the chosen pair total is unchanged, the redistribution
density is the same in both directions, and the stratum rejection is a
restriction of state space rather than a Hastings correction.  Physical--
physical and physical--slack moves both remain in the mixture.  Coordinate
identities can exchange their large/small roles when one member of a selected
pair crosses downward and the other crosses upward in the same proposal.
The I chain targets `F_*^2`; the J chain targets the finite envelope `g`, not
the potentially singular direct-ratio law.

Every active I and common-J stratum receives at least four independently
seeded chains.  Each chain starts from a separately randomized interior point
of that same stratum, passes through the frozen tempering ladder, and records
proposal-type acceptance separately.  No unvisited stratum can be hidden:
failure to initialize or retain finite density in any positive-weight stratum
is a hard failure.

## D4 calibration gate

The first calibration run uses the 16 exact C10 strata, all six normalized
channels `1,L/alpha,Z/alpha,(L/alpha)^2,LZ/alpha^2,(Z/alpha)^2`, and the exact
96-dimensional oracle.  It must satisfy all of the following before any D12
screen:

1. The conditional weighted reconstruction covers all 336 structural upper-
   triangle I entries and all 876 structural upper-triangle J entries.
2. Every exact entry lies in the predeclared simultaneous band built from
   within-stratum batch means, propagating the joint numerator/`z` ratio on
   the J side; no exact nonzero entry may be replaced by a structural zero or
   an empirical zero-width interval.
3. Split R-hat and batch-means ESS are reported within each stratum for every
   nonconstant retained conditional moment.  At least four chains per stratum
   remain after burn-in.
4. The degree-zero, affine, and quadratic generalized roots agree with the
   exact-oracle roots within their propagated bands.  All rationally null
   coordinates are removed from the exact I diagonal, not inferred from a
   noisy eigensolve.
5. Leave-one-chain-out reconstructions delete one chain only within its own
   stratum and then restore the fixed stratum weight.  A deletion shift above
   one quarter of the apparent D12 gain would reject a later candidate.
6. The constant-channel sums reconstruct exactly one for both normalized
   expectation matrices; raw antisymmetry and every nonfinite ratio are
   recorded before any symmetrization.

The simultaneous-band multiplier, batch size, chain count, tempering schedule,
and sample count must be serialized before observing calibration output.

## D12 use and theorem boundary

Once D4 passes, the same conditional construction may rank a finite rational
degree-three or piecewise multiplier list around a D12 base whose stratum
normalizers were serialized by the grouped recurrence.  It authorizes a fresh
scalar recurrence only if every leave-one-chain-out quotient exceeds `1.005`
and the conservative propagated lower endpoint exceeds `1.002`, as already
specified in `IMPORTANCE-RITZ-DESIGN.md`.

Neither target sampling, Decimal normalizers, statistical bands, nor a sampled
generalized eigenvalue is a proof.  The only theorem path remains: serialize a
finite rational multiplier, reconstruct its complete capped I and J forms,
prove `I>0` and `48J-I>0` exactly (or by audited outward intervals), and run an
independent certificate checker.
