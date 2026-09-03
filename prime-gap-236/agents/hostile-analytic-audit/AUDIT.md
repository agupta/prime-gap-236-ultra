# Hostile analytic audit of the repaired Proposition 3

## Verdict

**AUDIT FAIL.**  The proposed baseline lemma in
`agents/source-fidelity/repaired-proposition3.md` is not presently a proved
equidistribution theorem.  There is a theorem-level gap in its treatment of
Type I convolutions with a smooth factor just above the square root.  The
argument invokes the Polymath Type II lemma after swapping the convolution
factors, but the newly designated second factor is the original arbitrary
coefficient sequence and need not have the Siegel--Walfisz property required
by that lemma.

There is also a separate, readily repairable, lost-slack error in the Type III
parameter substitution.  After that correction, the baseline support and the
proposed enlarged support

```text
B_1=B_2=3/20,       B_m=889/5000  (m>=3)
```

pass all exact scalar and continuum partition checks, including the natural
zero-count extension.  Thus the enlarged-support *combinatorics* receive a
conditional pass, but the analytic equidistribution conclusion does not.

This audit does not assert that the failed Type I equidistribution statement
is false.  It identifies an explicit convolution for which the cited theorem
cannot be invoked and for which no replacement proof is supplied by the
primary sources.

**Post-audit bypass.**  The failure is avoidable for the actual choice
`c_1=c_2=0`: `direct-hb-prime-equidistribution.md` gives a separately audited
direct Heath--Brown proof for a weighted prime minorant.  It classifies every
Heath--Brown term as Type 0, Siegel--Walfisz/Siegel--Walfisz Type II, or smooth
Type III, and never invokes the failed Type I lemma or Proposition 2.  That
specialized proposition has status **SPECIALIZED ANALYTIC AUDIT PASS** for
both the baseline and `889/5000` supports.  Thus this file's `AUDIT FAIL`
applies to the claimed universal repaired Proposition 3, not to the newer
specialized route.

## Audited artifacts and source fingerprints

The audit used the following exact local files.

| File | SHA-256 |
|---|---|
| 2026 TeX, `agents/source-fidelity/source-tree/Bounded_Gaps_2.0.tex` | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| Polymath8a PDF, `agents/source-fidelity/sources/polymath8-edz-1402.0811.pdf` | `f4b4556f9451ea0524b974376b9dbe4478faf3734847897460274f6bae98b65c` |
| Stadlmann 2023 TeX, `sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex` | `60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30` |
| Baker--Irving TeX, `sources/baker-irving-1505.01815-src/primegaps_paper.tex` | `743ca0053146471648040fa1224f2177258221ded4927f8c9fe3221c35b6702e` |
| Baker--Weingartner PDF, `agents/hostile-analytic-audit/baker-weingartner.pdf` | `9cf7740307aeaa9c02846b48fe166e1eada728b442ab1337c186a83ae268aba9` |
| candidate baseline repair | `bcd8dc5a0f6f25925f30bdd6baa59cf8276be432f36b68394d36d8cf128fc635` |
| enlarged-support proof audited | `cd0f6a7bffbe85d7129291a9466f7c1e716171942a98b15fc41ce98651dc3ce3` |

Line references below are to those TeX files as numbered by `nl -ba`.  The
Baker--Weingartner references are to the local `pdftotext -layout` extraction
`baker-weingartner.txt`.

## 1. Exact failed dependency: the high-gamma Type I swap

The dependency chain is short and unambiguous.

1. Definition 5 in the 2026 paper permits a Type I function
   `f=alpha*beta` with `alpha` merely a coefficient sequence and `beta`
   smooth; it imposes no Siegel--Walfisz condition on `alpha`
   (`Bounded_Gaps_2.0.tex:1104--1113`).
2. The 2026 Baker--Irving Type I lemma repeats exactly those hypotheses
   (`:611--627`).
3. For `gamma` in the transition interval
   `[1/2,1/2+2 omega+epsilon]`, its proof says to apply the Polymath Type II
   lemma “with the roles of alpha and beta swapped” (`:940--947`).
4. The cited Polymath Type II lemma requires its second coefficient sequence
   to have the Siegel--Walfisz property (`:572--583`).  After the swap, that
   second sequence is the original `alpha`.
5. Hence the cited lemma has an unmet hypothesis.  Commutativity of Dirichlet
   convolution does not remove it: without swapping, the second scale is
   `x^gamma>x^(1/2)`, contrary to the same lemma's scale hypothesis.

