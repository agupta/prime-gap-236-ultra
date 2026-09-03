# Inner-D16 plus count-tagged shell: exact preflight

Status: **exact regression and cost tranche; full traversal not authorized**.

This note freezes the implementation against the independently audited
`nonuniform-outer-plateau16605-v2` support.  A subsequently proposed plateau
`3329/20000` continuation is under a separate analytic audit, so these bytes
must not be silently relabelled as that stronger support.

## Frozen identity

The parameters are

```
k = 48
delta = 361/50000
epsilon = 3/400
A = (-3/400, 1/4, 3121/12000)
alpha = (103/400, 3211/12000)
eta = (97/400, 3031/12000)
B = (597/5000,633/5000,669/5000,141/1000,737/5000,
     773/5000,1553/10000,809/5000,81/500,3321/20000,...)
```

The plateau is repeated through the first empty count, giving active outer
counts `R=0,...,22`.  The analytic support audit is JSON SHA
`700f7931b5a700a4b144a05a94f9c0f28791d3f40c257a4b56a5a8482617af7b`
and reports `AUDIT PASS`, `c1=c2=0`.

The finite space has 24 coordinates.  Coordinate zero is the exact radial BV
D16 vector: if `a` is its second rational amplitude, its marginal is

```
a m_{S<103/400} + (1-a) m_{S<97/400}.
```

Coordinate `R+1` is the constant on the capped outer-shell stratum with
exactly `R` large coordinates.  Shell I is diagonal and shell J is
tridiagonal.  The inner/shell cross at target count R is reconstructed as

```
a (J(R-full,H_R)-J(R-full,L_R))
 + (1-a) (J(V-full,H_R)-J(V-full,L_R)).
```

These are raw J cross entries.  A future pencil assembler must multiply them
by `k=48` exactly once.  It must likewise form the shell block as
`48*(HH-HL-HL^T+LL)`; entrywise `-2 HL` is not valid.

## Exact optimization and oracle

The direct implementation replaces the four artificial distinguished-t
branches of each uncapped full-simplex inner marginal by

```
integral_0^(alpha-U) t^e (1-U-t)^a dt.
```

It uses the existing audited `Stotal` polynomial primitive before imposing
that primitive's branch restriction, and instead imposes only `U<=alpha`.
Signed contributions are then grouped only when their exact target count and
exact rational polygon/interval are identical.  Hence this is linear
reassociation, not numerical domain matching.

At the production face `(common_r,h)=(10,10)`, the four-branch and direct
forms agree exactly in every one of the 49 serialized target-count entries:

| mode | artifact SHA-256 | literal products | exact groups | wall | RSS |
|---|---|---:|---:|---:|---:|
| four-branch oracle | `100413c17287e0b8cb2029e2ee0bd6270fa68bc843540e537707c23701982d8f` | 64 | 15 nonzero | 13.516 s | 49,356 KiB |
| direct full fiber | `1aaaa0bd7a265d48524931b26c57f51a5e6e2463099c0389f8ea38078e3e0739` | 16 | 11 nonzero | 5.121 s | 37,616 KiB |

The old uniform-start support equality artifact
`fbdab9ea345422d6037cba2821ed19af82c6b38c045b53ebbd28b71030305ae6`
is retained as a separate regression and is not a computation on this support.

The test suite checks exact equality with the literal canonical recurrence in
polygon, z-interval, w-interval, and zero-dimensional point geometries.  It
also checks signed weights, target-count ownership, shell polarization and
tridiagonality, the exact radial contraction, analytic parameter identity,
and exclusive publication.

Frozen source SHA:
`eff218454a1ce60a0af4aa0d046a41c27f787245af917697bed3d274f1b91f4b`.

Frozen test SHA:
`c5aaa159eafe7246157409743ec6551aafad95cb9595413dde6e087f0d2191fe`.

Both normal and `python3 -O` pass 6/6.

## Cost envelope and gate

The exact preflight inventories 552 common `(r,h)` faces, 34,960 literal
branch products, and at most 7,325 exact target/domain groups before algebraic
cancellation.  The predeclared representative direct probes were
`(0,17),(5,15),(10,10),(15,10),(22,6)`.  Their wall times were respectively
6.229, 6.497, 5.121, 4.470, and 4.578 seconds; maximum measured RSS was
38,132 KiB.

A deliberately conservative one-worker projection uses the largest observed
face time for all 552 faces:

```
552 * 6.497321385890245 s = 3586.521405... s = 0.9963 h.
```

A resource authorization, if later issued for the same exact support and
source, should reserve a factor 3 in wall time (10,759.6 s, 2.99 h), a factor
4 in RSS (152,528 KiB), require two fresh `MemAvailable` readings of at least
1.4 GiB, use one worker, and stage independently by common count.  This is an
engineering envelope, not a proof bound.  No full stage producer or quotient
was run in this tranche.  A later producer must hard-pin every stage rather
than accept caller-chosen hashes, and its final assembler must publish with
exclusive inode ownership.

## Reproduction

```
python3 agents/small-delta-frontier/test_frontier_inner_d16_tagged_shell.py
python3 -O agents/small-delta-frontier/test_frontier_inner_d16_tagged_shell.py
python3 agents/small-delta-frontier/frontier_inner_d16_tagged_shell.py --preflight-only
```

No quotient, positive sign, or theorem follows from this preflight.
