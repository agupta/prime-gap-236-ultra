# Specialized direct Heath--Brown equidistribution proposition

## Status

**SPECIALIZED ANALYTIC AUDIT PASS**, subject to using the exact Type II and
corrected Type III Section 3 lemmas as proved in the 2026 paper.  This route
does not invoke the flawed high-gamma Type I lemma, Definition 5's universal
Type I class, Proposition 2, or the Baker--Weingartner good-sifted-set
argument.

It supplies a direct candidate for all four analytic hypotheses on `rho` in
Proposition 1, for either the published support or the enlarged
`B_m=889/5000` support.

## Proposition

Put

```text
varepsilon = 3/400,
A_0 = -3/400,  A_1 = 253/1000,
delta = 7/250,
h = 10^-10,
B_0 = 0,
B_1=B_2=3/20,
B_m=889/5000  (3<=m<=35).
```

The same assertion holds if `889/5000` is replaced by the published
`17/100`.

For `n in [x,2x]`, define

```text
rho(n;x) = (log n/log(3x)) 1_P(n),
```

and set it to zero outside that interval.  Then, for every fixed
`varepsilon_0>0`, `C>0`, and integer `a` coprime to every prime at most `x`,

```text
sum_{q in Q*(x;...), q squarefree} |Delta(rho;a mod q)|
    <<_{C,varepsilon_0} x/log(x)^C.
```

Moreover `rho` satisfies all the other Proposition 1 hypotheses with
`c_1=c_2=0`:

```text
0 <= rho <= 1_P,
sum_{x<=n<=2x} rho(n;x) = (1+o(1))x/log x,
rho(n;x) != 0  => every prime factor of n exceeds x^beta
```

for, say, `beta=1/2>3/20`.

## 1. Heath--Brown decomposition with reserved slack

Use Polymath8a Section 3, local TeX
`sources/polymath8-edz-1402.0811-src/newergap.tex:1421--1589`, with
`K=10`.  Its Heath--Brown identity is exact on `[x,2x]`.  Its
finer-than-dyadic partition produces only `log(x)^O_C(1)` convolutions

```text
alpha_1 * ... * alpha_{2j},       1<=j<=10,
```

with scales `N_i`, and its Facts lemma (`:1637--1737`) proves:

- every sub-convolution is a coefficient sequence at the product scale;
- an individual factor at scale at least `x^(2 sigma)` is smooth;
- every sub-convolution at a fixed positive power scale is
  Siegel--Walfisz;
- the product of all scales is comparable to `x`.

Keep the outer indicator `1_[x,2x]` in the exact identity at
`:1521--1531`.  This avoids asking an interval estimate to control an
unstated full convolution.  The 2026 Type II and Type III lemmas are already
stated with this sharp outer interval.  The only additional interval version
needed below is bilinear Bombieri--Vinogradov for the genuinely small moduli;
it is justified in Section 5.

Alternatively, Polymath removes the sharp interval at the cost of an error in
two boundary intervals of total length `O(x log(x)^(-A_0))`; the detailed
Cauchy--Schwarz estimate at `:1600--1627` remains a cross-check.  For the
present `q<=x^(253/500)`, its summed discrepancy is
`x log(x)^(-A_0/2+O(1))`, uniformly in `a`.

For the combinatorial classification do **not** take the forbidden endpoint
`sigma=1/10`.  Put

```text
s = h/10,
sigma = 1/10+s.
```

Polymath's combinatorial Lemma (`:1305--1395`) applies because
`sigma>1/10`.  Its `K` condition is `1/K<2 sigma`, which holds for `K=10`.
It places every scale tuple into one of the following alternatives.

## 2. Type 0

There is an individual scale exponent at least

```text
1/2+sigma = 3/5+s.
```

That factor is smooth by the Facts lemma.  The direct Poisson argument at
Polymath8a TeX `:1780--1863` applies to **all** moduli up to

```text
Q <= x^(A_1+A_1) = x^(253/500) = x^(1/2+2(3/1000)).
```

With the outer interval retained, write the complementary convolution as
`alpha_S`.  For each `m`, the long smooth factor is restricted to the
intersection of its smooth support with `[x/m,2x/m]`; this has bounded
variation `log(x)^O(1)`.  Summation in residue classes and Möbius inversion
for the coprimality average give discrepancy
`tau(q)^O(1)log(x)^O(1)` for that one-variable sequence.  Since

```text
sum_m |alpha_S(m)| << N_S log(x)^O(1),
N_S << x^(2/5-s),
```

summing over every `q<=x^(253/500)` gives

```text
x^(2/5-s+253/500) log(x)^O(1)
  = x^(453/500-s) log(x)^O(1),
```

which is power-saving.  As a cross-check, if the cutoff is first removed,
the stronger Poisson calculation in Polymath gives

