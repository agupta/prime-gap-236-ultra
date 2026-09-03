# C10 D12 fixed-vector dyadic driver: hostile prelaunch audit

Date: 2026-09-02 (Europe/Berlin)

## Verdict

**SCOPED PRELAUNCH AUDIT PASS** for unlaunched driver SHA
`1759db7e6c03bc25fb9b0d3826413f548deb3dff8bb87a7bc5b6869c2d6556ed`
and producer tests SHA
`533cbb264709d2a17196903f827fa31dfbed11e1c5c30849374253b5d219b000`.
No target D12 integration was launched.  Even a positive output has
`theorem_ready=false` and requires an independent output audit and a second
reconstruction.

## Counterexamples repaired

Against the preceding driver SHA `1dfa65ca...`:

1. At precision 384, a staged singleton interval with
   `lo_integer=hi_integer=2^384`, Boolean `lower_fraction=true` and
   `upper_fraction=true`, and string width `"0"` was accepted as `[1,1]`.
   The repaired parser requires every endpoint/integer token to be a nonempty
   canonical string and rejects Boolean/integer substitutes.
2. Input, stage, driver, and dependencies were rehashed before publication
   but not after it.  Mutating the pinned input inside the output-write
   boundary allowed the old driver to return a positive result.  The repaired
   driver rehashes input, stage, output, driver, and the complete dependency
   closure after publication; failure replaces the accepted-looking file by
   a strict `theorem_ready=false` failure record.

The independent repaired regressions are in
`test_fixed_dyadic_hostile_extra.py` SHA
`24c6216a035705f6af075bba64502c2cd9cb3973114b72d8722b56b6b28b6721`.

## Arithmetic and scaling

The loader accepts only a pinned input byte SHA, strict JSON, 272 distinct
canonical labels whose set is the complete no-ones degree-at-most-12 basis,
and 272 canonical rational coefficients.  If `L` is their common denominator
and `g` the integer content, it evaluates the primitive vector

\[
 v_i=(L/g)c_i.
\]

The scale `L/g` is positive, so both quadratic forms are multiplied by its
positive square and the Rayleigh sign is unchanged.  The frozen source
reconstructs a 714-bit `L`, content `1`, 272 coordinates, ordered payload SHA
`8ea54de0...`, and exactly 5,929 orbit-product pairs.

The support is the pinned C10 point

\[
(k,\alpha,\eta,\delta,B_1,B_2,B_{\ge3})=
(48,79247/300000,76247/300000,1/100,3/20,3/20,97/625).
\]

The single distinguished-coordinate integral returned by the grouped engine
is `J`.  The driver forms `M2=48*J` exactly once and accepts only

```text
I.lo > 0 and (48*J-I).lo > 0.
```

The equality case is rejected.  No positive-definiteness or matrix
invertibility assumption is made.

## Independent containment and traversal checks

A signed `k=2` four-label Fraction oracle gave

```text
I = 1938469/15000000, groups=4, faces=15
J = 12066211/262500000, components=5, domains=31.
```

At 384 dyadic bits, both forward and fully reversed serial `r` traversals
enclosed these exact `I` and `J` values.  Reverse mode reverses the complete I
list `max_r,...,0` and complete J list `max_r,...,0`; reverse with more than
one worker is rejected rather than silently using a non-reversed fork path.

The stage parser checks exact field sets, recursively type-exact common
metadata (so `bool` cannot impersonate `int`), canonical interval endpoints,
strictly positive `I.lo`, traversal counts 1,575/312, finite nonnegative
timing values, and nonnegative integer RSS values.  J requires 695 marginal
components and 1,200 branch domains.  Input/stage/output path collisions with
each other or protected code are rejected, and a stale stage/output is
replaced by an incomplete non-certificate sentinel before input parsing.

## Reproduction

```sh
cd prime-gap-236
PYTHONPATH=.:agents/exact-integrator:agents/exact-integrator/src \
  python3 verify/test_c10_d12_fixed_vector_dyadic.py -v
PYTHONPATH=.:agents/exact-integrator:agents/exact-integrator/src \
  python3 -O verify/test_c10_d12_fixed_vector_dyadic.py -v
PYTHONPATH=.:agents/exact-integrator:agents/exact-integrator/src \
  python3 agents/small-delta-frontier/test_fixed_dyadic_hostile_extra.py -v
PYTHONPATH=.:agents/exact-integrator:agents/exact-integrator/src \
  python3 -O agents/small-delta-frontier/test_fixed_dyadic_hostile_extra.py -v
```

The producer suite passes 9/9 and the independent suite passes 3/3 in both
normal and optimized modes.

## Scope limitations

- No D12 target traversal or sign computation was performed by this audit.
- A caller-supplied I-stage SHA is a staged-computation binding, not a proof
  that an arbitrary third-party stage was honestly produced; final use must
  reconstruct/audit the I stage.
- Directed interval correctness still depends on the separately audited and
  pinned dyadic/backend/integrator closure recorded in the driver.
- `theorem_ready=false` is deliberate until a positive output, independent
  reconstruction, and analytic proof audit all pass.
