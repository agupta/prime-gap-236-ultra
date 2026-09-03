# Active25 inner-D16 staged v3 prelaunch

Status: **FROZEN; TARGET EXECUTION WITHHELD PENDING INDEPENDENT V3 DELTA
AUDIT AND A LATER EXPLICIT ROOT LAUNCH**.

The authorized resource gate pins the frozen disabled-v2 audit PASS:
checker `dba6064473a56cb16c99c4423efb0852b3990d0a7f39d027c1b5c1bdc0f4c622`,
result `bd93b52f3556b9d35edb2568b61c74362e4e156f5b607e6755f2ac7203a3c9a2`,
and report `0c37f563d99191f0fbb4abc1c0ea5700ed6288ed9011d5edc691c91394cdc6a9`.
It fixes one worker, two live `MemAvailable` readings at least five seconds
apart and each at least 1,400,000 KiB, a projected envelope
9989.249547201907905 seconds, and a hard 14,400-second stop.

The producer holds the canonical record-directory inode, permits only the 26
fixed leaves `common_r_00.json` through `common_r_25.json` plus
`manifest.json`, creates every missing leaf through `openat(O_EXCL)`, and
strictly validates any existing leaf before resuming.  Every shard binds the
driver, gate, full frozen dependency closure, exact support parameters, inner
identity, count, and canonical Fraction vector.  It rebinds all shards,
dependencies, the held directory, and source before publishing the manifest.
No multiprocessing or alternate worker count exists.

The assembler accepts only an externally supplied canonical SHA-256 for the
completed manifest.  It reopens the exact directory and all 26 bound
stage inodes, reconstructs the exact shell I and tridiagonal 48J block, and
sets each inner/shell matrix cross to `48*raw_J` exactly once.  Decimal100 and
Decimal160 Jacobi solves are discovery only; their quotient agreement and
residuals must be at most `1e-70`.  The emitted rational vector is contracted
exactly.  A verification mode redoes the entire reconstruction.  Neither
eigenvalue optimality nor a sieve theorem is claimed.

Frozen tuple:

- gate `results/frontier_active25_innerD16_tagged_shell_authorized_gate_v3.json`:
  `19ab3d54c08fbd24d6b70ea9d946ca7272030bf20716da383f4bed285de411bb`;
- staged producer `frontier_active25_inner_d16_staged_v3.py`:
  `79cbeb74b994e8d6bdd5f16e7d0f7d11aa148d6f9d6d4f32a12932854d62efd8`;
- staged tests `test_frontier_active25_inner_d16_staged_v3.py`:
  `ab74ac22409f58e3bc7c3ae5a8c50a05c482c47cea69f6f30493adbeaa864e73`;
- assembler `assemble_frontier_active25_inner_d16_v3.py`:
  `c48feddb0cfd1a70ab7140813f4cf0037ae6f21374c229a38089198404079788`;
- assembler tests `test_assemble_frontier_active25_inner_d16_v3.py`:
  `f69f4dac10b610a5a08ec792b7e6bb4c74c4199d0edab78492dadd9703f8aa19`.

Tests pass 6/6 producer and 5/5 assembler under both normal Python and
`python3 -O`; both sources also pass `py_compile`.  Normal and `-O` preflight
bytes have SHA `6a7443e9462b1afbff8a13860ebc99f4f2b7b0fe635ae12831eb82bcbeceec5e`.

The intended fresh output directory is
`agents/small-delta-frontier/results/frontier_active25_innerD16_v3_stages`.
It is currently absent.  Only after both required authorizations, the exact
execution command is:

```sh
mkdir agents/small-delta-frontier/results/frontier_active25_innerD16_v3_stages
python3 agents/small-delta-frontier/frontier_active25_inner_d16_staged_v3.py --record-dir agents/small-delta-frontier/results/frontier_active25_innerD16_v3_stages
```

After root independently records the emitted manifest SHA, assembly is:

```sh
python3 agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v3.py --record-dir agents/small-delta-frontier/results/frontier_active25_innerD16_v3_stages --expected-manifest-sha256 MANIFEST_SHA_FROM_ROOT --output agents/small-delta-frontier/results/frontier_active25_innerD16_v3_exact_pencil.json
```

Neither command has been run.
