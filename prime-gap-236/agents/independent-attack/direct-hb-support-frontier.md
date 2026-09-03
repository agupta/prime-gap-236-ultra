# A direct-Heath--Brown support frontier

This note optimizes the one-stratum support after the specialized direct
Heath--Brown reduction in
`../../hostile-analytic-audit/direct-hb-prime-equidistribution.md`.  That
reduction removes Proposition 2 and all Type I conditions.  Only the exact
Type IIa/IIb/repaired-IIc and corrected Type III inequalities are imposed.

Throughout, use `xi_2=2/5`, direct-HB `gamma_3=2/5-h/10`, analytic
`h=10^-10`, and support enlargement `varepsilon=1/200`.  The latter can be
changed independently; it is absent from the support-classification
inequalities and cancels from the total modulus exponent.

The Polymath8a Heath--Brown classification is used with
`sigma=1/10+h/10` and `K=10`.  For every candidate the checker also verifies
exactly: the forbidden endpoint is avoided; `1/K<2sigma`; the central
aggregate lies inside the chosen Type-II interval; a Type-0 term remains
power-saving after summing all `q<=x^(2A)`; and the prime-power removal is
power-saving.  The near-square-root Type-IIc interval is empty because

```
1/2-sigma > 1/3+(7/3)delta+3h.
```

## Scalar frontier for `A`

For a one-stratum support write `omega=A-1/4`.  The three Type-II scalar
bounds, after substituting `xi_2=2/5`, are

```
19/2 - 36A - 13delta + 100h >= 0,
21/25 - (16/5)A - 2h >= delta,
63/80 - 3A - 2h >= delta.
```

On the tested interval `0.006<=delta<=0.028`, the last is the active upper
frontier, so

```
A <= (63/80-delta-2h)/3.
```

The candidates below sit at a rational interior point.  The corrected
direct-HB Type-III choice

```
gamma_3 = 2/5-h/10,
delta_3 = 1/2-(7/2)omega-(9/8)gamma_3-h
```

has both `delta_3>delta` and
`28omega+9gamma_3+8delta_3<4` at every listed point.

## Exact two-bin lemma for all Type-IIc partitions

Let the count-dependent schedule be

```
B_1=u,  B_2=v,  B_m=b for every m>=3.
```

Over the full repaired Type-IIc rectangle

```
0<=omega_0<=omega,
2/5-h <= gamma <= 1/3+8omega+(7/3)delta+3h,
```

the first two bin capacities are bounded below by

```
C = 2/5 - 2delta - 8omega - 2h,
D = 1/6 - 10omega - (7/3)delta - 4h.
```

Bins 3 and 4 are nonnegative but will be left empty.  For a tuple of total
`T`, a bin-2 subset must have sum in
`[L,D]`, where `L=max(0,T-C)`.  The following six strict inequalities are a
finite sufficient criterion:

```
b<C,              2v<C,
v+b-C<delta,      b/3<D,
2b-C<2delta,      2(2b-C)<D.                 (*)
```

Here is a complete proof, including zero counts.

* If one count is zero, `T<=b<C`; use the empty bin-2 subset.
* If both counts are at most two, `T<=2v<C`; again use the empty subset.
* If exactly one count is at most two, then `L<=v+b-C<delta`.  The other
  block has count at least three, so its least entry `a` satisfies
  `delta<=a<=b/3<D`.  Put `a` in bin 2.
* If both counts are at least three, let `a,a'` be their least entries.  If
  either is at least `L`, that entry alone works.  Otherwise
  `a+a'<2L<=2(2b-C)<D`, while
  `a+a'>=2delta>2b-C>=L`.  Put both in bin 2.

The complement has sum at most `C` by the definition of `L`.  This is a
continuum proof, not a sampled test.

For IIa, IIb, and corrected III, every listed candidate satisfies

```
2b < min(first IIa capacity, first IIb capacity,
         corrected first III capacity),
```

and every unused capacity is strictly positive.  Thus all entries go in the
first bin.  The checker separately repeats IIa, IIb and III at `omega=0`
for the near-square-root strip; this is necessary because the first IIa/IIb
capacities are smaller there.  Together with `(*)`, this proves every
required partition.

## Exact candidate list

All unlisted `B_m` equal the displayed `b`.

| ID | `delta` | `A` | `B_1` | `B_2` | `b=B_{m>=3}` | first empty count |
|---|---:|---:|---:|---:|---:|---:|
| C60 | `3/500` | `26049/100000` | `179/1250` | `179/1250` | `179/1250` | 24 |
| C65 | `13/2000` | `78097/300000` | `1447/10000` | `1447/10000` | `1447/10000` | 23 |
| C70 | `7/1000` | `78047/300000` | `731/5000` | `731/5000` | `731/5000` | 21 |
| C75 | `3/400` | `25999/100000` | `1477/10000` | `1477/10000` | `1477/10000` | 20 |
| C80 | `1/125` | `77947/300000` | `373/2500` | `373/2500` | `373/2500` | 19 |
| C85 | `17/2000` | `77897/300000` | `3/20` | `3/20` | `1507/10000` | 18 |
| C90 | `9/1000` | `25949/100000` | `3/20` | `3/20` | `761/5000` | 17 |
| C95 | `19/2000` | `77797/300000` | `3/20` | `3/20` | `1537/10000` | 17 |
| C10 | `1/100` | `77747/300000` | `3/20` | `3/20` | `97/625` | 16 |
| C12 | `3/250` | `25849/100000` | `3/20` | `3/20` | `403/2500` | 14 |
| C14 | `7/500` | `77347/300000` | `3/20` | `383/2500` | `209/1250` | 12 |
| C16 | `2/125` | `77147/300000` | `3/20` | `769/5000` | `849/5000` | 11 |
| C20 | `1/50` | `1279/5000` | `3/20` | `19/125` | `43/250` | 9 |
| C2005 | `401/20000` | `1279/5000` | `3/20` | `1521/10000` | `1721/10000` | 9 |
| C24 | `3/125` | `25449/100000` | `3/20` | `188/1250` | `109/625` | 8 |
| C28 | `7/250` | `75947/300000` | `3/20` | `3/20` | `221/1250` | 7 |

