# Wide C722 nonuniform active-25 tail analytic audit

## Verdict

`AUDIT PASS` for the analytic Proposition-1 hypotheses only.  The independently
reconstructed outer schedule is

```text
B1..B9 = 597/5000, 633/5000, 669/5000, 141/1000,
          737/5000, 773/5000, 1553/10000, 809/5000, 81/500
B10     = 3329/20000
B11..B25 = (1690,1695,1718,1737,1752,1762,1764,1774,
             1782,1790,1796,1801,1806,1811,1815)/10000
B26 onward = 1815/10000.
```

The common parameters are `k=48`, `delta=361/50000`, `epsilon=3/400`,
and `A=(-3/400,1/4,3121/12000)`.  The checker imports no discovery script.
It installs these exact rationals in the frozen source-level C722 verifier
and reruns all fixed and continuous cases.

Total large counts `0,...,25` are active and count 26 is the first empty
count.  In particular,

```text
B25 - 25 delta = 1/1000,
26 delta - B26 = 311/50000.
```

There are therefore 26 shell-constant coordinates.  Adding the retained
inner D16 coordinate gives dimension **27**, not 26.

## Complete exact inventories

The mixed and transposed families each contain 935 ordered nonzero count
pairs and 2,805 branch checks.  Their common least margin is
`139967/45000000000`, at corrected IIb and count pair `(1,10)` (with the
orientation reversed for the transpose).

The outer and outer-near families each contain 675 ordered pairs and 2,025
checks.  Their least margins are respectively
`59999869/600000000000` at III `(9,18)` and `199999/2500000000` at IIb
`(11,24)`.  The dynamic IIc audit covers all 172,800 rational continuum
cells for 675 ordered pairs; its least prefix margin is
`549979/120000000000`, at `(5,12)` and cell `(13,1)`.  The smallest
source-level strict inequality outside the packing checks remains
`1/200000000000`.

The serialized range assignment is unchanged: inner/inner uses
Bombieri--Vinogradov; every mixed and outer ordered-band range is covered by
the repaired fixed/dynamic alternatives; and
`rho(n;x)=(log n/log(3x)) 1_P(n)` has `c1=c2=0`.

## Strict component interior

There is an exact 25-parameter neighborhood: `B1,...,B24` vary independently
by less than `1/1000000`, while `B25` and all later entries share one plateau
parameter varying by the same radius.  Direct interval minimization of every
affine Definition-1 condition gives

```text
minimum independent transition increase = 99/500000
minimum transition step slack            = 9/500000
minimum active-count margin               = 999/1000000
minimum empty-count margin                = 6219/1000000.
```

Every support in this box is contained in its componentwise upper corner.
A full fresh check of that corner retains mixed least margin
`94967/45000000000` and dynamic least margin
`309979/120000000000`.  This proves the packing conditions throughout the
box without an infeasible or incomplete sample of its vertices.

Three hostile mutations retain Definition-1 geometry but are rejected by
the actual fixed-prefix verifier:

```text
B1  += 1/10000  -> mixed III, pair (1,1)
B9  += 1/10000  -> mixed IIb, pair (1,9)
B10 += 1/10000  -> mixed IIb, pair (1,10).
```

The schedule agrees with the frozen plateau-0.16645 support through B10 and
strictly raises every entry from B11 onward, activating the two new total
large counts 24 and 25.

## Frozen artifacts and replay

```text
agents/audit/verify_wide_c722_nonuniform_active25_tail_analytic.py
  c96b1d1c052a1fe598ac9547b46af3575bc56afb8e6050be7d9384a6861b42f7
agents/audit/results/wide_c722_nonuniform_active25_tail_analytic_audit.json
  111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda
```

Run from `prime-gap-236/`:

```bash
python3 agents/audit/verify_wide_c722_nonuniform_active25_tail_analytic.py
python3 -O agents/audit/verify_wide_c722_nonuniform_active25_tail_analytic.py
```

The normal and optimized JSON outputs are byte-identical with SHA-256
`111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda`.

This is an analytic support certificate, not a quotient certificate.  Any
matrix code must pin this exact schedule, use all 26 shell strata, and rebuild
the dimension-27 forms before it can consume this support.
