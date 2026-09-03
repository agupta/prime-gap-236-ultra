# General minorant: an exact `K=0` sliver and its theorem blockers

Date: 2026-09-02  
Status: **GEOMETRIC AUDIT PASS; NOT A SIEVE RESULT**

This note answers a narrow structural question.  A nonzero-minorant parameter
point can have a nontrivial symmetric finite-basis subspace on which the
repaired `K` form vanishes identically, while the associated `J` fibers
strictly exceed the audited C10 fibers.  Thus the large constant-function
`K` penalty in `GENERAL-MINORANT-K-REPAIR.md` is not a geometric no-go theorem.

The construction is not currently theorem-usable.  The universal
equidistribution chain has the already identified high-`gamma` Type-I
Siegel--Walfisz gap, and the general signed `c2>0` form of Proposition 1 has
not received the repairs/audit proved only for `c2=0`.  Nothing below proves
`H_1 <= 236`.

## 1. Pinned source and the sign of `K`

The source is

```text
sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex
SHA-256 c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba
```

Relevant locations are Definition 1 at lines 140--147, Definition 5 at
210--217, Proposition 1 at 228--242 and its bilinear forms at 297--306,
Proposition 2 at 1118--1163, and Proposition 3 at 1397--1448.

Definition 5's displayed `K` is syntactically malformed.  The proof defines

\[
 K_i(F,G;C)=\int_{\sum_{s\ne i}t_s>C}F(t)G(t)\,dt.
\]

The disjoint stratum decomposition therefore reconstructs, for a one-stratum
support with `eta=A-epsilon`,

\[
 K_i(F)=\int_{\sum_{s\ne i}t_s>\eta}F(t)^2\,dt.                 \tag{1}
\]

This is nonnegative and occurs in Proposition 1 with the adverse sign
`-k c2 K`.  The repair is derived in
`../structural-basis/GENERAL-MINORANT-K-REPAIR.md`; it remains a source-text
repair rather than a corrected published definition.

## 2. Exact rational parameter box

Take one stratum and

\[
\begin{aligned}
 k&=48,& \varepsilon&=\frac{37}{10000},&
 A&=\frac{521}{2000},\\
 \alpha=A+\varepsilon&=\frac{1321}{5000},&
 \eta=A-\varepsilon&=\frac{321}{1250},&
 \delta&=\frac7{1250},\\
 B_m&=\frac{21}{2500}\quad(m\ge1),&&&
 (\xi_1,\xi_2,\xi_3)&=
 \left(\frac{3989}{10000},\frac{4001}{10000},\frac{4001}{10000}\right).
\end{aligned}                                                     \tag{2}
\]

Write `h=10^-10` for Proposition 3's internal epsilon, not the support
enlargement.  Also

\[
 \omega=A-\frac14=\frac{21}{2000},\qquad
 \beta=1-2\xi_2=\frac{999}{5000}.
\]

The Definition-1/Proposition-1 support reserves include

\[
 B-\delta=\frac7{2500},\quad
 \frac12-\varepsilon-A=\frac{1179}{5000},\quad
 \beta-B=\frac{957}{5000}.
\]

The constant schedule is nondecreasing and has increment zero.  It also has
`B<2 delta`, with reserve `2 delta-B=7/2500`.

This point genuinely exceeds C10 in both relevant senses.  C10 has
`alpha_C10=79247/300000` and `eta_C10=76247/300000`, while

\[
 \alpha-\alpha_{C10}=\frac{13}{300000}>0,\qquad
 \eta-\eta_{C10}=\frac{793}{300000}>0.                         \tag{3}
\]

### Printed Proposition-2 inequalities

In their source order, their exact reserves are

\[
 \frac{19}{10000},\quad 0\ \text{(allowed non-strict)},\quad
 \frac1{5000},\quad \frac{1979}{10000},\quad
 \frac{1983}{10000}.                                           \tag{4}
\]

Here `xi2>2/5`, so Proposition 2 assigns `c2=24`; it is not permissible to
drop the negative `K` term.

### Printed Proposition-3 scalar inequalities

After moving every right-hand side to the left, the six reserves are

