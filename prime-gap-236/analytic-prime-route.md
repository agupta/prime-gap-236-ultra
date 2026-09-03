# Direct prime-equidistribution route (under hostile audit)

This note records a route that bypasses Proposition 2 and every Type I
estimate in arXiv:2608.31126v1.  It is **not yet an audited theorem**: the
remaining dependency is the repaired Type II/III modulus-factorization
argument described below.

## Fixed candidate parameters

Use

```text
k = 48
support epsilon = 3/400
A_0 = -3/400, A_1 = 253/1000
delta = 7/250
B_1 = B_2 = 3/20
B_m = 889/5000  (3 <= m <= 35)
xi_2 = xi_3 = 2/5
analytic h = 10^-10
```

Complete the undefined zero-index convention in Definition 3 by setting an
empty product equal to one and omitting its `B_{j,0}` inequality.  Equivalently
one may write `B_{j,0}=0` only for this vacuous condition.

For `n in [x,2x]`, define

```text
rho(n;x) = (log(n)/log(3x)) 1_P(n).
```

Then `0 <= rho <= 1_P`, a nonzero value has its only prime factor at least
`x`, and the prime number theorem gives

```text
sum_{x<=n<=2x} rho(n;x) = (1+o(1)) x/log(x).
```

Thus Proposition 1 has `c_1=c_2=0`, and its roughness hypothesis holds, for
example, with `beta=1/2>B_1`.

Every `q` in the completed `Q*` obeys, directly from Definition 3,

```text
q <= x^((1-epsilon_0)(A_1+A_1)) < x^(253/500) = x^0.506.
```

## Heath--Brown reduction without Harman's sieve

Apply the Heath--Brown identity and the finer-than-dyadic decomposition in
Section 3 of Polymath8a (arXiv:1402.0811v3), choosing `K=10` and
`sigma=1/10+s`, where for definiteness `s=h/10`.  (The strict inequality
`sigma>1/10` in Polymath8a Lemma 3.2 is essential.)  For each resulting convolution, write its scales as
`N_i=x^(t_i+o(1))`.  Polymath8a Lemma 3.3 gives exactly one of:

1. a smooth individual factor with `t_i>=3/5+s` (Type 0);
2. a subset and its complement with exponent sums in
   `(2/5-s,3/5+s)`;
3. three smooth individual factors with exponents in
   `[1/5+2s,2/5-s]` and every pair sum at least `3/5+s`.

Polymath8a Lemma 3.4 proves that every aggregate of total scale at least a
fixed positive power of `x` has the Siegel--Walfisz property.  Consequently
alternative 2 lies strictly inside the Type II class with `xi_2=2/5` after
swapping the two aggregates so that `gamma<=1/2`; alternative 3 is Type III
with distribution parameter `gamma_3=2/5-s`.  The gaps `s<h` and the fixed
analytic slack `h` absorb the finer-than-dyadic `o(1)` scale errors for
sufficiently large `x`.

Alternative 1 needs no result from the 2026 paper.  The Poisson-summation
argument at the end of Polymath8a Section 3 treats a smooth factor of length
at least `x^(3/5+s-o(1))` trivially for all `q<=x^0.506`; its power saving is
uniformly stronger than every requested logarithmic saving.

This reduction is the reason the missing Siegel--Walfisz hypothesis in the
2026 paper's high-`gamma` Type I swap does not lie on this route.  Nor does
the Baker--Weingartner/Harman `theta_0` branch in Proposition 2.

## Modulus split and exact support checks

For `q<=x^(1/2) log(x)^(-L)`, classical Bombieri--Vinogradov (or Polymath8a
Theorem 2.9 after grouping the displayed factors) is stronger than required.

For the remaining moduli, split into dyadic blocks.  Blocks at or below
`x^(1/2)` are treated with distribution parameter `omega_0=0`; blocks above
it have `0<=omega_0<=3/1000`.  The exact Type IIa, IIb, IIc and Type III
scalar and partition inequalities for the support above are proved in
`agents/independent-attack/support-889-proof.md` and checked by
`agents/independent-attack/verify_support_889.py`.  In particular:

- the total of all large coordinates is at most `889/2500`;
- the Type IIa and IIb first-bin capacities exceed that total;
- the Type III first-bin capacity, after restoring the lost `h` slack, also
  exceeds that total;
- the Type IIc four-bin continuum is reduced exactly to two bins, with a
  least-element argument covering every nonempty count pair, including one
  zero count;
- the empty count pair has all partition sums zero;
- for `omega_0=0` the Type IIc `gamma` interval is empty.

The impossible printed range `-h<=omega_0<0` is never used: small moduli are
handled first, and the above-square-root dyadic exponent is nonnegative.

## From Lambda to the minorant

The Heath--Brown argument proves the required discrepancy estimate for
`Lambda`.  On primes,

```text
rho(n;x) = Lambda(n)/log(3x).
```

The difference consists only of prime powers.  Summing their progression
terms over `q` and exchanging the order of summation costs
`sum_{p^r in [x,2x], r>=2} log(p) tau(p^r-a)=x^(1/2+o(1))`; the averaged
terms cost at most `x^(1/2) log(x)^O(1)`.  Both are negligible compared with
`x/log(x)^C` after the exponent `C` in the Lambda estimate is increased.
Division by `log(3x)` therefore gives Definition 4 for `rho`.

## Remaining audit obligation

Before this note can enter `PROOF.md`, an independent audit must check the
Type IIc `52h`/`100h` discrepancy in the statement and proof of the 2026
lemma, the uniform dyadic endpoint choices, and the repaired Type III slack.
No result in this note is used as a premise for a theorem claim until that
audit returns `AUDIT PASS`.
