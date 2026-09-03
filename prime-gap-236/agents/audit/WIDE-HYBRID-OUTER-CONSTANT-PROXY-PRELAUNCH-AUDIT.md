# Wide C722 k=30 two-schedule proxy prelaunch audit

## Verdict

**AUDIT PASS for the two frozen k=30 discovery runs only.**  Root may launch
the high-plateau and volume-ramp proxy processes concurrently after the
independent checker passes immediately before launch and root confirms that
session 11209 is finished.  This does not authorize the expensive k=48
contraction, and neither proxy is a theorem certificate.

The frozen driver is SHA-256
`21b9b384d0ec502cbfd83bacb2da1d7e7529a1131a8a959e28eaa948f568ba16`.
The producer gate is SHA-256
`718d8bba2e4df460583cac6f9c27f9da682de43e31fd86e2ce0ba04f599e058b`.
Both planned result paths were absent at audit freeze.

## Independent checks

The checker imports no producer module.  It pins the driver, builder, tests,
specification, gate, cost probe, and every transitive hash named by the gate.
It reconstructs both rational schedules, uses the strict open-threshold
active-count test, binds the two independent analytic `AUDIT PASS` artifacts,
checks the exact low-k signed/polarization constants and positive shell
masses, and verifies the radial-base exact quotient identity.

From the frozen cost datum it independently obtains 71,034 branch calls for
high-plateau and 70,266 for volume-ramp.  The parallel wall estimate is

`229635815590982497041/584000000000000000` seconds

(about 393.212 seconds), leaving an exact
`295964184409017502959/584000000000000000`-second margin to the 900-second
cap.  Aggregate estimated RSS is 70,640 KiB, leaving 191,504 KiB to its cap.
The k=48 estimates remain above the separate four-hour gate and the frozen
artifact keeps every k=48 authorization false.

The driver creates outputs with `O_EXCL`; the independent checker also fails
closed if either output already exists.  The producer's 9 driver tests and 5
gate tests pass in both normal and `-O` modes.  The builder replayed in both
modes to the frozen gate hash, and the driver's low-k preflight was identical
in both modes.

## Prelaunch replay

```bash
cd prime-gap-236
python3 agents/audit/verify_wide_hybrid_outer_constant_proxy_gate.py
python3 -O agents/audit/verify_wide_hybrid_outer_constant_proxy_gate.py
```

After those pass, root may run exactly these two commands concurrently:

```bash
python3 agents/structural-basis/code/wide_hybrid_outer_constant_proxy.py --schedule high_plateau --output agents/structural-basis/results/wide_hybrid_outer_constant_D4_k30_high_plateau.json
python3 agents/structural-basis/code/wide_hybrid_outer_constant_proxy.py --schedule volume_ramp --output agents/structural-basis/results/wide_hybrid_outer_constant_D4_k30_volume_ramp.json
```

Fresh outputs still require an exact comparator and a separate audited gate
before any follow-on calculation.