The baseline repair uses this invalid high-gamma branch twice: for the narrow
transition above `gamma=1/2` in its square-root strip, and for the full
above-square-root block with `omega=3/1000`.  The enlarged support does not
alter this dependency.

### Explicit hypothesis counterexample

Take

```text
omega = 3/1000,
gamma = 503/1000,
M = x^(497/1000),
N = x^(503/1000).
```

Let `beta` be any nonzero smooth coefficient sequence at scale `N`, and let

```text
alpha_x(m) = 1  if M <= m <= 2M and m == 1 (mod 3),
             0  otherwise.
```

Then `alpha_x` is a coefficient sequence at scale `M`, so
`f=alpha_x*beta` belongs to the stated Type I class.  But, with `q=3`,
`r=1`, and primitive residue class `a=1`,

```text
Delta(alpha_x;1 mod 3)
 = #{m in [M,2M]: m=1 mod 3}
   - (1/2) #{m in [M,2M]: m=1 mod 3}
 = M/6 + O(1).
```

This violates the Siegel--Walfisz bound `O_A(M log(x)^(-A))`.  Moreover
`gamma=0.503` lies strictly in
`(1/2,1/2+2 omega)=(0.5,0.506)`.  Thus this is an explicit member of the
claimed class for which the role-swapped Polymath lemma is inapplicable.
It is a counterexample to the proof invocation, not a claimed counterexample
to the final distribution estimate.

The same issue is visible in the predecessors.  Baker--Irving's Type I lemma
explicitly assumes that `alpha` satisfies Siegel--Walfisz
(`primegaps_paper.tex:264--270`).  Stadlmann 2023 states a broader Type I class
with arbitrary `alpha` (`Primes_in_arithmetic_progressions.tex:1777--1792`)
and invokes Baker--Irving at `:1795--1797`, without adding the missing
hypothesis.  Consequently the 2023 universal Type I statement cannot by
itself repair the 2026 invocation.

## 2. The two requested Type I repairs

### Repair A: prove Siegel--Walfisz only for factors actually produced by the sieve

This works for an important but incomplete part of the 2023 decomposition.
In the Heath--Brown-derived class `mathcal B`, Stadlmann 2023 explicitly
requires every sub-convolution at scale at least `x^(10^-10)` to be
Siegel--Walfisz (`Primes_in_arithmetic_progressions.tex:1870--1879`).  The
large blocks selected for Type I are smooth (`:1882--1884`), and their
complements have polynomial scale in the cases used there.  Therefore the
original `alpha` in those Type I applications can be assigned the needed
Siegel--Walfisz property from class-B property (3).  This repairs those
Heath--Brown pieces.

It does **not** close the earlier good-sifted-set part that is absorbed into
`theta_0`.  Stadlmann 2023 invokes Baker--Weingartner Lemma 14 and says only
“After verifying that the sequences which appear in the proof ... have the
Siegel--Walfisz property” (`:1823--1828`).  No list of all recursive
coefficients or verification is given.

The omitted check is substantive:

- Baker--Weingartner Lemma 14 assumes its estimate (4.1) for **any**
  coefficients `a_m` (`baker-weingartner.txt:952--977`).
- Its proof forms new coefficients at `:1000--1018` and recursively applies
  Buchstab splitting at `:1028--1132`; the variables are linked and then
  separated by “cosmetic surgery.”
- Baker--Irving claims its Type I lemma verifies (4.1)
  (`primegaps_paper.tex:395--410`), but that Type I lemma itself assumes
  Siegel--Walfisz for `alpha` (`:266--269`) and therefore does not establish
  (4.1) for arbitrary `a_m` as stated.
- Baker--Irving's general sentence at `:312` and Stadlmann's sentence at
  `:1826` do not provide the required uniform, recursion-by-recursion proof.

Under the requested standard that a large compatibility verification may
not be called routine, Repair A remains **theorem-level blocked** at the
following exact missing result:

> Prove, uniformly through every recursive term of Baker--Weingartner Lemma
> 14 used for each of Stadlmann's six good-sifted functions, that the
> coefficient placed on the smaller side in every transition-range Type I
> estimate has the Siegel--Walfisz property after all support separations; or
> prove the necessary Type I estimate without that property.

### Repair B: redefine Type I in `mathcal H` to require `alpha` Siegel--Walfisz