\[
\begin{array}{c|c}
\text{I, first branch}&269499997/15000000000\\
\text{I, second branch}&518999993/35000000000\\
\text{II, first line}&4920001/100000000\\
\text{II, first minimum branch}&4049999/5000000000\\
\text{II, second minimum branch}&2124999/5000000000\\
\text{III}&37687499/5000000000.
\end{array}                                                       \tag{5}
\]

These checks establish only the displayed arithmetic, not the proposition's
validity.

### Tuple capacities

Every entry of `Xi(B,B,m,m',delta)` is at least `delta`, and each group's
sum is at most `B`.  Since `B<2 delta`, a nonempty tuple has `m,m'<=1` and
total at most `2B`.  Assign all entries to the first bin.  The first-bin
reserves after subtracting `2B` for I, IIa, IIb and III are respectively

\[
 \frac{1910499999}{5000000000},\quad
 \frac{2207199999}{5000000000},\quad
 \frac{1033999999}{2500000000},\quad
 \frac{1600249999}{5000000000}.                                \tag{6}
\]

All unused-bin capacities are nonnegative; the exact checker prints each of
them.  In the repaired above-square-root IIc range `0<=omega0<=omega`, the
four worst reserves are

\[
 \frac{1440499999}{5000000000},\quad
 \frac{121499999}{2500000000},\quad
 \frac{55999999}{10000000000},\quad 0.                         \tag{7}
\]

The last zero is the allowed empty fourth bin at `omega0=0`.

These are not a claim that printed Proposition 3 applies.  Literally it asks
for `omega0` down to `-h`; at `omega0=-h`, its fourth capacity is `-8h`, so
even the empty fourth bin would require `0<=-8h`.  The existing direct-HB
work repairs that endpoint by treating moduli below the square root
separately.  The more serious high-`gamma` obstruction remains in Section 6.

## 3. A symmetric `K=0` finite basis

Define

\[
 E_1=\left\{t\in[0,1]^{48}:
 \sum_i t_i<\eta,\quad
 \#\{i:t_i>\delta\}=1,\quad
 \sum_{i:t_i>\delta}t_i\le B\right\}.                          \tag{8}
\]

This is symmetric and has positive measure.  It is contained in the
one-stratum support from (2): its total sum lies in `[0,A+epsilon)`, and its
only cap is the defined `B_1`.  In particular, (8) does not rely on the
source's missing `B_0` convention.

For every `t in E_1` and every `i`,

\[
 \sum_{s\ne i}t_s\le\sum_st_s<\eta.
\]

Consequently (1) gives `K_i(F)=0` for every square-integrable `F` supported
on `E_1`.  This is pointwise, so it also annihilates every bilinear `K`
matrix entry on the finite family

\[
 G_{a,\lambda}(t)=1_{E_1}(t)(\eta-\textstyle\sum_i t_i)^a
                  m_\lambda(t),\qquad a+|\lambda|\le D,        \tag{9}
\]

where `m_lambda` is any symmetric monomial-orbit sum.  Formula (9) is an
explicit finite basis for every fixed `D`; no limiting or approximation
claim is being made.

## 4. The `J` extension is open, not a boundary artifact

For the 47 common coordinates in `J`, take one coordinate

\[
 b=\frac1{125}
\]

and the other 46 equal to

\[
 s=\frac{4963}{920000}.
\]

Their common sum is `U=5123/20000`.  Take both distinguished coordinates
equal to `t=t'=1/10000`.  Exact strict reserves are

\[
\begin{array}{c|c}
b-\delta&3/1250\\
B-b&1/2500\\
\delta-s&189/920000\\
U-\eta_{C10}&299/150000\\
\eta-U&13/20000\\
\eta-U-t&11/20000\\
\delta-t&11/2000.
\end{array}                                                       \tag{10}
\]

Thus a full open neighbourhood of this pair belongs to the `J` integral for
`1_{E_1}`, whereas C10 excludes the entire neighbourhood by its common-sum
condition `U<=eta_C10`.  This proves genuine `J`-fiber extension, not merely
a larger total endpoint or a measure-zero boundary change.

## 5. Exact density-loss bound and singleton contraction

Put

