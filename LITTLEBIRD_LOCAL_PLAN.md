# Little Bird — Local & Private Clone: Architecture Research + Build Plan

> Goal: understand how Littlebird (littlebird.ai) is built, then design and plan a
> version that runs **entirely on your own machine** — no cloud storage, no cloud
> inference, no data leaving the device.
>
> **Target machine (confirmed):** MacBook with **Apple M4 Pro, 24 GB unified memory**,
> macOS. This is a strong local-AI target — model picks below are pinned to it.
>
> **Status: IMPLEMENTED.** The working application now lives in this repo — see
> `HOMEBIRD.md` for usage. Phases 0–2 and 4 (store, hybrid search, RAG chat,
> routines, privacy controls, CLI) are built and covered by a 19-test suite;
> the macOS capture daemon (`capture/macos/AXReader.swift`) and whisper.cpp
> meeting script ship as source to compile/run on the Mac. Two corrections vs.
> the original plan, discovered during implementation: (1) vectors are stored
> as blobs in plain SQLite with pure-Python cosine + RRF instead of the
> `sqlite-vec` extension — zero dependencies, plenty fast at personal scale;
> `sqlite-vec` remains an optional optimization. (2) at-rest encryption defers
> to FileVault by default; SQLCipher is optional, not the default.

---

## Part 1 — What Littlebird actually is (research findings)

Littlebird is a native **macOS** "full-context" AI assistant that launched publicly
in March 2026 alongside an $11M seed round. Its pitch: an always-on assistant that
*already knows what you're working on*, so you can ask questions or take actions
across your apps without re-explaining context.

### How it captures context (the core trick)
- **Screen reading via macOS Accessibility APIs, not screenshots.** It walks the
  accessibility tree of the **frontmost window** and extracts structured *text*
  nodes. An observer scans the active window ~**20× per second**.
- Because it stores **text, not images**, storage is tiny, retrieval is fast, and
  the privacy surface is smaller than screenshot-based tools (e.g. Rewind).
- It **redacts password fields** and **ignores minimized windows** by default.
- Very low resource cost (testers report ~0.05% battery/hour).
- **Meeting capture:** a built-in note-taker taps **system audio**, transcribes in
  real time, and generates notes + action items.

### How it stores & queries
- Captured screen text + transcripts are normalized into **searchable, queryable
  text** and indexed so the assistant can answer questions grounded in your real
  work ("unified memory across all apps").
- **Where it lives today:** encrypted, but **stored in the cloud on AWS**. This is
  the single biggest gap versus "private and local," and the main thing our clone
  changes.

### Assistant / actions layer
- Chat interface (Mac + iPhone) with continuity across devices.
- **Routines:** scheduled prompts that run at intervals — e.g. *daily briefing*,
  *weekly activity summary*, *yesterday's work summary*.
- **Integrations:** hundreds of app connectors (project mgmt, design, dev tools,
  CRM, finance, meetings, marketing, analytics). **MCP support** was announced as
  imminent.

### Privacy posture
- SOC 2 certified, GDPR/CCPA compliant, **never trains on user data**, per-app/site
  exclusions, pause capture, one-click delete. But **inference and storage are
  cloud-side** — your context does leave the machine.

### Prior art worth stealing from
- **Screenpipe** is an open-source, local-first alternative (24/7 screen + audio
  capture into a local store you query with an LLM). It's a realistic starting
  skeleton for the capture + storage layers rather than building from zero.

---

## Part 2 — Design goals for the local clone

1. **100% on-device.** No AWS, no cloud LLM, no telemetry. All capture, storage,
   embeddings, and inference run locally. Network is optional and off by default.
2. **Same core loop as Littlebird:** passively capture context → index it →
   let a local LLM answer/act grounded in that context → run scheduled routines.
3. **Privacy by construction:** encrypted-at-rest local store, per-app/site
   allow/deny lists, secret redaction, pause switch, hard delete, retention window.
