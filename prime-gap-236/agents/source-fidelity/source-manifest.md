# Primary-source manifest

Retrieved 2026-09-01 (Europe/Berlin). SHA-256 hashes below are hashes of the
local bytes, not hashes quoted by the publishers.

## Stadlmann 2026

| Item | Version/date | URL | SHA-256 |
|---|---|---|---|
| PDF | arXiv:2608.31126v1; submitted 2026-08-31 17:39:30 UTC; 34 pages | https://arxiv.org/pdf/2608.31126 | `4296e63a3028fcff62725c7e751811679cbfea78e4d4213486b2f9a3e81ee994` |
| abstract/version record | v1 only as retrieved | https://arxiv.org/abs/2608.31126 | `c72b0b2be3a7762060b25c60eda4defe797c86432c77523bbde436b42577504b` |
| e-print tarball | v1 | https://export.arxiv.org/e-print/2608.31126 | `77b09473ece2a81fc0dc144ca604eadc3d876dd9125f9e095d3ef7ec6ff442a5` |
| extracted TeX | `Bounded_Gaps_2.0.tex`, 1,885 lines | member of e-print tarball | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| extracted bibliography | `bibstad.bib` | member of e-print tarball | `b2f7a6a39b06cfd839ad0942661e3868fcfbbd22f08a3421bb497c4bbfd96cae` |
| arXiv build manifest | `00README.json` | member of e-print tarball | `2ce2c3bc69b276bc0cce446b5fea517547050c1ab0870298eac716d71d0ab9a0` |

The tarball has exactly three members:

```text
00README.json
bibstad.bib
Bounded_Gaps_2.0.tex
```

In particular, it contains no source code, matrix data, coefficient vector,
certificate, or ancillary file. The PDF and TeX agree on all key ambiguous
passages checked below, including `degree <= 21` versus `B_19`, the endpoint
of Proposition 3(D), and the final numerical parameter paragraph.

## Primary predecessors actually invoked

| Item | Version/date | URL | SHA-256 |
|---|---|---|---|
| Polymath8b, *Variants of the Selberg sieve...* | arXiv:1407.4897v4; 2014-12-22; 80 pages | https://arxiv.org/pdf/1407.4897 | `4085a675d4716db2b22e672d083d4e38262b88b37b8d05b06bcdceb7cb4086a7` |
| published Polymath8b page/DOI | published 2014-10-17 | https://doi.org/10.1186/s40687-014-0012-7 | not stored |
| Polymath8b erratum | published 2015-07-30; bibliographic corrections only | https://doi.org/10.1186/s40687-015-0033-x | `4f601de0598f307f722670e52136f2c4451908533047accc8c63f62f264a6785` |
| Polymath8a, *New equidistribution estimates of Zhang type* | arXiv:1402.0811v3; 2014-09-03; 107 PDF pages | https://arxiv.org/pdf/1402.0811 | `f4b4556f9451ea0524b974376b9dbe4478faf3734847897460274f6bae98b65c` |
| Stadlmann, *On primes in arithmetic progressions and bounded gaps between many primes* | arXiv:2309.00425v3; 2025-02-22; 43 pages; published Adv. Math. 468 (2025), 110190 | https://arxiv.org/pdf/2309.00425 | `d356514b423fbd799642e53ed92cad434b084da3630f444a2cc90c084e9ea399` |

The Polymath8b erratum only adds missing arXiv identifiers to references; it
does not alter Theorem 3.6 or Lemma 4.1, the two results used in Stadlmann's
Section 2.

## Tuple database

| Item | URL | SHA-256 |
|---|---|---|
| candidate 48-tuple | https://math.mit.edu/~primegaps/tuples/admissible_48_236.txt | `adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9` |
| MIT prime-gap database landing page | https://math.mit.edu/~primegaps/ | `481bab570673bf0c05c367ab458a03af250b6e958bbf21cf03856929a6933a2b` |

The local tuple has 48 distinct entries, minimum 0, maximum 236. A quick
independent residue check found a missing class for every prime at most 48;
this observation is ancillary to this source-fidelity package and is not a
substitute for the project's standalone final checker.

## Initial exact-phrase/code search

On 2026-09-01, searches for the paper title together with `B_19`, `2a+b`,
`code`, `coefficients`, and arXiv number `2608.31126`, including a GitHub-domain
query, found no author code, coefficient vector, matrix dump, or independent
reproduction. This is an absence-of-hit report only, not a priority claim.

