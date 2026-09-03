# C10 candidate: exact analytic Proposition 1 dossier

## Status and scope

This is the candidate-ready analytic half of the C10 calculation.  It proves
all four hypotheses of Stadlmann's Proposition 1 for a weighted prime
minorant, conditional only on the Section 3 Type-II and corrected Type-III
distribution lemmas already audited in
`../hostile-analytic-audit/direct-hb-prime-equidistribution.md`.  It does not
assert that the capped finite-dimensional quotient is greater than one; that
is a separate exact computation.

The direct Heath--Brown route is essential.  It does not use Proposition 2,
the paper's false negative-`omega_0` endpoint, or the unproved high-`gamma`
Type-I role swap.  The baseline version of this route has already received
`SPECIALIZED ANALYTIC AUDIT PASS`.  The new work here is the complete C10
parameter substitution and continuum partition proof.

## 1. Exact data and Definition 1

Use one stratum and

```text
k = 48,                    varepsilon = 1/200,
A_0 = -1/200,              A_1 = 77747/300000,
delta = 1/100,
B_1=B_2 = 3/20,
B_m = 97/625  for every 3<=m<=100=floor(1/delta).
```

The same data are in `c10-support.json`.  They satisfy Definition 1 exactly:

```text
A_1-A_0                  = 79247/300000 > 0,
1/2-varepsilon-A_1       = 70753/300000 > 0,
B_1-delta                = 7/50 > 0,
B_m-delta (m>=3)         = 363/2500 > 0,
B_3-B_2                  = 13/2500,
B_2+delta-B_3            = 3/625,
```

and every other `B` transition is equality on the lower side and has upper
slack `1/100`.  Since

```text
15 delta = 3/20 <= 97/625 < 4/25 = 16 delta,
```

the strata with 16 or more large coordinates are empty.  Thus the finite
schedule through count 100 is proved even though the continuum checker only
needs to enumerate counts 0 through 15 and explicitly test count 16 as the
first empty count.

Write

```text
h=10^-10,  s=h/10,  sigma=1/10+s,
omega=A_1-1/4=2747/300000,  xi=2/5.
```

The relevant-modulus definition gives, uniformly in its shrink parameter
`varepsilon_0`,

```text
q <= x^((1-varepsilon_0)((A_1-varepsilon)+(A_1+varepsilon)))
  <= x^(2A_1),
2A_1 = 77747/150000 = 1/2+2omega.
```

Notice that the support enlargement cancels exactly in this exponent.

## 2. The minorant and Proposition 1 hypotheses (1), (3), and (4)

For `n in [x,2x]`, put

```text
rho(n;x) = (log n/log(3x)) 1_P(n),
```

and put `rho=0` outside that interval.  Take

```text
c_1=c_2=0,       beta=1/2.
```

For all sufficiently large `x`, `0<=log n/log(3x)<1` on `[x,2x]`.
Consequently

```text
-c_2=0 <= rho(n;x) <= 1_P(n),
```

which is hypothesis (1).  If `rho(n;x)` is nonzero, then `n` is a prime at
least `x`; its only prime factor exceeds `x^(1/2)`.  Since
`beta=1/2>B_1=3/20`, hypothesis (3) follows.  Finally the prime number
theorem gives

```text
sum_{x<=n<=2x} rho(n;x)
 = (theta(2x)-theta(x))/log(3x)
 = (1+o(1)) x/log x,
```

which is hypothesis (4) with `c_1=0`.

No unweighted-prime substitution is being made: this particular weighted
`rho` is the function whose equidistribution is proved next and whose
density occurs in the sieve criterion.

## 3. Hypothesis (2): direct equidistribution

We prove that for every fixed `varepsilon_0>0`, `C>0`, and residue `a`
coprime to every prime at most `x`,

```text
sum_{q in Q*(x), q squarefree} |Delta(rho;a mod q)|
   <<_{C,varepsilon_0} x/log(x)^C.                 (ED)
```

### 3.1 Exact Heath--Brown trichotomy

Apply the exact `K=10` Heath--Brown identity and the combinatorial lemma in
Polymath8a Section 3 (local source
`../../sources/polymath8-edz-1402.0811-src/newergap.tex`, especially the
identity at lines 1421--1589 and the scale facts at 1637--1737).  Keep the
outer indicator `[x,2x]`.  The forbidden endpoint is avoided because

```text
sigma-1/10       = 1/100000000000,
2sigma-1/K       = 5000000001/50000000000.
```

Every term lies in one of three alternatives.

1. **Type 0.**  One smooth atom has exponent at least `1/2+sigma`.
   Its complementary convolution has exponent at most `1/2-sigma`.