4. **Text-first capture** (accessibility tree, not screenshots) to keep storage and
   the privacy surface small — mirror Littlebird's key design choice.
5. **Extensible actions via local MCP**, so "integrations" are MCP servers you run,
   not third-party cloud connectors.

**Working name for the build:** *Homebird* (a private Little Bird). Rename freely.

---

## Part 3 — Target architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│  Homebird (all processes local to your machine)                         │
│                                                                         │
│  CAPTURE                    INGEST/INDEX              REASON/ACT         │
│  ┌───────────────┐          ┌──────────────┐         ┌────────────────┐ │
│  │ Screen reader │─text──▶  │ Redactor +   │         │ Chat / Agent   │ │
│  │ (a11y tree,   │          │ deduper      │         │ orchestrator   │ │
│  │  ~5–20 Hz)    │          │              │         │ (RAG loop)     │ │
│  └───────────────┘          │ ┌──────────┐ │  query  │                │ │
│  ┌───────────────┐          │ │ chunker  │ │◀────────│ local LLM      │ │
│  │ Audio capture │─pcm──▶   │ │ +embed   │ │ context │ (Ollama)       │ │
│  │ + whisper.cpp │─text──▶  │ └──────────┘ │────────▶│ + tools (MCP)  │ │
│  └───────────────┘          └──────┬───────┘         └───────┬────────┘ │
│                                    ▼                         │          │
│                     ┌──────────────────────────┐            │          │
│                     │ Local store              │            │          │
│                     │ SQLite + FTS5 (keyword)   │◀───────────┘          │
│                     │ + sqlite-vec (semantic)   │                       │
│                     │ encrypted at rest         │                       │
│                     └──────────────────────────┘                       │
│                                                                         │
│  ROUTINES: local scheduler (cron) fires saved prompts on intervals      │
│  UI: menu-bar app + chat window + capture controls / kill switch        │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.1 Capture layer
- **Screen text (macOS):** use the **Accessibility API** (`AXUIElement`) to read the
  focused window's element tree; extract role+value text. Poll on focus/change
  events plus a low-frequency timer (start at 2–5 Hz, not 20 Hz, to keep it simple
  and cheap; raise later). Requires the user to grant **Accessibility** permission.
  - **Cross-platform note:** Linux → AT-SPI (`pyatspi`/AT-SPI2); Windows → UI
    Automation (UIA). Same "read the a11y tree" idea, different API per OS. If your
    "machine" is not a Mac, this layer is the one that changes most.
  - Fallback where a11y text is unavailable (e.g. canvas/Electron apps that expose
    nothing): optional **local OCR** (Apple Vision framework / Tesseract) on a
    single-frame grab, off by default because it's heavier and less private.
- **Audio/meetings:** capture **system + mic audio** (macOS `ScreenCaptureKit` audio
  or a virtual device like BlackHole) and transcribe on-device with
  **whisper.cpp** (`base`/`small` models are enough for notes). Produce transcript +
  LLM-generated summary/action items.

### 3.2 Ingest / index
- **Redactor** (runs before anything is stored): drop password/secure fields, mask
  patterns (API keys, card numbers, SSNs), and honor per-app/site deny lists.
- **Deduper:** the a11y tree barely changes frame-to-frame; hash windows and only
  persist deltas so you don't store the same screen 5×/sec.
- **Chunk + embed:** split captured text into passages; embed with a **local**
  embedding model (e.g. `nomic-embed-text` or `bge-small` via Ollama /
  `sentence-transformers`).

### 3.3 Storage
- **SQLite**, single file, the whole datastore.
  - **FTS5** virtual table for fast keyword search.
  - **sqlite-vec** (or `sqlite-vss`) for vector similarity — keeps semantic search
    in the same DB, no separate vector server. (pgvector is the alternative if you'd
    rather run local Postgres; SQLite is lighter for a personal app.)
