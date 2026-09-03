# Cached-v7 `R<=9` one-band assembler hostile audit

## Verdict and scope

**PRE-CERTIFICATE AUDIT PASS for the frozen aggregation/projection layer.**
The source audited here is

```text
verify/assemble_one_band_236_cached_v7_r09.py
aaa3dc5199636da3dcff198fd16a84b097a192a72d89a5326dc690206946ce29
```

and its production tests are

```text
verify/test_assemble_one_band_236_cached_v7_r09.py
261077214d0d523db0da5ce83ee885cdab4d2c0a0d6a7816790cbb22a1b2183f
```

The independent hostile test is

```text
agents/audit/test_assemble_one_band_236_cached_v7_r09_independent.py
bdcd3e2e860b29a6eb3e0482582c2bf5b6c06f973b248a2c4e78d8eaf82bd992
```

This verdict establishes the exact count/branch selection and the scalar
algebra, inventory, source closure, and publication behavior of these bytes.
It is not an integration replay, does not assert that any target cached-v7
shard exists, does not assert a positive scalar margin, and is not a theorem
verdict.

## Definition-5 derivation independent of the implementation narrative

Definition 1 in the pinned Stadlmann TeX defines the large-coordinate set by

```text
I(t)={i:t_i>delta}.
```

For a Definition-5 marginal, write the 47 shared coordinates as `u`, put
`r=#{i:u_i>delta}`, and call the distinguished outer coordinate `t`.  The
new symmetric direction is

```text
H_9(u,t) = 1_{r+1_{t>delta}<=9} H_full(u,t).
```

Consequently its marginal is, up to the null endpoint `t=delta`,

```text
m_H9(u)
 = 1_{r<=9} integral_{t<=delta} H_full(u,t) dt
 + 1_{r<=8} integral_{t>delta} H_full(u,t) dt.
```

This identity alone gives the complete branch schedule:

| shared count `r` | small distinguished (`t<=delta`) | large distinguished (`t>delta`) |
|---:|:---:|:---:|
| `0..8` | keep | keep |
| `9` | keep | discard |
| `>=10` | discard | discard |

The frozen cross engine constructs the right-hand outer polynomial with
`distinguished_components`, while the left-hand inner polynomial has already
been fiber-integrated by `marginal_polynomial`.  Its two `S` domains,
`Sdelta` and `Stotal`, partition the available small distinguished fiber; its
two `L` domains, `Ltotal` and `Lbig`, partition the large distinguished fiber.
Thus the assembler's rule—four branches for common `r=0..8`, only
`Sdelta+Stotal` for common `r=9`, and no shards for `r>=10`—is exactly the
literal indicator above.  It does not depend on the nonuniform cap index or
on an endpoint convention.  The endpoint `t=delta` is small under the source
definition and in any event has measure zero.

For each retained common count, Definition 5 and symmetry contribute the
factor `k=48` exactly once.  The outer band is an upper cumulative endpoint
minus a lower cumulative endpoint, so the exact retained `r=9` contribution
is

```text
48 * ((high.Sdelta + high.Stotal)
      - (low.Sdelta + low.Stotal)).
```

The independent test perturbed every high and low small branch separately
and observed the signed change `+48*q` or `-48*q`.  It also perturbed every
large branch and verified that the selected `r=9` value was invariant while
the audited full-shard value changed.

## Diagonal energy and projection algebra

The exact total-count strata are disjoint apart from measure-zero faces, so

```text
I(H_9) = sum_{R=0}^9 I(1_{total-count=R} H_full).
```

The assembler therefore validates all thirteen immutable `A` shards but
sums exactly counts `0..9`; counts `10..12` are preserved with their hashes
as explicitly zeroed rows.  The mixed term sums common counts `0..8` in full
and the small-distinguished part of common count `9`, as derived above.

Writing `D=I(F)-48J(F)>0`, `A=I(H_9)`, and `b=48J(F,H_9)`, the inner and
outer total-sum bands have zero `I` cross term and `48J(H_9)>=0`.  At
`c=b/A`,

```text
48J(F+cH_9)-I(F+cH_9)
 >= -D + 2*c*b - c^2*A
  = (b^2-A*D)/A.
```

This gives exactly the assembler's sufficient sign test `b^2-A*D>0` and its
reported lower bound

```text
1 + (b^2-A*D)/(A*I(F)+b^2).
```

The scales are internally consistent: `A` carries `10^76`, `b` carries
`10^125`, and `I,D` carry `10^174`, so both terms in the margin carry
`10^250`.  An injected, unrelated exact fixture independently reconstructed
every scalar, row, hash, mixing coefficient, margin, denominator, and
quotient.

## Fail-closed structure

- `require_mixed_files` requires precisely regular, non-symlink files
  `common_r_00.json` through `common_r_09.json`; missing, extra, and symlink
  mutations fail.
- Every selected mixed shard is first passed as the exact byte snapshot to
  the pinned full cached-v7 result audit.  That audit checks exact schema,
  canonical rationals, the full branch inventory, `H=14-r`, factor 48,
  fixed-denominator and cache metadata, geometry, scaling, and the live
  transitive source closure.  The `r=9` selector then parses the same bytes.
- The output row hashes bind the exact bytes used in the computation.  Later
  replacement of a pathname cannot change the computed fraction.
- The flat runtime closure is exactly the 42-entry audited full-v7 assembler
  closure plus the full-v7 assembler itself, for 43 end-rechecked pins.  The
  `R<=9` assembler is separately bound by the mandatory external self hash.
- All runtime source snapshots are compared again before publication.
- Publication uses the inherited `O_EXCL`, write, flush, and `fsync` path;
  a pre-existing output is not overwritten.
- The production source contains no Python `assert`, floating-point
  arithmetic, subprocess, pickle, `eval`, or `exec` path.  Normal and
  optimized modes exercise the same explicit exceptions.

## Test evidence

The production suite passed `3/3` in normal and optimized modes.  The
independent suite passed `10/10` in normal and optimized modes.  Its coverage
includes:

- exhaustive exact low-`k` count classification for every possible common
  count, every cap, and rational fibers below, at, and above `delta`;
- all target count rows and the strict endpoint convention;
- all four exact branch values, both endpoint orientations, factor 48,
  cancellation/sign mutations, missing branches, malformed counts, and a
  noncanonical rational;
- complete mixed-shard inventory and regular-file rules;
- independent exact reconstruction of truncated `A`, mixed `b`, margin,
  quotient, and every serialized row hash;
- equality and live hashing of all 43 runtime pins;
- dependency TOCTOU rejection and exclusive-publication preservation.

Replay with a private empty bytecode cache:

```bash
cd prime-gap-236
python3 -B -I -X pycache_prefix=/tmp/r09-prod-normal \
  verify/test_assemble_one_band_236_cached_v7_r09.py
python3 -B -O -I -X pycache_prefix=/tmp/r09-prod-opt \
  verify/test_assemble_one_band_236_cached_v7_r09.py
python3 -B -I -X pycache_prefix=/tmp/r09-audit-normal \
  agents/audit/test_assemble_one_band_236_cached_v7_r09_independent.py
python3 -B -O -I -X pycache_prefix=/tmp/r09-audit-opt \
  agents/audit/test_assemble_one_band_236_cached_v7_r09_independent.py
```

## Remaining gate

No `R<=9` aggregate or compact certificate was available during this audit.
Any target result still requires strict result-level checking, independent
integration replay of the selected `A` and mixed contributions, exact
positive-margin verification, and the full analytic/theorem audit.  This
report grants no inheritance of a future result-level verdict.
