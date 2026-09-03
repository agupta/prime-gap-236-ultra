# Wide C722 nonuniform schedule with plateau 0.16605: `AUDIT PASS`

The independently verified support is

```text
m=1..9:
597/5000, 633/5000, 669/5000, 141/1000, 737/5000,
773/5000, 1553/10000, 809/5000, 81/500

m=10 onward: 3321/20000
```

This single schedule pointwise dominates both independent predecessor
enlargements:

- it retains every count-1-through-9 gain from the nonuniform plateau-`.166`
  support and raises every later cap by `1/20000`;
- it retains the `.16605` plateau and strictly raises every count-1-through-9
  cap from the start-`.104` plateau-`.16605` support.

It therefore also strictly enlarges the original `.104/.166` support in
every displayed coordinate.  Counts 0 through 22 are active and count 23 is
strictly empty.

## Independent plateau reconstruction

Before combining the two improvements, the checker separately reconstructed

\[
B_m=\min\{13/125+(m-1)361/50000,3321/20000\}.
\]

Its first-empty margin is `1/100000`.  All 2,481 mixed checks in each
orientation, 1,584 outer checks in each fixed regime, and 135,168 continuous
IIc cells pass.  The exact dynamic minimum is

`9649997/60000000000`

at ordered counts `(8,9)`, cell `(15,6)`.  The mixed-IIc gamma interval is
empty by `71149997/7500000000`.  This independently confirms the plateau-only
claim rather than inheriting it from a discovery script.

## Combined exact audit

For the schedule displayed above the exact minima are:

| family | exact checks | least slack |
|---|---:|---:|
| mixed fixed IIa/IIb/III | 2,481 | `724973/37500000000` |
| transpose fixed | 2,481 | `724973/37500000000` |
| outer fixed | 1,584 | `4439999869/600000000000` |
| outer near-square | 1,584 | `45199999/2500000000` |
| outer dynamic IIc | 135,168 | `174999/5000000000` |

The source-level range assignment, open endpoints, corrected uniform Type-IIb
capacity, prime-power cases, weighted-prime minorant, and every continuous
dynamic cell are inherited only from the frozen independently audited C722
engine and rerun.  The minorant has `c1=c2=0`; no quotient is assumed.

## Strict interior and sensitivity

The first nine caps can vary independently by `1/200000`, and the common
plateau can independently vary by the same radius.  Every one of the 1,024
box vertices has the same active inventory and satisfies all affine schedule
conditions.  The worst schedule margin is `1/200000`.  Every box support is
contained in the fully checked upper corner, whose least fixed and dynamic
slacks are

`537473/37500000000` and `124999/5000000000`.

Fail-closed mutations remain effective: increasing only `B1` by `1/10000`
fails mixed Type III at `(1,1)`, while increasing only `B9` by `1/10000`
fails mixed Type IIb at `(1,9)`.  Both mutated sequences still satisfy the
Definition-1 schedule geometry, so these are genuine packing-check fixtures.

## Frozen replay

```sh
python3 agents/audit/verify_wide_c722_nonuniform_plateau16605_analytic.py
python3 -O agents/audit/verify_wide_c722_nonuniform_plateau16605_analytic.py
```

Normal and optimized modes emit identical bytes, equal to the frozen JSON.

- checker SHA256:
  `1c041d15fbd18ec4e049bd32690e135310f98d93d653f67892244f47fc3ce607`
- JSON audit SHA256:
  `700f7931b5a700a4b144a05a94f9c0f28791d3f40c257a4b56a5a8482617af7b`
- schedule canonical SHA256:
  `52d71a369e8344c57e7a34d6e73217ef4604a40d042c4c2b0c0d82550034a77b`

Verdict scope is analytic Proposition-1 support only.  An exact capped
finite-dimensional quotient above one and final theorem audit remain
required.
