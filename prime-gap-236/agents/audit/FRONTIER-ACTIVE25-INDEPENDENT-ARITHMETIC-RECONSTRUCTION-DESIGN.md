# Independent arithmetic reconstruction for the active25 D16 pencil

Status: implementation design for the successor to the rejected staged-v4
package.  This is not a launch authorization or a certificate.

## Trust model and process boundary

The final checker should be a one-shot fresh process invoked as

```text
python3 -I CHECKER --expected-self-sha256 CHECKER_SHA \
  --record-dir PRODUCER_RECORDS --expected-manifest-sha256 MANIFEST_SHA \
  --candidate ASSEMBLED_CANDIDATE --expected-candidate-sha256 CANDIDATE_SHA \
  --output FRESH_AUDIT_OUTPUT
```

It must reject unless its source hash equals the externally supplied hash
before opening either input directory.  It should not expose an import-callable
production function or replaceable clock, reader, runner, or arithmetic hook.
The bounded threat model assumes the fresh isolated interpreter and standard
library are not themselves modified after launch.

The checker should run all 26 reconstructions in this single process, with an
external wall timeout.  Its projected runtime is well below four hours and its
memory use is modest; avoiding checker checkpoints removes an entire ledger
and resume trust surface.  It writes exactly one O_EXCL result through a held,
bound output-directory descriptor and fsyncs both file and directory.

## Static mathematical closure

The checker may import the frozen low-level exact arithmetic core, but it must
not import the staged producer or assembler and must not call their shard,
merge, matrix-assembly, or validation functions.  Before and after the long
calculation it hashes and inode-binds:

- the active25 analytic audit and exact rational schedule;
- the D16 certificate, radial two-amplitude contraction, and exact-integrator
  implementation;
- the support/inclusion-exclusion and grouped-domain implementations;
- the independent low-dimensional true-ungrouped oracle and its result;
- its own source and every imported local module file;
- the producer manifest, ledger, 26 stage files, candidate file, and both
  held input directories.

Every source must be loaded from the path whose bytes were hashed.  Hashing a
path and then importing it later is insufficient: retain the bytes/inode,
verify the loaded module's `__file__`, and rebind after import and at exit.

## Reconstruction independent of shard values

Read and pin the producer leaf set at the start, but do not parse a shard's
arithmetic payload until the corresponding expected value has been computed.
For each common count `r = 0,...,25`, independently perform the following.

1. Parse the pinned D16 basis and rational vector.  Recompute the two radial
   amplitudes, inner `I`, and inner `48J` from the pinned exact radial matrices;
   do not take these three values from a stage.
2. Construct the four named exact support/component pairs

   ```text
   R = radial outer polynomial on the high support
   V = radial outer polynomial on the low support
   H = constant one on the high support
   L = constant one on the low support.
   ```

3. Use the exact weights

   ```text
   rh = outer_amplitude
   rl = -outer_amplitude
   vh = inner_amplitude - outer_amplitude
   vl = -(inner_amplitude - outer_amplitude)
   ```

   and the Definition-5 cross cutoff `eta2`.  Re-run the grouped branch/domain
   traversal with `common_strata=(r,)` and the full left radial components.
   This produces exact counts, face inventory, and a length-49 raw-J vector.
4. Prove directly that the vector is supported only at target total counts
   `r` and `r+1`.  At `r=25`, the count-26 value must be exactly zero because
   count 26 is outside the audited active shell.
5. Only after steps 1--4, parse producer stage `r` with an independently
   written strict canonical schema and require exact equality of every
   arithmetic field: counts, inventories, inner identity, dimension, and all
   49 rational cross entries.  Self-declared source hashes and child-stdout
   hashes are provenance diagnostics, never substitutes for this equality.

The checker should retain the freshly computed vectors, not the stage vectors,
for all subsequent work.  Sum them coordinatewise in canonical `r` order and
again require all target counts above 25 to vanish.

The grouped traversal is validated at the formula level by the already frozen
true-ungrouped low-dimensional oracle and by literal/direct equality fixtures.
Those fixtures do not replace the full 26 reconstructions.

## Independent shell and matrix assembly

Construct the shell constants `C_r = 1_{H\L}` directly from the exact support
objects, rather than calling the producer's `shell_i_and_j` or assembler.

- Recompute each exact I mass `I_r = I_H(r)-I_L(r)`, require
  `I_r > 0` exactly for `r=0,...,25`, and require every later mass to be zero.
- At cutoff `eta2`, separately recompute the four ordered raw-J tables
  `HH`, `HL`, `LH`, and `LL`.  Form

  ```text
  raw_shell_J = HH - HL - LH + LL,
  shell_48J   = 48 * raw_shell_J.
  ```

  Check `LH = transpose(HL)`, exact symmetry after inclusion-exclusion, and
  exact tridiagonality on active counts.  Do not replace the two ordered mixed
  orientations by `2*HL` entrywise.
- Recompute the inner-inner block at cutoff `eta1` from the radial exact
  artifact.  It is already `48J` and must not be multiplied again.
- The inner/shell entry at shell index `r` is
  `48 * fresh_raw_cross[r]`.  There is no extra factor two: symmetry supplies
  the second occurrence in the quadratic form.

Thus independently form

```text
A = diag(inner_I, I_0, ..., I_25)
B[0,0] = inner_48J
B[0,r+1] = B[r+1,0] = 48 * fresh_raw_cross[r]
B[r+1,s+1] = shell_48J[r,s].
```

Require all A diagonal entries positive, B symmetric, the shell block
tridiagonal, dimension 27, and exact equality to the candidate's serialized
forms.  This checks the Definition-5 cutoff split and applies factor 48 exactly
once in each block.

## Particular exact certificate

Numerical eigendiscovery is outside the trusted conclusion.  Parse only the
candidate's canonical rational 27-vector `c`, then compute from the freshly
reconstructed forms

```text
D = sum_i A[i,i] c_i^2,
N = sum_{i,j} c_i B[i,j] c_j,
margin = N-D.
```

Require `D > 0` and `margin > 0` as exact `Fraction` comparisons.  Recompute
and match every serialized numerator, denominator, quotient, and margin.  Do
not assume A or B is nonsingular or positive definite.  A passing output may
print the exact positive margin; any mismatch must publish only a fixed
rejection sentinel and must not print a quotient or eigenvalue.

## Required hostile fixtures

Before certificate use, normal and `-O` suites must include at least:

- one altered rational in each of the 26 stages;
- a fully self-consistent fake production manifest carrying a false inner
  `48J` (the frozen-v4 `999` counterexample);
- swapped `r/r+1` target ownership and a nonzero count-26 tail;
- wrong `eta1/eta2` assignment, missing or doubled factor 48, and `2*HL`
  substituted for the two ordered mixed orientations;
- duplicate, missing, extra, symlinked, hardlinked, deleted, and replaced
  ledger/stage/candidate leaves, including mutations during reconstruction;
- changed imported-source bytes between hash and import and during the run;
- a rational vector with a forged positive serialized margin;
- normal/optimized exact-output identity.

Only this reconstruction, followed by the separate analytic dependency audit,
can promote a staged candidate.  A producer manifest, externally recorded
hash, or internally reconstructed child-stdout hash alone never authenticates
the arithmetic.