With that stronger definition, the role swap in the 2026 Type I lemma is
formally valid.  But Proposition 2's hypothesis and proof would then have to
be restated and every actual sequence used in its Harman decomposition shown
to belong to the narrower class.  The class-B pieces above can be covered;
the good-sifted-set pieces encounter exactly the unresolved recursion just
described.  Thus Repair B is also **theorem-level blocked** from the cited
primary text.

The fact that `xi_2=2/5` makes the final formula `rho=1_P` does not remove
this dependency.  Proposition 2 assumes equidistribution for every member of
the stated `mathcal H` at `Bounded_Gaps_2.0.tex:1132--1135`, and its proof uses
that machinery to establish equidistribution of the resulting prime
minorant.  A new specialized proof for `1_P` could bypass Proposition 2's
universal premise, but no such proof is contained in the audited artifacts.

## 3. Type III lost slack

This is a second failure of the baseline repair as written, but it has a clean
exact correction.

Definition 5 permits

```text
N_i <= x^(xi_3+h),
N_i N_j >= x^(1-xi_3-h),
N_i >= x^(1-2xi_3-h),              h=10^-10.
```

The Section 3 Type III lemma uses a parameter `gamma_3` satisfying

```text
N_i <= x^gamma_3,
N_i N_j >= x^(1-gamma_3),
N_i >= x^(1-2 gamma_3)
```

and requires

```text
28 omega + 9 gamma_3 + 8 delta_3 < 4
```

(`Bounded_Gaps_2.0.tex:653--668`).  The worst permitted Definition-5 scales
force `gamma_3=xi_3+h`; one cannot substitute `xi_3`.

The paper and the baseline repair instead use, at general `omega`,

```text
delta_3 = 1/2 - (7/2)omega - (9/8)xi_3 - h.
```

Then

```text
28 omega + 9(xi_3+h) + 8 delta_3 = 4+h > 4,
```

so the distribution lemma's strict hypothesis fails.  Concrete allowed
scales requiring `gamma_3>=xi_3+h` are

```text
log_x N_1 = xi_3+h,
log_x N_2 = log_x N_3 = (1-xi_3-h)/2.
```

For `xi_3=2/5`, these satisfy all three Definition-5 scale conditions.

Use instead

```text
gamma_3 = xi_3+h,
delta_3 = 1/2 - (7/2)omega - (9/8)xi_3 - 2h.
```

The strict distribution margin is then exactly `7h`.  The corresponding
partition capacities are

```text
C_1 = 1 - 6omega - (3/2)xi_3 - (8/3)h,
C_2 = (5/2)omega + (3/8)xi_3 + (2/3)h.
```

At `omega=0`, the same corrected choice is

```text
delta_3 = 1/2-(9/8)xi_3-2h.
```

The exact checker verifies `delta_3>7/250`, the `7h` strict margin, and that
the first bin holds the entire baseline total `17/50`.  The enlarged-support
artifact has already adopted the corrected first capacity.

## 4. Printed negative-omega defect and the square-root split

The proposed repair correctly identifies a literal contradiction in printed
Proposition 3.  Condition D quantifies
`omega_0 in [-h,omega]` and requires

```text
sum_{i in I_4} y_i <= 8 omega_0.
```

At `omega_0=-h`, even the empty subset has sum `0>-8h`.  This includes
`m=m'=0`; it is not repaired by declaring an empty fourth part.
The contradiction is present at `Bounded_Gaps_2.0.tex:1431--1438` and follows
from the fourth capacity in partition Lemma 13 (`:1337--1345`).

The three-way split proposed in the baseline artifact is logically suitable:

1. `q<=x^(1/2) log(x)^(-L)` by bilinear Bombieri--Vinogradov;
2. `x^(1/2) log(x)^(-L)<q<=x^(1/2)` by the Section 3 factorization lemmas
   with `omega=0`;
3. dyadic blocks above `x^(1/2)`, for which `omega_0>=0`.

For fixed support-shrink parameter `varepsilon_0`, the middle strip is above
`x^(1/2-epsilon_1)` for every fixed sufficiently small `epsilon_1` once `x`
is large, so partition Lemmas 11 and 12 apply.  Above the square root, define
`omega_0` from the upper endpoint of each dyadic block.  Then
`0<=omega_0<=3/1000`; the strict scalar margins are uniform and an initial
extra logarithmic saving absorbs the `O(log x)` blocks.  No negative
`omega_0` is needed.

This validates the geometry of the square-root repair, conditional on valid
distribution estimates for all sequence classes.  The high-gamma Type I gap
in Section 1 prevents it from proving the claimed universal result.

