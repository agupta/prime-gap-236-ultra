# Truncated lower-energy v3 hostile audit

## Verdict

**`AUDIT PASS` for the frozen one-outer-band tuple, with an independent
continuum-completion finding.**  Reconstructing the primary definitions and
the sorted-removal packing argument confirms every exact minimum recorded in
the frozen result.  All 43,008 nonempty Type-IIc cells pass, the retained and
deleted band inventory is exact, and the direct Heath--Brown route supplies
the four Proposition-1 hypotheses without invoking Propositions 2 or 3.

The producer's Type-IIb breakpoint oracle is not generically complete: it
omits ordinary sorted-prefix equality roots.  The independent checker inserts
all 2,522 missing roots for this tuple and checks 24,226 endpoints/intervals
instead of 19,182.  No inserted root changes the frozen minimum or produces a
counterexample.  Thus this is an implementation/proof-description defect in
the reusable oracle, not a counterexample to the exact frozen support tuple.

This audit makes no Riesz-energy, quotient, or bounded-gap theorem claim;
`theorem_ready=false`.

## Frozen inputs and independent artifacts

| File | SHA-256 |
|---|---|
| `agents/analytic-new-lever/verify_truncated_lower_energy_v3.py` | `fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5` |
| `agents/analytic-new-lever/truncated_lower_energy_v3_exact.json` | `c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f` |
| `agents/analytic-new-lever/test_truncated_lower_energy_v3.py` | `9b0e1409ef4ea2dda1292a69881c344a35d52f4886f0568c0e8a71f806d0b1fa` |
| `agents/analytic-new-lever/verify_three_outer_energy_v2.py` | `87747ad848c502e4d0047d60ca324d77ba94c9b0f5cb2afd6b5d46b953575605` |
| `agents/analytic-new-lever/verify_two_outer_band_v1.py` | `187a87f6c29532645100d9a91b94ce8038c38511dfff22326efe9722ea0f8001` |
| `agents/analytic-new-lever/verify_adaptive_support_v1.py` | `b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d` |
| `sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex` | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| `sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex` | `60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30` |
| `sources/polymath8-edz-1402.0811-src/newergap.tex` | `fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea` |
| `agents/audit/verify_truncated_lower_energy_v3_hostile_audit.py` | `b4e889ab47690fb8619342267e4259dab5b31882ef5a25b9015957d4e210394b` |
| each independent result (`normal`, `opt`, canonical) | `fea750c78b8bc7a022d8ee7d407a59405f4f790b1729305f47b21f8d4f2117a1` |

The independent checker imports no producer or packing module.  It snapshots
the primary sources and frozen dependencies, reconstructs the arithmetic
first, and only then strictly parses the producer artifact.  Duplicate JSON
keys, floating-point values, non-ASCII content, missing final newline,
non-regular files, hard links, hash changes, and mutation during the audit are
rejected.

## Support and band inventory

The exact parameters reconstructed from Definition 1 are

```text
delta=1/60, epsilon=3/400,
A=(-3/400, 1/4, 9230917/36000000).
```

The endpoint `9230917/36000000` retains 37/40 of the former outer-band
width.  The old middle endpoint `3081133/12000000` and old top endpoint
`231241/900000` are absent.  The result contains exactly one outer band.
Inner counts `0,...,15` and outer counts `0,...,12` are active.  The first
empty outer reserve is `3749/750000`; every cap column and weak plateau step
passes literally.

The source-geometry inequalities for Type 0, direct II, IIa, IIb, IIc, III,
prime squares, and higher prime powers were recomputed as exact fractions for
the near, mixed, and outer regimes.  The least source reserve is
`1/200000000000`, the strict Type-IIc factor-width margin.

## Sorted-removal packing reconstruction

The fixed inventory consists of 582 main ordered pairs, 168 near ordered
pairs, 39 zero-left cases, 39 zero-right cases, and four explicit `(0,0)`
families.  All 1,500 fixed IIa/III checks pass.  The least reserve is

```text
34448999/5000000000
```

for inner/outer counts `(1,4)`, Type IIa, using the all-first action.  The
enhanced action is selected 283 times and repairs 18 ordinary-prefix
failures.

For Type IIb, let `K=C+D` be the selected third-bin total, `S` the residual
total cap, `B` the chosen pool cap, and `r` an ordinary sorted-prefix length.
Besides the third-bin, overload, cross-pool, and crossing-item roots used by
the producer, the action can change at

```text
C_root=(n-r+1)K-(n-r)S-B,
gamma=C_root+3*zeta+r0.
```

For `r>=2` these roots are not redundant with the producer's listed roots.
Inserting all of them adds 2,522 unique breakpoints.  The completed partition
contains 24,226 exact endpoint/interval probes and selects a nonempty third
bin 6,387 times.  Every probe passes.  Its least reserve remains exactly the
producer value

```text
140008691/30000000000000
```

for inner/outer counts `(1,1)` at the endpoint
`11936390009/30000000000`.

For Type IIc, the only nonempty family is outer/outer.  There are 168 ordered
count pairs and 256 adverse omega/gamma cells per pair: exactly 43,008
nonempty cells, plus 256 explicit empty-tuple cells.  Independently sorting
the removed entries into three consecutive blocks gives 36,927 cells solved
by one alternate action and 6,081 requiring the three-block action.  The
least reserve is

```text
71/66000000
```

at counts `(11,11)`, cells `(12,8)`, right removal 6, block sizes `(2,3,1)`,
assigned in order `(3,1,2)`.  This exactly matches the producer result.

## Cap translation and Proposition-1 interface

The certified perturbation is a common outer-cap translation of radius
`1/10000000`.  Both endpoints retain the same active counts and pass the
completed Type-IIb partition and all Type-IIc cells.  At the adverse upper
endpoint the least fixed, IIb, and dynamic reserves are respectively

```text
34448499/5000000000
137008691/30000000000000
349/330000000.
```

As established independently in the frozen base hostile audit, the direct
Heath--Brown reduction supplies equidistribution for

```text
rho(n;x)=(log n/log(3x))*1_P(n) on [x,2x], zero outside.
```

Together with `0<=rho<=1_P`, beta `1/2`, and the prime-number-theorem mass,
this gives Proposition 1 with `c1=c2=0`.  Printed Proposition 2's universal
`H` hypothesis is neither proved nor used, and Proposition 3 is bypassed.

## Dual-mode regression

The producer reproduced its canonical artifact byte-for-byte in normal mode
(`101.36 s`, RSS `22,596 KiB`) and `python3 -O` (`103.72 s`, RSS
`27,044 KiB`).  Its five regression tests passed in both modes (`102.36 s`,
RSS `22,984 KiB`; `102.44 s`, RSS `26,620 KiB`).

The independent completed-continuum result is byte-identical in normal mode
(`95.47 s`, RSS `23,484 KiB`) and `python3 -O` (`88.10 s`, RSS
`27,644 KiB`), at the result hash pinned above.
