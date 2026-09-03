# Truncated one-outer-band energy support v3

This is the theorem-safe analytic handoff obtained by deleting the two narrow
upper bands from the three-outer-band discovery.  It has exactly one inner
band and one outer band.  The deletion is not assumed monotone: the exact
checker reconstructs every remaining Definition-1, source, fixed Type-II,
Type-III, literal Type-IIb, and repaired Type-IIc case.

No Riesz energy, quotient, or bounded-gap conclusion is claimed here.

## Exact support

\[
k=48,\qquad \delta=\frac1{60},\qquad
\epsilon=\frac3{400},\qquad A_1=\frac14,
\]

\[
A_2=\frac{9230917}{36000000}
    =A_1+\frac{37}{40}\frac{6241}{900000}.
\]

Thus

\[
\alpha_1=A_1+\epsilon=\frac{103}{400},\qquad
\alpha_2=A_2+\epsilon=\frac{9500917}{36000000}.
\]

The outer cap schedule through its first empty count is

```text
(140375,157041,168544,174338,185488,190375,
 193097,197146,202047,207090,211668,211668) / 10^6.
```

It is extended by the final plateau for Definition 1.  Counts 0 through 12
are active; count 13 is the first empty count.  Relative to the frozen
single-band schedule, its broad-band gains at counts 4 through 7 are

```text
53/20000, 1951/250000, 9787/1000000, 1939/200000.
```

The direct-HB main-face value and reserve are respectively

\[
3(A_2-A_1)+\delta=\frac{143639}{4000000},\qquad
\frac3{80}-3(A_2-A_1)-\delta=\frac{6361}{4000000}.
\]

## Definition-5 cutoffs

Literal Definition 5 uses

\[
\eta_{11}=A_1-\epsilon=\frac{97}{400},
\]

and, for both the inner/outer and outer/outer terms,

\[
\eta_{12}=\eta_{22}=A_2-\epsilon
 =\frac{8960917}{36000000}.
\]

These follow from
\(\eta_{mm'}=\max(A_m-\epsilon,A_{m'}-\epsilon)\).
Because only one outer band remains, an outer Riesz function supported on
that band has its self-term at a single cutoff.  This checkpoint makes no
multiband outer-\(J\) positivity claim.

## Exact inventory

The checker covers:

- 582 main ordered pairs and 168 near-root ordered pairs;
- 39 main pairs with a zero left count and 39 with a zero right count;
- 1,500 fixed Type-IIa/III instances;
- every exact affine Type-IIb breakpoint interval and endpoint; and
- 168 repaired-Type-IIc pairs, or 43,008 closed adverse rational cells.

The original one-prefix fixed proof fails in 18 cases.  The literal IIb cover
selects the crossing-item mechanism on positive inventory and selects a
nonempty third bin on positive inventory.  In Type IIc, the old one-alternate
action fails on 6,081 cells; all are covered by the three-consecutive-block
lemma proved in `THREE-OUTER-ENERGY-V2.md`.  Strategy SHA-256 digests in the
JSON commit to every deterministic finite choice.

The common cap interval \(B_m+t\), \(|t|\le10^{-7}\), is checked at its
adverse upper endpoint.  It preserves the active inventory and has positive
fixed, Type-IIb, and Type-IIc margins.

## Reproduction

```bash
python3 agents/analytic-new-lever/verify_truncated_lower_energy_v3.py
python3 -O agents/analytic-new-lever/verify_truncated_lower_energy_v3.py
python3 -m unittest agents/analytic-new-lever/test_truncated_lower_energy_v3.py
```

Normal and `python -O` runs are byte-identical.  Frozen hashes:

```text
checker  fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5
result   c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f
tests    9b0e1409ef4ea2dda1292a69881c344a35d52f4886f0568c0e8a71f806d0b1fa
v2 core  87747ad848c502e4d0047d60ca324d77ba94c9b0f5cb2afd6b5d46b953575605
```
