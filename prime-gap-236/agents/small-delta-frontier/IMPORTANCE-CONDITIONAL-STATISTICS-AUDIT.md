# Hostile audit: conditional importance statistics (superseded snapshot)

> **Superseded.** This file records counterexamples against old statistics
> SHA `79d670...` and conditional SHA `9862307...`.  Repairs and the current
> scoped PASS are in `IMPORTANCE-CONDITIONAL-STATISTICS-REAUDIT.md`.

Verdict for the pinned snapshot: **COUNTEREXAMPLES; NO AUDIT PASS.**  The
fixed-stratum proposal/initializer and the core statistical formulas pass in
their intended domain, but three fail-closed gates are missing from
`importance_statistics.py`.

Audited bytes:

- `importance_statistics.py` SHA
  `79d670882bc67f8973f79c062c733098a1c3e95642d743fca254d23ae7f9db00`;
- `importance_conditional.py` SHA
  `9862307efaba2142ca93f27161a28f78b2aad5243d98f4ec47c9be44b8687385`;
- producer tests SHAs `fcae2e9c...` and `c1cbe0da...`.

The producer's 5 statistics and 3 conditional tests pass in normal and
optimized modes.  The independent executable snapshot counterexamples are in
`audit_importance_statistics_snapshot.py`.

## Correct scoped identities

1. `split_rhat` treats axis 0 as chain and axis 1 as batches.  Concatenating
   the first/second halves along the chain axis gives `2m` chains of length
   `n/2`; its within/between formulas are the ordinary split-R-hat formulas.
2. Given at least two equal-size nonoverlapping batch means and consistent raw
   first/second moments, batch ESS is
   `N Var(X)/(batch_size Var(batch_mean))`, capped at `N`.  No extra division
   by batch size is missing.
3. The joint ratio residual
   `Y_b - ratio Z_b` and its sample deviation divided by
   `mean(Z)*sqrt(number_of_batches)` is the standard batch delta-method SE;
   numerator/denominator covariance is not dropped.
4. Diagonal equilibration in `largest_generalized_root` is algebraically
   correct.  If `D=diag(A_ii^-1/2)`, it solves the pencil in `DAD,DBD` and maps
   back by `x=Dy`.  A positive `1e-30` rare-stratum diagonal therefore survives
   a global scale disparity.
5. `randomized_interior_start` puts every designated large coordinate
   strictly above `delta`, every small coordinate strictly below it, keeps
   both total and large cap strict, then requires finite target log density.
   The actual C10 D4 test finds finite I and J starts in all 16 strata.
6. The conditional pair kernel rechecks the exact stratum before and after
   each move.  At density power zero, finite-to-finite moves have log ratio
   zero; the underlying sampler separately accepts transitions involving a
   `-inf` density at power zero.  No power-zero sign error was found.

## Counterexample 1: active-index omission and false exact null

```
A = diag(1,1), B = diag(1,100), active_indices=[0]
```

returns root `1` and vector `(1,0)`, silently discarding the true root `100`.
The function validates only that the supplied indices are distinct and in
range; it does not bind them to an exact basis/null manifest.

More sharply, the producer's own test supplies `A_22=0,B_22=100` and accepts
after omitting coordinate 2.  For an exact null sieve function, every A and B
row/column must be null; nonzero `B_22` is an inconsistency, not harmless data.

Required repair: the caller must byte-bind an exact active-index manifest and
the solver must either require every inactive realized A/B row and column to
be the declared structural zero, or receive and validate an exact null-space
transformation.  A bare index list is not fail-closed provenance.

## Counterexample 2: ESS can return NaN or false full sample size

With one chain, one batch, mean `0`, second moment `1`, and batch size 10,
`batch_means_ess` computes a `ddof=1` variance from one value and returns
`[nan]`.  It never checks the flattened batch count or output finiteness.

With mean `10`, second moment `0`, four visibly nonconstant batch means, it
clips the materially negative raw variance to zero and reports full ESS 40.
The zero-variance branch is valid only for a proved exact constant; it cannot
repair inconsistent moments.

Required repair: require at least two (operationally, the predeclared larger
minimum) flattened batches, finite outputs, and
`second-mean^2 >= -tolerance`.  Only an exact-null/constant manifest may turn
a negative roundoff-sized variance into the full sample count; a material
negative value must reject.

## Counterexample 3: ratio diagnostics accept impossible/nonfinite data

For one chain with two denominator batches `(-1,3)`, the mean is positive and
the function returns a ratio and SE.  Envelope `z=m_*^2/g` is pointwise in
`[0,2]`, so a negative batch is malformed and should reject.

With finite denominator batches both equal to `1e-320` and unit numerator
batches, division overflows; the function returns ratio `inf` and SE `nan`
instead of failing.  This defeats the intended small-ratio-denominator
conditioning gate.

Required repair: require every denominator batch finite and nonnegative (and,
for this envelope consumer, at most `2` up to a stated rounding reserve), a
strictly positive mean above the predeclared conditioning floor, and finite
ratio/residual/SE outputs.  Diagonal `y_ii>=0` and the known `|y_ij|` bounds
should be validated before batching or in the envelope accumulator.

## Other scoped cautions

- `split_rhat` and the other routines accept finite inputs whose intermediate
  squares overflow.  Bounded envelope features avoid this normally, but every
  returned diagnostic still needs an explicit finiteness check.
- `simultaneous_coverage` coerces arbitrary masks to Boolean and permits an
  empty mask.  The calibration consumer must bind the exact structural mask
  and checked-entry count; otherwise all entries can be hidden.
- The C10 initializer proof uses the audited C10 cap schedule.  A generic
  support in which a large distinguished branch extends beyond the common
  small-branch cap may need a separate initializer family, although the
  current chain can in principle move there after initialization.

No stochastic quotient, confidence statement, or theorem follows from this
audit.
