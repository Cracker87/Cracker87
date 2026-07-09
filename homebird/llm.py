"""Answering layer.

OllamaChat talks to a local Ollama server (the real experience on the Mac).
ExtractiveAnswerer is a zero-dependency fallback that composes an answer
purely from retrieved passages — useful for tests, CI, and machines without
a model. Both are grounded: every answer cites capture ids.
"""

from __future__ import annotations

import datetime as dt
import json
import textwrap
import urllib.request

from .store import Capture

SYSTEM_PROMPT = (
    "You are Homebird, a private local assistant. Answer the user's question "
    "using ONLY the numbered context passages captured from their own screen "
    "and meetings. Cite passages like [1]. If the context is insufficient, "
    "say so plainly. Never invent facts."
)


def _fmt_ts(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def format_context(passages: list[Capture]) -> str:
    blocks = []
    for i, p in enumerate(passages, 1):
        head = f"[{i}] ({_fmt_ts(p.ts)} · {p.app or p.source}"
        if p.window:
            head += f" · {p.window}"
        head += ")"
        blocks.append(head + "\n" + p.text)
    return "\n\n".join(blocks)


class OllamaChat:
    def __init__(self, model: str = "qwen2.5:14b",
                 base_url: str = "http://127.0.0.1:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.name = f"ollama:{model}"

    def answer(self, question: str, passages: list[Capture]) -> str:
        user = (f"Context passages:\n\n{format_context(passages)}\n\n"
                f"Question: {question}")
        body = json.dumps({
            "model": self.model, "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/chat", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())["message"]["content"]


class ExtractiveAnswerer:
    """No-model fallback: presents the most relevant captures, grouped by
    app, newest first, with citations. Deterministic and fully offline."""

    name = "extractive"

    def answer(self, question: str, passages: list[Capture]) -> str:
        if not passages:
            return ("I found nothing relevant in your captured activity. "
                    "Either it wasn't on screen, or capture was paused.")
        lines = [f"Here is what your captured activity shows "
                 f"(no local LLM running — extractive mode):", ""]
        for i, p in enumerate(passages, 1):
            src = p.app or p.source
            snippet = textwrap.shorten(" ".join(p.text.split()), width=220,
                                       placeholder=" …")
            lines.append(f"[{i}] {_fmt_ts(p.ts)} · {src}"
                         + (f" · {p.window}" if p.window else ""))
            lines.append(f"    {snippet}")
        lines.append("")
        lines.append("Install Ollama and pull a model (e.g. `ollama pull "
                     "qwen2.5:14b`) for synthesized answers.")
        return "\n".join(lines)


def default_answerer(model: str | None = None):
    from .embed import ollama_available
    if ollama_available():
        return OllamaChat(model=model or "qwen2.5:14b")
    return ExtractiveAnswerer()
