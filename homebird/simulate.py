"""Generate a realistic simulated workday of captures.

This stands in for the macOS Accessibility reader when developing or
testing off-Mac. The content deliberately includes near-duplicate frames
(as a real 2–5 Hz screen reader produces) and a secret that must be
redacted, so the pipeline is exercised end to end.
"""

from __future__ import annotations

import datetime as dt


def _ts(day: dt.date, hh: int, mm: int) -> float:
    return dt.datetime.combine(day, dt.time(hh, mm)).timestamp()


def workday(day: dt.date | None = None) -> list[dict]:
    if day is None:
        day = dt.date.today() - dt.timedelta(days=1)
    T = lambda h, m: _ts(day, h, m)
    events: list[dict] = []

    # Morning email triage (Mail) — includes near-duplicate frames
    mail = ("Inbox — 3 unread. From: Priya Sharma — Subject: Q3 vendor "
            "contract renewal. Priya: 'The Acme Corp contract renews on "
            "August 15. Legal needs our redlines by July 20. Can you own "
            "the pricing section?'")
    events.append(dict(ts=T(9, 4), app="Mail", window="Inbox", text=mail))
    events.append(dict(ts=T(9, 4), app="Mail", window="Inbox", text=mail))  # dup frame
    events.append(dict(ts=T(9, 11), app="Mail", window="Inbox", text=(
        "From: Finance Bot — Subject: June spend report ready. Total cloud "
        "spend June: $18,420 (up 12% MoM). Biggest driver: staging cluster "
        "left running over weekends.")))

    # Coding session (VS Code) — includes a secret that must be redacted
    events.append(dict(ts=T(10, 2), app="Visual Studio Code",
                       window="payments/api.py — cracker-billing", text=(
        "def charge_customer(customer_id, amount_cents): TODO handle "
        "idempotency keys for retried webhook deliveries. FIXME: Stripe "
        "webhook handler returns 500 on duplicate events. "
        "api_key = 'sk_live_9hF2kL8mQ4pR7sT1vW3xZ6'")))
    events.append(dict(ts=T(10, 40), app="Visual Studio Code",
                       window="payments/api.py — cracker-billing", text=(
        "Fixed: webhook handler now checks event_id against processed_events "
        "table before charging. Added unit test "
        "test_duplicate_webhook_is_noop. All 42 tests passing.")))

    # Slack thread
    events.append(dict(ts=T(11, 15), app="Slack", window="#eng-payments", text=(
        "Dev: deploy of billing v2.3 is blocked on the migration review. "
        "You: I'll review the migration after standup. Dev: also we should "
        "bump the retry backoff from 30s to 60s, customers are seeing "
        "double-charge alerts that are actually retries.")))

    # Meeting transcript
    events.append(dict(ts=T(14, 0), app="Meeting", window="Billing v2.3 go/no-go",
                       source="meeting", text=(
        "Transcript: Maya: The migration adds the processed_events table, "
        "review looked clean. Decision: ship billing v2.3 Thursday morning. "
        "Action items: (1) You — review and approve migration PR #218 today. "
        "(2) Dev — raise retry backoff to 60s before the deploy. "
        "(3) Maya — draft the incident comms template in case of rollback.")))

    # Afternoon docs work
    events.append(dict(ts=T(16, 20), app="Google Chrome",
                       window="Acme contract redlines — Google Docs", text=(
        "Acme Corp Renewal — pricing section draft: propose 8% uplift capped "
        "at CPI+2, net-45 payment terms, and removal of the auto-renew "
        "clause. Deadline for legal redlines: July 20.")))

    return events


def to_jsonl(events: list[dict]) -> str:
    import json
    return "\n".join(json.dumps(e) for e in events)
