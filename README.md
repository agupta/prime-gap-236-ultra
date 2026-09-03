# Prime Gap 236 — Codex Ultra research prompt

This public repository contains a self-contained research prompt for asking a fresh
Codex session to extend Julia Stadlmann's 2026 bounded-prime-gaps method from
`H_1 <= 240` to the next natural target, `H_1 <= 236`.

The prompt is in [`PROMPT.md`](PROMPT.md). It does not depend on AutoTAO or any other
local repository.

The resulting research package is in [`prime-gap-236/`](prime-gap-236/). Its current
status is recorded in [`prime-gap-236/RESULT.md`](prime-gap-236/RESULT.md); it does not
claim that the target has been proved. One regenerable exact-integration SQLite cache
is omitted because it exceeds GitHub's 100 MB per-file limit.

## Start Codex in one command

Install and authenticate the Codex CLI first. Then clone this repository, enter it, and
start an interactive GPT-5.6 Sol Ultra session with live search and multiagent v2:

```bash
gh repo clone agupta/prime-gap-236-ultra
cd prime-gap-236-ultra

codex \
  --model gpt-5.6-sol \
  -c 'model_reasoning_effort="ultra"' \
  --enable multi_agent_v2 \
  --search \
  --approve-for-me \
  "$(cat PROMPT.md)"
```

The command starts an interactive session rather than `codex exec`, so you can watch,
answer genuine approval questions, steer if needed, and later resume the session.

`--approve-for-me` uses Codex's automatic approval review with workspace-write
confinement. Do not replace it with `--dangerously-bypass-approvals-and-sandbox`.

## Interactive `/model` alternative

If the installed CLI does not accept `ultra` through the config override, launch Codex
without an initial prompt:

```bash
codex --enable multi_agent_v2 --search --approve-for-me
```

Then:

1. Enter `/model`.
2. Select **GPT-5.6 Sol**.
3. Select **Ultra** reasoning effort.
4. Paste the complete contents of `PROMPT.md` and submit it.
5. Enter `/status` to confirm the active model, effort, permissions, and workspace.

Ultra uses automatic task delegation. The prompt additionally tells the root agent how
to manage repeated, diverse multi-agent research rounds and independent audits.

## Expected output

The prompt instructs Codex to create a `prime-gap-236/` research directory in this
repository containing source notes, an approach registry, reproducible experiments,
proof and certificate files, independent verification code, an adversarial audit, and an
honest `RESULT.md`.

Commit checkpoints periodically during a long run. No generated result should be made
public or presented as a theorem without independent expert review.
