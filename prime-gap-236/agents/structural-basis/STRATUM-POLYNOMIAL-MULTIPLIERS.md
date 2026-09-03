# Fixed-polynomial, stratum-polynomial multiplier space

## Status

This is an exact finite-basis construction proposed after the scalar
stratum-amplitude calculation.  It is not a quotient certificate.  Its purpose
is to adapt a strong high-degree global polynomial to the cap boundary inside
each large-coordinate stratum, rather than merely rescaling the entire
stratum by one constant.

Fix a symmetric polynomial `F0`.  For a point `t`, write

\[
 R(t)=\#\{i:t_i>\delta\},\qquad
 L(t)=\sum_{t_i>\delta}t_i,\qquad
 Z(t)=\sum_{t_i\leq\delta}t_i.
\]

For a small multiplier degree `d`, use the explicit symmetric basis

\[
 G_{R,a,b}(t)=1_{R(t)=R}F_0(t)
              \left(\frac{L(t)}{\alpha}\right)^a
              \left(\frac{Z(t)}{\alpha}\right)^b,
 \qquad a+b\leq d.                                           \tag{1}
\]

The powers of `alpha` only improve conditioning and may be omitted without
changing the span.  Every input is rational, so all matrix entries remain
rational.  The scalar-amplitude space is exactly the `d=0` subspace.

## Exact denominator blocks

The grouped integrator's `I` face has `r` large common coordinates and `h`
small coordinates translated by inclusion--exclusion.  Its aggregate
variables satisfy

\[
 L=r\delta+z,\qquad Z=h\delta+w.                             \tag{2}
\]

Let `P_{r,h}(z,w)` be the existing exact face polynomial for `F0^2`, including
the angular orbit density and residual power.  Since the stratum indicators
are disjoint, `I` is block diagonal in `R`, and its entry is obtained by
multiplying the existing face polynomial by

\[
 \alpha^{-a-a'-b-b'}(r\delta+z)^{a+a'}(h\delta+w)^{b+b'}     \tag{3}
\]

before the unchanged polygon or degenerate-interval integration.  No new
geometric decomposition is needed.

## Exact marginal blocks

On a `J` face, let `r,h,z,w` describe the `k-1` common coordinates and put

\[
 L_c=r\delta+z,\qquad Z_c=h\delta+w.
\]

The existing four marginal branches split into two classes.

* On `Sdelta` or `Stotal`, the distinguished coordinate `u` is small.  The
  completed point has `R=r`, `L=L_c`, and `Z=Z_c+u`.
* On `Ltotal` or `Lbig`, the distinguished coordinate is large.  The completed
  point has `R=r+1`, `L=L_c+u`, and `Z=Z_c`.

For one component `u^e(1-S)^q P_lambda(common)` of `F0`, the multiplier is
therefore inserted before marginal integration by the exact expansions

\[
 \begin{aligned}
  \text{small: }&L_c^a(Z_c+u)^b
     =L_c^a\sum_{j=0}^b {b\choose j}Z_c^{b-j}u^j,\\
  \text{large: }&(L_c+u)^aZ_c^b
     =Z_c^b\sum_{j=0}^a {a\choose j}L_c^{a-j}u^j.             \tag{4}
 \end{aligned}
\]

Thus each term in (4) calls the already audited marginal primitive with
distinguished exponent `e+j`, then multiplies its bivariate output by the
indicated exact affine powers of `L_c` and `Z_c`.  The existing orbit product,
branch-intersection domain, and polygon integral are unchanged.

A small branch contributes only labels with total stratum `R=r`; a large
branch contributes only `R=r+1`.  Consequently the `J` form is block
tridiagonal in `R`.  For multiplier degree `d`, each nonempty stratum block has
size `(d+1)(d+2)/2`.  At `d=1` this is only three basis functions per stratum:
`F0`, `L F0`, and `Z F0`.

## Required falsification tests

Before using this space for discovery, an implementation must pass all of the
following exact tests.

1. At `d=0`, every `I` diagonal and every small--small, small--large, and
   large--large `J` block is bit-for-bit equal to `stratum_amplitude.py`.
2. Giving coefficient one to every constant multiplier and zero to every
   other multiplier reconstructs the original fixed-vector `I` and `kJ`.
3. A separately expanded `k=2` or `k=3` constant-`F0` example agrees with
   direct symbolic integration, including an interior cap/total branch switch.
4. Every matrix entry with `|R-S|>1` is exactly zero, and both forms are exactly
   symmetric.
5. For a signed rational multiplier vector, a fresh branch-scaled traversal
   agrees bit-for-bit with both quadratic forms assembled from the matrices.
6. Serial and forked evaluations agree, and malformed/incomplete stratum
   schedules fail closed.

Floating generalized eigenvectors may select a candidate only.  The reported
result must rationalize the full coefficient vector and verify `I>0` and
`kJ-I>0` (or its exact negative value) with `Fraction` arithmetic.

## Decision rule

First run `d=1` on the exact C10 degree-4 polynomial.  If its exact gain over
the scalar-amplitude result is negligible, retire this multiplier family at
low degree.  If it is material, apply the same matrix construction to the
degree-12 fixed polynomial at multiprecision for discovery; only a candidate
above one warrants the independent exact reconstruction.
