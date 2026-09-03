# Theorem-facing `PROOF.md` hostile draft audit

Date: 2026-09-03 (Europe/Berlin)

## Verdict

**PRE-CERTIFICATE DRAFT AUDIT PASS AFTER REPAIR.  THIS IS NOT A THEOREM
AUDIT PASS.**

For the final `PROOF.md` bytes pinned below, every displayed support,
normalization, cutoff, polarization, `R<=9` projection, and tuple formula
agrees with the frozen exact inputs and with the conditional analytic audit.
The draft still expressly assumes the unproved certificate condition `(C)`:

```text
A > 0 and b^2 - A D > 0.
```

No completed aggregate or compact certificate was available, and this audit
did not run a mixed or diagonal target integral.  It therefore proves no new
prime-gap theorem and does not authorize removal of the warning at the top of
`PROOF.md`.

## Frozen bytes

| item | SHA-256 |
|---|---|
| `PROOF.md` on receipt | `846e2f77b7f3e493ca0ec13b01ccb47acbef700443230cadf7f44aaa6c578e38` |
| repaired `PROOF.md` | `1c221e0bcdaf2b6985ddc1164bae35ffd977210ad0f44088aacdb391c00d23aa` |
| Stadlmann TeX | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| conditional analytic audit | `951e927d91b961a1aa734ce73c620725d5a5b9286eed92aa0183a553c58629b3` |
| frozen support result | `c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f` |
| hostile support replay result | `fea750c78b8bc7a022d8ee7d407a59405f4f790b1729305f47b21f8d4f2117a1` |
| exact D19 inner result/vector | `8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170` |
| exact D14 outer candidates | `722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0` |
| tuple data | `adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9` |

The lightweight independent replay is
`agents/audit/verify_proof_draft_frozen_facts.py`.  It imports no project
arithmetic module and independently rebuilds both even bases, exact rational
LCMs, the support/cutoff arithmetic, the inner form relation, and all tuple
residue witnesses.  Its SHA-256 is
`754586fba411ced7fa6419e6bd2835983a687c5147f5c00e8080c3ef252ef19f`.

## Defects found and repaired

The received draft was not accepted unchanged.

1. **Definition-3 quantifier was weakened/ambiguous.**  “Primitive `a`” can
   mean merely `(a,q)=1`, whereas Stadlmann Definition 3 literally requires
   `(a,p)=1` for every prime `p<=x`.  The repaired draft states the literal
   quantifier and defines its abbreviated `Q*(x)` notation.

2. **The claimed global definition of `rho` was not globally defined.**  It
   multiplied `log(n)` by an indicator even for nonpositive integers.  The
   repaired definition is piecewise and evaluates `log(n)` only for a prime
   in `[x,2x]`.  The displayed theta identity also omitted a possible endpoint
   prime.  It now carries an harmless `O(1)` after division by `log(3x)`.

3. **The cap-chain display referred to an undefined terminal entry.**  The
   old statement applied `B[j,m+1]` to all 120 entries, including `m=60`.
   The repair separates the 120 lower bounds from the 118 defined adjacent
   transitions `1<=m<60`.

4. **The paper's basis contradiction was silently bypassed.**  The TeX
   introduction says `2 deg(p)+b<=21`, while Section 5 names `B_19`; its
   displayed family does not itself prescribe a serialized finite basis.
   The repair explicitly defines the certificate's independent Polymath8b
   even-signature convention and exact label order.  It states that the
   source contradiction remains unresolved and that degree 21 is not a
   premise.

5. **The scale wording could falsely suggest that dilation preserves integral
   coefficients.**  The exact LCMs `10^87` and `10^38` clear the stored D19
   and D14 vectors.  Substitution by the rational
   `gamma=9270000/9500917` can introduce further denominators.  The repair
   distinguishes the stored-vector normalization from the expanded dilated
   polynomial.

6. **The mixed-count projection was asserted without its one-line proof.**
   The repair now lets `r=R(u)` and observes that a small distinguished outer
   coordinate leaves total count `r`, while a large one makes it `r+1`.
   Hence all four branches survive for `r=0,...,8`, only `Sdelta,Stotal`
   survive for `r=9`, and `r>=10` vanishes.  It also records the null
   `t=delta` boundary convention.

7. **Several Markdown/TeX fragments were corrupted or undefined.**  Plain
   `(n)`, `(delta)`, `(gamma)`, `(K)`, and `(S)` were restored as mathematics;
   the residual-capacity `K` was renamed `K_cap` to avoid collision with the
   sieve integral; the rational reserves in the table were marked as math;
   the sorted-factor lemma now states `p<n` and `q<=n-p`; and `Lambda 1` was
   typeset with separation.  Polarization and the marginal `M_X` are now
   explicitly defined.

