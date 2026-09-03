# Wide C722 nonuniform outer schedule: `AUDIT PASS`

This verdict covers every analytic Proposition-1 hypothesis, not a sieve
quotient.  Starting only from the frozen `.104/.166` support and the frozen
source-level C722 verifier, the independent search found the exact outer
schedule

```text
m=1..9:
597/5000, 633/5000, 669/5000, 141/1000, 737/5000,
773/5000, 1553/10000, 809/5000, 81/500

m=10 onward: 83/500
```

Counts 0 through 22 are active; count 23 is the first empty count.  The
schedule is genuinely nonuniform: its successive increments before the
plateau are

`9/1250, 9/1250, 9/1250, 4/625, 9/1250, 7/10000,
13/2000, 1/5000, 1/250`.

## Pointwise improvement

Against the frozen baseline

\[
B_m=\min\{13/125+(m-1)361/50000,83/500\},
\]

the exact coordinate gains at counts 1 through 9 are

```text
77/5000, 769/50000, 48/3125, 767/50000, 363/25000,
29/2000, 399/50000, 363/50000, 3/12500.
```

All are strictly positive; counts 10 onward are unchanged.  The sum of the
23 displayed head-coordinate gains is `5299/50000`.

## Complete exact audit

Inner/inner moduli use BV.  Both mixed orientations use BV below the stated
threshold and repaired direct-HB IIa/IIb/III above it; the mixed IIc interval
is empty.  Outer/outer uses BV below square root, the omega-zero near-square
cases, and the full 16-by-16 dynamic-IIc continuum cover above square root.
The range assignment, source inequalities, open endpoints, prime-power
removal, and weighted-prime minorant are rerun from the frozen primary-source
audit.  Here

\[
\rho(n;x)=\frac{\log n}{\log(3x)}1_{\mathbb P}(n)1_{[x,2x]}(n),
\qquad c_1=c_2=0,
\]

and all source margins remain strictly positive.

| family | exact checks | least slack |
|---|---:|---:|
| mixed fixed IIa/IIb/III | 2,481 | `724973/37500000000` |
| transpose fixed | 2,481 | `724973/37500000000` |
| outer fixed | 1,584 | `4499999869/600000000000` |
| outer near-square | 1,584 | `45449999/2500000000` |
| outer dynamic IIc | 135,168 | `850003/30000000000` |

The least source-level margin is `1/200000000000`.

## Strict interior and hostile fixtures

The first nine caps may vary independently by `1/200000`, while the common
plateau may independently vary by the same radius.  All 1,024 vertices of
this ten-parameter box pass the schedule and active-inventory conditions.
Every support in the box is contained in its componentwise upper corner.
That upper corner passes all fixed cases and all 135,168 dynamic cells; its
least fixed and dynamic slacks are respectively
`537473/37500000000` and `550003/30000000000`.

Two fail-closed sensitivity fixtures retain valid Definition-1 geometry:

- increasing only `B1` by `1/10000` destroys the mixed Type-III prefix
  certificate at pair `(1,1)`;
- increasing only `B9` by `1/10000` destroys the mixed Type-IIb certificate
  at pair `(1,9)`.

Thus the pass is neither a favorable rounded boundary value nor a checker
that accepts arbitrary cap enlargement.

## Frozen replay

```sh
python3 agents/audit/verify_wide_c722_nonuniform_outer_analytic.py
python3 -O agents/audit/verify_wide_c722_nonuniform_outer_analytic.py
```

Normal and optimized modes emit identical bytes, equal to the frozen JSON.

- checker SHA256:
  `9265fead8dda30c5b1d4a67907f2faa3926cdb4a1891ea083ec8b37fbc40d726`
- JSON audit SHA256:
  `ab782d6c814271380a73fda6bbdeaa0e097c5216856cd64348e569ddf728f473`
- schedule canonical SHA256:
  `3b776367c51deeb6a245af03cf84606603708655b0a81a752bb6247fee8b1ff1`

An exact finite-dimensional quotient above one and a final theorem audit are
still required.
