# Full-BV two-band support audit

Status: corrected analytic v5 **PASS** for the first support; its incomplete
v4 predecessor remains withdrawn.  The independent `R=0` degree-four
finite-form block is also **PASS**.  Neither result supplies a quotient above
one.  Two wider C722-shell schedules now have separate analytic audits.

## First exact support

The frozen support is

```text
k=48, epsilon=3/400, delta=7/250
A=(-3/400,1/4,253/1000)
inner B_m=103/400
outer B=(43/500,43/500,57/500,71/500,71/500,71/500,...)
```

The historical source-level checker
`verify_full_bv_two_band_prop1.py` has SHA-256
`1a771681617757b7a67c137e80a0dced72046493a55cfa9aa64a3e38e2ff53aa`.
Its immutable v4 result
`results/full_bv_two_band_prop1_audit_v4.json` has SHA-256
`2c413b368a6c4fc9e82641d3bd68d644dd0b1f10fc32c83a867b2389e235a549`.

**Retraction (2026-09-02).**  V4 covered fixed IIa/IIb/III at the maximal
band-pair `omega` and the repaired above-square IIc rectangle, but did not
separately cover the near-square-root strip at `omega=0`.  For this
`delta=7/250` support the mixed IIc gamma interval at maximal omega is
nonempty, so the omission cannot be bypassed by the empty-range argument
available for the newer wide support.  Consequently the following v4
inventory is retained only as historical evidence, not as a complete
Proposition-1 audit.  A corrected v5 must add literal omega-zero
IIa/IIb/III covers for both mixed orders and outer/outer.  No finite-form
matrix or quotient arithmetic depends on this analytic-label correction.

The replacement `verify_full_bv_two_band_prop1_v5.py` (SHA-256
`03cc767fb8c95156afffdcc0c30c5b8811934a6a495827ff9478bb3c1323ecae`)
and its four-test suite (SHA-256
`2715fb18f037d02fcafce8f1e0a2c7c6bf70bb85aad2ab8f0e2f757116adb329`)
pass in normal and optimized modes.  Their full result bytes are identical:
`results/full_bv_two_band_prop1_audit_v5.json` has SHA-256
`358b5bf1528265b75afd8085da656582a58ce3e62205b9d7eb53638969686b76`.

V5 explicitly splits each direct-HB pair into small-modulus BV, an
`omega=0` near-square strip, and a nonnegative-`omega_0` above-square
strip.  Its literal near-square IIa/IIb/III covers contain respectively
`59/59/35` count pairs and `177/177/105` family boxes for mixed, transpose,
and ordered outer pairs; every box is certified at one node.  The least
all-first slack is negative,

```text
IIb mixed (m,m')=(1,4): -6250003/7500000000,
```

so the former implicit all-first argument would fail.  The exact cover moves
one right coordinate to the second bin and has two-bin prefix slack
`63249999/2500000000`; this does not assert that the third bin is occupied.
The corrected safe IIb third capacity is `delta+2omega`, exactly `2H/7`
below its inward-shifted infimum.  The near-square IIc interval is empty by
`9999997/7500000000`.  Above the square root the exact IIc cell inventories
are `15104/15104/8960`, all one-node covers.  Thus the analytic condition on
which the D4/D6/D8 finite forms depend is restored; `theorem_ready` remains
false because their quotients are below one.

It reconstructs every Definition-1 condition and assigns the four ordered
band pairs as follows:

```text
(1,1): classical Bombieri--Vinogradov, modulus exponent 1/2
(1,2),(2,1): repaired direct-HB, omega=3/2000
(2,2): repaired direct-HB, omega=3/1000
```

Fresh exact fixed covers contain 59 mixed pairs in each order and 20
unordered outer pairs.  The independently widened 16-by-16 IIc subdivision
contains 15,104, 15,104, and 8,960 cover nodes respectively.  The checker
pins the repaired analytic source chain and uses
`rho=(log n/log(3x))*1_P`, hence `c1=c2=0`; it does not silently substitute
the literal prime indicator.  Its `theorem_ready` field is false because an
exact `k=48` quotient above one is still absent.

The earlier v3 output is rejected: its source changed while it was running.
The earlier v2 output remains historical but is superseded by v4, which adds
the corrected `gamma_min=2/5-H`, explicit `(0,0)` handling, and the weighted
minorant identity.

## Independent R=0 degree-four reconstruction

Root's producer `scripts/two_band_bv_r0_block.py` (SHA-256
`e1bccfc497c8193bd7e4d8c828a07e303b709f59d4223b183b9ca88c6f0b163e`)
emitted the 11-dimensional D4 artifact with SHA-256 prefix `0d31daa7`.
The independent checker
`verify_two_band_r0_d4_block.py` (SHA-256
`cb8a6a4e2286c4e91ef014bc929985a378c37d74e31e394773c8fb3c3efaad7c`)
does not import that producer.  It reconstructs all 66 symmetric entries of
both `I` and `48J` using a separate unshifted-box/orbit formula, then checks
the exact LDL pivots and particular-vector contractions.

