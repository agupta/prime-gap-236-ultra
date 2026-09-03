# Exact audit of the published parameter point

Use distinct symbols

```text
eta = support enlargement = 3/400,
h   = Harman slack         = 1/10^10,
d   = delta                = 7/250,
A_0 = -eta,
A_1 = 253/1000,
w   = omega(1,1)=A_1-1/4  = 3/1000,
xi_1=19/50,
xi_2=xi_3=2/5.
```

There is one stratum. `floor(1/d)=35`, and

```text
B_1=B_2=3/20,
B_m=17/100 for 3<=m<=35.
```

The support prerequisites are strict where required:

```text
0<eta, d;
-eta=A_0<A_1<1/2-eta;
d<B_m;
B_m<=B_{m+1}<=B_m+d.
```

For zero large coordinates, set the explicit convention `B_0=0` or handle
the empty group outside Definition 2.

## Proposition 3 scalar conditions

All computations below are exact. The comparison shown is after including
the printed `h` correction.

| condition | limiting raw expression | margin |
|---|---:|---:|
| I, first branch | `xi_1-4A_1+2/3 = 13/375` | `(13/375-2h)-d = 99999997/15000000000 > 0` |
| I, second branch | `9/7-(34/7)A_1 = 199/3500` | larger than first branch |
| II, first line | `19/2-36A_1-13d+100h` | `2800001/100000000 > 0` |
| II, first min branch | `xi_2/10-(32/10)A_1+8/10 = 19/625` | larger than second branch |
| II, second min branch | `xi_2/4+11/16-3A_1 = 57/2000` | `(57/2000-2h)-d = 2499999/5000000000 > 0` |
| III | `11/8-(7/2)A_1-(9/8)xi_3 = 79/2000` | `(79/2000-2h)-d = 57499999/5000000000 > 0` |

The first Type II line is non-strict in the proposition; the two min branches
are also non-strict. Conditions I and III are strict. The point lies in the
strict interior anyway.

## Proposition 3 partition conditions A, B, C, E

Any tuple in `Xi(B_m,B_m',m,m',d)` has total sum at most

```text
B_m+B_m' <= 17/50 = 0.34.
```

At `w=3/1000`, the first-bin capacities are:

| branch | first-bin capacity | decimal |
|---|---:|---:|
| A (Type I) | `19/50-2h` | `0.3799999998` |
| B (Type IIa) | `2/5+(24/5)w+(7/5)d-2h` | `0.4535999998` |
| C (Type IIb) | `1/3+8w+(7/3)d-4h` | `0.422666666266...` |
| E (Type III) | `1-6w-(3/2)xi_3-2h` | `0.3819999998` |

All exceed `0.34`. Put every coordinate in the first bin and leave the other
bins empty. Their capacities are positive:

```text
A2 = 0.154666666466...,
B2 = 0.061142856942...,
C2 = 0.0403999996,
C3 = 0.047257142457...,
E2 = 0.1574999998.
```

The omitted high-`gamma` Type I condition derived at TeX lines 1524--1531 is
also immediate here: its first capacity is at least `1/2-2w-2h`, which exceeds
`0.4939>0.34`, and its empty second bin has positive capacity.

## Proposition 3(D): exact repaired verification

The printed quantifier is

```text
-h <= omega_0 <= w,
xi_2-h <= gamma <= 1/3+8w+(7/3)d+3h.
```

The four capacities are

```text
C1=gamma-2d-8omega_0-h,
C2=1/2-gamma-2omega_0-h,
C3=4omega_0+d-h,
C4=8omega_0.
```

Literal failure: at `omega_0=-h`, `C4=-8h<0`; even an empty fourth bin has
sum zero and cannot satisfy `0<=C4`. Thus the printed proposition cannot be
invoked literally.

Repair: split the moduli at `x^(1/2)`. A complete proof is in
`repaired-proposition3.md`: genuinely smaller moduli use the bilinear
Bombieri--Vinogradov theorem; the remaining moduli through the square root use
the paper's Type I/II/III cases with distribution parameter `omega=0`, for
which the Type IIc interval is empty. Apply the four-factor condition only on

```text
0 <= omega_0 <= w.
```

On this interval, `C3>=d-h>0`, `C4>=0`, and the worst first two capacities are

