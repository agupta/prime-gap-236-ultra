# Three rational 20-band trials v3: final-closure delta audit

Date: 2026-09-02 (Europe/Berlin)

## Verdict

**SCOPED AUDIT PASS (discovery-only), superseding v2.**  The v3 mathematical
vectors are unchanged apart from explicit C10 parameter fields and new
provenance bytes.  The v2 formula audit transfers exactly, and the missing
final trial-byte closure is repaired.

Current hashes are generator
`5e999a3727b9922aac986629e6b022b08614cfcd5ab38203b5f1a8e9e806a7bc`,
tests `4b0390f9f1004440b018bd600a5161eb53e67582e1f6f11e6912cee78e551c09`,
manifest `c16b960004b42e0c66fd2255fd6002eed1cbcf049167fe88f1f18c124e7686e5`,
and 5/10/20-percent trials respectively
`43ba7ad464cc4db70fd8b8ae1152f0aed64d5c888b79af7071c8f2df51b0f816`,
`e3319cde99820683737d1b4abc9aa61a4e44c40b0cadb73a11d2750555ea782d`,
and `88c1d26f6cf46bbdd12dc000eb802cac8efe91be0ad003d6827f2ccdc6c0ff47`.

## Repair audit

`bind_written_trials` adds each newly written resolved path and its recorded
SHA to the same closure already containing the raw gradient, recovered
action, source, bands, baseline, generator, recovery code, line-search code,
and arithmetic dependencies.  It rejects a collision with a pre-existing
trusted path and calls `rebind_trusted` on the complete closure.  The generator
invokes this immediately before the atomic manifest write.  The new mutation
test changes a trial after its nominal write and proves that this final bind
fails closed.  All six tests pass in normal and optimized Python.

The independent delta auditor
`audit_band_trials_v3.py` pins the prior exact Fraction math auditor, replaces
only its v3 byte/path pins, requires every trial's explicit parameters to be

```text
alpha=79247/300000, delta=1/100, eta=76247/300000,
beta1=beta2=3/20, beta3plus=97/625,
```

and reruns the complete exact reconstruction: 20-by-20 full-simplex
preconditioner, serialized-action residual direction, pole and near-side
steps, all 20 compressed and 272 expanded fractions, perturbation statistics,
actual displacement first derivatives, provenance, and absence of finite form
fields.  It passes with the same exact diagnostics (P-norm error about
`9.93e-189`, preconditioned residual error about `9.11e-189`).

```sh
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/agents/small-delta-frontier/audit_band_trials_v3.py
```

This remains a discovery-only PASS.  Decimal100 action values are not exact
integrals, and the three rational trials have no finite capped form value;
fresh scalar evaluation is mandatory.
