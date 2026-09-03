# C10 D12 sparse six-core Ritz reconstruction

Status: negative discovery result.  This closes only the selected six-core
cross tier, not the 20-coordinate degree-band space.

## Frozen inputs and implementation

- pair manifest: `results/c10_D12_sparse_core6_pair_manifest_v2.json`, SHA-256
  `32d7e86840b0ba8a859cd41b30f3242bcde3cc8518e0a598f30a304e741ca4ad`;
- pair builder: `code/build_sparse_pair_core6.py`, SHA-256
  `ac8186bd7d6e3b569e0b02b4385f8b55f9e5abb4b96cd89f68cef217fe9d2667`;
- Ritz solver: `code/solve_sparse_pair_core6_ritz.py`, SHA-256
  `894626ba0b0b66b3acedc26ddd1025abcd15155db13d72482bd500ef36a3ed26`;
- solver tests: `tests/test_sparse_pair_core6_ritz.py`, SHA-256
  `2410262763eb211ff66371c653645ec93e662a5f0e141741167d120fa0f1b9c4`.

The selected directions, in matrix order after the base vector, are
`d10,d9,d6,d8,d5,d11`.  All 15 inputs are literal, unscaled sums `d_i+d_j`.
For each form, the off-diagonal entry is reconstructed by

```text
A_ij = (A(d_i+d_j)-A_ii-A_jj)/2,
B_ij = (B(d_i+d_j)-B_ii-B_jj)/2,
```

where `B=48J` throughout.  The 15 fresh Decimal100 grouped runs took
253.241739 seconds in aggregate and had maximum reported parent RSS 24,768
KiB.  Every result was replayed against its input, static count tuple, stage,
and dependency hashes before matrix construction.

## Result

The sanitized result is

```text
results/c10_D12_sparse_core6_ritz_mp100_sanitized.json
SHA-256 906a84cb233d107d6887ac71945ba7aa3eab61e08c75ffa198bd6e6227d80f24
```

The exact-Fraction denominator matrix, exact relative to the serialized
Decimal100 forms, has seven positive LDL pivots.  Independent Decimal120 and
Decimal190 Cholesky/Jacobi solves give

```text
top quotient =
0.970974468240619122464713832002280486196017926804702107921170108673458304310766259109902219828482017089345...

gain over base =
0.000004620606829548352323827862724482454453360916173681022109453362357854330369985012145243252043717331066...

shortfall to 1 =
0.029025531759380877535286167997719513803982073195297892078829891326541695689233740890097780171517982910655...
```

The relative eigen-residuals are `2.1464e-211` and `5.3534e-287`.  The gain
fails the predeclared `1/10000` continuation gate by a factor about 21.64, so
the proposed H8/H7 pair rows were not launched.  The artifact has
`rational_candidate_emitted=false` and contains neither a coefficient vector
nor a candidate form claim.

An independently written reconstruction gives `SCOPED AUDIT PASS` in
`agents/small-delta-frontier/CORE6-PAIR-RITZ-AUDIT.md`, SHA-256
`7d634b94b98af340140f26b7aaa7ec727f4b9ac2c0c039a2219110e5979fda41`.
Its result SHA-256
`14b779ccddad14755a7b7152a9b6094c487683fdc73d8d9b7bd94c66dc6293b4`
uses solver SHA `78820c6d...`; tests SHA `c9bf7770...` pass 3/3 in normal
and optimized mode.  It froze its own output before comparison, then found
the exact `A`, `B48`, and LDL-pivot arrays identical.  The top values differ
by only `4.01e-189`, from the different final Decimal truncations, and both
fail the continuation gate.  No vector from the independent diagnostic is
promoted or consumed as a candidate here.

The earlier file `results/c10_D12_sparse_core6_ritz_mp100.json`, SHA-256
`8193ef60d24103f3be5de824fc4728350f49667f9d6347ab118f7fedf17452c9`,
is deliberately preserved as invalid/superseded evidence.  Its matrices and
Ritz value agree, but it violated the run policy by serializing an internal
rationalized vector although the quotient was below one.  It must not be used
as a candidate artifact.

## Reproduction

```bash
python3 agents/structural-basis/tests/test_sparse_pair_core6_ritz.py
python3 -O agents/structural-basis/tests/test_sparse_pair_core6_ritz.py
python3 agents/structural-basis/code/solve_sparse_pair_core6_ritz.py \
  --pair-manifest agents/structural-basis/results/c10_D12_sparse_core6_pair_manifest_v2.json \
  --pair-builder agents/structural-basis/code/build_sparse_pair_core6.py \
  --coordinate-manifest agents/small-delta-frontier/results/c10_D12_sparse_coordinate_scan_manifest.json \
  --preflight agents/structural-basis/results/c10_D12_sparse_coordinate_scan_independent_preflight.json \
  --core-audit agents/structural-basis/results/c10_D12_sparse_core_self_forms_audit.json \
  --diagonal-results-dir agents/small-delta-frontier/results/sparse_coordinate_scan_all \
  --output /tmp/c10_D12_sparse_core6_ritz_recheck.json
```

This is not a rigorous integral certificate: exact algebra begins only after
the Decimal100 form values have been serialized.  It is also not an upper
bound for omitted band coordinates.
