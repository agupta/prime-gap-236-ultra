# Frozen piecewise D16 R15 tuple: `AUDIT FAIL`

The specialized evaluator's mathematical pruning passes; the frozen
assembler does not fail closed.  A cost-only evaluator probe is safe, but no
assembled result from this tuple may be consumed.

## Evaluator finding

An independent exact low-dimensional comparison checked all five tags on
both relevant common-count rows.  The pruned values equal the corresponding
target-count entries of the unpruned tables exactly:

- common count 14 retains only `Ltotal,Lbig` (distinguished variable large);
- common count 15 retains only `Sdelta,Stotal` (distinguished variable small);
- no other common count can feed total count 15;
- the inner side retains all four branches;
- factor 48 is absent from the raw evaluator and applied once by assembly;
- for this single shell coordinate, `HH+LL-2HL` is valid because the
  bilinear integral is symmetric.  This does not license entrywise `-2HL`
  for a multi-count matrix.

The frozen target and specialized producer tests also pass in normal and
optimized mode, and the target preflight outputs are identical.

## Smallest assembler counterexample

The assembler accepts newly fabricated stage JSON containing:

- the expected literal `script_sha256` strings;
- arbitrary Decimal I/J values;
- no `source_hashes` at all;
- no authenticated support schedule and almost all parameters omitted.

The caller then hashes those fabricated bytes into its own manifest.  A
manifest-provided digest proves only that the assembler read the bytes the
caller selected; it does not authenticate that a frozen driver produced
them.  The current assembler does not compare the full source-hash and
support-parameter schemas, so it emits a plausible-looking result.

Its `exists()` followed by `write_bytes()` publication is separately unsafe:
the regression supplies a dangling output symlink, the precheck reports it
absent, and the assembler follows it and creates the symlink target.  Atomic
exclusive creation is required.

## Frozen artifacts

- target driver `cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c`
- specialized evaluator `5086a4a381d301ae3a5b321f5e5afba685b677d6851694ef555f6ec76d7fdc58`
- failing assembler `290dc32bf233083ffa52162a4176e0618d6a1fb932d009ca73740d349fe3a363`
- hostile regression `cafcf414804a136b85a79b54425a009b093e2dffcb3a9470ffcbf50610657947`
- independent verifier `159d1e4c8a31e8928c6a1574dfe9924d6e68ca677a2739b265c6f0608347ad94`
- machine-readable audit `0804655c58d2dc1eb97e836eb21222613f232a192743b3d5459149d1d0e32b48`

Replay:

```sh
python3 agents/audit/verify_piecewise_d16_R15_frozen_tuple.py
python3 -O agents/audit/verify_piecewise_d16_R15_frozen_tuple.py
python3 agents/audit/test_piecewise_d16_R15_frozen_assembler_forgery.py
python3 -O agents/audit/test_piecewise_d16_R15_frozen_assembler_forgery.py
```

Both verifier modes emit identical bytes; both regression modes reproduce
the two counterexamples.  A superseding assembler must validate exact full
stage provenance and support schema and publish with `O_EXCL`, then undergo a
fresh audit.
