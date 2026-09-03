# A proved baseline repair of Proposition 3

This is a specialized lemma for the published parameter point. It is not a
claim that Proposition 3 is correct in its full printed generality.

## Lemma (baseline equidistribution, with the square-root split)

Let

```text
varepsilon=3/400,  delta=7/250,
A_0=-varepsilon,  A_1=253/1000,
B_0=0,
B_1=B_2=3/20,
B_m=17/100 (3<=m<=35),
xi_1=19/50,  xi_2=xi_3=2/5,
epsilon=10^-10.
```

Here `B_0=0` is an explicit empty-product convention repairing Definition 2.
For every convolution `f` in `H(xi_1,xi_2,xi_3)`, every fixed
`varepsilon_0>0`, every fixed `C>0`, and every integer `a` coprime to every
prime at most `x`,

```text
sum_{q in Q*(x;...), q squarefree} |Delta(f;a mod q)|
  <<_{C,varepsilon_0,f} x/log(x)^C.
```

Consequently the equidistribution hypothesis in Proposition 2 holds at the
published point. The argument uses only the distribution lemmas stated and
proved in Sections 3--4 of the paper plus the bilinear Bombieri--Vinogradov
theorem quoted below.

## Proof

It suffices to fix `j=j'=1` and `0<=m,m'<=35`; there are finitely many such
choices. Write

```text
w=A_1-1/4=3/1000.
```

Every modulus in this component is at most
`x^((1-varepsilon_0)2A_1)<x^(1/2+2w)`.

### 1. The genuinely small moduli

Polymath8a Theorem 2.9 (arXiv:1402.0811v3, printed page 11; local extracted
text lines 550--562) says: if `alpha,beta` are coefficient sequences at scales
`M,N`, `MN asymp x`, `N>=x^c` for fixed `c>0`, and `beta` has the
Siegel--Walfisz property, then for every target log saving there is `L>0`
such that

```text
sum_{q<=x^(1/2)log(x)^(-L)} sup_{primitive a(q)}
  |Delta(alpha*beta;a(q))| << x/log(x)^C.
```

It applies to every member of `H`:

- Type I: use its displayed `alpha*beta`; `beta` is smooth, hence
  Siegel--Walfisz (compare Polymath8a Lemma 3.4(iii), printed pages 19--20),
  and `N>=x^(19/50-epsilon)`.
- Type II: use its displayed `alpha*beta`; `beta` is Siegel--Walfisz and
  `N>=x^(2/5-epsilon)`.
- Type III: group `alpha*psi_1*psi_2` into one coefficient sequence and take
  `beta=psi_3`. Dirichlet convolution preserves the required divisor bound
  and scale localization (split the fixed-width product support into a fixed
  number of dyadic pieces if desired); `psi_3` is smooth and
  `N_3>=x^(1-2xi_3-epsilon)=x^(1/5-epsilon)`.

Thus the desired sum over
`q<=x^(1/2)log(x)^(-L)` follows from a theorem stronger than needed (it sums
over all moduli and takes a supremum over primitive residue classes).

### 2. The remaining moduli at or below the square root

For large `x`, every

```text
x^(1/2)log(x)^(-L) < q <= x^(1/2)
```

also satisfies the lower-size premise `q>x^(1/2-epsilon_1)` in partition
Lemmas 11 and 12, for any fixed sufficiently small `epsilon_1>0`. Rerun Cases I,
II, III in the proof of Proposition 3 with distribution parameter `omega=0`
rather than `w`.

For Type I with `gamma<=1/2`, the paper's choice becomes

```text
delta*(gamma)=gamma-1/3-epsilon.
```

At the smallest allowed `gamma=19/50-epsilon`,
`delta*>=7/150-2epsilon>delta`. The two-bin partition has first capacity
`xi_1-2epsilon>0.3799>0.34`, so all coordinates go in it. For the short branch
`1/2<gamma<=1/2+epsilon'`, the extra condition derived at TeX
`1524--1531` has first capacity `1/2-2epsilon>0.49>0.34`; for larger `gamma`,
the third branch of Baker--Irving Type I imposes no factorization condition.

For Type II, by symmetry take `gamma<=1/2`. At `omega=0`, the IIa/IIb
transition values are

