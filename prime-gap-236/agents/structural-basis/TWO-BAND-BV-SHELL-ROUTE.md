# Two-band support retaining the complete BV core

Status: **new analytic/computational mechanism; no equidistribution proof, matrix, or quotient yet**.

## Exact candidate support

Definition 1 permits more than the one total-sum band used in the published
proof.  With the published enlargement and endpoint data, take

```text
k       = 48
epsilon = 3/400
delta   = 7/250
A_0     = -3/400
A_1     = 1/4
A_2     = 253/1000
```

and use the cap schedules

```text
B_{1,m} = 103/400                         (m >= 1),
B_{2,1} = B_{2,2} = 3/20,
B_{2,m} = 17/100                          (m >= 3).
```

The first cap is redundant on its band.  Thus the support is exactly

```text
{sum(t) < 103/400}
union
{103/400 <= sum(t) < 521/2000 and
 sum_{i:t_i>7/250} t_i <= B_{2,R(t)}}.                 (1)
```

It strictly contains the complete epsilon-enlarged classical BV support,
rather than deleting its large-coordinate corners as the published one-band
support does.  The two common-coordinate cutoffs in Definition 5 are

```text
eta_1 = A_1-epsilon = 97/400,
eta_2 = A_2-epsilon = 491/2000.
```

All endpoints above are rational.  The total-sum bands are half open, the
test `t_i>delta` is strict, and the cap inequalities are weak, exactly as in
Definition 1.  Boundary choices do not alter the integrals but must remain
literal in a checker.

## Why this is not the completed C10 route

The one-band C10 calculation imposes its large-coordinate cap even below the
BV total-sum threshold.  Consequently, transferring a full-simplex D12
polynomial loses substantial mass and gives only `0.9709698476...`.  Support
(1) keeps every BV-core point and adds a disjoint capped shell.  The resulting
finite-dimensional problem contains the rigorously checked BV functions as
the subspace obtained by setting every shell coefficient to zero.  In
particular its supremum is at least the achieved exact BV value
`0.9812858896095555...`; no monotonicity of a particular global polynomial is
being assumed.

The natural basis is piecewise.  Write `F=F_1 1_{band 1}+F_2 1_{band 2}`.
Then `I` is block diagonal by band, while `J` has a genuine cross block.  This
is incompatible with simply evaluating one inherited polynomial on the
one-band cap and is therefore a new mechanism rather than another degree
increase in that implementation.

## Exact distribution split that must be proved

For the relevant-modulus class, split the band pair `(j,j')` before using any
factorization theorem.

* For `(1,1)`, Definition 2 gives

  ```text
  log_x q <= (1-epsilon_0)
             ((A_1-epsilon)+(A_1+epsilon))
          = (1-epsilon_0)/2.
  ```

  This pair must be handled directly by the same sharp-interval bilinear
  Bombieri--Vinogradov argument as the audited classical-BV route; the
  redundant `B_1` values are not fed to a smooth-factor lemma.

* For `(2,2)`, the current published/specialized large-factor analysis sees
  exactly the old outer cap pair and can reuse it only after all endpoint and
  source-small-parameter reserves are rechecked with band indices retained.

* The new work is `(1,2)` and `(2,1)`.  Their crude total exponent is
  `(1-epsilon_0)(A_1+A_2)`, only `0.503(1-epsilon_0)`, but one side may have
  large-coordinate load as high as `103/400`.  It is invalid to replace that
  load silently by `17/100`.  Every Type-IIa/IIb/IIc/III partition must be
  proved on the complete continuous polytopes
  `Xi(B_{1,m},B_{2,m'},m,m',delta)` and its transpose, including zero counts.

This route is analytically open until that mixed-band universal check and the
underlying predecessor hypotheses pass.  A sampled tuple check is not enough.
If the mixed pair fails, record the smallest exact counterexample and test a
rationally smaller redundant first-band cap only if it still remains at least
`103/400`; otherwise the full BV containment has been lost and the mechanism
must be renamed.

