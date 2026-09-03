# Source-fidelity work package

This directory is an independent, source-locked audit of Julia Stadlmann,
*Bounded gaps between primes*, arXiv:2608.31126v1.

Start with:

- `source-manifest.md` for versions, URLs, and hashes;
- `paper-map.md` for definitions, notation, and the proof-dependency graph;
- `parameter-audit.md` for the exact published-parameter check and the defects
  that have to be repaired before Proposition 3 can be cited literally;
- `repaired-proposition3.md` for a proved baseline-only replacement, with an
  explicit split below, near, and above `x^(1/2)` and all zero-index cases;
- `baseline_check.py` for an executable exact-rational check of every scalar
  margin and of the endpoint obstruction.

The full 1,885-line TeX file and all downloaded primary sources are under
`source-tree/` and `sources/`. No top-level project deliverable was edited.

## Headline findings

1. The paper and TeX source are arXiv v1, submitted 2026-08-31. The source
   package contains only the TeX, bibliography, and arXiv build manifest: no
   integration code, coefficient vector, matrices, or exact quotient.
2. The introduction says degree `2a+b <= 21` three times, while Section 5.1
   explicitly says the actual calculation used `B_19`. Under Section 5.1's
   own definition these are different cutoffs; no convention in the source
   reconciles them.
3. Definition 5's `K` integral is not well-formed: it contains an unbound
   variable `t'_k`. This does not affect the published `c_2=0` specialization,
   but blocks literal use of the general-minorant route.
4. Proposition 3(D), read literally at its stated endpoint
   `omega_0=-10^-10`, is impossible for any nonempty tuple because its fourth
   bin has negative capacity. The proof also changes this lower endpoint to
   `-varepsilon_0`. The repair is to split at the square root and require (D)
   only for `omega_0 >= 0`; a proved specialized version, including the
   near-square-root transition, is in `repaired-proposition3.md`.
5. After that repair, the published rational parameters satisfy all scalar
   and partition conditions with explicit margins. This analytic check is
   independent of `k`, so it applies equally to `k=48`.
6. Section 5 is only a sketch, not an implementable recurrence specification;
   it contains several index/interval errors itemized in `paper-map.md`.
