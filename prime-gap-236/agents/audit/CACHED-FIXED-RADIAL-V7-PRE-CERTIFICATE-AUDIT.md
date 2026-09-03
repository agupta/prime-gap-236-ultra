# Cached fixed-denominator radial v7 hostile audit

## Verdict

**SCOPED PRE-CERTIFICATE AUDIT PASS** for the frozen cached backend/runner:

```text
backend 79c9a8ef26de0b7fba55fbdb6e113a88f0b52b20f9cbcb34cbc2dbb507ba74c4
tests   0f0bd15426ff961e47281b32d57795f1848e75280fd645abc599df8d1410fd5b
runner  b427c6961c377cb79d5a72b54f8c2e8c7642b87d66d338f53b5dc56d98991984
```

The target `r=12` launch remained in progress when this source verdict was
updated.  No target v7 result is covered here; any landed result requires the
separate checker and result-level verdict below, with exact comparison to a
same-r v6 shard when one exists.

## Exact identity and cache safety

V7 changes no coefficient formula.  It calls the audited v6 falling-factorial
convolutions and only caches these immutable quantities:

```text
factorials_through(ceiling)
factorial_ratio(ceiling,x_power,y_power)
delta_scales(delta_numerator,delta_denominator,maximum_degree,total_degree)
```

The keys contain every argument on which the returned value depends.  The
first and third return tuples and the second returns an integer; no caller
mutates a cached object.  Face size, number large, orbit multiplicity, shift,
partition split, family coefficient, and common gcd are all applied outside
these caches.  Alternating cold/warm and reverse-order calls across different
deltas, ceilings, degrees, faces, parts, and shift bounds produce exactly the
v6 integer maps.

The independent suite covers empty/odd/repeated parts, `n=0..6`, every face,
three rational deltas including nonunit numerators, 40 deterministic random
family maps, and target dimension `n=47` at `r=0,1,11,12,46,47` with the
`14-r` shift boundaries.  Packed rows and reduced denominators equal v6
exactly.

`cached_factorial_ratios` and `cached_delta_scale_tables` are cumulative
`cache_info().currsize` values in the current process.  They are cache-entry
inventory, not multiplication counts, cache-hit counts, or mathematical
certificate fields.  They can legitimately depend on earlier calls in a
reused process; the production runner uses a fresh process.  A result checker
must treat them as nonnegative diagnostic counts and never demand equality to
v6, which has no such fields.

## Frozen target result checker

```text
agents/audit/verify_cached_v7_cross_shard.py
80ec3329215f66e784708039f9a1d673d7064769c48a31825961dc44f6ae7343

agents/audit/test_verify_cached_v7_cross_shard.py
669ab6178848201927a42c36c9271a27c119f67038606873ca9924a2883db186
```

The checker requires the exact identity, v7 algorithm map, and complete live
and serialized source closure.  For the fresh runner process it verifies

```text
cached_delta_scale_tables <= min(E+1, orbit_transforms),
cached_factorial_ratios <= (factorial_ceiling+1)^2.
```

It then removes exactly those two diagnostics and renames only the cached
radial timing label.  The normalized object goes through the pinned fixed-v6
checker `46a8...`, which rechecks exact branch geometry, `H=14-r`, fixed
denominator, active families, work inventories, and factor 48.  An optional
same-r v6 reference is itself audited and compared in every mathematical,
branch, and fixed-radial field.  Mutation tests pass 9/9 in normal and
optimized mode.

## Source and publication closure

The runner recursively pins v6, v5, v2, the base runner, all backends/tests,
and the primary candidate/support closure.  All live bytes matched.  It
rechecks each snapshot after computation and publishes through the audited
same-directory temporary-file, `link(O_EXCL)`, file-fsync, directory-fsync
path.  No mutable global other than the three exact caches is consulted by the
new transform.

## Reproduction

```bash
python3 agents/exact-projection-engine/test_cached_fixed_denominator_radial.py
python3 -O agents/exact-projection-engine/test_cached_fixed_denominator_radial.py
python3 agents/audit/test_cached_fixed_denominator_radial_v7_independent.py
python3 -O agents/audit/test_cached_fixed_denominator_radial_v7_independent.py
python3 agents/audit/test_verify_cached_v7_cross_shard.py
python3 -O agents/audit/test_verify_cached_v7_cross_shard.py
```

Production passes 2/2 under both interpreters.  Independent tests pass 5/5
under both interpreters; SHA-256:

```text
a0e01aca8c9ce81b4473f25cc4e447e7cff19aec35c5aae9d4a8bf6b48c12f22
```
