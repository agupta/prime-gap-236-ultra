# C10 D12 transferred-affine certification runbook

Status: prepared, not launched.  No target sign is asserted here.

## Frozen candidate

```text
k                         48
alpha                     79247/300000
eta                       76247/300000
delta                     1/100
beta1,beta2               3/20
beta3plus                 97/625
base degree/dimension     12 / 272
affine channels           (1,L,Z), R=0,...,15
effective linear cutoff   11
```

Pinned inputs:

```text
original base   719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87
integer base    8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93
affine vector   ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158
```

The integer base must reconstruct from the original with its exact 714-bit
LCM.  The effective affine table must reconstruct with its exact positive
206-bit LCM after setting `b_R=c_R=0` for `R>11`.

The proof-to-loader candidate identity has a static scoped audit pass:

```text
agents/small-delta-frontier/AFFINE-CANDIDATE-IDENTITY-AUDIT.md
839d7dfbf5568c35fa6f83d6ec35b788da69e9b45071219821b998e60e4c53ef
```

That pass covers all 272 ordered coefficients, all 16 effective triples,
and both I/J multiplier formulas. It contains no target sign.

## Launch gate

Do not start a target-sized rigorous run until the complete Decimal100
transfer artifact exists, passes all of its discovery-only gates, and has
reported `quotient>1`.  A Decimal sign is only a resource-allocation gate; it
is never certificate evidence.

Before launch, stop every nonessential memory-heavy computation and check
that swap is stable.  Recompute and compare the driver SHA below.  Any source
change voids the pre-launch audit and requires reaudit.

## Primary grouped enclosure

Audited driver:

```text
verify/check_c10_d12_affine_dyadic.py
bf0ad4b3c1288c1d2df67e92f9ebe9e63613b9dcd2892c3f96522217d920677b
```

Pre-launch audit report:

```text
agents/small-delta-frontier/DYADIC-D12-DRIVER-AUDIT.md
7315f5dcde8d171eb56aeaf129cefbe2f66f4bc88ab2ac755983c9055af3567a
```

Run both stages in one invocation so the I-stage SHA is not treated as proof
of external computational origin:

```bash
cd prime-gap-236
/usr/bin/time -v python3 verify/check_c10_d12_affine_dyadic.py \
  --phase all \
  --stage certificate/c10-d12-affine-p512-i.json \
  --output certificate/c10-d12-affine-p512.json \
  --precision 512 --shadow-bits 96 --progress
```

The only positive decision is exact integer comparison

```text
I.lo > 0 and (48J-I).lo > 0.
```

Record the output SHA, exact endpoint integers/fractions, widths, wall time,
peak RSS, 1,575 I groups, 312 I faces, 695 marginal components, and 1,200 J
domains.  A quotient midpoint or upper endpoint is irrelevant.

If positive, rerun at higher precision and reverse count order into distinct
paths:

```bash
/usr/bin/time -v python3 verify/check_c10_d12_affine_dyadic.py \
  --phase all \
  --stage certificate/c10-d12-affine-p768-reverse-i.json \
  --output certificate/c10-d12-affine-p768-reverse.json \
  --precision 768 --shadow-bits 128 --reverse-counts --progress
```

Both interval results must contain a common value and retain a positive
margin lower endpoint.  This is a robustness check, not the independent
algebraic reconstruction.

## Independent tagged enclosure

Current second driver:

```text
verify/check_c10_d12_affine_independent_dyadic.py
7e2ed20a68e3c3e95a9566b32cae3d403949a79a3a81adfa61b8dab833b640b9
```

It routes coefficient intervals through the independently implemented
ordered-branch partition-radial recurrence.  Its pre-launch audit is frozen at

```text
agents/small-delta-frontier/INDEPENDENT-DYADIC-DRIVER-AUDIT.md
5c42829e3d412a903f987057b67322ef389468894ab6f6c282eafb3eb0ea3a85
```

Seven hostile tests pass in normal and optimized modes.  Launch only after
the long production jobs release memory and a resource check shows that a
target run is practical.  Use `--phase all`, not a caller-supplied resumed
stage.

```bash
/usr/bin/time -v python3 verify/check_c10_d12_affine_independent_dyadic.py \
  --phase all \
  --stage certificate/c10-d12-affine-independent-p512-i.json \
  --output certificate/c10-d12-affine-independent-p512.json \
  --precision 512 --shadow-bits 96
```

The grouped output cannot receive final certificate status until this or
another arithmetic reconstruction agrees on enclosures and an auditor checks
the actual output files.

## Post-run theorem checks

After two positive reconstructions:

1. freeze all source and output hashes in `CERTIFICATE.md`;
2. insert the exact positive lower margin into `PROOF.md`;
3. replace the deliberately unarmed `verify_all.py` base-polynomial stage
   with a fresh invocation of the affine reconstruction.  Merely filling its
   current constants is forbidden: its present `exact_capped_certificate.py`
   command reconstructs the unmodified 272-term polynomial, not (35b), and
   must therefore fail against affine values;
4. run the analytic C10 support/distribution checkers and tuple checker in
   normal and optimized modes;
5. give an independent auditor the candidate definition, primary definitions,
   and raw checker outputs, not the discovery narrative;
6. require an end-to-end `AUDIT PASS` before changing `RESULT.md` to a theorem.
