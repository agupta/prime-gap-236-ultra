# BV D16 piecewise Definition-5 hostile audit

## Verdict

**AUDIT PASS for the frozen uncapped search pencil only.**  An independent
exact reconstruction, which imports neither the producer nor its matrix,
agrees on every entry of the 2-by-2 `I` and `48J` matrices.  For inner
dilation `1`, outer dilation `3090/3211`, and the displayed rationalized
stationary amplitude, the exact quotient is

```text
q = 1.00510111767528007059574062514480033287442324136230203560690...
q - 1 = 0.00510111767528007059574062514480033287442324136230203560689945...
```

The reduced exact fraction for `q-1` is emitted by the checker.  No decimal
sign is used in the verdict.  Independently, `48J-I` has two negative diagonal
entries and negative determinant, hence exactly one positive direction.  The
displayed rational vector lies in that direction.

## Definition-5 and dilation checks

Writing `m_i` for the inner polynomial's marginal to `alpha1`, and `m_o1`,
`m_o2` for the outer polynomial's marginals to `alpha1`, `alpha2`, the exact
blocks reconstructed by the audit are

```text
B00 = 48 integral_[U <= eta1] m_i^2
B01 = 48 integral_[U <= eta2] m_i (m_o2 - m_o1)
B11 = 48 integral_[U <= eta2] (m_o2 - m_o1)^2.
```

Thus inner/inner alone uses `eta1=97/400`, while every block involving the
outer band uses `eta2=3031/12000`.  The factor 48 occurs exactly once; the
ordinary quadratic contraction supplies the factor two on `B01`.  The `I`
matrix is diagonal because the total-sum bands are disjoint.  Endpoint choices
affect null sets only.

The inner block (`c_inner=1`) agrees exactly with the original frozen BV D16
certificate, including both `I` and `48J`.  The outer block agrees exactly
with the separately frozen natural-dilation computation.  The independently
computed stationary root is stable between 100 and 160 decimal digits, and
its 70-digit rationalization is exactly the amplitude serialized in the
successful row.

## Scope

The outer full simplex is uncapped and is not the analytically approved
volume-ramp support.  This is therefore an exact search point, not a
Proposition-1 support certificate, not a lower bound for the capped quotient,
and not a proof of `H1<=236`.  A separately audited capped contraction is
still necessary.

## Frozen inputs and replay

- producer/artifact: `f3bbc9c6c35e2cb8b1ac7ce6accf56144c01099be81dfe288407b4552165b7bb`
  / `e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7`;
- independent checker:
  `a9210778111aff552dc0dc4142520bc7d442174617e7c620a1cf0ddc5d9b07ab`;
- audit result:
  `00e273d07ab98f667fcb3a8172a13349841ed0a4d58807c2308d6850fb3b2b25`.

```bash
cd prime-gap-236
python3 agents/audit/verify_bv_d16_piecewise_definition5.py
python3 -O agents/audit/verify_bv_d16_piecewise_definition5.py
python3 scripts/evaluate_two_band_piecewise_dilations.py \
  agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json \
  --inner-c 1 --outer-c 3090/3211 --output /tmp/piecewise-normal.json
python3 -O scripts/evaluate_two_band_piecewise_dilations.py \
  agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json \
  --inner-c 1 --outer-c 3090/3211 --output /tmp/piecewise-opt.json
```

The frozen producer replayed byte-identically in normal and optimized mode.
The independent checker also emitted byte-identical normal/optimized output.