8. **A staged computation was described as though one final checker already
   existed.**  The repaired text distinguishes the existing producers and
   shard checkers from the still-pending end-to-end replay.

All paths cited by the repaired proof exist at the pinned workspace
location.  The display-math delimiter counts, inline-dollar parity, and code
fences are balanced.

## Formula audit

### Support and relevant moduli

- `alpha1=A1+epsilon=103/400`,
  `alpha2=A2+epsilon=9500917/36000000`, and
  `eta=A2-epsilon=8960917/36000000` are exact.
- The twelve stated outer caps agree term-for-term with the frozen support;
  the last is extended constantly through column 60.
- `13 delta-B[2,13]=3749/750000>0`, so an outer point cannot have 13 or more
  large coordinates.  The inner cap is redundant because the first total
  band has total `<103/400`.
- Definition 2's asymmetric total-factor bounds add to
  `(1-epsilon0)(A_j+A_jprime)`, with no spurious `2 epsilon`.  Thus
  `q<=x^(2 A2)` and `2 A2=9230917/18000000<1`.
- The `epsilon0=1` and `epsilon0>1` branches (`q=1` and empty,
  respectively) agree with the conditional analytic audit.

### Analytic implication

The draft's `h,s,sigma,r0,zeta`, three Heath--Brown cases, three `omega`
values, sorted-factor inequality, IIb root, finite inventories, source
repairs, and prime-power exponents match
`agents/audit/PROP1-TO-H1-ONE-BAND-AUDIT.md` exactly.  In particular it does
not invoke the general Harman minorant, Proposition 2, or Proposition 3 as a
black box, and it sets `c1=c2=0` only after verifying the direct nonnegative
prime weight.

The Proposition-1 specialization has one factor `48`, not `49`; the repaired
numerator step is a lower bound because `rho>=0`; and the subsequence
`x_r=3^(60r+1)` makes `x_r^delta` nonintegral while leaving disjoint ranges.
This audit compared the theorem-facing summary against the already-frozen
line-by-line analytic audit.  It did not rerun that audit's 43,008-cell
enumeration.

### Basis, dilation, and scales

Independent generation gives exactly 568 labels for the complete D19 even
basis and 195 for D14, in order

```text
(a+|lambda|, |lambda|, length(lambda), lambda, a).
```

The JSON label lists match exactly.  The reduced coefficient-denominator LCMs
are exactly `10^87` and `10^38`.  The inner exact forms obey
`I-48J=D`, `I>0`, `D>0`, and the stored exact normalized deficit is `D/I`.
The dilation is exactly

```text
alpha1/alpha2 = 9270000/9500917.
```

Consequently `I(hat F)` and `D` scale by `10^174`, `A` scales by `10^76`,
and the mixed `b=48J(hat F,hat H)` scales by `10^125`.  Both terms in
`b^2-A D` therefore have scale `10^250`; no scale is missing from the scalar
criterion.

### Definition 5 and `R<=9`

The literal cutoffs are

```text
inner/inner: 97/400
inner/outer: 8960917/36000000
outer/outer: 8960917/36000000.
```

Polarization turns the two equal ordered mixed-band terms into one marginal
integral, and Proposition 1 then supplies the single factor 48 in `b`.
Because `H` occupies one outer band, its diagonal Definition-5 form is the
integral of `M_H^2` over the outer cutoff and is nonnegative.  Disjointness of
the inner and outer total bands gives `I(hat F+c hat H)=I+c^2 A`.
Substitution `c=b/A` reproduces the draft's exact lower bound

```text
48J/I >= 1 + (b^2-A D)/(A I+b^2).
```

This implication is valid only after exact proof of `(C)`.

### Tuple

The tuple file is strictly increasing, has 48 distinct entries, endpoints
0 and 236, and diameter 236.  Independent modular reconstruction reproduces
every displayed least missing residue for the 15 primes through 48.  A set
of 48 residues cannot cover all classes modulo a prime greater than 48, so
the admissibility conclusion and `H(48)<=236` are correct.  The final
prime-gap conclusion remains explicitly conditional on `(C)`.

## Replay

From `prime-gap-236/`:

```bash
python3 agents/audit/verify_proof_draft_frozen_facts.py
python3 -O agents/audit/verify_proof_draft_frozen_facts.py
```

Both modes must print `PRE-CERTIFICATE FROZEN-FACT REPLAY PASS`.  This replay
checks only the theorem-facing draft's frozen non-integral facts.  It must not
be represented as the missing exact scalar integration or as an independent
certificate audit.
