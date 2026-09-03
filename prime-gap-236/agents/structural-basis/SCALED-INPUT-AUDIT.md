# Adversarial audit of the integer-scaled D12 input

Date: 2026-09-01

## Final artifacts

```text
source D12 JSON
  719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87
integer-scaled input
  8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93
generator make_integer_scaled_input.py
  ba96aeb3a794dcedea342bdee29e945bb3ce3addb33d690d40f384e0b52e78f9
independent checker verify_integer_scaled_input.py
  546f2e8fe020507a78ec86808bd2785502c30ac674f645cf7c655f8f970d80d0
producer mutation tests
  4f9168a555cbc6e96b6d99fc7a9e4bcbc642fdc721599a4137982de6f172bfa0
independent audit tests
  bce3de67ab0c53d47ad10f2bce739d8402de9a30ebcd1801eda69bc370e6eee5
```

The scaled input is
`agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12_integer_scaled.json`.
It preserves the production loader's `basis` and `rational_vector` keys; every
new vector token is an integer string.

## Independent arithmetic check

The audit parsed the 272 source coefficients as exact `Fraction`s and rebuilt
their least common denominator by the gcd recurrence

```text
L <- L/gcd(L,d_i)*d_i.
```

The result equals the 215-digit metadata value and has 714 bits.  For every
index, independently,

```text
scaled[i] == L * source[i]
```

as a Fraction with denominator one.  All 272 tokens have the strict grammar
`-?(0|[1-9][0-9]*)` with the canonical zero exception, their gcd is one, and
their ordered basis is exactly the source basis of dimension 272.  Thus the
scaled polynomial is `L*F`, and both quadratic forms and their margin are
multiplied by the positive factor `L^2`.

Generating from an absolute source path and from the documented relative path
produces byte-identical output, in both cases equal to scaled SHA-256
`8650e44c...`.  The independent checker accepts both absolute and relative
verification commands.

## Counterexamples found and repaired

The first checker accepted an artifact whose sole mutation was
`basis_dimension: 272 -> 271`; it also parsed decimal-looking integer values via
`Fraction`.  The repaired checker requires exact top-level and metadata schemas,
status, basis dimension, canonical integer strings, the exact LCM, all 272
scaling relations, primitive content, source hash, form-scale text, and the
boolean sign-preservation field.

The next generator stored the argv spelling of the source path, while the
checker required canonical `results/<basename>` metadata.  Consequently a
generator invocation with an absolute source path created an output which its
own checker rejected.  The generator now canonicalizes that metadata, and an
absolute generator-to-checker roundtrip is a mandatory test.  These repairs do
not change the production scaled artifact hash.

After repair, the audit independently mutated each of the following and
confirmed nonzero checker exit status:

- one integer coefficient;
- the claimed LCM;
- the source SHA;
- the sign-preservation boolean;
- an extra metadata key;
- vector truncation;
- basis order;
- basis dimension, status, form-scale text, decimal integer syntax, and an
  extra top-level key in the producer suite.

## Commands and verdict

```sh
cd prime-gap-236/agents/exact-integrator
python3 -m unittest tests/test_integer_scaled_input.py -v

cd ../../../
python3 -m unittest \
  prime-gap-236/agents/structural-basis/tests/test_scaled_input_audit.py -v
```

The producer suite passes 8/8 tests and the independent suite passes 3/3 tests.

`SCALED INPUT AUDIT PASS` after the two repairs above.  This verdict covers
only deterministic vector scaling and provenance.  It does not assert a capped
D12 quotient or trust any serialized matrix.
