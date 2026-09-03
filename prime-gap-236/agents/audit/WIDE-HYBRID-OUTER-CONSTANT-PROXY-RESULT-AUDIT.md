# Wide C722 k=30 constant-shell proxy result audit

## Verdict

**AUDIT PASS on the exact output arithmetic; PREDECLARED PROXY GATE FAIL.**
The constant-shell k=30 proxy mechanism is retired.  No k=48 contraction is
authorized by these results.

The frozen output hashes are:

- high plateau:
  `aed2641e604c050a96c572b08ad1f84d6ded59b12e3b05b714be6a0301a79798`;
- volume ramp:
  `ff9d05d610f3960fa898bbf22f3fdc367232e22621a64ed350d5da7a19684acb`.

The independent comparator strictly parses and hashes both results and their
dependency closures, binds each rational schedule to the prelaunch gate,
recontracts both exact 2-by-2 matrices at the serialized rational vectors,
and independently recomputes each quotient, gain, ranking, and separation.
Every target-k48 and theorem-ready flag remains false.

The high-plateau quotient is approximately
`0.3921422990454916089`, with gain `5.262887779506117e-19`.  The volume-ramp
quotient is approximately `0.3921422996465289070`, with gain
`6.010372986094198e-10`.  Both are far below the predeclared `1e-5` gain
threshold.  Volume ramp wins, but the separation is only about
`6.010373e-10`, also far below the predeclared `1e-7` threshold.

## Replay

```bash
cd prime-gap-236
python3 agents/audit/verify_wide_hybrid_outer_constant_proxy_results.py
python3 -O agents/audit/verify_wide_hybrid_outer_constant_proxy_results.py
```

Both modes emit byte-identical audit JSON.
