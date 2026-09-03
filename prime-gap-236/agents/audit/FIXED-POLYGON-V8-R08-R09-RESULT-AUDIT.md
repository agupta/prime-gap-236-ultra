# Fixed-polygon-v8 target shard result audit: common `r=8,9`

## Verdict and scope

**RESULT AUDIT PASS** for exactly these immutable target files:

```text
agents/exact-projection-engine/results/d14_grid38_scaled_b_fixed_polygon_v8/common_r_08.json
ffbeb7f3cbc13c279a8c89b561d93af36fafed8d2442c90d22bb6c244e531631

agents/exact-projection-engine/results/d14_grid38_scaled_b_fixed_polygon_v8/common_r_09.json
e9397f72f78f9ad53716d61bb3f10854a640081f81632028904836d6c6778d88
```

The externally pinned checker was

```text
agents/audit/verify_fixed_polygon_v8_cross_shard.py
ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c
```

Normal and optimized checker outputs were byte-identical for each shard,
with audit-output hashes

```text
r=8  777497dbaf94598bae0396b3bd055ab586b6bf4b0eb5eb03c22625f354257794
r=9  86b8926e29c358fee4b1a1e779bebbb107692404e2e94c639b6526cff09ca45f
```

This is a shard result verdict, not an aggregate/certificate or theorem
verdict.  No same-count independent engine result existed during these two
checks; future Green-v9 equality provides an additional gate.

## Independent exact checks

Both files are canonical ASCII JSON objects with the exact 17-field v8
schema, exact v8 format/status/algorithm, `rigorous=true`, no serialized
matrix input, producer hash `36a8e027...`, `k=48`, and the pinned rational
geometry.  Their identical 29-entry serialized source maps have canonical
map hash

```text
2f79d61724bd9690b964bc855fb1005e1073150bf4e0507730092bf214f6f814
```

and every listed digest independently matched the current source bytes.

For each shard all four high and all four low values—`Sdelta`, `Stotal`,
`Ltotal`, and `Lbig`—were independently parsed as canonical reduced
rationals.  Direct exact recombination verified

```text
scaled_b_shard = 48 * (sum(high branches) - sum(low branches)).
```

Both full values are positive.  To avoid treating unwieldy decimal displays
as evidence, the exact canonical fraction strings have hashes and sizes

```text
      fraction SHA-256                                           numerator bits  denominator bits
r=8   f9768521630bec553ded76a6dacdae9360318e4ccfc9c7ea9a4bca29d8c357a4     2364             2477
r=9   a10c4d1f46a563ac7eb792152cdad00854d43e937943401afc78ef0bf005e9c8     2338             2458
```

For the symmetric total-large-count-`<=9` direction, the `r=9` shard retains
only `Sdelta+Stotal`.  The exact selected fraction

```text
48*((high.Sdelta+high.Stotal)-(low.Sdelta+low.Stotal))
```

is positive and its canonical fraction-string SHA-256 is

```text
21dde6c965a67f15a6eceee9e42a53c736f17fe81e7e3bfd35a7def4c2833f0e
```

with 2344 numerator bits and 2464 denominator bits.  This selection is not
used to reinterpret the file's full-shard identity; it is recorded for the
later `R<=9` aggregate.

## Radial and work metadata

Both records have maximum orbit degree 32 and forced factorial ceiling
`32+46=78`.  With `delta=1/60`, the independent checker constructed

```text
D = 60^32 * 78!
```

and verified the reported reduced radial denominator divides `D`, the
quotient has the reported common-gcd bit length, and all family/radial/
combined denominator bit lengths agree with the exact serialized integers.
The strict inclusion-exclusion ceilings are

```text
r=8: H=14-r=6
r=9: H=14-r=5.
```

Every endpoint branch has respectively seven and six active shifts.  All
three families `large`, `small`, `small_total` are active, so no family is
silently pruned.  The independently summed work totals are

```text
      scalar products   surviving final product monomials
r=8     275,256,504                    36,778
r=9     233,384,424                    31,524
```

and agree with the checker output.  Family coefficient totals, orbit-tag
associations, transform counts, packed terms, cache-table inventories, and
per-branch requested moments satisfy every exact v6/v7 relation.

The recorded total wall times and peak RSS were 1046.608 seconds/774816 KiB
for `r=8` and 897.478 seconds/666460 KiB for `r=9`.  These host-dependent
fields were checked only for exact type, finiteness, nonnegativity, and
component consistency; they do not enter any mathematical comparison.

## Replay

```bash
cd prime-gap-236
python3 -B -I -X pycache_prefix=/tmp/v8-r8-normal \
  agents/audit/verify_fixed_polygon_v8_cross_shard.py \
  --expected-self-sha256 ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c \
  agents/exact-projection-engine/results/d14_grid38_scaled_b_fixed_polygon_v8/common_r_08.json
python3 -B -O -I -X pycache_prefix=/tmp/v8-r8-opt \
  agents/audit/verify_fixed_polygon_v8_cross_shard.py \
  --expected-self-sha256 ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c \
  agents/exact-projection-engine/results/d14_grid38_scaled_b_fixed_polygon_v8/common_r_08.json
python3 -B -I -X pycache_prefix=/tmp/v8-r9-normal \
  agents/audit/verify_fixed_polygon_v8_cross_shard.py \
  --expected-self-sha256 ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c \
  agents/exact-projection-engine/results/d14_grid38_scaled_b_fixed_polygon_v8/common_r_09.json
python3 -B -O -I -X pycache_prefix=/tmp/v8-r9-opt \
  agents/audit/verify_fixed_polygon_v8_cross_shard.py \
  --expected-self-sha256 ec0162a73381d031e4ab7b5d8cb1fa16381e41f19c74a6fd74aafa0c30a8655c \
  agents/exact-projection-engine/results/d14_grid38_scaled_b_fixed_polygon_v8/common_r_09.json
```

Any byte change retires this verdict.  These two passes cannot be extrapolated
to another common count or promoted to the final scalar inequality without
the remaining exact shards, aggregation, standalone replay, and analytic
audit.