## 5. Bilinear Bombieri--Vinogradov audit

Polymath8a Theorem 2.9 (local extracted text `:552--563`) applies to
`alpha*beta` at scales `M,N`, with `MN asymp x`, `N>=x^c`, and `beta`
Siegel--Walfisz.  The algebraic application to the three Definition-5 classes
is valid:

- Type I: the displayed smooth `beta` is Siegel--Walfisz and
  `N>=x^(19/50-h)`.
- Type II: the displayed `beta` is assumed Siegel--Walfisz and
  `N>=x^(2/5-h)` after using convolution symmetry if needed.
- Type III: group `alpha*psi_1*psi_2` as the first coefficient sequence and
  use `psi_3` as the second.  Then `N_3>=x^(1/5-h)`, `psi_3` is
  Siegel--Walfisz, and convolution preserves coefficient-sequence bounds and
  scale localization.  Polymath8a Lemma 3.4(i),(iii), local text
  `:985--1012`, records the relevant closure properties.

There is, however, an expositional gap in the candidate proof.  Polymath's
discrepancy is for the entire finitely supported convolution, while the 2026
target inserts the sharp restriction `n in [x,2x]`.  A Perron/finer-than-
dyadic separation can produce an interval version while preserving the
Siegel--Walfisz input and losing only logarithmic factors, but the candidate
does not state that argument or cite an exact interval-form theorem.  This is
repairable and is not the decisive obstruction, but under the requested
audit standard it must be written before the small-modulus step is complete.

## 6. Baseline branch-by-branch parameter audit

Apart from Sections 1, 3, and the sharp-cutoff point in Section 5, the branch
arithmetic checks out.

### Type I, `omega=0`

For `gamma<=1/2`, the choice
`delta_*=gamma-1/3-h` has its minimum at `gamma=19/50-h`, giving

```text
delta_* >= 7/150-2h > 7/250.
```

All support coordinates fit in the first partition bin because its capacity
is `19/50-2h>17/50`; the second capacity is positive.  For
`1/2<gamma<=1/2+epsilon'`, both high-gamma partition capacities are positive
and the first holds the total.  That transition branch nevertheless depends
on the invalid Type I role swap.  For a fixed `gamma` separated from `1/2`,
the Type-0 branch applies, but Definition 5 allows `gamma(x)` to approach
`1/2`, so it does not uniformly eliminate the transition.

### Type II, `omega=0`

By symmetry take `gamma<=1/2`.  The nominal Type IIc range is empty because

```text
(2/5-h) - (1/3+(7/3)(7/250)+3h) = 1/750-4h > 0.
```

The remaining range is covered by IIa and IIb.  Their first capacities are,
respectively,

```text
2/5+(7/5)(7/250)-2h > 17/50,
1/3+(7/3)(7/250)-4h > 17/50.
```

All unused capacities and all hypotheses of partition Lemmas 11 and 12 are
strictly positive.  The chosen auxiliary factor widths are strictly larger
than `7/250`, not merely equal to it.

### Type III, `omega=0`

The candidate's substitution fails as shown in Section 3.  The corrected
substitution passes with exact distribution margin `7h`; all coordinates fit
in the corrected first capacity.

### Above the square root

The Type IIa, IIb, and IIc scalar inequalities have strict exact margins at
`omega=3/1000`.  For IIc, `delta_*=delta=7/250` is permitted throughout

```text
2/5-h <= gamma <= 317/750+3h.
```

The four-factor structural hypotheses of partition Lemma 13 follow after
choosing the distribution slack much smaller than `h`.  The baseline
two-bin construction for condition D is a continuum proof, not sampling:
if both blocks have count at most two, their total is at most `3/10`; if a
block has at least three entries, its least entry lies in
`[7/250,17/300]` and supplies the second bin while the complement fits in the
first.  Zero-count cases follow separately.  Type III passes after the
Section 3 correction.  Above-square-root Type I still fails at the theorem
invocation in Section 1.

## 7. Enlarged support `889/5000`

### Definition and scalar conditions

The sequence satisfies Definition 1 exactly:

```text
B_3-B_2 = 139/5000 < 7/250,
B_{m+1}-B_m = 0  (m>=3).
```

For `m>=7`, `m delta>=49/250>889/5000`, hence `Xi` is empty.  Only counts
`0,...,6` can be nonempty.  All Proposition 2 and scalar Proposition 3
margins printed in `support-889-proof.md` were recomputed with rational
arithmetic and are positive.

