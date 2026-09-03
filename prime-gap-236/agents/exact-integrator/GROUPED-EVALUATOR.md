# Independent grouped fixed-vector evaluator

`grouped_fixed_vector.py` reconstructs the two quadratic forms for one explicit
rational polynomial without reading any matrix entries.  It is algebraically
independent of both the pairwise matrix builder and the structural-basis fixed
vector program.

## Polynomial contraction

Write

\[
 F(t)=\sum_{a,\lambda}c_{a,\lambda}(1-S)^aP_\lambda(t),
 \qquad S=\sum_i t_i,
\]

where `P_lambda` is the monomial-orbit sum.  The integer structure constants

\[
P_\lambda P_\mu=\sum_\nu m(\lambda,\mu;\nu)P_\nu
\]

are reconstructed by `multiply_monomial_orbits`; they are not loaded from a
matrix.  The program first forms the exact coefficients `q_(nu,c)` in

\[
 F^2=\sum_{\nu,c}q_{\nu,c}P_\nu(\alpha-S)^c,
\]

using

\[
(1-S)^b=\sum_{c=0}^b {b\choose c}
 (1-\alpha)^{b-c}(\alpha-S)^c.
\]

Diagonal basis pairs occur once and unequal pairs occur twice.  Thus the
contraction is exactly the rational-vector quadratic form, with no assumption
that the Gram matrix is nonsingular or positive definite.

## The `I` integral

On a support face, let `r` coordinates exceed `delta`, translate those
coordinates by `delta`, and let `z` be their translated sum.  Inclusion-
exclusion for the remaining box-constrained coordinates translates `h` of them;
let `w` be their residual sum.  For every orbit `P_nu`, finite binomial
expansion followed by the Dirichlet simplex identity gives an exact bivariate
polynomial density in `(z,w)`.  Multiplication by

\[
(\alpha-(r+h)\delta-z-w)^c
\]

and summation over all `(nu,c)` produces one polynomial for the entire `F^2` on
that face.  This polynomial is integrated over the rational polygon

\[
z,w\ge0,\quad z+w\le\alpha-(r+h)\delta,
\quad z\le B_r-r\delta
\]

(with the evident one-dimensional degeneracies).  All feasible `r,h` are
enumerated, including a later feasible stratum after a nonmonotone `B_r` jump.

## The `J` integral

Fix the distinguished coordinate `t` and call the other `k-1` variables `u`.
The exact orbit identity is

\[
 P_\lambda(u,t)=\sum_{e\in\{0\}\cup\operatorname{parts}(\lambda)}
 t^eP_{\lambda\setminus e}(u),
\]

with one term for each distinct exponent `e`.  On each of the four affine
upper-limit branches `Sdelta`, `Stotal`, `Ltotal`, and `Lbig`, the elementary
antiderivative in `t` is a bivariate polynomial in `(z,w)`.  Terms with the same
remaining orbit label are combined before multiplication.  The square of the
marginal is then contracted over unordered branch pairs: an unequal branch pair
has factor two, and within one branch unequal orbit labels have factor two.
Orbit structure constants are reconstructed again, and the resulting complete
polynomial is integrated over the intersection of the two exact branch domains.
Summing all faces gives `J`; the reported numerator is `k*J`.

The `Sdelta`/`Stotal` and `Ltotal`/`Lbig` boundaries are harmless: their overlap
has measure zero, and the source integrator assigns the one zero-dimensional tie
to a single branch.  Open versus closed choices therefore cannot alter these
polynomial integrals.

## Arithmetic and memory discipline

With no arithmetic flag, every scalar is `fractions.Fraction`, so positivity of
the denominator and of `k*J-I` is decided exactly.  `--decimal-dps N` executes
the same finite expansions in `Decimal` and is explicitly marked non-rigorous.
Orbit densities, marginal polynomials, and polygon moments are reused throughout
one `(r,h)` face and then cleared.  Values from an old face are never reused, so
this changes memory consumption but not the calculation.

The 60-digit regression

```sh
python3 grouped_fixed_vector.py results/hb_a2558_eps005_cut_noones_D4.json \
  --alpha 163/625 --delta 1/50 --eta 627/2500 \
  --beta1 3/20 --beta2 3/20 --beta3plus 17/100 --decimal-dps 60
```

gave

```
0.887273520064345754675253407883144755761078452297139624169825
```

versus `0.8872735200643458` from the independent exact pairwise calculation.
An exact rerun is required before using a larger fixed-vector result as a
certificate; the Decimal agreement is only a regression test.
