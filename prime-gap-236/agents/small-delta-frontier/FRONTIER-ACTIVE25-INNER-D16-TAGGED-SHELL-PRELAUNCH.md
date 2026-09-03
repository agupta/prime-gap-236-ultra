# Active25 inner-D16 plus count-tagged shell prelaunch

Status: **PRELAUNCH DISABLED; independent implementation audit pending**.

## Analytic identity

The pinned analytic audit is
`agents/audit/results/wide_c722_nonuniform_active25_tail_analytic_audit.json`,
SHA
`111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda`.
It reports `AUDIT PASS`, `c1=c2=0`, and fixes

```
k=48, delta=361/50000, epsilon=3/400,
A=(-3/400,1/4,3121/12000),
alpha=(103/400,3211/12000), eta=(97/400,3031/12000).
```

The outer schedule through the first empty count is

```
(597/5000,633/5000,669/5000,141/1000,737/5000,
 773/5000,1553/10000,809/5000,81/500,3329/20000,
 169/1000,339/2000,859/5000,1737/10000,219/1250,
 881/5000,441/2500,887/5000,891/5000,179/1000,
 449/2500,1801/10000,903/5000,1811/10000,
 363/2000,363/2000).
```

Since `B_25=363/2000 > 25 delta=361/2000` and
`B_26=363/2000 < 26 delta`, the active total counts are exactly
`R=0,...,25`.  There are 26 shell constants and one fixed inner coordinate,
so the dimension is 27.  This is derived from the audit JSON; the earlier
dimension-26 parenthetical is withdrawn.

## Exact finite space and factors

Coordinate zero is the exact audited radial BV D16 polynomial on the inner
band.  If its second rational amplitude is `a`, its marginal is

```
a*m_(S<103/400) + (1-a)*m_(S<97/400).
```

Coordinate `R+1` is the constant on the capped outer band with exactly `R`
large coordinates.  I is block diagonal: the inner I entry plus 26 diagonal
shell masses.  Shell J is tridiagonal.  The raw inner/shell cross is

```
a*(J(Rfull,H)-J(Rfull,L))
 +(1-a)*(J(Vfull,H)-J(Vfull,L)).
```

The final generalized numerator must multiply this raw cross by 48 exactly
once.  The shell numerator is exactly
`48*(HH-HL-HL^T+LL)`; replacing the two oriented HL entries by entrywise
`2*HL` is forbidden.

The fixed inner loader is isolated behind the contract
`(basis,vector,amplitudes,inner_I,inner_48J)`.  A future independently audited
471-label D18 loader can therefore reuse all shell support, target-count,
common-r, and merge logic.  No D18 provenance or capped form is claimed here.

## Direct-fiber identity and true oracle

For an uncapped inner simplex the distinguished-fiber marginal is computed
directly as

```
integral_0^(alpha-U) t^e (1-U-t)^a dt.
```

The optimized path groups contributions only when both the target count and
the exact rational polygon/interval are identical.  The independent target
oracle uses the ungrouped `tagged_cross_catalog` and all four canonical
distinguished-coordinate branches.

At `(common_r,h)=(10,10)`, all 49 exact target-count entries agree:

- true ungrouped oracle artifact SHA
  `f97e16231e47d028406a88702631457fb110fe1cf00fcb9a2a4ba71557dbc21c`;
- direct-full grouped artifact SHA
  `37b0d249a0fd17e823f154277bfabe162c3b80c72c344c97686312c7fac7e393`.

The oracle used 64 literal branch products and took 13.368 seconds / 48,564
KiB; the direct path used 16 literal products, 11 nonzero exact groups, and
took 5.692 seconds / 37,668 KiB.  Low-k tests independently compare the
grouped and direct paths with the ungrouped canonical recurrence in polygon,
z-interval, w-interval, and zero-dimensional geometries.

## Inventory, cost gate, and stages

The source-derived inventory is 585 `(common_r,h)` faces, at most 37,024
literal products, and at most 7,731 exact target/domain groups before
polynomial cancellation.  Six source-bound direct probes at

```
(0,17),(5,15),(10,10),(15,10),(22,6),(25,5)
```

have maximum wall time 5.691880083875731 seconds and maximum RSS 38,160 KiB.
Using that maximum for all 585 faces gives 3329.749849067302635 seconds.
The disabled gate reserves a factor 3 in time (9989.249547201907905 seconds),
a factor 4 in RSS (152,640 KiB), one worker, a hard 4-hour ceiling, and two
fresh `MemAvailable >= 1,400,000 KiB` readings.

The arithmetic is exactly shardable by common count.  A shard fixes one
`r=0,...,25`, evaluates every h face for that r, and emits a 49-entry raw-J
target vector supported only at `R=r,r+1`.  Merge requires exactly one strict
shard for every r, sorts by r, and sums Fractions componentwise.  Thus merge
is independent of completion and input order.  A low-k actual recurrence test
checks full traversal equals forward and reverse shard sums.

The current resource gate has `launch_authorized=false`; the stage producer
therefore cannot execute a target shard.  After an independent prelaunch
audit, authorization requires a new byte-pinned gate and a delta audit.  A
post-run assembler must hard-pin the actual stage bytes, reconstruct shell I
and J, apply factor 48 once, and use exclusive inode-owned publication.  It
must not trust caller-chosen stage hashes.

## Frozen tuple and commands

- arithmetic core `frontier_active25_inner_d16_tagged_shell.py`:
  SHA `1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a`;
- arithmetic tests: SHA
  `a9c822357bb2cb9225030b0df46f11bca225ec05158e48ee0d57ff2394f7071f`,
  6/6 normal and `-O`;
- disabled resource gate: SHA
  `1642a5efcc4e2b304271fe3b785d439ce9b1ddb405855f56a7e62a1b4e61e6ac`;
- gate verifier: SHA
  `552e6e92916c62179f56262f33fddfeda46d65463c7a13edb165892f0c15020b`,
  PASS normal and `-O`;
- staged wrapper: SHA
  `bb00675f722a843c0d87ef36e382aea812d6622c79da517e238b0146af9592dd`;
- staged tests: SHA
  `77ab338b79a30e653ba8b52cb468c3b5bd1db43f057da4d0799e390df360bf64`,
  6/6 normal and `-O`.

Reproduce without target integration:

```
python3 agents/small-delta-frontier/test_frontier_active25_inner_d16_tagged_shell.py
python3 -O agents/small-delta-frontier/test_frontier_active25_inner_d16_tagged_shell.py
python3 agents/small-delta-frontier/verify_frontier_active25_prelaunch_gate.py
python3 -O agents/small-delta-frontier/verify_frontier_active25_prelaunch_gate.py
python3 agents/small-delta-frontier/test_frontier_active25_inner_d16_staged.py
python3 -O agents/small-delta-frontier/test_frontier_active25_inner_d16_staged.py
python3 agents/small-delta-frontier/frontier_active25_inner_d16_staged.py --preflight-only
```

No target stage, quotient, sign, or sieve theorem is produced by this package.
