# Recovered 20-band gradient hostile audit

Date: 2026-09-02 (Europe/Berlin)

## Verdict

**SCOPED AUDIT PASS (discovery output only).**  The current recovery wrapper
does what it claims: it rejects every raw artifact except the byte-pinned
completed traversal, rechecks the substantive producer/provenance gates, and
replaces the nine last-place rounded diagnostic halves by the *exact rational
halves of the serialized Decimal gradient strings*.  It does **not** prove
that those decimals are exact form actions, does not evaluate a new vector,
and supplies no finite-step quotient or theorem certificate.

The retired wrapper/artifact hashes `b0b6eee7...` / `d838bbc8...` are not
covered.  The audited current objects are:

- raw rejected traversal SHA
  `0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d`;
- recovery wrapper SHA
  `9342fa3f6d8157a4d9b8603a20bb0527b7f47087a5aa3c9d39aebef892f9fee5`;
- recovered-v2 artifact SHA
  `6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43`;
- hostile-test SHA
  `a9926cefa7ed92b30abeac3801a8866fac4ffe97b593b28b898e9579c9c1a716`.

## Line-by-line findings

1. The wrapper pins the raw, baseline, 272-term source, 20-band map, sparse
   producer, band dependency, grouped evaluator, and integrator at lines
   32--47 and 78--92.  The active invocation's source, bands, raw, baseline,
   wrapper, and dependency paths are pairwise distinct; lines 95--101 reject
   a destination alias with any of them.
2. Lines 132--169 require the exact raw byte SHA, rejected/discovery status,
   `complete=true`, the full producer-gate key set, and
   `gradient_halves_match` as the sole false gate.  They independently bind
   source/bands/dependency hashes, `k=48`, dimensions `272` and `20`, C10
   parameters, precision 100, two workers, and five length-20 channels.
3. Lines 173--207 recompute the base denominator, numerator, quotient, Euler
   identities, 16-stratum sums, finiteness, and positivity at Decimal100.
   Lines 236--266 additionally require traversal counts
   `(1575,312,695,1200)`, 16 I/J buckets, the pinned baseline and its source
   dependencies, a 50-digit baseline agreement, and positive resource data.
4. Lines 209--232 use exact `Fraction` arithmetic for the only recovery:
   `gradient/2`.  The mismatch sets must be exactly
   `A: {7,12,16,17}` and `B: {10,16,17,18,19}`, with each relative mismatch
   at most `10^-98`.  An independent payload contraction confirmed all 40
   emitted fractions equal the corresponding serialized gradient divided by
   two.
5. Lines 290--323 label the result `rigorous=false`, state the narrow recovery
   meaning, and emit neither a projected trial nor projected quotient.  Lines
   325--339 rehash every trusted byte immediately before file-fsync and atomic
   replacement and repeat the alias check.

## Hostile tests

The following passed under normal and optimized Python (`3/3` each):

```sh
PYTHONPATH=prime-gap-236/agents/structural-basis/code \
  python3 prime-gap-236/agents/structural-basis/tests/test_recover_band_gradient.py -v
PYTHONPATH=prime-gap-236/agents/structural-basis/code \
  python3 -O prime-gap-236/agents/structural-basis/tests/test_recover_band_gradient.py -v
```

They cover the actual byte-pinned recovery, a material gradient mutation, and
destination aliases.  I separately parsed the frozen recovered-v2 artifact
and checked all 40 rational-half identities against the frozen raw bytes.

## Exact limitation and permissible next use

The label “exact fraction half” means exact as a rational interpretation of a
100-digit serialized Decimal, not an exact integral.  A rational trial can be
selected without making a quotient claim: for example, form the exact
serialized residual direction

\[
  h_j=D\,g^{(N)}_j-N\,g^{(D)}_j,
\]

where `D,N,g` are interpreted as Fractions from the recovered strings, then
map the 20 band coordinates back to the 272 coefficients and rationally
normalize.  Such a vector remains discovery-only and must be freshly
reevaluated by a scalar capped integrator.  Neither the recovery nor the sign
of its base-point directional derivative supplies a finite-step Rayleigh
bound.

The wrapper does not fsync the containing directory after `os.replace`, and
does not lock inputs against a malicious concurrent writer in the tiny gap
after the final rehash.  Those are durability/concurrency limitations, not a
false arithmetic acceptance of the frozen byte-pinned artifact; any consumer
must pin the recovered artifact and revalidate its input hashes.
