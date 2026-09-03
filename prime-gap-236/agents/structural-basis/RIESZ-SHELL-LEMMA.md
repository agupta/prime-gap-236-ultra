# Riesz shell lemma for a disjoint support enlargement

## Status

This is an exact structural reduction, not a positive capped certificate and
not a bounded-gap theorem.  It identifies a smaller exact computation that
would suffice to close the `k=48` quotient.

The lemma is deliberately a **single-outer-band** statement.  It must not be
applied by splitting a multiband outer support into `V_1,V_2,...`, computing a
separate Riesz energy on each band, and summing those energies.  Disjointness
of the bands makes the I Gram block diagonal, but Definition 5 uses pairwise
maximum common-coordinate cutoffs and its cross-band J kernel need not be
positive semidefinite.  For two cutoffs, at a rest sum between them the kernel
is `[[0,1],[1,1]]`, with eigenvalue `(1-sqrt(5))/2<0`.  A multiband
combination therefore needs its exact outer J block or an independent special
sign argument.  Testing any one band by itself remains within this lemma.

Let `U,V` be two distinct bands of a Stadlmann support, disjoint up to null
boundaries, and let `F` be a symmetric square-integrable function supported
on `U`.  Write `eta_UV` for the common-coordinate cutoff in the `U,V` term
of Definition 5.  (For the inner/outer active-25 pair this is
`eta_UV=A_2-epsilon=3031/12000`.)  For each coordinate put

```text
m_i^F(t without i) = integral_{t_i:(t without i,t_i) in U} F(t) dt_i,
G_F(t) = 1_V(t) sum_{i=1}^k
         1_{sum_{j != i} t_j <= eta_UV} m_i^F(t without i).
```

The compact rational-polytope supports used here make `G_F` square
integrable.  It is symmetric and supported on `V`.

## Exact identity

For every symmetric square-integrable `H` supported on `V`, Fubini,
symmetry, and the literal common-coordinate truncation in Definition 5 give

```text
k J(F,H)
 = sum_i integral_{sum x <= eta_UV} m_i^F(x) m_i^H(x) dx
 = sum_i integral_V H(t)
       1_{sum_{j != i}t_j <= eta_UV} m_i^F(t without i) dt
 = integral_V G_F(t) H(t) dt
 = <G_F,H>_I.
```

The cutoff is essential: omitting it would compute the ordinary untruncated
marginal form, not Stadlmann's Definition-5 cross term.  No positivity,
invertibility, or eigenvalue-optimality assertion is used.
In particular, with `H=G_F`,

```text
k J(F,G_F) = I(G_F).
```

Since the supports are disjoint,

```text
I(F+G_F) = I(F)+I(G_F),
kJ(F+G_F) = kJ(F)+2I(G_F)+kJ(G_F).
```

The final term is nonnegative by the definition of `J`.  Consequently the
single exact inequality

```text
I(G_F) > I(F)-kJ(F)                                      (R)
```

implies `kJ(F+G_F)>I(F+G_F)`.

## Finite projection version

Let `H_1,...,H_d` be explicit symmetric functions supported on `V`, let

```text
A_ij = I(H_i,H_j),
b_i  = kJ(F,H_i) = <G_F,H_i>_I.
```

If an exact rational vector `c` satisfies `A c=b`, then for
`H=sum_i c_i H_i`,

```text
I(H)=c^T A c=c^T b=kJ(F,H).
```

Thus `c^T b>I(F)-kJ(F)` is another sufficient exact certificate; the
outer-shell `kJ(H)` matrix is unnecessary.  More generally, any explicit
`c` satisfying the exact inequality

```text
2 c^T b-c^T A c > I(F)-kJ(F)
```

closes after discarding the nonnegative `kJ(H)` term.  This form does not
assume that `A` is invertible.

## Exact uncapped D18 calibration

For the independently audited refined-D18 Definition-5 two-band matrices in

```text
results/wide_c722_B18_piecewise_cinner1_couter_natural_exact.json
```

the projection of `G_F` onto the single natural-dilation outer coordinate has
exact squared norm `B01^2/A11`.  Direct contraction of the serialized exact
fractions gives

```text
(B01^2/A11)/A00
  = 0.0228600229981829438307095359602785956934618818274723904123492...

(A00-B00)/A00
  = 0.0146491591498227584440665051991207178494918368587055358095411...

(B01^2/A11)/(A00-B00)
  = 1.56050069252333362775212035084513529119218790509479918200483...
```

These decimals are discovery displays of exact rational quantities.  They
show that criterion (R), and even its one-dimensional projection version,
closes comfortably on the analytically unapproved uncapped outer simplex.
They make the retained capped Riesz energy the decisive quantity.  They say
nothing by themselves about the analytically approved scheduled cap.

## Concrete next computation

Use the audited active-25 or gamma-correlated lifted shell as `V`, the exact
refined-D18 radial inner coordinate as `F`, and the explicit cross cutoff
`eta_UV=3031/12000`.  Either:

1. reconstruct `I(G_F)` count-by-count and compare it exactly with
   `I(F)-48J(F)`; or
2. choose a finite cap-adapted shell basis, reconstruct only its exact Gram
   matrix `A` and inner-cross vector `b`, and test
   `2c^Tb-c^TAc>I(F)-48J(F)` for a rational `c`.

Both routes avoid every outer-shell `J` entry.  Any numerical screen must be
calibrated against exact low-dimensional identities and exact shell masses
before it can authorize the expensive rational reconstruction.
