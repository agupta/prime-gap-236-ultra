# Uncapped piecewise D18 Definition-5 audit

Date: 2026-09-03 (Europe/Berlin).

## Verdict

`AUDIT PASS`, scoped strictly to the frozen two-dimensional **uncapped search
relaxation**.  This is not an approved Proposition-1 support, a capped
quotient, or a proof of `H1 <= 236`.

The independently reconstructed rationalized stationary direction has

```
q = 1.009466545645507973252113917583019903542277363493897033680759358482484...
q - 1 = 0.009466545645507973252113917583019903542277363493897033680759358482483908...
```

The full exact fractions for `q`, `q-1`, and the raw positive quadratic-form
margin are in the audit JSON.  Their signs are checked as integer signs; the
decimals above are displays only.

## Independent reconstruction

The checker does not import `scripts/evaluate_two_band_piecewise_dilations.py`
and does not trust its serialized matrices.  Starting from all 471 exact
coefficients in the frozen D18 vector, it uses the separately implemented
orbit-moment engine to rebuild:

- the inner and naturally dilated outer polynomial squares;
- the inner, outer-low, and outer-high marginals;
- six independently collected self/cross orbit products;
- every entry of the 2-by-2 I and 48J matrices.

The rebuilt matrices equal the producer matrices as exact Fractions.  The
inner `c=1` block also exactly equals the denominator and numerator recorded
in the source D18 certificate.

Definition 5 is enforced as follows:

- inner/inner uses `eta1 = 97/400`;
- every mixed or outer/outer integral uses `eta2 = 3031/12000`;
- the off-diagonal is
  `48*(J(inner,outer-high)-J(inner,outer-low))`;
- the outer diagonal is
  `48*(J(high,high)+J(low,low)-2J(low,high))`.

Thus factor 48 occurs exactly once.  The exact `B-I` determinant is negative,
and the displayed rational vector contracts to a strictly positive
`c^T(B-I)c`, independently proving the search-pencil sign.  The stationary
root agrees at 100 and 160 decimal digits before its declared 70-digit
rationalization.

## Frozen artifacts and replay

- checker: `agents/audit/verify_bv_d18_piecewise_definition5.py`;
- result: `agents/audit/results/bv_d18_piecewise_definition5_audit.json`.

Run from `prime-gap-236/`:

```bash
python3 agents/audit/verify_bv_d18_piecewise_definition5.py
python3 -O agents/audit/verify_bv_d18_piecewise_definition5.py
```

Normal and optimized outputs are byte-identical.  Each run reconstructs the
matrix from the coefficient vector and can take several minutes.

The next mathematically relevant experiment is an exact contraction of this
D18 inner coordinate against the analytically approved capped outer support;
the present uncapped pass cannot be substituted for that calculation.
