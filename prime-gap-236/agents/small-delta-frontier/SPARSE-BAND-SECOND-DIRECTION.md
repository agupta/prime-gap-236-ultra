# Sparse 20-band second-direction contingency

## Verdict

**A concrete sparse tangent direction is determined, but no nonzero finite
step is certified by the stored first-order data.**  In the 20-coordinate
compression (12 individual degree-at-most-four coordinates followed by
`H5,...,H12`), the exact top coordinate under the relative-step score is

\[
 d=e_{H6}.
\]

It expands to exactly 11 of the 272 no-ones orbit labels.  It is therefore a
minimal, one-band candidate for a future scalar/self-form evaluation.  No new
integral was run and no finite quotient is claimed.

The fail-closed selector is
`select_sparse_band_contingency.py`, SHA
`50284460fc4d2629b760016b56792617dbf64b0f24cf6c912875c92365cf3b79`.
Its output is
`results/c10_D12_sparse_second_direction.json`, SHA
`705908c6528454e8be237d293998127445b213ee31f2833ea48139408b724286`.

## Bound inputs and base semantics

The selector independently reconstructs the disjoint 20-to-272 map and binds
the following bytes:

- exact 272-term source SHA `719c656e...d64a87`;
- 20-band partition SHA `29d38a9e...d31e9`;
- recovered gradient SHA `6411f11d...56a43`;
- rejected raw traversal SHA `0ac99ee5...d644d`.

The gradient producer evaluated the exact band map after conversion to
Decimal100.  Thus its serialized `theta` is the exact rational represented by
`Decimal100(theta_source)`, not the longer source fraction.  The selector
checks this rounding coordinate by coordinate and separately checks that the
unrounded band map reconstructs all 272 source coefficients.  An initial
byte-for-byte equality check correctly failed and was not weakened to an
uncontrolled tolerance.

Write the serialized denominator and numerator as `D0,N0`, and the recovered
half-gradients as `a=A theta`, `b=B theta`.  They are discovery decimals, used
as exact fractions only to make all subsequent manipulation reproducible.
They are not promoted to exact integrals.

## Exact selection rule and result

For each gauge-preserving coordinate `j<19`, define

\[
 R_j=D_0 b_j-N_0 a_j,
 \qquad d_j=\operatorname{sgn}(\theta_jR_j)\theta_j e_j.
\]

This normalizes every candidate to maximum relative coordinate change one,
and gives
\(R(d_j)=|\theta_jR_j|>0\).  Coordinate 19 (`H12`) is held fixed as the
projective gauge.  Sorting these exact fractions gives, in order, `H6`, `H7`,
and `H5`; the unique winner is coordinate 13, `H6`, oriented positively.

For `H6`,

\[
 R(d)=6.02065802020080552979708476341640588447\ldots 10^{-252},
\]

and the formal quotient directional derivative from the serialized data is

\[
 {2R(d)\over D_0^2}
 =15496557083626953.2391386607649133086\ldots .
\]

The large derivative is a scale artifact of the tiny polynomial forms and is
not a predicted finite quotient gain.

There is a roughly `1e-61` Euler discrepancy because the Decimal100 action and
forms were accumulated independently.  Replacing the displayed base forms by
the action-consistent values
\(\bar D=\theta\cdot a\), \(\bar N=\theta\cdot b\) preserves the exact ranking:
`H6,H7,H5`.  It also gives

\[
 \bar R(e_{H6})
 =6.02065802020080552979708476341640588447\ldots 10^{-252}>0.
\]

Thus the selection is not an artifact of choosing either of the two
Decimal100 base reconstructions.

## Exact finite-step falsification criterion

Let `A11=I(d,d)` and `B11=48J(d,d)` be the two missing self-forms, and let
`a01=I(theta,d)`, `b01=48J(theta,d)`.  For any positive rational `tau`, direct
expansion gives

\[
 \begin{aligned}
 &N(\theta+\tau d)D_0-D(\theta+\tau d)N_0\\
 &\quad=2\tau R(d)+\tau^2 C(d),\\
 &C(d)=D_0B_{11}-N_0A_{11}.
 \end{aligned}
\]

Consequently the proposed finite step strictly improves the base quotient
exactly when

\[
 C(d)>-{2R(d)\over\tau}.
\]

This is the requested exact falsification test.  A future evaluation needs
only the two H6 self-forms (the cross forms are already present); it does not
need a full 20-by-20 matrix.

The existing action cannot determine the sign for any specified nonzero
`tau`.  To see this even after enforcing exact action consistency, split off
the base vector `theta` and choose a vector `v` perpendicular to it with
`v.d != 0`.  Adding `M vv^T`, `M>=0`, to `B` preserves positive
semidefiniteness, the complete action `B theta`, and the base form, while
making `B11` arbitrarily large.  Adding the same term to `A` instead makes
`A11` arbitrarily large.  Hence `C(d)` can be arbitrarily positive or
negative without changing any stored first-order datum.  The test suite also
exhibits two explicit rational 2-by-2 positive-semidefinite completions with
the same base and cross action whose finite-step signs are opposite.

This does not deny the usual local existence conclusion from a genuine exact
positive derivative.  It says that these discovery decimals supply neither a
rigorous derivative nor an explicit certified step size.

## Independent checks

Run from the workspace root:

```bash
python3 prime-gap-236/agents/small-delta-frontier/test_sparse_band_contingency.py
python3 -O prime-gap-236/agents/small-delta-frontier/test_sparse_band_contingency.py
```

The independent test SHA is
`20e0f9f899517b8e00b2643bb4c1283b4c4ff7df6e3491d54b0d648b0b17798a`.
All 3 tests pass in both modes.  They reconstruct the exact ranking and
literal 272-term H6 expansion, check every factor in the finite-step identity,
and verify the opposite-sign PSD completions.  The output explicitly has
`rigorous=false`, `finite_form_value_claimed=false`, and
`fresh_scalar_reevaluation_required=true`.