```text
C1 >= 2/5-h-2d-8w-h = 1599999999/5000000000
   = 0.3199999998,

C2 >= 1/2-[1/3+8w+(7/3)d+3h]-2w-h
   = 534999997/7500000000
   = 0.071333332933... .
```

Taking the Type IIc lemma's auxiliary threshold to be exactly `delta*=d`
is legitimate throughout this range.  At the worst endpoints its three
strict hypotheses have respective positive margins

```text
1-(8w+4d+2gamma_high) = 279999991/15000000000,
gamma_low-(32w+10d)   = 239999999/10000000000,
(-1)-(48w+16d-4gamma_low) = 19999999/2500000000.
```

This explicit choice avoids relying on the printed proof's directionally
ambiguous sentence about replacing `delta*` by a smaller `delta`.

It remains to partition continuously, without sampling.

- If both nonempty groups have size at most 2, total sum is at most `3/10`,
  so put everything in bin 1.
- If a group has size at least 3, that group's sum is at most `17/100`, so its
  smallest member is at most `17/300`. It is at least `d=7/250`. Put this one
  member in bin 2. Even if the total over both groups is the maximal `17/50`,
  the bin-1 remainder is at most
  `17/50-7/250=39/125=0.312<0.3199999998`, while bin 2 is at most
  `17/300<0.071333332933...`.
- If one group is empty, the nonempty group has total at most `17/100`; put it
  in bin 1.

Leave bins 3 and 4 empty. This proves (D) for every real tuple in every
nonempty `Xi`, including the `m=0` or `m'=0` cases omitted by the formal
Proposition 3 quantifier.

## Proposition 2 and Proposition 1

The five Harman inequalities have margins

```text
2-(2xi_1+3xi_2) = 1/25,
xi_3-xi_2       = 0       (formal condition is non-strict),
4-(xi_1+9xi_2)  = 1/50,
2xi_1+xi_2-1    = 4/25,
7-17xi_2        = 1/5.
```

At `xi_2=2/5`, the two subtracted sums defining `rho` are empty and both
displayed density integrals have zero domain/measure. Hence

```text
rho=1_P, c_1=0, c_2=0.
```

The remaining Proposition 1 hypotheses are then direct:

1. `0<=rho<=1_P`.
2. Equidistribution follows from the repaired Proposition 3 -> Proposition 2
   chain above.
3. If `rho(n;x)!=0`, then `n` is prime. Choose any fixed
   `beta in (17/100,1)`, for example `beta=1/5`; for `n in [x,2x]` and large
   `x`, its only prime factor `n` exceeds `x^beta`.
4. The prime number theorem gives
   `sum_{n in [x,2x]}rho(n;x)=(1+o(1))x/log x`.

Therefore, after explicitly supplying the three short source repairs (zero
indices, the high-`gamma` Type I condition, and the `omega_0>=0`/BV split),
the published analytic parameter point is valid for every fixed `k`, including
`k=48`. This does not supply the missing exact `k=48` integral certificate.

## Strict/non-strict endpoint ledger

- Definition 1: `A_0<...<A_n<1/2-varepsilon` and `delta<B`; adjacent `B`
  monotonicity and step-size inequalities are non-strict.
- Definition 1 support: total interval `[lower,upper)`; large-coordinate test
  `t_i>delta`; large-coordinate sum `<=B`.
- Definition 2: factor-product and total-product bounds are `<=`; large
  factors have logarithm `>=delta`; smooth primes are `<x^delta` by the
  paper's convention.
- Proposition 1: quotient `>1`, factor cutoff `beta>max B_{j,1}`.
- Section 3 distribution lemmas: all displayed admissible parameter
  inequalities are strict; TeX line 588 explicitly says uniformity requires
  fixed room to spare.
- Proposition 2: all five inequalities are strict except `xi_2<=xi_3`; the
  `c_2=0` branch includes `xi_2=2/5`.
- Proposition 3: scalar I and III use `>`; scalar II uses `>=`; all partition
  bin bounds use `<=`; the `omega_0` and `gamma` ranges are closed.
- Boundaries in `I,J,K` are measure-zero for polynomial certificates, so the
  `<` versus `<=` changes in the smoothing proof do not alter exact Lebesgue
  integrals. They must not be used to repair the negative-capacity endpoint,
  which is a universal partition assertion rather than an integral boundary.
