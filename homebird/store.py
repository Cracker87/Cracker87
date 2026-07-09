"""Local datastore: one SQLite file with FTS5 keyword index + vectors.

Privacy properties enforced here:
  * redaction runs before any write (callers pass raw text; we redact);
  * exact-duplicate captures are dropped via a content hash;
  * per-app deny list is checked before ingest;
  * retention purge and delete-all are first-class operations.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from . import embed as embed_mod
from .redact import redact

DEFAULT_DIR = Path.home() / ".homebird"

SCHEMA = """
CREATE TABLE IF NOT EXISTS captures(
    id      INTEGER PRIMARY KEY,
    ts      REAL NOT NULL,
    source  TEXT NOT NULL,          -- screen | meeting | note | file
    app     TEXT NOT NULL DEFAULT '',
    window  TEXT NOT NULL DEFAULT '',
    text    TEXT NOT NULL,
    hash    TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_captures_ts ON captures(ts);
CREATE VIRTUAL TABLE IF NOT EXISTS captures_fts USING fts5(
    text, app, window, content='captures', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS captures_ai AFTER INSERT ON captures BEGIN
    INSERT INTO captures_fts(rowid, text, app, window)
    VALUES (new.id, new.text, new.app, new.window);
END;
CREATE TRIGGER IF NOT EXISTS captures_ad AFTER DELETE ON captures BEGIN
    INSERT INTO captures_fts(captures_fts, rowid, text, app, window)
    VALUES ('delete', old.id, old.text, old.app, old.window);
END;
CREATE TABLE IF NOT EXISTS embeddings(
    capture_id INTEGER PRIMARY KEY REFERENCES captures(id) ON DELETE CASCADE,
    backend    TEXT NOT NULL,
    vec        BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS routines(
    name     TEXT PRIMARY KEY,
    schedule TEXT NOT NULL,
    prompt   TEXT NOT NULL,
    last_run REAL
);
CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);
"""


@dataclass
class Capture:
    id: int
    ts: float
    source: str
    app: str
    window: str
    text: str


def _norm_for_hash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


class Store:
    def __init__(self, path: str | Path | None = None, embedder=None):
        if path is None:
            DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
            path = DEFAULT_DIR / "homebird.db"
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        self.embedder = embedder or embed_mod.default_embedder()

    # ---------------- settings / deny list ----------------

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.db.execute(
            "SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value))

    def deny_list(self) -> list[str]:
        raw = self.get_setting("deny_apps", "[]")
        return json.loads(raw)

    def set_deny_list(self, apps: list[str]) -> None:
        self.set_setting("deny_apps", json.dumps(sorted(set(apps))))

    def paused(self) -> bool:
        return self.get_setting("paused", "0") == "1"

    def set_paused(self, value: bool) -> None:
        self.set_setting("paused", "1" if value else "0")

    # ---------------- ingest ----------------

    def add(self, text: str, source: str = "screen", app: str = "",
            window: str = "", ts: float | None = None) -> int | None:
        """Redact, dedupe, and store one capture. Returns row id or None
        if the capture was skipped (paused, denied app, empty, duplicate)."""
        if self.paused():
            return None
        if app and any(d.lower() == app.lower() for d in self.deny_list()):
            return None
        text = redact(text).strip()
        if len(text) < 3:
            return None
        h = hashlib.sha256(
            (_norm_for_hash(text) + "|" + app + "|" + window).encode()
        ).hexdigest()
        ts = ts if ts is not None else time.time()
        with self.db:
            cur = self.db.execute(
                "INSERT OR IGNORE INTO captures(ts,source,app,window,text,hash)"
                " VALUES(?,?,?,?,?,?)", (ts, source, app, window, text, h))
            if cur.rowcount == 0:
                return None  # duplicate
            cid = cur.lastrowid
            vec = self.embedder.embed(text)
            self.db.execute(
                "INSERT INTO embeddings(capture_id,backend,vec) VALUES(?,?,?)",
                (cid, self.embedder.name, embed_mod.pack(vec)))
        return cid

    def add_jsonl(self, lines) -> tuple[int, int]:
        """Ingest an iterable of JSON lines {ts?,source?,app?,window?,text}.
        Returns (stored, skipped)."""
        stored = skipped = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            rid = self.add(rec["text"], rec.get("source", "screen"),
                           rec.get("app", ""), rec.get("window", ""),
                           rec.get("ts"))
            if rid is None:
                skipped += 1
            else:
                stored += 1
        return stored, skipped

    # ---------------- search ----------------

    @staticmethod
    def _fts_query(query: str) -> str:
        toks = re.findall(r"[A-Za-z0-9]+", query)
        return " OR ".join(f'"{t}"' for t in toks) if toks else '""'

    def keyword_search(self, query: str, limit: int = 20,
                       since: float | None = None) -> list[tuple[int, float]]:
        sql = ("SELECT c.id, bm25(captures_fts) AS score FROM captures_fts "
               "JOIN captures c ON c.id = captures_fts.rowid "
               "WHERE captures_fts MATCH ?")
        params: list = [self._fts_query(query)]
        if since is not None:
            sql += " AND c.ts >= ?"
            params.append(since)
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)
        return [(r[0], r[1]) for r in self.db.execute(sql, params)]

    def vector_search(self, query: str, limit: int = 20,
                      since: float | None = None) -> list[tuple[int, float]]:
        qvec = self.embedder.embed(query)
        sql = ("SELECT e.capture_id, e.vec FROM embeddings e "
               "JOIN captures c ON c.id = e.capture_id WHERE e.backend = ?")
        params: list = [self.embedder.name]
        if since is not None:
            sql += " AND c.ts >= ?"
            params.append(since)
        scored = []
        for cid, blob in self.db.execute(sql, params):
            scored.append((cid, embed_mod.cosine(qvec, embed_mod.unpack(blob))))
        scored.sort(key=lambda x: -x[1])
        return scored[:limit]

    def hybrid_search(self, query: str, limit: int = 8,
                      since: float | None = None) -> list[Capture]:
        """Reciprocal-rank fusion of keyword and vector results."""
        k = 60.0
        ranks: dict[int, float] = {}
        for rank, (cid, _) in enumerate(self.keyword_search(query, 30, since)):
            ranks[cid] = ranks.get(cid, 0.0) + 1.0 / (k + rank + 1)
        for rank, (cid, _) in enumerate(self.vector_search(query, 30, since)):
            ranks[cid] = ranks.get(cid, 0.0) + 1.0 / (k + rank + 1)
        top = sorted(ranks.items(), key=lambda x: -x[1])[:limit]
        return [self.get(cid) for cid, _ in top]

    def get(self, cid: int) -> Capture:
        r = self.db.execute(
            "SELECT id,ts,source,app,window,text FROM captures WHERE id=?",
            (cid,)).fetchone()
        return Capture(*r)

    def recent(self, since: float, limit: int = 200) -> list[Capture]:
        rows = self.db.execute(
            "SELECT id,ts,source,app,window,text FROM captures "
            "WHERE ts >= ? ORDER BY ts LIMIT ?", (since, limit))
        return [Capture(*r) for r in rows]

    # ---------------- retention ----------------

    def purge(self, older_than_days: float) -> int:
        cutoff = time.time() - older_than_days * 86400
        with self.db:
            cur = self.db.execute("DELETE FROM captures WHERE ts < ?",
                                  (cutoff,))
        return cur.rowcount

    def delete_all(self) -> None:
        with self.db:
            self.db.execute("DELETE FROM captures")
            self.db.execute("DELETE FROM embeddings")

    def stats(self) -> dict:
        n = self.db.execute("SELECT COUNT(*) FROM captures").fetchone()[0]
        span = self.db.execute(
            "SELECT MIN(ts), MAX(ts) FROM captures").fetchone()
        apps = self.db.execute(
            "SELECT app, COUNT(*) FROM captures GROUP BY app "
            "ORDER BY COUNT(*) DESC LIMIT 10").fetchall()
        return {"captures": n, "first_ts": span[0], "last_ts": span[1],
                "top_apps": apps, "embedder": self.embedder.name,
                "paused": self.paused(), "deny_apps": self.deny_list(),
                "db_path": self.path}

    def close(self) -> None:
        self.db.close()
