# Exact support lemma: `B_m = 889/5000` for `m >= 3`

Status: exact verification of all numerical and partition hypotheses of
Propositions 2 and 3 **after** replacing the impossible printed Type-IIc range
`omega_0 in [-h,omega]` by `omega_0 in [0,omega]`.  The need for, and analytic
status of, that repair is recorded separately in `prop3-negative-omega.md`.
This file does not claim that the printed Proposition 3 has been satisfied.

## Parameters

Use exact rational values

```
epsilon_support = 3/400
h               = 1/10^10   (the paper's epsilon in Definitions 5 / Prop. 3)
A_0             = -3/400
A_1             = 253/1000
delta           = 7/250
xi_1            = 19/50
xi_2 = xi_3     = 2/5
B_1 = B_2       = 3/20
B_m             = 889/5000,  3 <= m <= floor(1/delta)=35.
```

Here `omega(1,1)=A_1-1/4=3/1000`.

## Definition 1 checks

We have

```
-epsilon_support = A_0 < A_1 = 253/1000 < 197/400
delta = 7/250 < B_1 = 3/20,
B_2-B_1 = 0,
B_3-B_2 = 139/5000 < 140/5000 = delta,
B_{m+1}-B_m = 0 for m >= 3.
```

Thus `delta < B_m <= B_{m+1} <= B_m+delta` throughout.  Also
`floor(1/delta)=35`.

For the natural extension of Xi to a zero count, put `B_0=0` and omit that
empty coordinate block.  If `m>=7`, then

```
m delta >= 7 delta = 49/250 = 0.196 > 889/5000,
```

so every `Xi(B_m,B_m',m,m',delta)` with such a count is empty.  Consequently
only counts `0 <= m,m' <= 6`, not both zero, need checking.

## Proposition 2 (Harman) scalar checks

All five inequalities are exact:

```
2 xi_1 + 3 xi_2 = 49/25 < 2,
xi_2 = xi_3,
xi_1 + 9 xi_2 = 199/50 < 4,
2 xi_1 + xi_2 = 29/25 > 1,
17 xi_2 = 34/5 < 7.
```

Since `xi_2=2/5`, Proposition 2's displayed definition gives
`rho=1_P`, `c_1=c_2=0`, and all nonzero values of rho have no prime factor
below `x^(1-2xi_2)=x^(1/5)`.  In particular `1/5>B_1=3/20`.

## Proposition 3 scalar conditions I--III

The two candidates in scalar condition I, before subtracting `2h`, are

```
xi_1 - 4 A_1 + 2/3 = 13/375,
9/7 - 34 A_1/7       = 199/3500.
```

The minimum is `13/375`, and

```
13/375 - 2h - delta = 1/150 - 2h > 0.
```

The first Type-II scalar expression is

```
19/2 - 36 A_1 - 13 delta + 100h = 7/250 + 100h > 0.
```

The two candidates in the second Type-II expression, before subtracting
`2h`, are

```
xi_2/10 - 32 A_1/10 + 8/10 = 19/625 = 0.0304,
xi_2/4 + 11/16 - 3 A_1      = 57/2000 = 0.0285.
```

Thus its margin over `delta` is `1/2000-2h>0`.  Finally the Type-III
left side before subtracting `2h` is `79/2000=0.0395`, so its margin over
`delta` is `23/2000-2h>0`.

## Partition conditions A, B, C, and E

For any nonempty Xi under consideration, its total sum is at most

```
2*(889/5000) = 889/2500 = 0.3556.
```

At `omega=3/1000`, the first-bin capacities in conditions A, B, C, and E
are respectively

```
A: 19/50 - 2h,
B: 567/1250 - 2h,
C: 317/750 - 4h,
E: 191/500 - (8/3)h.
```

For E we use the slightly smaller, proof-safe capacity obtained by taking the
Type-III lemma parameter `gamma_3=xi_3+h` and
`delta_3=1/2-(7/2)omega-(9/8)xi_3-2h`; this corrects the paper proof's lost
`h`-slack and is stronger than merely copying the displayed `-2h` capacity.

Each first capacity is strictly greater than `889/2500`.  Every unused-bin
capacity is nonnegative as well:

```
A_2 = 1/6 - 4 omega - 2h > 0,
B_2 = 1/14 - 24 omega/7 - 2h > 0,
C_2 = 1/10 - 34 omega/5 - 7 delta/5 - 4h > 0,
C_3 = 1/35 + 22 omega/35 + 21 delta/35 - 4h > 0,
E_2 = 5 omega/2 + 3 xi_3/8 - 2h > 0.
```

Assign every index to `I_1` and take every other part empty.  This proves A,
B, C, and E, including all zero-count cases.

## Type-IIc condition D on the repaired range

Let

```
0 <= omega_0 <= 3/1000,
2/5-h <= gamma <= 317/750+3h.
```

The four capacities in D are

```
C_1 = gamma - 2 delta - 8 omega_0 - h,
C_2 = 1/2 - gamma - 2 omega_0 - h,
C_3 = 4 omega_0 + delta - h,
C_4 = 8 omega_0.
```

Uniformly over this rectangle,

```
C_1 >= C := 8/25 - 2h,
C_2 >= D := 107/1500 - 4h,
C_3 > 0,
C_4 >= 0.
```

We construct only `I_1,I_2` and leave `I_3=I_4=empty`.

Write `T=sum y_i` and `L=max(0,T-C)`.  A subset put into `I_2` must have
sum in `[L,D]`; its complement then fits in `I_1`.

### One count is zero

Then `T<=889/5000<C`; put every index in `I_1`.

### Both nonzero counts are at most two

Then `T<=2*(3/20)=3/10<C`; again put every index in `I_1`.

### Exactly one count is at most two

The other count is at least three.  We have

```
T <= 3/20 + 889/5000 = 1639/5000,
L <= 39/5000 + 2h < delta.
```

Let `a` be the least entry in the block having at least three entries.  Then

```
delta <= a <= (889/5000)/3 = 889/15000 < D.
```

If `L=0`, put everything in `I_1`; otherwise put `a` in `I_2`.

### Both counts are at least three

Let `a,b` be the least entries of the two blocks.  Then

```
delta <= a,b <= 889/15000 < D,
L <= 2*(889/5000)-C = 89/2500+2h.
```

If `a>=L`, use `{a}` for `I_2`; if `b>=L`, use `{b}`.  In the remaining
case `a<L` and `b<L`.  Then

```
a+b >= 2 delta = 7/125 > 89/2500+2h >= L,
a+b < 2L <= 89/1250+4h < 107/1500-4h = D.
```

The final strict inequality has exact margin

```
107/1500 - 89/1250 - 8h = 1/7500 - 8h > 0.
```

Use `{a,b}` for `I_2`.  This completes every nonempty count pair.

Because the constructed sums obey the uniform lower capacities `C,D`, they
obey the actual `C_1,C_2`; the empty third and fourth parts obey their
nonnegative capacities on the repaired range.  Thus all continuum cases in D
are verified without sampling or rounding.

## Exact checker

Run

```
python3 verify_support_889.py
```

The checker uses Python `Fraction`, verifies every displayed scalar margin,
enumerates count pairs `0..35`, identifies empty Xi cases, and checks the
case-lemma inequalities above.  It does not silently change the printed
negative-omega range; that repair must be supplied analytically.
