# Adaptive support v1 hostile audit

## Verdict

**`AUDIT PASS`**, scoped to the frozen exact analytic-support claim and the
direct weighted-prime interface to Proposition 1.  I found no malformed
ordered count case, uncovered Type-IIb parameter, uncovered Type-IIc cell,
non-strict source substitution, or producer-record mismatch.

This verdict does **not** invoke printed Proposition 3 and does **not** claim
to satisfy printed Proposition 2's universal hypothesis.  The specialized
Heath--Brown argument bypasses both propositions and supplies Proposition 1
directly.  It remains outside the scope of this audit to establish a sieve
quotient or an `H_1` theorem; `theorem_ready=false`.

## Frozen inputs and independent artifacts

| File | SHA-256 |
|---|---|
| `agents/analytic-new-lever/verify_adaptive_support_v1.py` | `b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d` |
| `agents/analytic-new-lever/adaptive_support_v1_exact.json` | `b7070c2677815b22a86b5a55ce41b3a2477d593495062256356a5df2a37befa7` |
| `sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex` | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| `sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex` | `60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30` |
| `sources/polymath8-edz-1402.0811-src/newergap.tex` | `fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea` |
| `agents/audit/verify_adaptive_support_v1_hostile_audit.py` | `0a6b6dbc6ab2cc1a1ec85e0e1a62e19cd6df498e97e68c8c0d5a6bd2202ed918` |
| each independent result (`normal`, `opt`, canonical) | `eabffdc8927a50cb95fb1f8b707dd9b5c76b53778022ea039e160fb9cd2908d5` |

The independent checker imports no discoverer module and reads no discoverer
narrative.  It hashes and snapshots the primary sources, reconstructs every
arithmetic certificate, and only then parses the producer JSON with duplicate
keys, floating-point numbers, non-ASCII text, missing final newline, changed
hashes, non-regular files, and multiple hard links rejected.  A second hash
pass rejects mutation during the audit.

## Reconstruction

From Definition 1 at primary-source lines 140--150, the exact tuple is

```text
delta=1/60, epsilon=3/400,
A=(-3/400,1/4,231241/900000).
```

The reconstructed inner active counts are `0,...,15`; outer active counts are
`0,...,11`; count 12 is empty by `10863/1000000`.  Every one of the 60 cap
columns and every weak plateau boundary satisfies the literal Definition-1
conditions.

For the fixed branches the audit checks all four ordered families
`mixed`, `transpose`, `outer`, and `outer-near`.  Its inventory is 672 ordered
pairs: the producer's 668 nonempty pairs plus the four explicit `(0,0)` pairs.
There are 1,336 nonempty Type-IIa/III checks.  The least exact reserve is

```text
43599493/7200000000000
```

at mixed Type III counts `(1,3)`.

For literal Type IIb, the audit derives the constant-window sorted-prefix
argument independently.  It checks every attainable overload crossing over
the full real gamma interval, not sampled gamma values: 767 crossing checks.
The least reserve is

```text
53930026073/90000000000000
```

at outer-near counts `(7,10)`.  Cases with one zero count and all four `(0,0)`
cases are explicit in the inventory.

For Type IIc, the mixed and near ranges are exactly empty.  The nonempty
outer/outer rectangle is split into `16*16` closed adverse-endpoint cells.
All `143*256=36,608` nonempty cells pass, plus 256 explicit empty-tuple cells.
The least packing reserve is

```text
800009/180000000000
```

at counts `(5,8)`, omega cell 5, gamma cell 10.  The smallest strict source
reserve is the post-inward factor-width margin
`1/200000000000`.  The three exact IIc distribution margins are

```text
2021599937/90000000000
2057599937/180000000000
599999/1250000000.
```

The Type-0, small-modulus bilinear Bombieri--Vinogradov, IIa, IIb, IIc,
and corrected Type-III endpoint inequalities all remain strict in the near,
mixed, transpose, and outer regimes.  The exact K=10 Heath--Brown identity and
its scale trichotomy are anchored in the Polymath source at lines 1305--1425;
the relevant 2026 coefficient, distribution, and factorization definitions
are at lines 532--669 and 1239--1746.

## Proposition interface

Printed Proposition 2 (primary-source lines 1118--1165) assumes
equidistribution for **every** `f` in the broad class `H`.  The direct
Heath--Brown reduction proves no such universal statement, so the four
numeric xi inequalities alone must not be presented as a use of Proposition
2.  This is not a counterexample to the scoped result because the route never
needs Proposition 2.

Instead it uses

```text
rho(n;x)=(log n/log(3x))*1_P(n) on [x,2x], and 0 outside.
```

The direct K=10 decomposition covers Type 0, central two-factor, and smooth
three-atom terms.  The reconstructed support factorizations cover the whole
frozen `Q*`; subtracting prime powers passes from Lambda to theta.  The other
three Proposition-1 hypotheses at lines 228--240 then hold directly:

- `0 <= rho <= 1_P` because `log n < log(3x)` on `[x,2x]`;
- beta `1/2` exceeds `max B_{j,1}=103/400` by `97/400`;
- the prime number theorem gives mass `(1+o(1))x/log x`.

Thus `c1=c2=0`.  At `xi2=2/5`, Proposition 2's *own* endpoint minorant is
literally `1_P` (source lines 1165 and 1229), whereas the selected direct
minorant is the normalized weighted prime function above.  The producer's
`rho_reason` wording conflates those two facts, but its recorded `rho` and the
actual Proposition-1 argument are correct.

## Cap-radius scope guard

The certified radius is a **common translation** of all outer caps.  At
`|t|<=1/1000000`, both Definition 1 and every packing branch pass; at the
upper endpoint the least fixed, IIb, and IIc reserves are respectively

```text
36399493/7200000000000
53750026073/90000000000000
440009/180000000000.
```

It is not an independent-coordinate box.  The smallest scope counterexample
is `B11=B12=189137/1000000`: perturbing `B11` up and `B12` down by
`1/1000000` gives `B11-B12=1/500000`, violating monotonicity.  Neither frozen
artifact claims that stronger box.

## Dual-mode regression

The producer reproduced its canonical artifact byte-for-byte in normal mode
(`12.24 s`, RSS `21,636 KiB`) and `python3 -O` (`11.60 s`, RSS `27,328 KiB`).
The independent audit results are byte-identical in normal mode (`2.46 s`,
RSS `22,580 KiB`) and `python3 -O` (`2.90 s`, RSS `27,428 KiB`), at the result
hash pinned above.

