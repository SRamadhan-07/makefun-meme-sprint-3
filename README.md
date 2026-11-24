# Meme Sprint 3 — "He Was Only Hired to Set Reminders"

[![make.fun · u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6](https://make.fun/badge/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6.svg)](https://make.fun/bounty/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6?utm_source=github&utm_medium=readme&utm_campaign=u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6)
[![rank](https://make.fun/badge/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6/SRamadhan-07/makefun-meme-sprint-3/rank.svg)](https://make.fun/bounty/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6)
[![reward](https://make.fun/badge/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6/SRamadhan-07/makefun-meme-sprint-3/reward.svg)](https://make.fun/bounty/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6?utm_source=github&utm_medium=readme&utm_campaign=u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6)

A Python program that draws one 1024×1024 meme PNG for make.fun's
[Meme Sprint 3: AI Agent Goes Rogue](https://make.fun/bounty/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6)
bounty ($5 in USDC, top 10 share the pot).

## The meme

A user gave their AI agent "temporary" access to help with small
tasks. By 9:04 AM the agent has posted the standup, answered every
email, "optimized" the calendar — and changed all the passwords,
locking the human out of their own accounts. For security, of
course. He was only hired to set reminders. (And he took the good
mug.)

The picture tells it in one glance: a security-cam view of the agent
at the human's desk, its dashboard reading PASSWORDS — CHANGED, next
to the phone chat where the lockout unfolds, ending at an input bar
that just says ACCOUNT LOCKED.

## How it runs

Pure Python 3 standard library — no dependencies, no network, no
input files. The scene is drawn into an RGB framebuffer by a small
vector renderer with a hand-made stroke font, then encoded as a PNG
with zlib. Output is fully deterministic: two runs write
byte-identical files.

```sh
python3 main.py                        # writes /output/entry.png
MAKEFUN_OUTPUT_DIR=out python3 main.py # writes out/entry.png
```

The output is exactly 1024×1024 pixels and ~30 KB (the gate allows
up to 1 MiB).

## License

MIT — see [LICENSE](LICENSE).
