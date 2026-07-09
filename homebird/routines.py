"""Routines: saved prompts that run on a schedule (Littlebird's Routines,
but local). Schedules are simple strings:

    "hourly"
    "daily HH:MM"
    "weekly mon HH:MM"    (mon,tue,wed,thu,fri,sat,sun)

`run_due` is idempotent per period — a routine fires at most once per its
period, so it can be driven by launchd/cron every few minutes safely.
"""

from __future__ import annotations

import datetime as dt
import re
import time

from .store import Store

_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

DEFAULT_ROUTINES = [
    ("daily-briefing", "daily 08:30",
     "Summarize what I worked on yesterday: key documents, conversations, "
     "meetings and action items. Group by project."),
    ("weekly-summary", "weekly fri 16:30",
     "Write a weekly activity summary: main projects touched, meetings held, "
     "decisions made, and open action items for next week."),
]


def _parse(schedule: str) -> tuple[str, dict]:
    s = schedule.strip().lower()
    if s == "hourly":
        return "hourly", {}
    m = re.fullmatch(r"daily (\d{1,2}):(\d{2})", s)
    if m:
        return "daily", {"h": int(m.group(1)), "m": int(m.group(2))}
    m = re.fullmatch(r"weekly (\w{3}) (\d{1,2}):(\d{2})", s)
    if m and m.group(1) in _DAYS:
        return "weekly", {"dow": _DAYS.index(m.group(1)),
                          "h": int(m.group(2)), "m": int(m.group(3))}
    raise ValueError(f"bad schedule: {schedule!r}")


def next_fire_after(schedule: str, after: float) -> float:
    """Earliest scheduled fire time strictly after `after`."""
    kind, p = _parse(schedule)
    t = dt.datetime.fromtimestamp(after)
    if kind == "hourly":
        nxt = t.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
        return nxt.timestamp()
    if kind == "daily":
        nxt = t.replace(hour=p["h"], minute=p["m"], second=0, microsecond=0)
        if nxt.timestamp() <= after:
            nxt += dt.timedelta(days=1)
        return nxt.timestamp()
    # weekly
    nxt = t.replace(hour=p["h"], minute=p["m"], second=0, microsecond=0)
    delta = (p["dow"] - nxt.weekday()) % 7
    nxt += dt.timedelta(days=delta)
    if nxt.timestamp() <= after:
        nxt += dt.timedelta(days=7)
    return nxt.timestamp()


def is_due(schedule: str, last_run: float | None, now: float) -> bool:
    anchor = last_run if last_run is not None else now - 8 * 86400
    return next_fire_after(schedule, anchor) <= now


class Routines:
    def __init__(self, store: Store):
        self.store = store

    def ensure_defaults(self) -> None:
        for name, sched, prompt in DEFAULT_ROUTINES:
            self.store.db.execute(
                "INSERT OR IGNORE INTO routines(name,schedule,prompt) "
                "VALUES(?,?,?)", (name, sched, prompt))
        self.store.db.commit()

    def add(self, name: str, schedule: str, prompt: str) -> None:
        _parse(schedule)  # validate
        with self.store.db:
            self.store.db.execute(
                "INSERT INTO routines(name,schedule,prompt) VALUES(?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET schedule=excluded.schedule, "
                "prompt=excluded.prompt", (name, schedule, prompt))

    def remove(self, name: str) -> None:
        with self.store.db:
            self.store.db.execute("DELETE FROM routines WHERE name=?", (name,))

    def list(self) -> list[tuple[str, str, str, float | None]]:
        return list(self.store.db.execute(
            "SELECT name,schedule,prompt,last_run FROM routines ORDER BY name"))

    def run(self, name: str, answerer, window_days: float = 1.0) -> str:
        row = self.store.db.execute(
            "SELECT prompt FROM routines WHERE name=?", (name,)).fetchone()
        if not row:
            raise KeyError(name)
        prompt = row[0]
        since = time.time() - window_days * 86400
        passages = self.store.hybrid_search(prompt, limit=12, since=since)
        if not passages:  # fall back to most recent activity in window
            passages = self.store.recent(since, limit=12)
        result = answerer.answer(prompt, passages)
        with self.store.db:
            self.store.db.execute(
                "UPDATE routines SET last_run=? WHERE name=?",
                (time.time(), name))
        # persist output as a note so it's searchable later
        self.store.add(f"Routine '{name}' output:\n{result}", source="note",
                       app="Homebird", window=name)
        return result

    def run_due(self, answerer, now: float | None = None) -> list[str]:
        now = now if now is not None else time.time()
        ran = []
        for name, sched, _prompt, last in self.list():
            if is_due(sched, last, now):
                window = 7.0 if sched.startswith("weekly") else 1.0
                self.run(name, answerer, window_days=window)
                ran.append(name)
        return ran
