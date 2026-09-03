# C10 analytic repair addendum

This addendum lists the two changes that are mandatory if
`agents/independent-attack/c10-candidate-analytic-dossier.md` is used in a
proof.  Full derivations and source anchors are in `C10-AUDIT.md`.

## 1. Correct the Type-IIb third-bin minima

The third capacity before harmless endpoint reserves is

\[
C_3(\gamma)=\frac{3\gamma}{7}-\frac17-rac{10\omega_*}{7}+O(\zeta,h).
\]

It increases with \(\gamma\).  The dossier/paper value obtained at the upper
IIb endpoint is therefore not a uniform lower bound.  At the lower endpoint,
after the explicit proof-safe choices in `C10-AUDIT.md`, the exact uniform
positive minima are

```text
omega_*=0:      350000001/35000000000
omega_*=2747/300000:  2972900003/105000000000.
```

Bin 3 is empty, so positivity is all that is required.

## 2. Give Type-IIc real width before shrinking open intervals

Put

```text
h       = 1/10^10
delta   = 1/100
delta_c = delta+4h = 25000001/2500000000
0 < zeta <= h/1000, chosen sufficiently small
r0      = h/10.
```

Use the three Type-IIc open intervals of width `delta_c` and feed the closed
intervals `[a_i+r0,b_i-r0]` to partition Lemma 13.  Their width exceeds the
support increment by exactly

```text
19/50000000000.
```

The exact Type-IIc distribution margins are

```text
403599967/15000000000
209599877/30000000000
1199983/2500000000.
```

The auxiliary proof-start face and the three potentially critical endpoint
margins are

```text
2120239997/6000000000
3899999995097/10000000000000
626499989641/15000000000000
7007999971/100000000000.
```

The resulting uniform partition capacities are

```text
C1 = 4601199986563/15000000000000
C2 =  776499995341/15000000000000
C3 =          25000001/2500000000
C4 =                    1/50000000000,
```

and the six complete zero/small/large-count packing margins are

```text
2273199986563/15000000000000
 101199986563/15000000000000
 173199986563/15000000000000
      499995341/15000000000000
 245199986563/15000000000000
  222299989489/5000000000000.
```

Independent command:

```bash
python3 prime-gap-236/agents/hostile-analytic-audit/c10_audit_exact.py
```

Expected last line: `C10 HOSTILE ANALYTIC EXACT PASS`.
