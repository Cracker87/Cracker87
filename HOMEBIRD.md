# Homebird 🐦 — your private, local Littlebird

Everything Littlebird does — always-on screen context, meeting notes, ask-
your-day chat, scheduled routines — but **nothing ever leaves your Mac**.
No cloud storage, no cloud inference, no accounts. Python stdlib only.

## Quick start (any machine — works today)

```sh
# from the repo root
python3 -m unittest discover tests          # 19 tests
python3 -m homebird simulate                # ingest a demo workday
python3 -m homebird ask "what are my action items from the billing meeting?"
python3 -m homebird status
```

Without a local LLM, answers are **extractive** (relevant captures with
timestamps + sources). With [Ollama](https://ollama.com) running, answers
are synthesized by a local model:

```sh
brew install ollama
ollama pull qwen2.5:14b          # ~9 GB — ideal for M4 Pro / 24 GB
ollama pull nomic-embed-text     # real semantic embeddings
python3 -m homebird ask "summarize yesterday"
```

Homebird auto-detects Ollama for both chat and embeddings; no config.

## Live capture on macOS

```sh
cd capture/macos
swiftc -O AXReader.swift -o axreader
./axreader --interval 0.5 | python3 -m homebird ingest -
```

AXReader reads **text from the frontmost window's accessibility tree**
(never screenshots), skips password fields, and only emits changed frames.
See `capture/macos/README.md` for the launchd setup that runs it at login,
and `scripts/meeting_capture.sh` for local whisper.cpp meeting notes.

## Daily use

```sh
homebird() { python3 -m homebird "$@"; }

homebird ask "when is the Acme deadline?" --days 7
homebird search "migration PR"
homebird routine list                     # daily-briefing, weekly-summary
homebird routine run daily-briefing
homebird routine add standup --schedule "daily 09:25" \
    --prompt "Prepare my standup: what I did yesterday and blockers."
```

Schedule `homebird routine run-due` every 5 minutes via launchd/cron —
each routine still fires at most once per period.

## Privacy controls

| Command | Effect |
|---|---|
| `homebird pause` / `resume` | global capture kill switch |
| `homebird deny "1Password"` | app is never captured |
| `homebird purge --days 30` | drop raw captures older than 30 days |
| `homebird delete-all --yes` | wipe everything |
| (automatic) | secrets — API keys, tokens, JWTs, cards (Luhn-checked), SSNs, private keys — are redacted **before** any write |

Data lives in one SQLite file at `~/.homebird/homebird.db`. Rely on
FileVault for at-rest encryption, or swap in SQLCipher.

## Architecture

```
AXReader (Swift, a11y text @2Hz)──┐
whisper.cpp meeting transcripts ──┼─▶ redact ▶ dedupe ▶ SQLite (FTS5 + vectors)
notes / files / simulate ─────────┘                          │
                        Ollama (qwen2.5:14b) ◀─ hybrid RRF ──┘
                              │
              chat answers with [n] citations · routines
```

See `LITTLEBIRD_LOCAL_PLAN.md` for the research and full design.