- **Encryption at rest:** SQLCipher, or app-level encryption with a key in the OS
  keychain. Configurable **retention window** (e.g. purge raw captures >30 days,
  keep summaries).

### 3.4 Reason / act (the assistant)
- **Local LLM via Ollama** (e.g. Llama 3.x / Qwen 2.5 / Mistral, sized to your RAM/
  GPU). No cloud API calls.
- **RAG loop:** hybrid retrieve (FTS5 keyword + vector) → rerank → stuff top
  passages into the prompt → answer with citations back to source app/time.
- **Tools/actions via MCP:** run a local **MCP host** so the assistant can *do*
  things (read files, query the DB, call local app scripts). "Integrations" = local
  MCP servers you choose to run, mirroring Littlebird's MCP direction but fully
  local. Keep a strict allow-list of tools.

### 3.5 Routines
- A local scheduler (system cron / `launchd` on macOS / an in-app scheduler) that
  fires saved prompts on a schedule and writes the output to a notes store or a
  notification: *daily briefing*, *weekly summary*, *yesterday's work*.

### 3.6 UI
- **Menu-bar app** with: capture on/off **kill switch**, per-app exclusions, a
  live "what am I capturing right now" indicator, and a **chat window**.
- Native SwiftUI is the clean macOS path; a Tauri/Electron shell is the fastest
  cross-platform path if you want Linux/Windows too.

### Suggested stack — pinned to M4 Pro / 24 GB
| Layer | Pick for this machine | Why |
|---|---|---|
| Capture (mac) | Swift + Accessibility API / ScreenCaptureKit | native, low overhead, correct permissions |
| Transcription | whisper.cpp **`medium`** (Metal) | M4 Pro handles medium easily; better meeting accuracy than small |
| Store | SQLite + FTS5 + sqlite-vec (+ SQLCipher) | one file, hybrid search, encrypted |
| Embeddings | Ollama `nomic-embed-text` (~0.3 GB) | local, no keys, fast |
| LLM (default) | **Qwen2.5-14B-Instruct Q4_K_M** (~9 GB) via Ollama or MLX | best quality that fits comfortably in 24 GB |
| LLM (fast/routines) | **Llama-3.1-8B** or **Qwen2.5-7B** Q4 (~5 GB) | snappier for background routines / quick asks |
| Actions | local MCP host | extensible, matches Littlebird's roadmap |
| Orchestration | Python or TypeScript service | glue: ingest, RAG, routines |
| UI | **SwiftUI menu-bar app** | native mac feel + kill switch (mac-only build) |

**Memory budget (24 GB unified):** a 14B Q4 model uses ~9–11 GB at runtime, leaving
comfortable room for macOS, the capture service, whisper, and embeddings running
concurrently. **32B models are not recommended** here — Q4 alone is ~18–20 GB and
would starve the rest of the pipeline. Stay in the **7B–14B** band.

**Consider MLX over Ollama for inference.** Apple's **MLX** runtime is typically
faster and lighter than llama.cpp/Ollama on Apple Silicon and uses the unified
memory + Neural Engine well. Ollama is the easier on-ramp; benchmark both in Phase 0
and keep whichever gives better tokens/sec at your chosen quant.

---

## Part 4 — Privacy & security design (the whole point)

- **No network by default.** Ship with outbound network disabled for the capture/
  LLM path; any sync is opt-in and peer-to-peer/local only.
- **Encrypted store** (SQLCipher) with the key in the OS keychain.
- **Redaction before persistence**, not after.
- **Consent surfaces:** global pause, per-app and per-site allow/deny, "incognito"
  hotkey, and a visible capture indicator.
- **Retention & delete:** configurable auto-purge + one-click "delete everything."
- **Never trains on your data** (there is no training pipeline at all).

---

## Part 5 — Build phases

**Phase 0 — Spike (½–1 wk):** stand up Ollama + a SQLite/FTS5/sqlite-vec store; prove
the RAG loop by hand-feeding a few docs and asking questions with citations.

