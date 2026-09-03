# Near20 v3 scalar output and Rayleigh-line audit

Date: 2026-09-02 (Europe/Berlin)

## Status

**PENDING FINAL SCALAR OUTPUT; NO QUOTIENT CLAIM.**  The independent auditor
and exact line tests are ready, but
`c10_D12_h12_near_20pct_v3_grouped_mp100.json` has not yet been emitted.
No form value, improvement, or stationary point is inferred from the I stage
alone.

Frozen bindings required by the independent auditor are:

- near20 v3 trial SHA `88c1d26f6cf46bbdd12dc000eb802cac8efe91be0ad003d6827f2ccdc6c0ff47`;
- recovered base action SHA `6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43`;
- grouped evaluator SHA `47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a`;
- exact integrator SHA `941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52`.

The current I stage SHA is
`db9caca00ecd24ab36bdfcaeb5839af69d0a668d3c546e62af498052a983c5bb`.
It has the expected MP100 discovery status, input SHA, C10 parameters, 272
input coordinates, 1,575 orbit groups, 312 faces, and positive denominator

```text
2.501361020595895591485184602791392461729407107149123620724382009944906312769905933310807164286724958E-132
```

but contains no J value.

## Independent reconstruction

Let `theta` be the recovered 20-coordinate base, `y` the exact rational
near20 endpoint, and let the trial metadata give nonzero `t,s` with

\[
y=s(\theta+t d).
\]

The auditor reconstructs every coordinate of
`d=(y/s-theta)/t`.  With recovered serialized actions `A theta,B theta`, base
forms `A00,B00`, and fresh endpoint forms `D_y,N_y`, it reconstructs

\[
A_{01}=d^T A\theta,
\quad
A_{11}=\frac{D_y/s^2-A_{00}-2tA_{01}}{t^2},
\]

and the analogous `B01,B11`.  It checks the endpoint identities exactly as
fractions of the serialized decimal strings.  The stationary numerator for

\[
q(u)=\frac{B_{00}+2B_{01}u+B_{11}u^2}
           {A_{00}+2A_{01}u+A_{11}u^2}
\]

is reconstructed as

\[
(B_{01}A_{00}-A_{01}B_{00})
+(B_{11}A_{00}-A_{11}B_{00})u
+(B_{11}A_{01}-A_{11}B_{01})u^2.
\]

Every reported real root must have positive reconstructed `D`; the auditor
also requires the reconstructed D line to be positive definite.

The stored base value and recovered action were rounded separately.  Their
Euler residuals are about `2.04e-61` and `9.75e-62` relative, so the tempting
identity `s*t*q'_raw=q'_(y-theta)` is not exact: its defect is about
`1.70e-60`.  The auditor instead checks the trial's recorded derivative
exactly from `h=y-theta`, records the raw-projective defect, and requires it to
be below `1e-50`; it does not silently set the defect to zero.

## Auditor and tests

- independent auditor SHA
  `3962451ce0090c8c1150591a1d7202a594b427ca8454d534b1d17f5262bd249e`;
- independent tests SHA
  `7612313006d7e045cd028f394c979dca3f722aee2cf5f459bf56b032f1852fe8`.

The tests pass 4/4 in normal and optimized modes: duplicate JSON rejection,
synthetic exact `y=s(theta+t d)` and `A11/B11` recovery, the actual recorded
derivative plus nonzero rounding defect, and an independent expansion of the
stationary derivative numerator.

The final invocation must supply freshly recorded byte SHAs:

```sh
cd prime-gap-236
PYTHONPATH=. python3 agents/small-delta-frontier/audit_near20_scalar_line_independent.py \
  --trial agents/structural-basis/results/c10_D12_h12_near_20pct_v3.json \
  --recovery agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json \
  --result agents/structural-basis/results/c10_D12_h12_near_20pct_v3_grouped_mp100.json \
  --i-stage agents/structural-basis/results/c10_D12_h12_near_20pct_v3_grouped_mp100.I-stage.json \
  --grouped-source agents/exact-integrator/grouped_fixed_vector.py \
  --integrator-source agents/exact-integrator/src/exact_integrator.py \
  --expect-result-sha256 <FRESH_RESULT_SHA> \
  --expect-stage-sha256 db9caca00ecd24ab36bdfcaeb5839af69d0a668d3c546e62af498052a983c5bb \
  --output agents/small-delta-frontier/results/near20_scalar_line_independent.json
```

No output file is authorized until the raw scalar result exists and is pinned.
