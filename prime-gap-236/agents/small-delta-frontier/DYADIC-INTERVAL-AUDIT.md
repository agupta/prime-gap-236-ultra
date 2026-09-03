# Hostile audit of the directed-dyadic grouped backend

Status: **SCOPED AUDIT PASS AFTER SIX REPAIRS** for the fixed-point ring and
its grouped/affine installation layer.  This is not a D12 sign, a complete
certificate driver, or a provenance audit of a future result artifact.

Frozen source SHA-256 values at the audited checkpoint:

```text
verify/dyadic_interval.py                              f6f1730f77ba490f04326338e7b3bfe5ab2e5c6438f10892bdf3f5bfe6fc875d
verify/test_dyadic_interval.py                         bf54fbfc940d292a49edd1fb2a6dd53743e36c6508527329e076caba3e6ed89e
agents/exact-integrator/dyadic_backend.py              1dae20016b5fcbde5f56cf222ce92b45899f14bd5ff07fd3c70b7b10ce4ce608
agents/exact-integrator/tests/test_dyadic_backend.py   21547aa6fba222bbcc920caa084a9ce0eaa869d586dffb93811722ce93985699
```

## Directed-rounding invariant

At precision `P`, `(lo,hi)` denotes the closed interval
`[lo/2^P,hi/2^P]`.  Rational leaves use integer floor/ceiling.  Addition and
negation are exact on endpoints; multiplication takes all four integer
products and floors/ceilings after division by `2^P`; division takes all four
endpoint ratios and rejects a denominator interval containing zero.  Integer
powers use these operations.  Thus each operation contains the corresponding
real operation by induction.  Comparisons use an exact rational shadow when
available; otherwise they return a boolean only when the two closed
enclosures prove the order and raise `IndeterminateComparison` on overlap.

The grouped installer replaces every scalar-producing hook used by the face
integrator, clears all module caches and all nine scalar-dependent
`OneStratumSupport` method caches, and installs an outward-rounded polygon
moment formula.  The orbit structure constants are copied into a validated
immutable snapshot before the closure is installed.

## Counterexamples found and repaired

1. **Live endpoints could be reinterpreted.**  Originally,
   `configure(16); x=D(1/3); configure(17)` made `x` cease to contain `1/3`
   because endpoints did not store their scale.  Configuration is now locked
   after the first interval; only an identical idempotent request is allowed.
2. **Exact-shadow hashes violated numeric equality.**  `D(1)==1` but their
   hashes differed, bifurcating dictionaries and LRU keys.  Exact-shadow
   intervals now delegate hashing to their exact `Fraction`.
3. **Exact and interval support caches collided.**  After the hash repair,
   numerically equal exact/interval support objects hit old cached Fraction
   branch constraints and marginals.  Installation now clears every
   scalar-dependent cached support method; a regression deliberately prewarms
   the old caches and requires fresh interval-valued misses.
4. **Equal enclosures falsely claimed equal numbers.**  At precision 16,
   shadow 8, the distinct rationals `1000/3001` and that value plus
   `1/655360` had the same nondegenerate enclosure and compared equal.  This
   could delete a genuinely distinct clipping vertex.  Shadowless
   nondegenerate intervals no longer claim numeric equality.
5. **Shadowless singleton hash corner.**  A proved zero-width dyadic singleton
   compared equal to its exact dyadic `Fraction` but used a tagged hash.  It
   now hashes as that exact fraction.
6. **Caller mutation changed orbit algebra after installation.**  For k=2,
   `F=P_(2)`, changing the caller-owned `((2,),(2,))` expansion to empty after
   installation changed the exact positive I enclosure to zero.  The backend
   now snapshots and validates the immutable integer expansion, including
   canonical partitions, positive multiplicities, and reverse consistency.

Each failure was reproduced before repair.  The final regression suite has
eight ring tests plus one isolated grouped/affine containment test and passes
under normal and optimized Python:

```bash
python3 -m unittest prime-gap-236/verify/test_dyadic_interval.py \
  prime-gap-236/agents/exact-integrator/tests/test_dyadic_backend.py
python3 -O -m unittest prime-gap-236/verify/test_dyadic_interval.py \
  prime-gap-236/agents/exact-integrator/tests/test_dyadic_backend.py
```

## Additional adversarial coverage

- 81,243 exhaustive operations on arbitrary signed endpoint intervals at
  low precision, including all four-corner products/divisions and every
  decided weak/strict comparison;
- 160,000 deterministic random exact expression steps with signed rational
  leaves, powers, division, and absolute value;
- 100,000 random exact floor divisions (99,968 decided correctly, 32 failed
  closed) and 400,000 decided signed comparisons;
- 320 random exact triangle moments with deliberately suppressed shadows;
- 12 signed random k=3 grouped I/J and affine I/kJ evaluations, all contained
  after exact caches were deliberately populated before installation; and
- every C10 r>=1 branch-pair polygon: 2,700 intersections and 27,000 moments
  through total monomial degree three, with exact vertex counts and exact
  Fraction values contained at 160 bits.

No directed-rounding or grouped-containment failure remains in this scope.

## Remaining result-level gates

A future D12 result must still pin and recheck the dyadic ring, backend,
grouped evaluator, exact integrator, affine evaluator, rational input, and
multiplier byte hashes; record precision and shadow limit; reconstruct the
orbit snapshot from the checked labels; and print integer endpoints for I,
kJ, and `kJ-I`.  The only rigorous success test is

```text
I.lo > 0  and  (kJ-I).lo > 0.
```

It should also agree under increased precision and reverse face order.  Those
runs are consistency checks, not substitutes for positive lower endpoints.
No D12 interval calculation was launched by this audit.
