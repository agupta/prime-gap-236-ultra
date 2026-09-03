# Sources and collision check

Initial acquisition date: 2026-09-01 (Europe/Berlin).  Supplemental BFI
source-chain check and correction-note acquisition: 2026-09-02.

| Artifact | Canonical URL | Local file | SHA-256 |
|---|---|---|---|
| Stadlmann, *bounded gaps between primes*, arXiv:2608.31126 PDF | https://arxiv.org/pdf/2608.31126 | `sources/stadlmann-2608.31126.pdf` | `4296e63a3028fcff62725c7e751811679cbfea78e4d4213486b2f9a3e81ee994` |
| Same, arXiv source bundle | https://export.arxiv.org/e-print/2608.31126 | `sources/stadlmann-2608.31126-source.tar` | `77b09473ece2a81fc0dc144ca604eadc3d876dd9125f9e095d3ef7ec6ff442a5` |
| Stadlmann, *On primes in arithmetic progressions and bounded gaps between many primes*, arXiv:2309.00425 PDF | https://arxiv.org/pdf/2309.00425 | `sources/stadlmann-2309.00425.pdf` | `d356514b423fbd799642e53ed92cad434b084da3630f444a2cc90c084e9ea399` |
| Same, arXiv source bundle | https://export.arxiv.org/e-print/2309.00425 | `sources/stadlmann-2309.00425-source.tar` | `7a2d758c3eda356e433daf8be72fa23eb1b8e1ca85d3f66bfeb116e8258eee3b` |
| Polymath8b, *Variants of the Selberg sieve...*, arXiv:1407.4897 PDF | https://arxiv.org/pdf/1407.4897 | `sources/polymath8b-1407.4897.pdf` | `4085a675d4716db2b22e672d083d4e38262b88b37b8d05b06bcdceb7cb4086a7` |
| Same, arXiv source bundle | https://export.arxiv.org/e-print/1407.4897 | `sources/polymath8b-1407.4897-source.tar` | `a54253946a0192a4afc1e5c849d57b479d19e0997df96a471dd687e74c3eb14d` |
| MIT admissible 48-tuple candidate | https://math.mit.edu/~primegaps/tuples/admissible_48_236.txt | `sources/admissible_48_236.txt` | `adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9` |
| Polymath8a, *New equidistribution estimates of Zhang type*, arXiv:1402.0811v3 PDF | https://arxiv.org/pdf/1402.0811 | `sources/polymath8-edz-1402.0811.pdf` | `f4b4556f9451ea0524b974376b9dbe4478faf3734847897460274f6bae98b65c` |
| Same, arXiv source payload | https://export.arxiv.org/e-print/1402.0811 | `sources/polymath8-edz-1402.0811-source.tar` | `4db2b22532e291782aaed923170de165e0392e49e83b3436163996503f6e13bf` |
| Baker--Irving, *Bounded intervals containing many primes*, arXiv:1505.01815 PDF | https://arxiv.org/pdf/1505.01815 | `sources/baker-irving-1505.01815.pdf` | `eafa5de75e20a226bb151fce3463de2248c05d2d455410717f1371adb0a5ef9e` |
| Same, arXiv source bundle | https://export.arxiv.org/e-print/1505.01815 | `sources/baker-irving-1505.01815-source.tar` | `5c48289c29c4432d5cc2787a8ad48c7585fcf72ba349782067e7d401379dfc42` |
| Bombieri--Friedlander--Iwaniec, corrections to *Primes in arithmetic progressions to large moduli*, arXiv:1903.01371 PDF | https://arxiv.org/pdf/1903.01371 | `sources/bfi-corrections-1903.01371.pdf` | `63b3515b99088d3670d31266e42e96937dc1253c7425da68831aab343608f1d4` |
| Same, arXiv source payload (gzip-compressed single TeX file) | https://export.arxiv.org/e-print/1903.01371 | `sources/bfi-corrections-1903.01371-source.tar` | `77fb13c75f732897870b6619e850705d1021687d15b9ae3688c7dc976a0d4eaa` |

The 2026 paper is arXiv v1, submitted 2026-08-31 17:39:30 UTC; no later version existed at the 2026-09-01 collision gate. Its source bundle contains only `Bounded_Gaps_2.0.tex`, `bibstad.bib`, and arXiv build metadata: it contains no code, matrices, or coefficient vector. PDF-to-text renderings and unpacked source trees are derived artifacts and are not primary downloads.

The bilinear Bombieri--Vinogradov input is quoted as Theorem 2.9 in the
pinned Polymath8a TeX and there attributes its proof to Theorem 0 of
Bombieri--Friedlander--Iwaniec, *Acta Math.* 156 (1986), 203--251,
DOI `10.1007/BF02399204`.  The primary Theorem 0 statement was consulted at
the publisher/YMSC indexed PDF on 2026-09-02 and agrees with Polymath8a's
formulation.  The publisher returned an HTML access page and the advertised
YMSC PDF endpoint returned HTTP 500 during local archival attempts, so no
spurious file or hash is recorded for the 1986 scan.  The authors' pinned
2019 correction note explicitly says that no theorem statement is affected;
its changes concern Lemma 1 and separation arguments in Sections 9--11, not
the large-sieve proof of Theorem 0 in Section 2.

A supplemental 2026-09-02 retrieval through Project Euclid was blocked by
its security page.  The Internet Archive capture of the YMSC URL explicitly
reported `warning: 299 wayback content truncated by "length"`: it contained
only 1,048,576 bytes although the crawler metadata reported 1,582,794 bytes,
and failed PDF cross-reference/page validation.  That partial object was
moved out of the source tree and is not assigned an evidentiary hash.

## One-time collision check

Searches run 2026-09-01:

- `site:arxiv.org 2608.31126 Stadlmann bounded gaps 236 240`
- `"H_1" "236" prime gaps Stadlmann`
- `"admissible_48_236"`
- `Julia Stadlmann code bounded gaps 240 coefficients B_19`

Initial result: no indexed paper, author code, coefficient vector, independent reproduction, or posted unconditional `H_1 <= 236` proof was found. A same-day Reddit discussion of arXiv:2608.31126 mentioned 236 informally but contained no proof or certificate. This is only a collision check, not a priority claim.
