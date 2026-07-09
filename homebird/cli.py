"""Homebird CLI.

    homebird status                       show store stats & privacy state
    homebird ingest FILE|-                ingest JSONL captures (- = stdin)
    homebird simulate [--date YYYY-MM-DD] ingest a simulated workday
    homebird ask "question" [--days N]    ask about your activity
    homebird search "terms" [--days N]    raw hybrid search
    homebird routine list|add|remove|run|run-due
    homebird pause | resume               capture kill switch
    homebird deny APP | allow APP         per-app exclusions
    homebird purge --days N               retention purge
    homebird delete-all --yes             wipe every capture
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time

from .llm import default_answerer
from .routines import Routines
from .simulate import to_jsonl, workday
from .store import Store


def _since(days: float | None) -> float | None:
    return None if days is None else time.time() - days * 86400


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="homebird",
                                 description="Private, local context assistant")
    ap.add_argument("--db", help="path to database file (default ~/.homebird)")
    ap.add_argument("--model", help="Ollama chat model override")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    p = sub.add_parser("ingest")
    p.add_argument("file", help="JSONL file of captures, or - for stdin")

    p = sub.add_parser("simulate")
    p.add_argument("--date", help="YYYY-MM-DD (default: yesterday)")

    p = sub.add_parser("ask")
    p.add_argument("question")
    p.add_argument("--days", type=float, default=None,
                   help="only consider the last N days")
    p.add_argument("--k", type=int, default=8, help="passages to retrieve")

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--days", type=float, default=None)
    p.add_argument("--k", type=int, default=10)

    p = sub.add_parser("routine")
    p.add_argument("action",
                   choices=["list", "add", "remove", "run", "run-due"])
    p.add_argument("name", nargs="?")
    p.add_argument("--schedule", help='e.g. "daily 08:30", "weekly fri 16:30"')
    p.add_argument("--prompt")
    p.add_argument("--window-days", type=float, default=1.0)

    sub.add_parser("pause")
    sub.add_parser("resume")
    p = sub.add_parser("deny"); p.add_argument("app")
    p = sub.add_parser("allow"); p.add_argument("app")
    p = sub.add_parser("purge")
    p.add_argument("--days", type=float, required=True)
    p = sub.add_parser("delete-all")
    p.add_argument("--yes", action="store_true")

    args = ap.parse_args(argv)
    store = Store(args.db)

    try:
        return _dispatch(args, store)
    finally:
        store.close()


def _dispatch(args, store: Store) -> int:
    if args.cmd == "status":
        s = store.stats()
        fmt = lambda ts: (dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                          if ts else "—")
        print(f"db          {s['db_path']}")
        print(f"captures    {s['captures']}  "
              f"({fmt(s['first_ts'])} → {fmt(s['last_ts'])})")
        print(f"embedder    {s['embedder']}")
        print(f"paused      {'YES — capture disabled' if s['paused'] else 'no'}")
        print(f"denied apps {', '.join(s['deny_apps']) or '—'}")
        for app, n in s["top_apps"]:
            print(f"  {n:6d}  {app or '(unknown)'}")
        return 0

    if args.cmd == "ingest":
        fh = sys.stdin if args.file == "-" else open(args.file)
        with fh:
            stored, skipped = store.add_jsonl(fh)
        print(f"stored {stored}, skipped {skipped} "
              f"(duplicates/denied/paused/empty)")
        return 0

    if args.cmd == "simulate":
        day = (dt.date.fromisoformat(args.date) if args.date
               else dt.date.today() - dt.timedelta(days=1))
        stored, skipped = store.add_jsonl(
            to_jsonl(workday(day)).splitlines())
        print(f"simulated workday {day}: stored {stored}, skipped {skipped}")
        return 0

    if args.cmd == "ask":
        passages = store.hybrid_search(args.question, limit=args.k,
                                       since=_since(args.days))
        answerer = default_answerer(getattr(args, "model", None))
        print(answerer.answer(args.question, passages))
        return 0

    if args.cmd == "search":
        for p in store.hybrid_search(args.query, limit=args.k,
                                     since=_since(args.days)):
            ts = dt.datetime.fromtimestamp(p.ts).strftime("%Y-%m-%d %H:%M")
            head = " ".join(p.text.split())[:120]
            print(f"#{p.id:<5} {ts}  {p.app or p.source:<22} {head}")
        return 0

    if args.cmd == "routine":
        r = Routines(store)
        r.ensure_defaults()
        if args.action == "list":
            for name, sched, prompt, last in r.list():
                last_s = (dt.datetime.fromtimestamp(last).strftime("%m-%d %H:%M")
                          if last else "never")
                print(f"{name:<18} {sched:<18} last:{last_s}  {prompt[:60]}…")
            return 0
        if args.action == "add":
            if not (args.name and args.schedule and args.prompt):
                print("routine add NAME --schedule ... --prompt ...",
                      file=sys.stderr)
                return 2
            r.add(args.name, args.schedule, args.prompt)
            print(f"routine {args.name!r} saved")
            return 0
        if args.action == "remove":
            r.remove(args.name)
            print(f"routine {args.name!r} removed")
            return 0
        answerer = default_answerer(getattr(args, "model", None))
        if args.action == "run":
            print(r.run(args.name, answerer, window_days=args.window_days))
            return 0
        ran = r.run_due(answerer)
        print(f"ran {len(ran)} due routine(s): {', '.join(ran) or '—'}")
        return 0

    if args.cmd == "pause":
        store.set_paused(True)
        print("capture PAUSED — nothing will be stored until `resume`")
        return 0
    if args.cmd == "resume":
        store.set_paused(False)
        print("capture resumed")
        return 0
    if args.cmd == "deny":
        store.set_deny_list(store.deny_list() + [args.app])
        print(f"{args.app!r} will never be captured")
        return 0
    if args.cmd == "allow":
        store.set_deny_list([a for a in store.deny_list()
                             if a.lower() != args.app.lower()])
        print(f"{args.app!r} removed from deny list")
        return 0
    if args.cmd == "purge":
        n = store.purge(args.days)
        print(f"purged {n} captures older than {args.days:g} days")
        return 0
    if args.cmd == "delete-all":
        if not args.yes:
            print("refusing without --yes", file=sys.stderr)
            return 2
        store.delete_all()
        print("all captures deleted")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