2. **Central aggregate.**  There are complementary Siegel--Walfisz
   aggregates with exponents in
   `(1/2-sigma,1/2+sigma)`.  Orient the smaller as the second factor, so its
   exponent is in `(2/5-s,1/2]`.
3. **Three atoms.**  Three smooth atoms have individual exponents between
   `2sigma` and `1/2-sigma` and pair sums at least `1/2+sigma`.

The exact containments in the 2026 Type-II/III scale hypotheses have margins

```text
Type-II lower, upper             9/100000000000, 9/100000000000,
Type-III individual lower       3/25000000000,
Type-III individual upper       11/100000000000,
Type-III pair                    11/100000000000.
```

These are reconstructed by `verify_c10_prop1.py`.

### 3.2 Type 0

For a fixed complementary variable, summation of the long smooth atom in a
residue class, with the sharp interval retained, has discrepancy
`tau(q)^O(1) log(x)^O(1)`.  The complement has `l^1` norm at most
`x^(1/2-sigma) log(x)^O(1)`.  Summing over every `q<=x^(2A_1)` is therefore

```text
<< x^((1/2-sigma)+2A_1) log(x)^O(1).
```

The exact power saving from exponent one is

```text
24506000003/300000000000 > 0.
```

This step uses neither a factorization of `q` nor a Type-I distribution
theorem.

### 3.3 Central aggregate: small and near-square-root moduli

For

```text
q <= x^(1/2) log(x)^(-L),
```

the sharp-interval bilinear Bombieri--Vinogradov lemma proved and audited in
Sections 3 and 5 of
`../hostile-analytic-audit/direct-hb-prime-equidistribution.md` applies: the
second aggregate is Siegel--Walfisz and has exponent at least `2/5-s`.

In the remaining strip up to the square root, use the 2026 Type-II
factorization lemmas with `omega=0`.  The IIc range is empty with exact gap

```text
12999999907/300000000000 > 0.
```

For IIa and IIb, put every support coordinate in the first bin.  With
`2B=194/625`, the respective first-bin margins and unused capacities are

| branch | first minus `2B` | unused 2 | unused 3 |
|---|---:|---:|---:|
| IIa, `omega=0` | `517999999/5000000000` | `2499999993/35000000000` | -- |
| IIb, `omega=0` | `346999997/7500000000` | `214999999/2500000000` | `604999993/17500000000` |

All are strict.  The lower edge of this logarithmic strip exceeds the fixed
`x^(1/2-epsilon_1)` threshold in the factorization lemmas for all sufficiently
large `x`.

### 3.4 Central aggregate: moduli above the square root

Split dyadically and parameterize a block by
`q asy x^(1/2+2omega_0)`, where `0<=omega_0<=omega`.  The three scalar
Type-II margins are

```text
4036001/100000000,
10479997/15000000000,
149999/5000000000.
```

For IIa and IIb the worst endpoint is `omega`; put every coordinate in the
first bin.  The margins are

| branch | first minus `2B` | unused 2 | unused 3 |
|---|---:|---:|---:|
| IIa | `737759999/5000000000` | `1401199993/35000000000` | -- |
| IIb | `298799999/2500000000` | `178009997/7500000000` | `2117169979/52500000000` |

For IIc, throughout the complete closed rectangle in
`(omega_0,gamma)`, the first two capacities are at least

```text
C = 4601199997/15000000000,
D = 388249997/7500000000.
```

Leave bins 3 and 4 empty.  If the two coordinate-group counts are denoted by
`m,m'`, the following is a complete continuum partition proof.

- If one count is zero, the total is at most `B<C`; use empty bin 2.
- If both counts are at most two, the total is at most `2B_2<C`; again use
  empty bin 2.
- If exactly one count is at most two, the required bin-2 lower load is at
  most `B_2+B-C<delta`.  The other group has at least three entries, so its
  least entry lies in `[delta,B/3]` and fits bin 2.
- If both counts are at least three, take the least entry of each group.  If
  either alone reaches the required lower load, use it.  Otherwise their sum
  reaches that load, is below twice its maximum, and fits bin 2.

Every assertion is strict by the six exact margins

```text
C-B                         = 2273199997/15000000000,
C-2B_2                      = 101199997/15000000000,
delta-(B_2+B-C)             = 173199997/15000000000,
D-B/3                       = 249997/7500000000,
2delta-(2B-C)               = 245199997/15000000000,
D-2(2B-C)                   = 55574999/1250000000.
```

This includes both zero-count branches and every point of every
`Xi(B_m,B_m',m,m',delta)`, not merely vertices or samples.  The exact
interval-cover checker independently reconstructs partitions for all 135
nonempty unordered count pairs.

### 3.5 Three smooth atoms: corrected Type III

