# Three rational 20-band trials: independent audit

> **SUPERSEDED / RETRACTED AS A PROVENANCE-CLOSURE PASS.**  A subsequent
> hostile audit found that v2 did not rehash the already-written trial files
> in the final closure immediately before emitting the manifest.  The exact
> formula/vector checks below remain correct for the frozen v2 bytes, but v2
> is retired.  The repaired v3 artifacts and generator are covered by
> `BAND-TRIALS-V3-AUDIT.md`.

Date: 2026-09-02 (Europe/Berlin)

## Verdict

**SCOPED AUDIT PASS (discovery trials only).**  The three frozen vectors are
exact rational expansions of the claimed 20-coordinate near-side projective
steps from the *serialized gradient-action base*.  Their provenance,
preconditioned direction, perturbation statistics, and base-point derivative
diagnostics check independently.  None contains a finite capped denominator,
numerator, quotient, or margin.  Each needs a fresh scalar capped evaluation.

Audited hashes:

- producer `c330855d0c42e5be55be7759714322149b4fa1fdde263ca7d7160315397a704e`;
- producer tests `a074150ecd38b81edb8d1d409a17e8feb7dc752ab7251060bb83ad86e625b8f8`;
- manifest `2a14bfc229ca56e279006c7fb3ee11b0663b5558f0f02aa7c46f8e26e5fcfc87`;
- 5%, 10%, 20% trials respectively `c43fe29367311383dceda07103fa87ebb2168f53793f1ed6a24a79e6144314c5`,
  `5cc0d13fc4d549983badca22e0c04b5177b77c3ce65b72527e04f9092256bc94`,
  and `ada77e63b32c3eb3e80708543acfc7bf709f0e3cab03a5bc68d313d94ed4c3dc`;
- independent auditor
  `3b3cd6377c8e2aa5359a05de74c9a067a79e057cdd152ca1eb829bb9fa0623fc`.

## Independent reconstruction

`audit_band_trials_v2.py` does not import the producer, its Decimal solver, or
its band-line-search arithmetic.  It byte-pins all inputs and outputs, parses
the 272 source labels and 20-band partition independently, and verifies that
the exact band weights expand to the source vector.

It then rebuilds the complete 20-by-20 full-simplex `I` preconditioner with
`Fraction` arithmetic from the independently audited monomial-orbit product.
For the frozen 230-digit rational direction `d`, serialized base `theta`, and
recovered residual `r=B theta-q A theta`, it checks:

- `d^T P d=1` to exact relative error about `9.93e-189`;
- exact `P`-orthogonality to `theta` (the squared normalized error is below
  `1e-350`);
- `P d` is proportional to the projection of `r` off `P theta`, with exact
  relative residual about `9.11e-189` and positive orientation;
- all serialized exact Fraction pairings, Euler residual, first derivatives,
  and Rayleigh first derivative.

For each target `u` in `1/20,1/10,1/5`, it independently reconstructs

\[
t=\frac{u}{\max_i|d_i/\theta_i-d_{19}/\theta_{19}|-u,d_{19}/\theta_{19}},
\qquad
\theta'=\frac{\theta+t d}{\theta_{19}+t d_{19}}.
\]

All three steps are strictly on the near side of the H12 projective pole,
have `theta'_19=1`, attain their stated maximum relative coefficient changes
exactly, and reproduce every one of the 20 compressed and 272 expanded
fractions byte-for-byte.  Max/median raw, normalized, and compressed change
statistics and both forms of first-order displacement diagnostic also agree
exactly.  A recursive field audit finds none of `denominator`, `numerator`,
`quotient`, or `margin` in a trial.

## Fail-closed and test evidence

The producer rejects recovery mutation and trusted-input mutation, checks all
destination paths are pairwise distinct and do not alias any trusted input,
rehashes every trusted byte before each atomic trial write and the manifest
write, and records each trial SHA in the manifest.  A crash can leave an
unmanifested partial set; consumers must require the pinned complete manifest
and the three listed trial hashes.

The producer's five tests passed under normal and optimized Python.  The
standalone audit command also passed:

```sh
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/agents/small-delta-frontier/audit_band_trials_v2.py
```

The exact caveat is unchanged: recovered `A theta` and `B theta` are rational
interpretations of Decimal100 gradient strings.  Therefore the positive
first derivatives are discovery diagnostics, not rigorous form derivatives,
and no finite-step improvement follows without fresh evaluation.
