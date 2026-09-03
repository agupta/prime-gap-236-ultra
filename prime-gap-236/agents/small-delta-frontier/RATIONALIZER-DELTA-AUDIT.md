# Compact band rationalizer: hostile delta audit

Date: 2026-09-02 (Europe/Berlin)

## Verdict

**SCOPED AUDIT PASS** for producer SHA
`d972aaf7881f1c1c2c9d8cc8379239f504ad49b12753d502511ea8483fe5301d`
and tests SHA
`e8b6107c4334d7f8c3b504173f1ea5d1fbb8d31709b91fb30f267e1ca266748b`.
This supersedes and retracts provenance passes for `fddb3735...`,
`09d10409...`, and `57c8ebb1...`.  The last of those had a check/rename race
in its exception quarantine: replacing the path after the saved inode stat
but before `os.replace` moved a foreign concurrent file.  The repaired
normal/optimized regression is in `test_rationalizer_hostile.py` SHA
`513903ac925a3c6b3639fa4de59b483f4eb7a5032d0cc1afd2243c452b272056`.
The output remains discovery-only and explicitly requires a fresh scalar MP
evaluation; it is not an exact integral, an error bound on a Rayleigh
quotient, or a sieve certificate.

## Counterexample and repair

The earlier producer rehashed trusted inputs before `atomic_write` but not
after publication.  Mutating the candidate inside the write boundary caused
the command to return success and leave an output claiming the old candidate
SHA.  The independent regression is
`test_rationalizer_hostile.py`.

The final producer reserves an absent destination with `O_EXCL` and writes
the final bytes only through that held `O_RDWR` descriptor.  It verifies the
owned inode, complete trusted closure, descriptor bytes, pathname bytes, and
final inode after publication.  On any exception it rewrites only the held
descriptor to strict rejection JSON; it never renames or unlinks a pathname.
If a foreign inode replaced the pathname, the held descriptor names only the
unlinked original and the foreign bytes remain untouched.  Independent tests
cover both post-publication dependency mutation and the adversarial saved-stat
replacement that broke `57c8ebb1...`.

## Exact common-grid check

For expanded coefficients `c_i`, let `M=max_i |c_i|`, `x_i=c_i/M`,
`L=10^d`, and `n_i=round(L x_i)` using exact `Fraction` arithmetic.  The
producer emits the primitive integer vector

\[
 p_i=n_i/g,\qquad g=\gcd_i |n_i|.
\]

Consequently the emitted projective vector is exactly the projective class of
`(n_i/L)`, `gcd(p_i)=1`, and

\[
 |x_i-n_i/L|\leq 1/(2L)
\]

coordinatewise, including half-grid ties (Python's exact integer tie-to-even
rule still has error exactly at most one half).  Since at least one normalized
coefficient is exactly `+1` or `-1`, quantization cannot annihilate the whole
vector.  Dividing by `g` changes only overall scale and not the reported
pre-primitive approximation error.

For the frozen near20 trial SHA `88c1d26f...` at `d=40`, an independent run of
the final producer emitted output SHA
`7da4f222c0c62f0d432ea249daacdd9634a762a71e6cd038d4ad416af95fd7d2`.
An independent parse reconstructed 272 canonical no-ones D12 labels, integer
LCM `1`, content `1`, primitive gcd `1`, maximum absolute integer `10^40`, and
ordered payload SHA
`2e09c72d30d4791f72b1da950c051f6ca2d61e5b820384432c6bc89fcd23a2a1`.

## Parser, expansion, and claim gates

- Candidate JSON rejects duplicate keys, nonfinite constants, JSON floats,
  oversized input, noncanonical or overlong rational strings, and unexpected
  schemas.
- The candidate is bound by a caller-supplied byte SHA.  The pinned C10 D12
  source/bands, `BandMap`, grouped evaluator, and exact integrator hashes are
  checked.  A quadratic candidate additionally binds the result auditor and
  quadratic postprocessor.
- The exact 20-to-272 expansion is recomputed and compared coordinate by
  coordinate to the candidate's ordered vector and the pinned source basis.
- Output fields state `rigorous=false`,
  `fresh_scalar_mp_recheck_required=true`, and
  `rigorous_identity_to_candidate=false`; no quotient or sign is emitted.

## Reproduction

```sh
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/agents/structural-basis/tests/test_rationalize_band_candidate.py -v
PYTHONPATH=prime-gap-236 python3 -O \
  prime-gap-236/agents/structural-basis/tests/test_rationalize_band_candidate.py -v
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/agents/small-delta-frontier/test_rationalizer_hostile.py -v
PYTHONPATH=prime-gap-236 python3 -O \
  prime-gap-236/agents/small-delta-frontier/test_rationalizer_hostile.py -v
```

Producer tests pass 8/8 in normal and optimized modes; the two independent
post-publication/inode-race regressions pass 2/2 in both modes.