Set

```text
gamma_3 = 1/2-sigma,
delta_3(omega_*) = 1/2-(7/2)omega_*-(9/8)gamma_3-h.
```

Use `omega_*=0` in the square-root strip and the worst endpoint
`omega_*=omega` above it.  Shrink both endpoints of the open factor interval
inward by `h`.  The remaining width above `delta` is respectively

```text
19083999307/2400000000000  (omega_*=omega),
31999999769/800000000000   (omega_*=0),
```

and the Section 3 distribution margin is `1/1250000000` in both cases.
Put all coordinates in the first bin.  The first-bin and unused-bin margins
are

| endpoint | first minus `2B` | unused second |
|---|---:|---:|
| `omega` | `20795999869/600000000000` | `138313333277/800000000000` |
| `0` | `53759999869/600000000000` | `359999999831/2400000000000` |

For smaller moduli, group two atoms and the residual sequence on one side
and the third smooth atom on the Siegel--Walfisz side of bilinear
Bombieri--Vinogradov.  Thus every three-atom term is covered.

The strict rational margins above allow the auxiliary small parameter in
the open Section 3 distribution intervals to be chosen uniformly smaller
than the minimum margin; no boundary is reached.

### 3.6 From `Lambda` to `rho`

The preceding cases give (ED) with `Lambda 1_[x,2x]` in place of `rho`, with
an arbitrarily large logarithmic saving.  Write

```text
theta(n)=log(n)1_P(n),       PP(n)=Lambda(n)-theta(n),
Q=x^(2A_1).
```

For squares, a squarefree `q` has at most `2^omega(q)` square roots of the
fixed reduced residue, giving total discrepancy

```text
<< x^(1/2)log(x)^3 + Q log(x)^2.
```

For powers of exponent at least three, the trivial bound gives

```text
<< Q x^(1/3) log x
 = x^(127747/150000) log x.
```

The exact exponent saving is

```text
1-127747/150000 = 22253/150000 > 0.
```

The coprimality-average term is smaller, using total prime-power mass
`O(x^(1/2)log x)` and `sum_{q<=Q}1/phi(q)<<log Q`.  Hence prime powers are
power-saving after summing over the larger set of all `q<=Q`, and (ED) holds
for `theta`.  Division by `log(3x)` proves (ED) for `rho`, establishing
Proposition 1 hypothesis (2).

## 4. Exact reproduction

The closed-form checker reconstructs Definition 1, all 100 `B_m`, every
Heath--Brown containment, the Type-0 and prime-power exponents, all scalar
faces, both `omega=0` branches, corrected Type III, the IIc lemma, and the
`c_1,c_2,beta` bookkeeping:

```bash
cd prime-gap-236/agents/independent-attack
python3 verify_c10_prop1.py
```

It must end with

```text
C10 PROP1 EXACT MARGINS PASS
```

The independent checker does not use the six-inequality proof.  It covers
the continuous `Xi` polytopes with rational boxes and reconstructs a bin
assignment in every leaf:

```bash
python3 verify_c10_box.py
```

It must end with

```text
DIRECT-HB EXACT SUPPORT COVER PASS pairs 135 nodes 2565
```

Current SHA-256 fingerprints are

```text
7681e1b75b02b1218a16bf9a4abd8abe5113a5fd38af028b02b1b7184eb2ecc7  verify_c10_prop1.py
34d0b87f427ddd082e1c6732784f91827dcb3c245e87f9a11b3006682b654e1d  verify_c10_box.py
cae956e38ae65230f333e49ddea934612c89c372d8c32f6437547781bdf2169b  code/verify_direct_hb_support.py
d120c5fac080d494b4876c7186f51123bba66bee5d9a04ec4d7ea79420fac564  code/interval_partition_verify.py
5345a6c43432facbed1f2c8302543fb3a11b7ab19ba145c9d485ac07381bbd5b  c10-support.json
```

## 5. Fresh-audit boundary

The baseline hostile audit already covers the structural analytic steps:
the exact Heath--Brown decomposition, avoidance of high-`gamma` Type I,
sharp-interval bilinear Bombieri--Vinogradov, corrected Type III, the
square-root split, prime-power removal, and passage to the weighted prime
minorant.  Those arguments are parameter-uniform once the displayed strict
margins hold.

The one analytic item not yet independently hostile-audited is this C10
parameter substitution itself: larger `omega`, smaller `delta`, the new
finite `B_m` schedule, and the resulting Type-0/prime-power exponents.  It is
checked by two independent exact programs above but should receive a fresh
adversarial read before final use.  Separately, the capped exact quotient,
its reconstruction checker, and the admissible 48-tuple remain outside this
analytic dossier.
