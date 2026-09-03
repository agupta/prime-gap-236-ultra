# H6 sparse scalar-line package

Date: 2026-09-02 (Europe/Berlin)

## Status

**DISCOVERY LINE COMPLETE; NEGATIVE.**  The exact relative first-order ranking
selects the positive `H6` compressed coordinate.  Its 11-label self-form run
and full projective line reconstruction are now complete.  The line maximum is
`0.97096994033087643550826164308854532661219495084162968305...` at
`s=1.1963659022852116293141046740272859982e-23`.  Thus its
serialized-pencil shortfall is about `0.02903005966912356`.  This retires only
the H6 line, not the 20-coordinate band space.  The integral values remain
Decimal100 discovery values, not a rigorous certificate.

The input for the direct self-form run is

```text
agents/small-delta-frontier/results/h6_scalar_line/c10_D12_h6_direction_11.json
SHA256 a716e6a8da809c7363c6fc3773dd453db534a886742654541dc1b2a7c1940b81
```

The manifest is
`agents/small-delta-frontier/results/c10_D12_h6_scalar_line_manifest.json`,
SHA `5ab604c0b0c262da61b024bd28db672b31912f50c0c125988e4ad7fccc34cd6a`.

## Exact candidate identity and normalization

Let `theta` be the exact fraction represented by each serialized Decimal100
base coordinate.  The line is

\[
 \theta(\tau)=\theta+\tau e_{H6}.
\]

Its H12 gauge coordinate stays exactly one.  Thus there is no finite
projective pole on this coordinate line: “near-pole” terminology does not
apply.  The literal rational choices `tau=1/20,1/10,1/5` nevertheless give
well-posed maximum expanded-coordinate relative changes of exactly 5%, 10%,
and 20%.  Exactly the 11 degree-six orbit coefficients change.

The emitted trial SHAs are:

- 5%: `83009208817e4ec7136af651c1be44382eb851d3ece3440a6b4d6b574c003b93`;
- 10%: `ddc6586e481842f1b0d925ecbaf766748197a99818cd9571c0d02da92f5a7d82`;
- 20%: `00e64aa26ba82dac5ddb8e73ec29876ad55f5aa87fc7284f6417ea1e77c9d9aa`.

All contain 272 explicit ordered labels and coefficients.  The generator
independently checks the exact unrounded source expansion and separately the
Decimal100 source-to-action rounding.  It binds source SHA `719c656e...`,
band map SHA `29d38a9e...`, recovered action SHA `6411f11d...`, raw action SHA
`0ac99ee5...`, sparse operator SHA `e1545435...`, grouped evaluator SHA
`47167e92...`, and integrator SHA `941ee82b...`.

## Action and self-form factors

Write the capped denominator and numerator operators as `A=I` and `B=48J`.
The sparse producer computes

```text
grad_denominator = 2 A theta
grad_numerator   = 2 B theta
```

and the byte-pinned recovery defines its actions by exact division by two.
For `d=e_H6`, therefore,

\[
 a_{01}=I(\theta,d)=a_{13},\qquad
 b_{01}=48J(\theta,d)=b_{13}.
\]

The independent grouped fixed-vector evaluator returns

```text
denominator = I(d,d)       = A11
j_value     = J(d,d)
numerator   = 48*j_value   = B11.
```

Thus factor 48 occurs exactly once.  The direct direction file uses the
literal 11 H6 labels and weights from the pinned band map; it does not contain
the other 261 labels and does not evaluate a full endpoint.

## Complete line recovery

Once `A11,B11` are available, every line point is

\[
 q(s)={N_0+2s b_{01}+s^2B_{11}
       \over D_0+2s a_{01}+s^2A_{11}}.
\]

The stationary polynomial, up to an irrelevant factor two, is

\[
 R+(D_0B_{11}-N_0A_{11})s
 +(B_{11}a_{01}-A_{11}b_{01})s^2,
\quad R=D_0b_{01}-N_0a_{01}>0.
\]

The fail-closed consumer
`recover_h6_scalar_line.py` checks the self-form result SHA, C10 parameters,
11/77/312/23/1200 label/group/face/marginal/domain counts, evaluator and
integrator SHAs, and `numerator=48*j_value`.  It then emits the exact pencil,
the three trial values, and the exact test for whether the line maximum is
strictly above one.  This remains a Decimal100 discovery reconstruction until
the winning vector is certified independently.

