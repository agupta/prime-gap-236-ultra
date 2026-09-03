# Frontier-r10 D16-inner plus outer B4 screen

Status: the scalar cost preflight was resource-aborted before its first form;
the old `83/500`-plateau target is disabled and superseded before launch.  A
later flat `3329/20000` candidate was itself superseded by an analytically
pending rising-tail schedule with the same first nine caps, active counts
`0..25`, and eventual plateau `363/2000`.  The exact finite-space formulas and
low-dimensional tests are retained for the schedule-parameterized batched
successor.
No numerical value from this package is a theorem unless its particular
quadratic forms are independently reconstructed.

## Support and analytic status

The common parameters are

```
k=48, delta=361/50000
alpha1=103/400, eta1=97/400
alpha2=3211/12000, eta2=3031/12000
B_m=min(13/125+(m-1)delta,83/500).
```

The cap reaches its plateau at `m=10`, has active outer counts `0..22`, and
count 23 is empty.  The Proposition-1 analytic verification is independently
frozen in
`../audit/results/wide_c722_start104_plateau166_analytic_audit.json`
(SHA-256
`148852f6021119015fb1dbf0ae61d842ac16371e14ee94001d80a3e832c892e7`).
It proves all required branches with `c1=c2=0`; it contains no quotient.

## Finite space

Let `F0` be the exact 307-label BV D16 polynomial from the pinned certificate.
The eleven coordinates are

```
F0 * 1_{S(alpha1)}
G_j * (1_{S(alpha2,B)} - 1_{S(alpha1,B)}),  G_j in even_basis(4).
```

The ten shell coefficients are independent.  Consequently this is a
support-adapted polynomial residual block, rather than the inherited/dilated
D16 coefficient direction rejected by the capped heuristic.

Writing `H,L` for the scheduled high/low supports, the denominator is block
diagonal:

```
A00 = I(F0,F0) on the full inner simplex,
Aij = I_H(G_i,G_j) - I_L(G_i,G_j),
A0j = 0.
```

Definition 5 attaches `eta1` to the fixed inner-inner numerator (the exact
certificate value) and `eta2` to every block involving the shell.  Thus

```
B0j = 48 * (J(F0_Hinner,G_j_H) - J(F0_Hinner,G_j_L)),
Bij = 48 * (J_HH(i,j) - J_HL(i,j) - J_HL(j,i) + J_LL(i,j)).
```

The two mixed orientations are retained separately; replacing them
entrywise by `2 J_HL(i,j)` is forbidden when `i != j`.

## Exact implementation and gates

`code/wide_frontier_r10_d16_outer_b4_v1.py` reconstructs every branch
intersection with Fraction arithmetic.  Its public CLI currently permits
only the worst-label cost preflight.  The target assembler is callable by a
future audited wrapper, but cannot be launched from this source alone.

The preflight uses `G=(0,(2,2))`, which has two distinguished marginal
components, and measures the fixed-D16/high, fixed-D16/low, high/high,
high/low, and low/low contractions.  It exact-checks same-support branch
traversals against the canonical `basis_j` recurrence.  Its conservative
target estimate is

```
2 * [10*(fixed/high + fixed/low)
     +55*(high/high + low/low) +100*(high/low)].
```

Target execution requires the estimate to be at most 7200 seconds, peak RSS
at most 524288 KiB, the frozen analytic audit above, a fresh-output gate, an
independent audit of the implementation/preflight, and separate root
authorization.

The scalar preflight session was interrupted at the predeclared 25-minute
boundary after at least 1500 seconds.  It printed no result and created no
stage or final artifact.  Its source publishes only after all five timed
contractions, so the internal substage reached at interruption is unknowable
and no partial form is claimed.  This is a concrete obstruction to that
uncheckpointed scalar cost-probe representation, not a quotient result.  A
separate face-batched helper (source SHA prefix
`c3f1559e`, tests `d10dfe81`, 4/4 normal and `-O`) exactly matches the literal
scalar cross matrix, its transpose, and the sum of individually selected
common-count rows in low dimension.  It remains a prelaunch implementation
candidate and must be repinned to the ultimately audited schedule.

A D6 outer block is predeclared only if the exact rational D4 particular
vector has quotient at least `199/200`, gains at least `1/100` over the fixed
base, and a fresh D6 resource estimate is at most 14400 seconds.  These are
continuation rules, not mathematical upper bounds.

An eventual independent checker must ignore any producer cache and rebuild
all 11-by-11 entries from the exact recurrence, then verify the matrix hash,
all exact Gram LDL pivots, the rational vector length, and the two particular
quadratic forms.  It must not infer optimality from the Decimal eigensolver.