**Phase 1 — Screen capture MVP (1–2 wk):** macOS Accessibility reader for the
frontmost window → redactor → dedupe → store. Menu-bar on/off toggle. Verify text
capture + search works on real apps.

**Phase 2 — Ask-your-day (1 wk):** wire chat UI to the RAG loop over captured screen
text. Hybrid retrieval + citations to app/time.

**Phase 3 — Meetings (1–2 wk):** system-audio capture + whisper.cpp transcription →
summaries/action items into the store, queryable alongside screen context.

**Phase 4 — Routines (½–1 wk):** scheduler + saved prompts (daily briefing, weekly
summary) writing to notes/notifications.

**Phase 5 — Actions via MCP (1–2 wk):** local MCP host + a couple of safe servers
(filesystem, the Homebird DB) so the assistant can act, with a tool allow-list.

**Phase 6 — Hardening (ongoing):** encryption, retention/purge, per-app exclusions,
redaction rules, incognito, performance tuning (raise capture rate carefully).

*Rough solo effort to a genuinely useful daily driver: ~6–10 weeks.*

---

## Part 6 — Hard parts & risks

- **Accessibility coverage is uneven.** Native apps expose rich trees; some Electron/
  canvas/game apps expose almost nothing → you'll need the optional OCR fallback for
  those, which is heavier and less private.
- **Permissions friction (macOS):** Accessibility + Screen/Audio recording prompts,
  and TCC can be finicky; budget time for the entitlement/permission plumbing.
- **Local LLM quality vs. size:** grounding + citations matter more than raw model
  size, but very small models will feel weaker than Littlebird's cloud models.
  Match model to your hardware.
- **Dedupe/noise:** 2–20 Hz capture produces huge redundancy; good hashing/deltas are
  essential or the DB and the context window fill with junk.
- **Cross-platform:** if the "machine" is Linux/Windows, the capture layer is a
  rewrite (AT-SPI / UI Automation). Everything downstream (store/RAG/LLM/routines) is
  portable.

---

## Part 7 — Decisions (resolved for M4 Pro / 24 GB)

1. **Target OS:** macOS — capture layer uses the Accessibility API + ScreenCaptureKit.
2. **UI:** **SwiftUI menu-bar app** (mac-only; Tauri not needed).
3. **Models (pinned):** default **Qwen2.5-14B Q4** for chat, **Llama-3.1-8B/Qwen2.5-7B
   Q4** for fast background routines, `nomic-embed-text` for embeddings, whisper.cpp
   `medium` for meetings. Benchmark **MLX vs Ollama** in Phase 0. Stay in the 7B–14B
   band; no 32B.
4. **Fork or from-scratch?** Recommend **starting from Screenpipe** for capture+store
   and layering our own RAG/routines/MCP on top, rather than greenfield.

Still worth a quick answer before Phase 1: (a) do you want **meeting transcription**
in the MVP or later? (b) which real apps do you most want it to "know" (browser,
Slack, VS Code, Notion…) — that sets which accessibility trees to test first.

---

### Sources
- [TechCrunch — Littlebird raises $11M](https://techcrunch.com/2026/03/23/littlebird-raises-11m-to-capture-context-from-your-computer-so-you-can-query-your-data/)
- [Littlebird — home](https://littlebird.ai/) · [FAQ](https://littlebird.ai/faq)
- [Efficient App — Littlebird review](https://efficient.app/apps/littlebird)
- [Screenpipe vs Littlebird (open-source alternative)](https://screenpipe.com/compare/littlebird)
- [AI CERTs — Littlebird $11M seed](https://www.aicerts.ai/news/littlebird-privacy-assistant-raises-11m-seed/)
- [Toolworthy — Littlebird review](https://www.toolworthy.ai/tool/littlebird-ai)
- [Product Hunt — Littlebird](https://www.producthunt.com/products/littlebird)