The completed input has result SHA `0ee7813d37284e3fc5a18193610685958cfa9e2934ad2b1fbceaecf9610e5f3f`
and I-stage SHA `f7ec9e5f8acfb10355b74595ca3826d656903f57ab40a5ce5ae3d0a4d8aefcb8`.
It gives `A11=3.14640787386387078996118e-95` and
`B11=1.24973413585648832092731e-95`.  Replaying the producer's actual
Decimal100 operation order is essential: independently serialized derived
fields can differ from exact Fraction contraction by one final Decimal unit.
A permanent mutation test rejects a one-unit change.  The reconstructed line
artifact is `results/h6_scalar_line/c10_D12_h6_line_reconstructed.json`, SHA
`58e700ae18dd2dd799b05fa9d305c025986d1fe9158bc1b224cf4a9e5ec11087`.
Its second stationary value is `.3969967481307691...`; the
projective-infinity value is `.3971939385982346...`.

For comparison, if a full endpoint at nonzero `tau` were evaluated instead,
one endpoint recovers

\[
 A_{11}={D_\tau-D_0-2\tau a_{01}\over\tau^2},\qquad
 B_{11}={N_\tau-N_0-2\tau b_{01}\over\tau^2}.
\]

After the endpoint I-stage alone, set
`h0=N0-D0<0`, `h1=b01-a01`.  If
`D0*A11-a01^2>0`, the exact endpoint-quotient threshold is

\[
 q_\tau^*=1+{(h_0+\tau h_1)^2\over h_0D_\tau}.
\]

Then the full line has maximum strictly above one if and only if
`q_tau>q_tau_star`.  The consumer's `threshold` mode computes this number from
only the pinned candidate and I-stage, but makes no sign claim before the
endpoint numerator exists.

## Launch command and cost gate

Run from `prime-gap-236/` only when the resource scheduler permits:

```bash
python3 agents/exact-integrator/grouped_fixed_vector.py \
  agents/small-delta-frontier/results/h6_scalar_line/c10_D12_h6_direction_11.json \
  --alpha 79247/300000 --delta 1/100 --eta 76247/300000 \
  --beta1 3/20 --beta2 3/20 --beta3plus 97/625 \
  --decimal-dps 100 --workers 2 \
  --i-stage agents/small-delta-frontier/results/h6_scalar_line/c10_D12_h6_self_mp100.I-stage.json \
  --output agents/small-delta-frontier/results/h6_scalar_line/c10_D12_h6_self_mp100.json
```

Static preparation gives 121 orbit keys/293 orbit terms, 77 grouped I orbits,
272 I residual terms, and 23 marginal components on 11 marginal orbits.  The
full D12 reference has 5,929/48,867/1,575/695 respectively.  The actual
two-worker run took `64.506742` seconds, with maximum child RSS `24608` KiB.

## Code and tests

- generator SHA `4222d304f72a89c3c37e1a4948c5164039e8050df3c6af93859a4288033fd196`;
- line consumer SHA `f2462e9688bf0f426856ff81f7354476a762e1617c1fd8c81b7b67a17098b797`;
- line tests SHA `365b08feb1339a60d95864b0cf20f4aee83f6badba08b7be64ca77b7a2af95c4`;
- dormant full-vector emitter SHA `160540af715f6cb971ae855a3fad58904c82ee11d128a884e505d3759284c361`;
- emitter tests SHA `a995fd7b2b82ee094bf0d2d6dfab14e75bed4b17bc137c317e3336db223a93a2`.

Run:

```bash
python3 agents/small-delta-frontier/test_h6_scalar_line_package.py
python3 -O agents/small-delta-frontier/test_h6_scalar_line_package.py
```

All 4 line tests and all 3 emitter tests pass in both modes.  They reproduce
all artifact SHAs, reject
pre-existing destinations, independently reconstruct the 11-label direction
and all three relative normalizations, audit the factor-two/factor-48 action
semantics, replay Decimal100 derived fields, reject a final-unit mutation,
check the complete generalized-eigenvalue line, and exercise canonical
rational, alias, postwrite-input, and output-inode race failures.  Because the
line is negative, the emitter is deliberately frozen without a production
candidate.