### First exact obstruction to a black-box Proposition-3 reuse

The repaired C10 capacity formulas were recomputed at the mixed-pair modulus
parameter

```text
omega_cross = (A_1+A_2-1/2)/2 = 3/2000.
```

IIa and Type III pass the existing exact prefix-subset criterion for all ten
feasible inner counts and seven feasible outer counts.  IIb has five failures,
and IIc has a smallest explicit obstruction already at `(m,m')=(1,1)`.  The
inward-shrunk IIc capacities are

```text
C1 = 1659999995521/5000000000000       = .3319999991042,
C2 = 1294999995341/15000000000000      = .0863333330227...,
C3 = delta+4*10^-10                    = .0280000004,
C4 = 2*10^-11.
```

The allowed point

```text
(y_1,y_2)=(103/400,3/20)
```

cannot be placed in these four bins: both entries cannot share bin 1 because
their sum is `163/400=.4075>C1`, while each individual entry is larger than
each of `C2,C3,C4`.  Thus the existing universal factorization lemma does
**not** prove the mixed-band case.  Merely adding a band index to the C10
checker would be false.

The support mechanism can now be reopened only by a materially stronger
cross-modulus argument.  The most relevant unused invariant is that an actual
outer-shell point has total at least `103/400`, hence when its large load is
`3/20` it carries at least `43/400` of small/smooth mass.  Definition 2's
present `Q*` overapproximation discards that lower bound.  A valid repair would
need to redo the Proposition-1 modulus reduction for the band pair while
retaining this smooth-factor lower bound, or prove another distribution
theorem covering the explicit obstruction.  Until then, (1) has no analytic
authorization regardless of any favorable numerical quotient.

## Matrix construction

For basis polynomials `P_i` in band 1 and `Q_a` in band 2, reconstruct

```text
I = [[ integral_band1 P_i P_j,                  0 ],
     [                 0, integral_band2 Q_a Q_b ]].
```

For common coordinates `u=(t_1,...,t_47)`, define the band marginals

```text
p_i(u) = integral_{u+t in band1} P_i(u,t) dt,
q_a(u) = integral_{u+t in band2} Q_a(u,t) dt.
```

Definition 5 gives the exact blocks

```text
J_11 = integral_{sum(u)<=97/400}       p_i p_j,
J_12 = integral_{sum(u)<=491/2000}     p_i q_a,
J_22 = integral_{sum(u)<=491/2000}     q_a q_b.              (2)
```

Equation (2), not a square of an unstratified marginal with one common
cutoff, is the required recurrence oracle.  A first implementation should
reproduce the existing BV matrix exactly when the shell block is removed and
the one-band capped matrix exactly when the BV block is removed.  Signed
`k=1,2,3` direct integrations must test the cross block and both unequal
cutoffs.

Begin with the already certified BV D16 vector as one retained coordinate and
a small exact shell basis aligned with `(R,L,Z)`; then add global shell orbit
coordinates or a separately optimized BV core only if the cross residual is
large.  Any numerical candidate must be replayed by a fresh exact or
outward-rounded scalar recurrence.  The full analytic proof above is required
even if the quotient crosses one.

## Falsification and continuation gates

1. Retire the stated parameter point if an exact mixed-band modulus or
   partition counterexample survives all allowed Type-0/BV/II/III cases.
2. Reject an integrator that treats both `J` cutoffs as `491/2000`, omits the
   cross block, or represents the shell as a difference without checking the
   overlap and endpoint conventions.
3. A low-degree shell screen is discovery only.  Continue to a high-degree
   scalar reconstruction only if an independently validated candidate gains
   at least `0.005` over the pinned BV coordinate; the final target still
   requires an exact quotient above one.
4. No result on (1) may be cited for the one-band C10 or C722 supports, and no
   one-band negative transfer is an upper bound for this piecewise space.