Normal and optimized runs both return `AUDIT PASS`.  The audit artifact
`results/two_band_bv_r0_D4_independent_audit.json` has SHA-256
`7e6e7dd716c91bbf40996346770263904c4d94a584d87a83088b9e1037da8f59`
and reproduces matrix SHA-256
`f2cb8b749cfb25464a7d7e88b61ba3e9bd4c2827498dda951e4c35247c8d4e3b`.
The exact achieved quotient is

```text
0.981286530059850515750832539384816186999810586699499443025146...
```

with exact gain

```text
6.40450294974624539985819715356330772169933190211233877669061e-7
```

over the certified radial BV benchmark.  D6 and D8 raise the gain only to
`1.648337872...e-6` and `2.996980957...e-6`; D8 misses the predeclared
`.005` continuation gate by about 1,668.  Thus the R=0-only ladder is retired.
This is not an upper bound on the complete outer-band correction space.

## Full-outer cross evaluator

`two_band_full_outer_constant.py` intersects the four literal marginal
branches of two potentially different supports.  Its low-dimensional tests
compare exact `k=2` constant marginals and support-difference polarization,
including the single factor `k` in `kJ`.  A first hostile fixture exposed
that the fixture itself violated Definition 1 (`B_2-B_1>delta`); the
production class now rejects such schedules.  Valid signed `k=2,3` orbit
tests and literal `k=2` tests pass in normal and optimized modes.

The source-bound run completed in `1483.674` seconds with peak self RSS
`35,768 KiB`.  Artifact
`results/full_bv_two_band_full_outer_constant_2x2_exact_v2.json` has SHA-256
`4a4d94f20ca5ae21a0fc83e874531299586db75e01ee357a16d1c1c9bdae0006`.
Its exact rational vector achieves

```text
q = 0.9812864684567660564609473370412215782327916050420421086...
gain over radial BV base = 5.7884721051533465478347612075e-7.
```

The fail-closed contraction checker
`verify_full_outer_constant_artifact.py` (SHA-256
`0d6618702b4e70e9ce7d09811806d22d0a59f4af9126506373b50c85a11cf9ce`)
reconstructs the exact particular forms, quotient, margin, all per-count
sums, and the projective root; it and the four geometry tests pass in normal
and optimized modes.  This direction lies about `6.16030845e-8` below the
independently audited R=0 D4 vector.  It is retired as a closing direction,
not as an upper bound on the full outer-shell space.

## Wider C722 shell

The next support preserves the same exact BV core but uses

```text
delta=361/50000, epsilon=3/400, A2=3121/12000,
B_outer,m=min(11/200+(m-1)delta,43/250).
```

The plateau `43/250` has active counts `0..23`.  A competing high-count ramp
with first cap `723/100000` has more formal high-count capacity but loses the
constant shell almost completely.  A second, volume-favoring schedule is

```text
B_outer,m=min(49/625+(m-1)delta,1599/10000), active counts 0..22.
```

The exact normal/optimized-identical volume artifact
`results/wide_c722_outer_volume_comparison_v3.json`
(SHA-256
`c9fefd5c06c02e6033e5a93666287597acfafa8ad575945c950ab9cb833f36a0`)
gives

```text
I_shell(plateau 3/20) = 2.5164838893415303652692e-91
I_shell(plateau 43/250) = 3.7099223495912935445329e-91
I_shell(high-count ramp) = 1.4553324827765291322252e-112.
I_shell(volume ramp) = 6.5006809721369850844695e-90
volume-ramp / plateau-43/250 = 17.5224178825552443567...
```

This comparison concerns only the constant-function `I` mass.  It proves no
quotient or upper bound.

The independent high-plateau analytic checker
`verify_wide_c722_two_band_prop1.py` has SHA-256
`3ec590c95376432a75fb55c7810fbff10e87b67964d6cc4f761576c23aa414ca`;
its six-test suite has SHA-256
`9a6d2c5a960b665c328c78701bd8af15d70058baa956b7105bb9c45de3e7a8d2`.
Normal and optimized full runs are byte-identical at artifact SHA-256
`d96f1f795cbd6e29796ce2b67619ec625032ddf90b9a2ce3939899812d20d14f`.
They implement the disjoint source-level range assignment:

```text
inner/inner: classical BV;
mixed: fixed omega=121/24000, whose IIc gamma range is empty;
outer near square root: omega=0 IIa/IIb/III, IIc empty;
outer above square root: fixed omega=121/12000 plus 0<=omega_0<=omega IIc.
```

The corrected safe IIb third capacity is `delta+2omega`, smaller than the
actual inward-shifted infimum by exactly `2H/7`.  The new outer-near audit
covers 575 ordered count pairs and 1,725 literal family boxes; all are
one-node covers and the least all-first slack is
`15449999/2500000000`.  The above-square outer IIc grid has 147,200 cells,
also all one-node covers.  A hostile regression records that the unused
mixed omega-zero pair `(1,17)` defeats the two-bin prefix shortcut, preventing
the range split from being silently broadened.  This analytic result remains
`theorem_ready=false` because no exact quotient above one exists.
