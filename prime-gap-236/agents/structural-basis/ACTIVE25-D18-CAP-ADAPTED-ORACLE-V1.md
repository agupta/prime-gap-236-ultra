# Active25 refined-D18 cap-adapted package v1

## Outcome

The exact cross identity points to a qualitatively different outer coordinate
from radial cap-slack powers.  For a fixed symmetric inner polynomial `F`, put

```text
m_F(x) = 1_(sum(x)<=eta_UV) integral_0^(alpha1-sum(x)) F(x,u) du,
G_F(t) = sum_(i=1)^48 m_F(t with coordinate i removed).
```

Then, with the same orientation used by the exact `48J` matrices,

```text
48 J(F,H) = integral_outer H(t) G_F(t) dt.
```

Thus `G_F` restricted to a legal cap is the exact I-Riesz representer of the
cross functional on that cap, and

```text
I(G_F 1_cap) = 48 J(F,G_F 1_cap).
```

The identity is checked by a literal exact `k=2` oracle.  Exact conditional
simplex-volume oracles separately check the capped importance weights.

For the exactly verified two-outer-band support, however, calibrated D18
sampling estimates even the *sum of the two positive I energies* below the
one-band sufficient threshold.  Consequently each band separately falls
below that threshold, and the expensive exact natural-D18 certificate target
is disabled.  This is a strong heuristic negative for either natural-D18
band coordinate, not a rigorous upper bound on cap-adapted functions or D20.

## Frozen geometry

The common values are

```text
k=48, delta=1/60, alpha1=103/400,
alpha2=237991/900000, radial boundary=263741/1000000.
```

The lower outer band uses

```text
eta_UV=248741/1000000,
B1..B12=(139683,156347,157797,173014,180929,183753,
         186776,188864,190396,191607,192583,199985)/1000000,
```

and the upper outer band uses

```text
eta_UV=224491/900000,
B1..B12=(138360,155020,158662,171688,177684,180588,
         183402,185486,187011,188221,189137,189137)/1000000.
```

Both schedules plateau after count 12 and have active counts `0,...,11`.
The exact analytic checker/result are pinned by the package.

## Numerical coordinates and samplers

The discovery oracle keeps the old refined-D18 coordinate explicitly.  Its
15-coordinate inventory is

```text
old inner D18,
cap-restricted Riesz D18,
natural outer D18,
two cap-slack transports at each count R=9,...,14.
```

The initial direct cap proposal is exactly unbiased for ordinary integrands:
large excesses are sampled on their conditional simplex, small coordinates on
the remaining simplex, and the variable volume is included in the weight.
It reproduces exact count-stratum volumes.  It nevertheless misses the narrow
high-degree D18 peaks and underestimates Riesz energy by 27--37 reported
standard errors.  Its apparent negative results are superseded, not erased.

The authoritative discovery screen instead targets the square of the natural
outer D18 polynomial on the full shell.  If `h` is that polynomial and
`r=G_F/h` in common polynomial scaling, then the exact natural contraction
gives

```text
I(G_F)/I(F) = (A11/A00) E_(h^2)[r^2],
E_(h^2)[r_top_eta] = B01/A11.
```

The second equation is a mandatory exact cross-moment calibration.  Shape
moves are complemented by an exact volume-radial independence proposal: hold
`t/sum(t)` fixed, draw `sum(t)` with density proportional to
`sum(t)^47`, and accept with ratio `h(new)^2/h(old)^2`.  The run fails closed
on shape, radial-total, or radial-band mixing, or on the exact cross check.

## Frozen two-band screen

Each final run has eight chains, burn 4000, 6000 retained draws per chain,
one worker, and a 512 MiB address-space cap.

| seed | uncapped `I(G)/I(F)` | capped `I(G)/I(F)` | retention |
|---:|---:|---:|---:|
| 2361817 | 0.0160016302 +/- 0.0001080700 | 0.0135229961 +/- 0.0001444021 | 0.8453381 |
| 2361818 | 0.0158405345 +/- 0.0000755680 | 0.0136261981 +/- 0.0001202101 | 0.8602820 |

The naive inverse-variance combination is

```text
0.01358395408 +/- 0.00009238724.
```

The exact *single-band* sufficient threshold from the inner D18 quotient is
`0.014649159149822788`; the summed I-energy diagnostic is lower by
`0.00106520507`, or 11.53 naive Monte Carlo standard errors.  The sum is used
only as a conservative scale comparison: it is not a multiband certificate.
These error bars diagnose the two finite runs and are not rigorous confidence
bounds.

Bandwise capped estimates were

| seed | lower outer | upper outer |
|---:|---:|---:|
| 2361817 | 0.0124186123 +/- 0.0001289301 | 0.0011043838 +/- 0.0000389612 |
| 2361818 | 0.0125032129 +/- 0.0001419819 | 0.0011229852 +/- 0.0000386530 |

Both final runs have split R-hat at most `1.00285` for `r` and `r^2`, at most
`1.00129` for radial total, and at most `1.00081` for the upper-band
indicator.  Every chain visits both bands.  Relative errors in the exact
cross-moment calibration are `0.00550` and `0.000368`.

An earlier seed-2361817 run with burn 1000 is retained in the failure ledger:
two shape chains had not equilibrated and split R-hat reached `1.5124`.  It is
not used in the final estimate, and the seed was not changed.

## Minimal exact certificate target

The disabled exact plan defines two separate two-coordinate tests