```text
x^(1-2 sigma+4(3/1000)) = x^(0.812-2s),
```

which is power-saving.  No factorization of the modulus and no
Siegel--Walfisz property for the complementary convolution are used.

## 3. Central aggregate alternative: only 2026 Type II

The combinatorial lemma supplies complementary aggregates with exponents in

```text
(1/2-sigma,1/2+sigma) = (2/5-s,3/5+s).
```

Both aggregates are Siegel--Walfisz by the Facts lemma, because each scale is
at least a fixed power of `x`.  Orient the smaller aggregate as the second
factor.  Its exponent `gamma` satisfies, for all sufficiently large `x`,

```text
2/5-h <= gamma <= 1/2.
```

Thus it is a 2026 Type II convolution.  This is the crucial point: no 2026
Type I estimate is needed.

### Small moduli

For

```text
q <= x^(1/2) log(x)^(-L),
```

the interval form of Polymath8a Theorem 2.9 applies, since the chosen second
aggregate is Siegel--Walfisz and has scale at least `x^(2/5-h)`.  Section 5
derives the required sharp-interval form from the printed theorem.

### Near-square-root strip

For

```text
x^(1/2)log(x)^(-L) < q <= x^(1/2),
```

use the 2026 Type II factorization lemmas with `omega=0`.  The Type IIc range
is empty even with the reserved `s`, since

```text
(2/5-s) - (1/3+(7/3)(7/250)+3h) > 0.
```

The IIa and IIb first-bin capacities at `omega=0` exceed
`2(889/5000)`, and every unused capacity is positive.  Put every large
support coordinate in the first bin.  Partition Lemmas 11 and 12 apply
because this strip lies above `x^(1/2-epsilon_1)` for large `x`.

### Above the square root

Dyadically split the remaining moduli and write the upper endpoint of a block
as `x^(1/2+2 omega_0)`, where

```text
0<=omega_0<=3/1000.
```

Use the paper's IIa, IIb, and IIc ranges with upper parameter
`omega=3/1000`.  Conditions B and C are satisfied by placing all support
coordinates in the first bin.  Condition D is the exact continuum two-bin
proof in `agents/independent-attack/support-889-proof.md`: uniformly in
`omega_0,gamma`, its lower capacities are

```text
C_1 >= 8/25-2h,
C_2 >= 107/1500-4h,
C_3 >= 7/250-h,
C_4 >= 0.
```

It covers every nonempty count pair and the empty `(0,0)` tuple.  Take the
IIc auxiliary width equal to `delta=7/250`; all three Section 3 distribution
inequalities are strict.  The IIa and IIb widths are strictly greater than
`delta` throughout their respective ranges.  Choose the Section 3 small
parameter much smaller than `h` to place all closed partition intervals
strictly inside the displayed distribution intervals.

## 4. Three-atom alternative: corrected 2026 Type III

The combinatorial lemma gives three individual factors with

```text
2 sigma <= t_i <= 1/2-sigma,
t_i+t_j >= 1/2+sigma.
```

They are smooth by the Facts lemma.  Set

```text
gamma_3 = 1/2-sigma = 2/5-s.
```

Then, with Vinogradov constants allowed as in the Section 3 lemma,

```text
N_i << x^gamma_3,
N_i N_j >> x^(1-gamma_3),
N_i >> x^(1-2 gamma_3).
```

For `omega` equal to `0` or `3/1000`, take

```text
delta_3(omega)
 = 1/2-(7/2)omega-(9/8)gamma_3-h.
```

Then

```text
4-(28omega+9gamma_3+8delta_3) = 8h > 0,
delta_3 > 7/250.
```

The factor interval in the stated Type III lemma is open.  Apply partition
Lemma 11 to the inward-shrunk interval `[a+h,b-h]`.  Its width remains at
least `7/250`, and both of its capacities are lowered by only `h`.  Exact
rational checks show that the first capacity still exceeds
`2(889/5000)` and the unused second capacity remains positive, for both
values of `omega`.  Hence all tuples, including every zero-count case, are
covered by putting all coordinates in the first bin.

For small moduli use interval bilinear Bombieri--Vinogradov by grouping two smooth
atoms and the residual coefficient sequence on one side and the third smooth
atom on the other.  For the near-square-root and above-square-root blocks use
the corrected Type III lemma and the factor just constructed.  This covers
all moduli.

## 5. Sharp-interval bilinear Bombieri--Vinogradov

The printed Polymath8a Theorem 2.9 estimates the discrepancy of the full
finitely supported convolution.  The following standard truncation gives the
version used here, with no unquantified boundary assumption.

For `y=x,2x`, apply truncated Perron inversion with height
`T=log(x)^D` to `1_(mn<=y)`.  On the main integral the two factors become

