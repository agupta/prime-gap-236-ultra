# Selective capped BV D16 count-15 contraction

Status: design only; no quotient or theorem claim.  The immutable staged
evaluator is `code/bv_d16_volume_ramp_capped_probe_v1.py` at SHA-256
`cad3e32b77717419061a46d9863e5a99785cf34f71fc5e992f684c3b1741f7f5`.

## Correct finite space

The inner coordinate is the certified BV D16 polynomial with dilation
`c_inner=1`, on the complete simplex `sum(t_i)<=103/400`.  The outer
coordinate is the same source polynomial dilated by `c_outer=3090/3211`,
restricted to the volume-ramp scheduled shell

```
S(3211/12000, B) \ S(103/400, B),
B_m = min(49/625 + (m-1) 361/50000, 1599/10000).
```

The scheduled low support is used only for subtracting the shell.  It is not
the inner coordinate.  The exact uncapped Definition-5 pencil is pinned by
`results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json` (SHA-256
`e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7`).

## Minimal count-15 forms

Let `H`, `L`, and `F` denote the high scheduled outer marginal, scheduled-low
outer marginal, and full inner marginal, respectively.  The count-15 shell
marginal is obtained on exactly two common-count rows:

- common `r=14`: retain `Ltotal,Lbig` on the outer side;
- common `r=15`: retain `Sdelta,Stotal` on the outer side.

The inner side retains every positive-measure branch.  With `X=H-L`, the
needed numerator entries are

```
B_0,15 = 48 * integral F X,
B_15,15 = 48 * integral X^2.
```

For each common count the implementation must separately reconstruct
`FH, FL, HH, HL, LL`.  For count-dependent amplitudes it must use

```
B_shell[R,S] = 48*(HH[R,S] + LL[R,S] - HL[R,S] - HL[S,R]),
```

not entrywise `HH+LL-2HL`.  The latter is valid only after summing every
entry against one uniform shell amplitude.

The denominator is diagonal by total count:

```
A_15,15 = integral_{H,total=15} F_outer^2
          - integral_{L,total=15} F_outer^2.
```

`A_00,B_00` are the exact inner entries in the pinned piecewise artifact and
equal the original exact certificate forms.  No natural-dilation inner form
may replace them.

## Branch and cost gate

For each `(r,h)` face, the unrestricted five-pair traversal considers up to
80 ordered branch pairs.  The selective count-15 traversal considers at most
28: two inner/outer pairs with `4*2` branch pairs each and three outer/outer
pairs with `2*2` each.  Empty intersections are rejected before orbit
contraction.  The staged evaluator carries 67 marginal rest orbits and 769
distinguished components, so actual polynomial contraction, not face count,
sets runtime.

Before launch, require:

1. the frozen source and dependency hashes to pass;
2. an independent same-support and distinct-kernel low-k replay;
3. output paths absent;
4. a one-face Decimal80 cost probe at `(r,h)=(14,0)` or `(15,0)`;
5. extrapolated `I_15` plus both J rows below four hours and peak RSS below
   512 MiB for one worker;
6. no simultaneous full all-tag traversal.

The completed Decimal80 outer-denominator diagnostic at total count 11 is
`results/bv_D16_volume_ramp_piecewise_D80_R11_cost_v1.json` (SHA-256
`d2846dac89b38bbdb00c8768e7c0c68d2059c1d8a1327b2810d17d3a6e61150f`).
It evaluated 561 grouped polynomials in 1575.8894349159673 seconds with peak
RSS 298284 KiB.  The scheduled high and low values were respectively

```
2.8281704208842098246140751889234299670084776267437824327556757979034977670853813e-152
2.8257452556376966339362908368450022891587362315582812841377140292949959359396572e-152
```

so their shell difference was
`2.4251652465131906777843520784276778497413951855011486179617686085018311457241e-155`.
This is 0.0008575032213776488 of the high count-11 mass and
0.0001317241564382349 of the uncapped outer denominator.  These ratios are
cost/mass diagnostics only; they neither determine a numerator contribution
nor justify omitting another count.

The staged driver has an independent discovery-stage formula audit:
`../audit/BV-D16-VOLUME-RAMP-CAPPED-STAGE-DRIVER-AUDIT.md` (SHA-256
`5db0a39a6207dbd089f142c104c42d1e6ac94c047eab6a81644a482a0cf4ee04`),
with checker SHA-256
`5cc5524bb21363d976ae1702632883569a02b8aec1e94bd1971d682ab7599141`.

The authorized one-face numerator cost probe is
`../small-delta-frontier/results/piecewise_d16_R15_r15_h0_cost_D80_v1.json`
(SHA-256
`16be6435f1deac122ef17b7d3e55fe7c69ff98b1678e171268266fdc76f339d4`).
It evaluated common `r=15,h=0` in 160.85425828606822 seconds with peak RSS
237692 KiB and 11 branch-domain integrals.  The directly formed scalar
combinations are

```
F*(H-L) = -9.2298991639854761748851737921373208323412681556906148e-159
(H-L)^2 =  8.1747200131116945544918285250225643407565903599949015e-159.
```

The second number is only 0.0017542271 of the largest separate `HH/HL/LL`
term, so this is explicitly a cancellation-sensitive cost probe, not sign
evidence for the complete common-count rows.  Subsequent mixing diagnostics
did not justify a full count-15 launch; the independent result audit is
`AUDIT FAIL` (report SHA-256
`aab0bdfced7711ba55a47b24deeff5d8d1ea0a2e0a151b305b9fbb81486dd63e`),
and found the count-15 local estimate 711.12 times its deterministic
Decimal80 calibration.  Every associated MCMC sign/ranking is withdrawn.
This selective line is therefore stopped after the promised one face.

A separate fused implementation forms the signed scalar shell before
integration (`code/bv_d16_r15_fused_scalar_probe.py`, SHA-256
`cddb8a40b2de3dbad940d8a16c499bb9e3a0ac036d3b797185e90f4dd90df7ce`).
Exact D4 tests agree with the literal five-form expansion on both common
rows.  On a fixed low-dimensional face it reduces 11 domain integrals to 6
and 15 nominal density lifts to 5 unique products; seven interleaved trials
gave a 1.45284x median wall speedup.  That timing is environment-specific
and was not extrapolated into another target launch.

The first finite decision is the exact/Decimal 2x2 span `{inner,R=15}`.  A
positive Decimal margin is only a discovery lead and must be rerun at a
second precision and then reconstructed exactly.  A negative result retires
only this two-coordinate span, not the entire count-tagged shell.