\[
 \tau=\xi_2-\frac25=\frac1{10000},\qquad
 \ell=1-2\xi_2=\frac{999}{5000}.
\]

On the first Buchstab domain in Proposition 2, nonemptiness confines each
of the four integration widths to at most `5 tau`; every one of the five
denominator factors is at least `ell`.  On the second domain all four widths
are at most `10 tau`, again with all five factors at least `ell`.  Positivity
therefore gives the rigorous bound

\[
 0\le c_1\le
 \frac{(5\tau)^4+(10\tau)^4}{\ell^5}
 =\frac{6640625}{1990019980009998}
 <\frac1{299000000}.                                            \tag{11}
\]

For the singleton basis `G_0=1_{E_1}`, inclusion--exclusion over the small
coordinate cube reconstructs `I` and `J` exactly.  The checker prints the
full rational numerator and denominator and obtains

\[
 q_0=\frac{48J(G_0)}{I(G_0)}
 =0.265999999999999999999999999999999999999993059422\ldots
 <\frac{133}{500}.                                              \tag{12}
\]

Since `K=0`, the full signed criterion for this vector is exactly

\[
 Q_{\rm signed}=(1-c_1)q_0.
\]

Using (11),

\[
 0.2659999991123675803540799368\ldots
 \le Q_{\rm signed}\le q_0<\frac{133}{500}<1.                 \tag{13}
\]

The `-48*24*K/I` loss is exactly zero, not rounded away.  The density loss
has the adverse sign and was retained.  Thus the singleton explicitly fails
the target with shortfall greater than `367/500`; (12) is not evidence for a
near miss.  It is also not an upper bound for the richer space (9).

## 6. Theorem-strength blockers

This parameter point cannot presently be passed through Propositions 2--3.

1. Its `omega=21/2000>0`, so the middle Type-I range
   `1/2<gamma<=1/2+2omega+epsilon'` is nonempty.  The source's Type-I lemma
   (lines 611--629) assumes only that `alpha` is a coefficient sequence and
   `beta` is smooth.  Its proof of the middle range swaps their roles and
   invokes a result requiring the new second factor--the original `alpha`--
   to be Siegel--Walfisz.  That hypothesis is absent.  A smallest hypothesis
   counterexample is

   \[
    \alpha(m;x)=1_{M\le m\le2M}1_{m\equiv1\pmod3},
   \]

   whose discrepancy modulo 3 is of order `M`.  This does not disprove the
   desired equidistribution conclusion; it disproves the stated proof step.
   Repairing it requires a new theorem or an additional structural property
   of every Type-I sequence arising from the minorant.

2. `PROP1-C2ZERO-AUDIT.md` proves a repaired implication only for the
   nonnegative `c1=c2=0` specialization.  It explicitly excludes the signed
   `c2>0` numerator, the composite-minorant coprimality subtraction and the
   `K` identification.  No exact `K=0` finite vector may be promoted to a
   theorem until that signed proof is independently repaired: the affine
   retreat/mollification and all numerator lower bounds must retain the
   adverse `c2` contribution.

Accordingly the verdict is:

> **AUDIT PASS for the exact geometry, parameter arithmetic, `K=0` identity,
> `J`-fiber extension and singleton contraction.  BLOCKED as an unconditional
> sieve route by the missing high-`gamma` SW lemma and the unaudited signed
> Proposition-1 implication.**

The result reopens one narrowly defined computational mechanism: exact
optimization in (9), or in the larger core
`{t in T: sum_{s!=i}t_s<=eta for every i}`, pays no `K` loss.  It does not
justify such a run until the analytic blockers above are removed.

## 7. Reproduction

```bash
python3 agents/small-delta-frontier/check_general_minorant_kfree.py
python3 -O agents/small-delta-frontier/check_general_minorant_kfree.py
```

Both modes produce byte-identical output.  Checker SHA-256 is
`e65aa613b9a84ce9faa049d5c8654363a50ee007fdce3fb7e3749da7105cfb18`.
It pins the Stadlmann source hash, uses `Fraction` arithmetic only, fails
closed without `assert`, includes literal `k=2,3` factor tests, prints every
margin and the exact `I,J,K` and criterion enclosure, and emits
`THEOREM_READY=false`.