```text
alpha_t(m)=alpha(m)m^(-it),
beta_t(n)=beta(n)n^(-it).
```

They remain coefficient sequences at the same scales.  For an *arbitrary*
abstract sequence, the untruncated Siegel--Walfisz definition alone would not
automatically control these twists.  Here `beta` is a Heath--Brown
sub-aggregate.  Distribute the twist among its atomic factors:
`n^(-it)=prod n_i^(-it)`.  A smooth atom remains smooth, and a smoothly
localized Möbius atom remains Siegel--Walfisz uniformly for
`|t|<=log(x)^D` by the same Dirichlet-character argument and partial
summation used in the Facts lemma.  Its convolution-closure proof then gives
uniform Siegel--Walfisz for `beta_t`, at the cost of a fixed power of
`log x`.  Ask Theorem 2.9 for a correspondingly stronger initial logarithmic
saving.  The integral itself costs only another power of `log x`.

The Perron error is divided into multiplicative shells according to the
distance of `mn` from `x` or `2x`.  The innermost shell has total length
`H=O(x/T)`.  For a coefficient sequence bounded by a fixed divisor power,
the divisor-moment bound in progressions and Cauchy--Schwarz give, uniformly
in the primitive class,

```text
sum_{q<=x^(1/2)log(x)^(-L)}
  sum_{n in a boundary shell, n=a(q)} |c(n)|
 << x T^(-1/2) log(x)^O(1).
```

The coprimality-average part has the same bound using
`sum_{q<=Q}1/phi(q)<<log Q`; the outer shells form a geometric series.
Choose `D` after the desired saving.  This proves the sharp-interval form of
Theorem 2.9 used in Sections 3 and 4.  It is the usual Perron/finer-than-
dyadic “cosmetic surgery,” but the argument here records why both the
Siegel--Walfisz hypothesis and the total error remain uniform.

## 6. From Lambda to a genuine prime minorant

Let

```text
theta(n)=log(n) 1_P(n),
PP(n)=Lambda(n)-theta(n).
```

The preceding argument proves the required estimate for
`Lambda 1_[x,2x]`.  Prime powers are negligible uniformly in the residue
class.  Write `Q=x^(253/500)`.

For squares, a squarefree modulus `q` coprime to `a` has at most
`2^omega(q)` solutions of `z^2=a mod q`.  Therefore

```text
sum_{q<=Q} sum_{x<=p^2<=2x, p^2=a(q)} log p
 << log x (x^(1/2) sum_{q<=Q}2^omega(q)/q
            + sum_{q<=Q}2^omega(q))
 << x^(1/2)log(x)^3 + Q log(x)^2.
```

For powers `p^r`, `r>=3`, there are `O(x^(1/3))` possible pairs `(p,r)`.
The uniform trivial bound of at most `Q` moduli per pair gives

```text
O(Q x^(1/3) log x) = O(x^(1259/1500) log x).
```

For the averaged part of the discrepancy, the total prime-power mass is
`O(x^(1/2)log x)` and
`sum_{q<=Q}1/phi(q)<<log Q`.  Consequently

```text
sum_{q in Q*, q squarefree} |Delta(PP 1_[x,2x];a(q))|
  << x^(1259/1500) log(x)^O(1)
  = o(x/log(x)^C)
```

for every fixed `C`.  Hence the same equidistribution estimate holds for
`theta`, and division by `log(3x)` gives it for `rho`.

Finally, the prime number theorem gives

```text
sum rho = (theta(2x)-theta(x))/log(3x)
        = (1+o(1))x/log x.
```

Since `log n<log(3x)` on `[x,2x]`, `0<=rho<=1_P`; and a nonzero value is
supported on a prime `n>=x`, proving the roughness condition.

## 7. Exact checker

Run

```bash
python3 prime-gap-236/agents/hostile-analytic-audit/direct_hb_exact.py
```

It checks, with `Fraction`, the strict `sigma` endpoint, all containment
margins, emptiness of the near-square-root IIc range, every near-square-root
IIa/IIb bin capacity for the enlarged support, both corrected Type III
parameter choices and inward endpoint perturbations, the Type 0 power
saving, and the higher-prime-power power saving.  It must end with

```text
DIRECT HB EXACT MARGINS PASS
```

## Dependency conclusion

This proposition replaces the failed implication

```text
all f in broad H equidistribute  => Proposition 2 => rho=1_P
```

by the direct implication

```text
Heath--Brown terms
  => Type 0 or (SW,SW) Type II or smooth Type III
  => weighted-prime rho satisfies Proposition 1 directly.
```

The prior `AUDIT FAIL` remains the correct verdict on
`repaired-proposition3.md` as written.  It is not an obstruction to this
specialized direct route.
