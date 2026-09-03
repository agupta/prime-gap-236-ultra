# BV D16 dilation and Definition-5 two-band proxy

## Scope

This is exact arithmetic on uncapped full simplexes, but the outer simplex is
not an analytically approved Proposition-1 support.  Neither the one-band
value above one nor the two-band value below one is a theorem, a capped-support
bound, or an upper bound for any richer space.

The frozen independent Definition-5 implementation/result are

```text
code/bv_dilation_definition5_two_band_proxy_v2.py
  0b322ed3b6ea45bfb4f6a7a57deebe34cc57f2a41df68f6f0a592c91dd848d95
tests/test_bv_dilation_definition5_two_band_proxy_v2.py
  bca7147b8e98a76f504fa50f45cb7dc0b4b43a72b1bedd21563f79749e3b77fe
results/bv_D16_dilation_Definition5_two_band_exact_v2.json
  05410084611a86d04877ebe2b73a17899e45915fdf1b9b466a25996d28db3171
```

Seven falsification tests pass normally and under `python3 -O`.  They cover
the two-residual moment formula by literal one-dimensional expansion,
ordered-versus-unordered cross factors, signed repeated-orbit products,
Definition-5 tail subtraction, the stationary equation, source mutation, and
exact replay of the frozen matrix and rows.  The computation took 162.22 s
wall and 120,688 KiB peak RSS.

## Exact dilation

Write

```text
G_(a,lambda)(t) = (1-sum(t))^a P_lambda(t),
c = alpha_0/alpha_1 = (103/400)/(3211/12000) = 3090/3211.
```

Since `P_lambda` is homogeneous of degree `|lambda|`, the exact coefficient
map for `F_0(c t)` is

```text
theta_(a,lambda) ->
  theta_(a,lambda) binom(a,b) (1-c)^(a-b) c^(b+|lambda|)
```

in coordinate `(b,lambda)`, for every `0<=b<=a`.  The finite D16 basis is
closed under this triangular map.

For a single full simplex, changing variables gives

```text
I_new = c^(-48) I_old,
J_new(alpha_1,eta_1) = c^(-49) J_old(alpha_0,c eta_1),
c eta_1 = 312193/1284400 = eta_0 + 363/642200.
```

The square integrand makes the enlarged-cutoff contribution nonnegative.
The old certified quotient alone therefore yields the exact lower bound

```text
q_new >= c^(-1) q_old
      = 1.01970356331108457990811371024598397828... > 1.
```

Direct exact contraction gives

```text
q_one_band = 1.02078237508311127938400608052903711736... .
```

The distinct frozen one-band component files are

```text
code/bv_dilation_fullsimplex_proxy_v2.py                 890f0ca4...
tests/test_bv_dilation_fullsimplex_proxy_v2.py           e442f8d3...
results/bv_D16_dilation_alpha3211_fullsimplex_exact_v2_frozen.json
                                                          34966e5e...
```

The preliminary one-band artifact `fa9113db...` is retained, but its original
source path was overwritten during development.  It is explicitly
superseded and not replayable; no audit or conclusion relies on it.

## Definition-5 two-band correction

Let `m_1(U)` and `m_2(U)` be the distinguished-coordinate marginals cut off
at `alpha_1=103/400` and `alpha_2=3211/12000`, respectively.  For

```text
F_a = F_dilated * (1_{S<alpha_1} + a*1_{alpha_1<S<alpha_2}),
```

the exact denominator is diagonal,

```text
A00 = integral_{S<alpha_1} F_dilated^2,
A11 = integral_{S<alpha_2} F_dilated^2 - A00.
```

Definition 5 uses the inner cutoff `eta_1=97/400` only for the inner/inner
block and the outer cutoff `eta_2=3031/12000` for blocks involving the outer
band.  Consequently

```text
B00 = 48 integral_{U<eta_1} m_1^2,
B01 = 48 integral_{U<eta_2} m_1 (m_2-m_1),
B11 = 48 integral_{U<eta_2} (m_2-m_1)^2.
```

Using `eta_2` in `B00` would be the wrong one-band interpretation.  The three
exact diagnostic quotients make the distinction visible:

```text
correct Definition-5 inner B00/A00  = 0.97134548718840404257123824864054576677...
inner polynomial with eta_2 cutoff   = 0.99287037597656767833512205320790531047...
uncapped one-band outer simplex      = 1.02078237508311127938400608052903711736...
```

The exact two-band contractions are

```text
a=1:
  q = 0.99986151078506529379786110546497507775...

a=1.0263209135536035058233619047794298069891887115525440221059282052677677:
  q = 0.99987975146175168554755274806943937735...
  1-q = 0.0001202485382483144524472519305606226494... .
```

The amplitude is one common exact decimal rational, and the displayed
quotient is its exact achieved Rayleigh quotient, not the algebraic optimum.
The independently assembled `2x2` matrices and both exact rows equal the
separate root implementation/result (`85c4847c...`/`9a75380b...`) as rational
numbers.

The next meaningful question is therefore quantitative: how much the exact
volume-ramp caps remove from these uncapped `A` and `B` blocks.  The cap loss
must be evaluated by exact geometry or a source-pinned high-precision grouped
contraction; binary64 uniform-simplex Monte Carlo is already falsified by its
failure on the known BV baseline.
