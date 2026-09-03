# BV D16 Definition-5 two-band hostile audit

## Verdict

**AUDIT PASS.**  Two distinct exact implementations produce identical 2-by-2
`I` and `48J` matrices, amplitudes, and rational contractions for the frozen
uncapped two-band natural-dilation pencil.  The displayed best rational
particular vector has

`q = 0.99987975146175168555...`,

with exact positive shortfall approximately
`0.00012024853824831445`.

More strongly, the checker verifies over exact rationals that `I-48J` is
positive definite.  Hence every nonzero real vector in this particular
two-dimensional uncapped pencil has quotient strictly below one; this is not
merely a near-miss at one rationalized eigenvector.

## Definition-5 correction

For the two bands, Definition 5 assigns the inner/inner block cutoff
`eta1=97/400`; any mixed or outer/outer block uses
`eta2=3031/12000`.  Writing `g1` for the inner fiber marginal and `g2` for the
outer-band fiber marginal, the exact blocks are

```text
B00 = 48 integral_[U<=eta1] g1^2
B01 = 48 integral_[U<=eta2] g1*g2
B11 = 48 integral_[U<=eta2] g2^2.
```

The independent implementations both realize `g2=m(alpha2)-m(alpha1)`.
They apply the factor 48 exactly once and agree on every rational matrix
entry.  At unit outer amplitude, the corrected numerator equals the earlier
one-band `eta2` numerator minus the strictly positive inner/inner tail over
`eta1<U<=eta2`.  Thus the exact one-band value
`1.020782375083111279...` was correctly computed but overcounts this tail and
is only a looser search signal, not the two-band Definition-5 quotient.

All open/closed fiber endpoints differ only on null boundaries.  The outer
simplex in this calculation is uncapped and is not the analytically approved
wide support.  Accordingly, neither the below-one obstruction nor the old
above-one one-band signal is a capped-support quotient or an H1 theorem.

## Frozen producers and replay

- root source/artifact:
  `85c4847c4803015d9aa14f67d257be62a4d23edbff5843f191e903ce885d4804` /
  `9a75380bb2f168adbae70751b6ca04ef9372892fa34c2f66bb0a1a05d59d3d7d`;
- independent source/tests/artifact:
  `0b322ed3b6ea45bfb4f6a7a57deebe34cc57f2a41df68f6f0a592c91dd848d95` /
  `bca7147b8e98a76f504fa50f45cb7dc0b4b43a72b1bedd21563f79749e3b77fe` /
  `05410084611a86d04877ebe2b73a17899e45915fdf1b9b466a25996d28db3171`.

```bash
cd prime-gap-236
python3 agents/audit/verify_bv_d16_definition5_two_band.py
python3 -O agents/audit/verify_bv_d16_definition5_two_band.py
python3 -m unittest agents/structural-basis/tests/test_bv_dilation_definition5_two_band_proxy_v2.py
python3 -O -m unittest agents/structural-basis/tests/test_bv_dilation_definition5_two_band_proxy_v2.py
```

The small checker emits byte-identical output in both modes.  The root
producer replayed byte-identically in both modes to its frozen artifact.  The
independent producer also replayed in both modes; after deleting its explicit
wall-clock field, both replays are byte-identical to each other and to the
frozen independent artifact.