```text
(F,H_lower) and (F,H_upper),
```

where each `H_j` is the one natural dilation of `F`, restricted to the
corresponding band and count schedule.  It would reconstruct only

```text
A_j=I(H_j),  b_j=48J(F,H_j).
```

For each band separately, the same-band Definition-5 marginal square gives
`J(H_j,H_j)>=0`.  Exact positivity of either separate expression

```text
b_j^2/A_j - (I(F)-48J(F,F))
```

would therefore suffice.  The two energies must not be summed: disjoint I
support does not imply positivity of the cross-band J kernel.  Indeed, at a
rest sum between two band cutoffs the two-band cutoff kernel can be
`[[0,1],[1,1]]`, whose smaller eigenvalue is `(1-sqrt(5))/2<0`.  A combined
multiband test needs the exact outer `48J` block or an independent special
sign proof.  Neither is part of this per-band target.  No eigensolve,
monotonicity argument, or `limit_denominator` vector is used.

For `H^2=sum c_(p,nu)(1-sum(t))^p m_nu(t)`, the exact denominator is staged by
band, active count `R`, and consecutive square-orbit group:

```text
A_j = sum_R sum_(p,nu) c_(p,nu)
      [M(alpha_high,B_j;p,nu,R)-M(alpha_low,B_j;p,nu,R)].
```

For the cross, the inner marginal uses the direct full-simplex fiber.  The
outer distinguished coordinate is split into the literal `Sdelta`, `Stotal`,
`Ltotal`, and `Lbig` branches.  Each immutable slice is indexed by band,
endpoint, common large count `r` among the 47 shared variables, translated
small-face count `h`, outer branch, and a consecutive right-marginal-orbit
range.  The assembler takes endpoint-high minus endpoint-low and applies the
factor 48 exactly once.  A low-k exact test shows that summing these slices is
identical to the canonical cross recurrence.

The proposed fresh-record driver is externally bound, abandons a partial
record after any failure, supports no resume, and requires independent exact
reconstruction before consumption.  This producer is not exposed in v1.

## Measured exact cost

The bounded exact probe ran in 67.82 seconds at 76,928 KiB RSS.  Reconstructing
and squaring the 471-term polynomial took 9.78 seconds.  Eight of 10,761 exact
square-orbit groups for lower-band count 11 took 3.38 seconds.  A simple linear
projection for all current A slices is about 30.3 hours.

One exact full-left cross slice against one of 97 right marginal orbits on the
fixed `(r,h,branch)=(10,4,Sdelta)` face took 54.66 seconds.  Linear projection
is about 5,302 seconds for that single face/branch and about 2,687 hours over
the maximum enumerated band/endpoint/face/branch inventory.  The latter is a
deliberately rough scale signal; grouping and heterogeneous faces can change
it substantially.  It is not a runtime bound.  The measured scale and the
negative D18 screen jointly forbid launching the present exact target.

## D20 and multiband gate

The exact formulas are degree-generic and the full-simplex inner support is
unchanged at `delta=1/60`.  A D20 substitution must bind all 707 labels and an
externally frozen vector.  It may use a refined exact vector or a Decimal100
vector placed on one common rational grid with at least 40 decimal digits.  A
`limit_denominator` vector is explicitly forbidden.  No D20 artifact is bound
in this package.

A future exactly verified multiband support can use one Riesz representer and
one cap schedule per disjoint radial band for numerical retention diagnostics.
Its bridge and exact plan must pin the new analytic checker/result and use the
band-specific `eta_UV`.  The theorem-facing consumer must either test one band
at a time or reconstruct the outer `48J` block/prove a special sign property;
it may never infer J-positivity from disjoint I support.  This v1 package does
not silently accept new geometry.

## Frozen files

```text
cap/Riesz core source     7258643c15d5ca26a1025ead96f8a6d2a6a9170e639913d2d272007b51e19840
cap/Riesz core tests      4c29a64db01e4be1e9c7294f15e1ede1c69105668a22a0b7e97c6cc2496b3c4c
verified wrapper source   d134832dbce0215e2e7b6d1fa70d71c4e855f7fdc1625b6a906182beef5f697e
verified wrapper tests    20d17515901b05ae5df94bad9ed945edc9f5a95de7847dbf805b643af485346a
h^2 bridge source         2d262e1ea4a1ea20f42ea03cb8c8bc6405ae75b8f94cc1db668dfeb0797dfe1b
h^2 bridge tests          05fdb84fd8be499b9d3d93a0958ea49d81e2278466a3fb1c6b640f77365d632b
seed 2361817 bridge        77f1975ae8e2326aa01816c10698921a5644a133a2286e6c5c5db65cfb4f2f3e
seed 2361818 bridge        4b7cfb8d3a71fe075f50134093347fe176c71517d98d5b8db624049d9be3d9c1
exact-plan source         a462d1e775c0d1b3a5caefc32b9b37dcfa94c4aae3bd8c4d3e33f850605e126a
exact-plan tests          3e3f8b12a627f997a191a811e639b250e0fff298c087de919669458590294031
exact cost probe          b7f1864c45934579fd89f1d6b4aeb2786530b55560b286473a602faf9ee9c273
failure ledger            5dae0400a6d79e330d5664d5ad6c7b84d309d87cba9fa1103eb3e28374d492f9
```

All numerical and exact-plan tests pass both normally and with `python3 -O`.
Every artifact states `launch_authorized=false`; no theorem or bounded-gap
claim is made.