In particular, at the root calculation's exact point
`A=1279/5000`, `delta=1/50`, C20 proves that every `B_m` for `m>=3` can be
raised unconditionally from `17/100` to `43/250=0.172`.  C2005 proves a
joint increase to

```
delta=401/20000=0.02005,
B_m=1721/10000=0.1721 (m>=3),
```

at the same `A`; the active scalar margin is exactly
`249999/5000000000>0`.  Thus neither `B_3=0.17` nor `delta=0.02` is a local
classification frontier at that `A`.

## Small-delta frontier and its obstruction

Put `tau=1/100000` and stay a fixed rational distance inside the active
scalar face:

```
A = 21/80-delta/3-tau.
```

Substitution in the uniform Type-IIc capacities gives the exact identities

```
C = 3/10+(2/3)delta+8tau-2h,
D = 1/24+delta+10tau-4h.
```

Two of the six conditions in `(*)` impose

```
b < 3D = 1/8+3delta+30tau-12h,
b < C/2+D/4 = 77/480+(7/12)delta+(13/2)tau-2h.
```

Ignoring the deliberately tiny `tau,h`, these faces cross at
`delta=17/1160`.  Below the crossing the first face is active.  Candidates
C60--C95 therefore take

```
b = 1/8+3delta+1/5000,
```

which leaves the exact margin `1/10000-12h` below `3D`.  We retain
`B_1=B_2=3/20` while this is no larger than `b`; below

```
delta = 1/120-(20/3)tau
```

we instead put every `B_m=b`.  The checker verifies all remaining faces,
including the transitions at `B_1,B_2`, exactly.

This also identifies a concrete obstruction to continuing toward
`delta=0`: the continuum partition lemma forces `b` toward `1/8`.  More
geometrically, for almost every fixed point with positive coordinates, all
48 coordinates eventually exceed `delta`; hence these supports converge
pointwise almost everywhere to the simplex `sum t_i<=1/8`, despite
`A+varepsilon` tending to approximately `0.2675`.  Dominated convergence
therefore sends every fixed finite polynomial-basis matrix to the much
smaller radius-`1/8` simplex problem.  A numerical turnover is thus expected
and is observed below; merely taking `delta` smaller is not an unbounded
source of sieve gain.

## Cheap quotient proxy ranking

The following values use the support-stratum-aligned degree-2 basis in
`code/numerical_piecewise_basis.py`, Gauss order 12, `k=48`, and
`varepsilon=1/200`.  They are discovery-only, but were run identically and
are useful for ranking supports:

| rank | support | heuristic `48J/I` |
|---:|---|---:|
| 1 | C10 | `0.8529866345313049` |
| 2 | C12 | `0.8339377781203415` |
| 3 | C14 | `0.8236724085633466` |
| 4 | C16 | `0.8180756302362501` |
| 5 | C20 | `0.8114239571124800` |
| 6 | C2005 | `0.8114079884604999` |
| 7 | C24 | `0.8057862748519076` |
| 8 | C28 | `0.7995173581826416` |
| reference | `A=.253,delta=.028,B_{m>=3}=.1778` | `0.7990050910211967` |

The requested `0.016<=delta<=0.028` scan is won by C16.  Extending the same
exact lemma below that interval produces C10--C14, and the cheap proxy favors
C10.  This extrapolation has a computational cost: it has 15 nonempty large
coordinate strata instead of C16's 10, so an exact matrix calculation may be
substantially larger.  A separate degree-8 total-sum basis gives
`0.8331716395121617` for C16 at the same `varepsilon`, supporting the in-range
ranking but not certifying a quotient.  The same fixed degree-8 total-sum
basis gives `0.8388111541948651` for C10, so its advantage is not solely an
artifact of the larger number of stratum indicator functions.

## Reproduction and independent checks

```
python3 verify_direct_hb_frontier.py
python3 code/verify_direct_hb_support.py \
  --delta 2/125 --A 77147/300000 \
  --bounds 3/20,769/5000,849/5000,849/5000,849/5000,849/5000,849/5000,849/5000,849/5000,849/5000,849/5000 \
  --gamma-cells 4 --omega-cells 4
```

The first command checks the closed-form lemma and every exact margin for all
five candidates.  The second independently covers every continuous Xi tuple
by exact rational parameter/y boxes and reconstructs every bin assignment;
it prints `DIRECT-HB EXACT SUPPORT COVER PASS`.