The total of two blocks is at most

```text
2(889/5000)=889/2500.
```

It fits in the first bin for A, B, C, the corrected E, and the additional
high-gamma Type I partition.  Every unused-bin capacity is nonnegative.

### Exact continuum proof for repaired condition D

Uniformly over

```text
0<=omega_0<=3/1000,
2/5-h<=gamma<=317/750+3h,
```

the first two capacities are bounded below by

```text
C=8/25-2h,
D=107/1500-4h,
```

and the last two by `7/250-h` and `0`.  Leave bins 3 and 4 empty.  For total
`T`, a second-bin subset must have sum in
`[L,D]`, where `L=max(0,T-C)`.

- If either count is zero, `T<=889/5000<C`; this includes `(0,0)` after the
  explicit convention `B_0=0`.
- If both counts are at most two, `T<=3/10<C`.
- If exactly one count is at most two, then
  `L<=39/5000+2h<delta`.  The least entry in the other block lies in
  `[delta,889/15000]`, and `889/15000<D`.
- If both counts are at least three, let their least entries be `a,b`.
  If one is at least `L`, use it.  Otherwise

  ```text
  a+b >= 2delta > L,
  a+b < 2L <= 89/1250+4h < D.
  ```

  The last strict margin is exactly `1/7500-8h>0`.

This proves every continuous tuple case.  The candidate checker skips the
single pair `(0,0)` in its enumeration, but the empty tuple is valid because
all four repaired capacities are nonnegative; `audit_exact.py` checks those
four capacities explicitly.  Thus there is no zero-case counterexample after
the `B_0=0` repair.

### Conditional verdict

**CONDITIONAL SUPPORT AUDIT PASS:** all enlarged-support definition, scalar,
and partition inequalities pass exactly after (i) restricting condition D to
`omega_0>=0` via the square-root split and (ii) using the corrected Type III
parameters.  This does not prove equidistribution because of the Type I gap.

## 8. Strict endpoints and the four epsilon parameters

The following quantities must not be conflated:

```text
varepsilon = 3/400     support enlargement in A_0,
h           = 10^-10  Definition-5/Proposition-3 fixed slack,
varepsilon_0           arbitrary support shrink in Q^*,
epsilon'               small slack in the distribution lemmas.
```

For Type I, IIa, IIb, and IIc, choose `epsilon'` smaller than a fixed
constant times `h`; the candidate partition capacities then lie strictly
inside the open divisor intervals.  Uniform strict scalar margins permit one
choice over the compact `omega_0,gamma` ranges.

The Type III divisor interval in the stated Section 3 lemma is open but does
not visibly contain an `epsilon'` shift (`Bounded_Gaps_2.0.tex:660--668`),
whereas partition Lemma 11 returns a closed interval (`:1248--1255`).  This
must be handled explicitly: replace its endpoints `a,b` in the partition
application by `a+eta,b-eta`, with fixed rational `eta>0` small enough that

```text
delta_3-2eta >= 7/250
```

and smaller than the positive first-bin margins.  The exact margins in
`audit_exact.py` leave abundant room.  Merely saying “take epsilon' small” is
not, by itself, an endpoint repair for the displayed Type III set.

## 9. Reproduction commands

From the repository root:

```bash
python3 prime-gap-236/agents/hostile-analytic-audit/audit_exact.py
python3 prime-gap-236/agents/independent-attack/verify_support_889.py
```

The first command must end with

```text
HOSTILE EXACT ARITHMETIC PASS
```

and the second with

```text
SUPPORT-889 EXACT CHECK PASS (for repaired omega0>=0 criterion)
```

These outputs certify only the stated rational inequalities and continuum
case bounds.  They intentionally do not print `AUDIT PASS`, because the
missing high-gamma Type I theorem remains on the proof's critical path.

## Final dependency status

```text
negative omega_0 endpoint        REPAIRED by square-root split
baseline A--E/D partitions       PASS after Type III correction
889/5000 A--E/D partitions       PASS after Type III correction
m=0 or m'=0, including (0,0)     PASS with explicit B_0=0 convention
small-modulus BV factor choices  PASS algebraically; interval cutoff to write
Type IIa/IIb/IIc hypotheses      PASS
Type III hypotheses              PASS only with corrected gamma_3,delta_3
high-gamma Type I theorem        FAIL / THEOREM-LEVEL BLOCKED
Proposition 2 specialized repair FAIL / missing good-sifted SW audit
overall analytic proposition     AUDIT FAIL
```
