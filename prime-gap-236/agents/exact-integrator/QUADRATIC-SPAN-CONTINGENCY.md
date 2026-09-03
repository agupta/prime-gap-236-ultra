# D12 two-vector multiplier contingency

Status: specified but not launched. The active transferred quadratic-multiplier
run must finish first.

Let `F` be the pinned D12 fixed polynomial and let `Q=Q_R(L,Z)` be the exact
96-coordinate D4 multiplier currently being transferred. Write

\[
D_{00}=I(F),\quad D_{11}=I(QF),\quad D_{01}=I(F,QF)
\]

and use `N=48J` for the analogous numerator form. The already known base
evaluation supplies `(D00,N00)`, and the active quadratic transfer supplies
`(D11,N11)`.

Choose a nonzero exact rational projective scale `lambda` and evaluate the one
additional multiplier

\[
H=1+\lambda Q.
\]

If its fresh scalar forms are `(DH,NH)`, polarization gives exactly, relative
to the serialized scalar arithmetic,

\[
D_{01}=\frac{D_H-D_{00}-\lambda^2D_{11}}{2\lambda},\qquad
N_{01}=\frac{N_H-N_{00}-\lambda^2N_{11}}{2\lambda}.
\]

Consequently the complete D12 Rayleigh quotient on `span{F,QF}` is

\[
R(t)=\frac{N_{00}+2tN_{01}+t^2N_{11}}
           {D_{00}+2tD_{01}+t^2D_{11}}.
\]

Its finite stationary points are the real roots of

\[
(N_{01}D_{00}-N_{00}D_{01})
+(N_{11}D_{00}-N_{00}D_{11})t
+(N_{11}D_{01}-N_{01}D_{11})t^2=0.
\]

The projective point `t=infinity`, with value `N11/D11`, must also be ranked.
Every reported finite candidate must satisfy a positive denominator. This is a
two-dimensional generalized eigenproblem, so no power-method largest-magnitude
ambiguity remains.

For the frozen D4 multiplier artifact
`results/c10_stratum_quadratic_cappedopt_D4_exact.json` (SHA-256
`fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86`),
the largest absolute multiplier coefficient is exactly one. Thus `lambda=1`
is already an exact coefficient-controlled scale: forming `1+Q` only adds one
to each stratum's channel-`1` coefficient, and no coefficient blow-up is
introduced. If the completed D12 form magnitudes show serious imbalance, a
dyadic `lambda=2^m` nearest to `sqrt(D00/D11)` may instead be used; its exact
rational value and the above polarization formula must be serialized.

## Implementation and cost

`stratum_quadratic_transfer_decimal.py` can consume this modified multiplier
without arithmetic or traversal code changes. It already accepts all 96 labels
`(R,1,L,Z,L^2,LZ,Z^2)` for `R=0,...,15` and inserts the supplied rational
vector before both I squaring and J marginal squaring. A new multiplier JSON is
still required: add `lambda*q_R` to each channel and add one to every
channel-`1` entry, then recompute the exact D4 forms and the
`rigorous_forms`/`block_direct_bitwise_equal` gates. Copying the old booleans or
matrix values would be invalid even though the transfer loader would accept
the same schema.

The discovery cost is exactly one more full scalar D12 transfer with the same
target combinatorics: 1,575 grouped I residuals, 312 I faces, and 1,200 active J
domains. The active Q-only run measured 3,319.761082 seconds for I; its J time
will be inserted after completion. The nonzero channel pattern changes only in
the R=0 constant entry, so `1+Q` should have comparable wall time and memory,
but that is a scheduling estimate, not a mathematical assumption. Existing I
or J stages cannot be reused because the squared multiplier changes.

Polarization and the 2-by-2 solve are negligible after that traversal. All
these forms are Decimal discovery data. A winning rational `t` still requires
a fresh exact or outward-rounded direct evaluation of `(1+tQ)F`; a positive
predicted eigenvalue is not itself a certificate.