```text
g_a=2/5+(7/5)delta+2epsilon,
g_c=1/3+(7/3)delta+3epsilon.
```

Crucially,

```text
(xi_2-epsilon)-g_c = 1/750-4epsilon > 0.
```

Therefore the nominal Type IIc range
`xi_2-epsilon<=gamma<=g_c` is empty. For `gamma>=g_a`, Type IIa applies and
its first-bin capacity at `omega=0` is

```text
2/5+(7/5)delta-2epsilon > 0.4391>0.34.
```

For `xi_2-epsilon<=gamma<g_a`, Type IIb applies and its first-bin capacity is

```text
1/3+(7/3)delta-4epsilon > 0.3986>0.34.
```

Put all coordinates in the first bin in either case. The unused Type IIa and
IIb bin capacities are positive. The scalar strict inequalities of the
corresponding distribution lemmas hold with room because their chosen
`delta*` is strictly larger than `delta`; these are the same algebraic checks
at TeX `1543--1623` with `omega=0`.

For Type III, take

```text
delta*=1/2-(9/8)xi_3-epsilon=1/20-epsilon>delta.
```

The Type III distribution inequality is strict, and the first partition bin
has capacity `1-(3/2)xi_3-2epsilon>0.3999>0.34`. Again put all coordinates in
that bin.

Partition Lemmas 11 and 12 now provide exactly the factors required by the
Section 3 Type I, IIa, IIb, and III distribution sets. Together with Step 1,
this proves the desired estimate for every `q<=x^(1/2)`. Notice that no
negative `omega_0` and no Type IIc four-factor partition has been used.

### 3. Moduli above the square root

Dyadically split `x^(1/2)<q<=x^(1/2+2w)`. Each block has an exponent
`omega_0` with

```text
0<=omega_0<=w
```

up to the harmless strict shrinkage already present in `Q*`. Run the proof of
Proposition 3 with its original upper parameter `w`. The exact scalar checks
and partitions A, B, C, and E are in `parameter-audit.md`. The omitted
high-`gamma` Type I partition also holds by placing everything in its first
bin.

For the Type IIc range, use the exact continuous four-bin argument from
`parameter-audit.md`. Uniformly for `0<=omega_0<=w` and every allowed
`gamma`, the first two capacities are at least

```text
0.3199999998 and 0.071333332933...,
```

while the last two are nonnegative. If either group has at least three
members, put its least member (between `delta` and `17/300`) in bin 2 and all
remaining members in bin 1; otherwise put everything in bin 1. The first-bin
sum is at most `0.312` in the former case and at most `0.30` in the latter.
Bins 3 and 4 are empty. Partition Lemma 13 then supplies the Type IIc
factorization. In the Type IIc distribution lemma choose its auxiliary
`delta*` equal to the original `delta`; the exact scalar margins in
`parameter-audit.md` put this choice strictly inside all three distribution
inequalities. Thus the four displayed capacities are the actual capacities,
not a favorable relaxation obtained by replacing a larger `delta*` by
`delta`.

The strict margins permit one fixed sufficiently small distribution slack
`epsilon'` uniformly over the compact `omega_0,gamma` ranges, exactly as
explained at TeX line 588. Summing the finitely/logarithmically many dyadic
pieces preserves an arbitrary log saving by initially increasing `C`.

### 4. Zero-index cases

If exactly one of `m,m'` is zero, the tuple total is at most `17/100`, so every
partition above works with everything in its first bin. If both are zero, the
tuple is empty and all partition sums are zero; every used capacity is
nonnegative. The elementary proofs of partition Lemmas 11--13 explicitly allow
`m_1,m_2 in N union {0}`, so their factor-extraction arguments apply after the
stated `B_0=0` convention. This closes the cases omitted by the formal
quantifier in printed Proposition 3. QED.

## Status of this repair

The lemma above is proved from explicit primary statements and the exact
baseline inequalities. It is the repair that may safely be imported into a
new proof.

What remains only a plausible editorial diagnosis is *why* the paper printed
`omega_0 in [-epsilon,w]`: presumably the author intended the square-root
split above and used a tiny negative endpoint as dyadic slack. That historical
intent is not needed for the repaired lemma and is not asserted as fact.
