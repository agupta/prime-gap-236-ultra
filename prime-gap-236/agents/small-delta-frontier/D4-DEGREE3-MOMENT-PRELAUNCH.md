# Exact D4 degree-three fused-moment fallback

Status: **PRELAUNCH PASS; NOT AUTHORIZED; NO DEGREE-THREE TRAVERSAL RUN**

The fallback is prepared for use only if the active D12 quadratic transfer is
negative and root separately authorizes this D4 experiment.

## Frozen identities

| artifact | SHA-256 |
|---|---|
| `check_stratum_moment_d4_degree3.py` | `e48d46f447893d21addef38d979670107086550495fd390a1adeebf1ad6ba7ef` |
| `test_check_stratum_moment_d4_degree3.py` | `a2f80e49a302d1c77c5edbff74f989a4b4934270a39fd8c1d8defc552f1f3b46` |
| `results/c10_D4_degree3_moment_prelaunch_gate.json` | `964ab9cdbe952b317f4c42d7b18a47269f886448fdf5f53d581f754405e32e3b` |
| fused engine | `8f8eabfa1f56db41da69bd425f7c506710b292f9e86ad1255d733dac018c8190` |
| independent unfused engine | `fcc471d8a0c8dce01147b6984f981ae5f40ef08a943d2f05ecbe1ec3b0eadccd` |
| exact D4 input | `2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b` |
| exact D4 degree-two oracle | `fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86` |
| completed fused D2 calibration | `72ece5aa4a15536153d7634ee630ebf5e1090dc2ce0a7104cf00190bf310f6eb` |

The gate pins the complete imported local arithmetic closure, the tests, all
three data artifacts, C10 rational parameters, and canonical degree-three tag
schema SHA
`320272a9dfb08ab6d12396127de3ff35ffe35c47b4715e4035bc985e67981aad`.
It explicitly records `production_launch_authorized=false`; production also
requires a separate root authorization binding the gate and driver bytes.

## Predeclared counts and resource gate

The degree-three channel order is

```text
1, L, Z, L^2, LZ, Z^2, L^3, L^2Z, LZ^2, Z^3.
```

The run must produce exactly:

| quantity | exact target |
|---|---:|
| matrix dimension | 160 |
| I faces | 312 |
| J branch domains / fused traversals | 1200 / 1200 |
| I scalar moments | 8736 |
| logical J moment products | 14712 |
| J scalar moments | 167380 |

The completed degree-two fused run took `449.47953073098324` seconds and
`50108` KiB for 57,788 J scalar moments.  Scaling only by the exact scalar-
moment count gives a deliberately frozen fused projection
`1301.89457765889068165016958538` seconds.  Before observing D3 timing, the
gate was fixed at:

- fused traversal at most 1,800 seconds;
- fused plus independent-unfused validation at most 3,600 seconds; and
- peak RSS at most 262,144 KiB.

This is a D4 run.  It does not authorize or project a D12 degree-three run.

## Exact validation targets

The production driver publishes only if all of the following hold:

1. fused and unfused implementations agree on every I/J moment and every
   entry of both 160 by 160 matrices;
2. the complete embedded degree-two principal submatrix agrees entry by
   entry with the independently frozen `fbc8c38d...` oracle;
3. the exact `fbc8c38d...` rational vector, embedded with all cubic
   coefficients zero, reconstructs that oracle's denominator and numerator
   exactly;
4. all sources, inputs, gate bytes, and authorization bytes remain unchanged
   through output publication; and
5. the fixed counts and resource gates pass.

The result serializes canonical exact I/J moment rows and the matrix hashes,
so a later independent checker can reconstruct matrices rather than trust a
dump.  The quotient of the embedded vector is a regression value only; the
run does not claim a degree-three optimum.

## Commands

The lightweight preflight, already tested in normal and optimized Python, is:

```sh
python3 agents/small-delta-frontier/check_stratum_moment_d4_degree3.py \
  --gate agents/small-delta-frontier/results/c10_D4_degree3_moment_prelaunch_gate.json \
  --mode preflight \
  --output /tmp/c10_D4_degree3_preflight.json
```

It deterministically emits SHA
`a17947488edbd0ec3e478e2d6868960870a89318fa06314c55a337b750a80940`.
The earlier value
`41b65c7a161ec9434ab1cf8226d7561d76af3393585c8159f6a0e830950d5157`
was a reporting/transcription error and is explicitly retracted.  A fresh
normal-mode run and a fresh `python3 -O` run against driver `e48d46f4...`
and gate `964ab9cd...` emitted byte-identical 1,029-byte payloads with the
corrected SHA above.
Production remains deliberately unlaunchable until root supplies a new
authorization JSON.  After such authorization, the prepared command is:

```sh
python3 agents/small-delta-frontier/check_stratum_moment_d4_degree3.py \
  --gate agents/small-delta-frontier/results/c10_D4_degree3_moment_prelaunch_gate.json \
  --mode production \
  --authorization AUTHORIZATION.json \
  --output agents/small-delta-frontier/results/c10_D4_degree3_moment_exact.json \
  --progress
```

No authorization file, exact D3 result, numerical eigenvector, or D3
quotient exists at this checkpoint.
