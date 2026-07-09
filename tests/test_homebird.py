"""Homebird test suite — run with:  python3 -m unittest discover tests -v"""

import datetime as dt
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from homebird.embed import HashEmbedder, cosine
from homebird.llm import ExtractiveAnswerer
from homebird.redact import REDACTED, redact
from homebird.routines import Routines, is_due, next_fire_after
from homebird.simulate import to_jsonl, workday
from homebird.store import Store


def mem_store():
    return Store(":memory:", embedder=HashEmbedder())


class TestRedaction(unittest.TestCase):
    def test_api_keys_and_tokens(self):
        cases = [
            "key AKIAIOSFODNN7EXAMPLE here",
            "token ghp_abcdefghijklmnopqrstuvwxyz0123456789",
            "auth sk-ant-api03-verysecretvalue-here",
            "Authorization: Bearer abcdef0123456789abcdef0123456789",
            "api_key = 'sk_live_9hF2kL8mQ4pR7sT1vW3xZ6'",
            "password: hunter2secret",
        ]
        for c in cases:
            out = redact(c)
            self.assertIn(REDACTED, out, c)
            self.assertNotIn("sk_live", out)
            self.assertNotIn("hunter2secret", out)

    def test_credit_card_luhn(self):
        self.assertIn(REDACTED, redact("card 4111 1111 1111 1111 exp 12/28"))
        # non-Luhn digit runs (order ids etc.) are preserved
        self.assertNotIn(REDACTED, redact("order 1234 5678 9012 3456 shipped"))

    def test_ssn_and_private_key(self):
        self.assertIn(REDACTED, redact("ssn 123-45-6789"))
        blob = "-----BEGIN RSA PRIVATE KEY-----\nMII...\n-----END RSA PRIVATE KEY-----"
        self.assertEqual(redact(blob), REDACTED)

    def test_plain_text_untouched(self):
        s = "Reviewed the Q3 contract and sent redlines to legal."
        self.assertEqual(redact(s), s)


class TestStore(unittest.TestCase):
    def test_dedupe_exact_frames(self):
        s = mem_store()
        a = s.add("same frame text", app="Mail")
        b = s.add("same  frame   TEXT", app="Mail")  # whitespace/case-normalized dup
        c = s.add("same frame text", app="Slack")    # different app -> kept
        self.assertIsNotNone(a)
        self.assertIsNone(b)
        self.assertIsNotNone(c)
        self.assertEqual(s.stats()["captures"], 2)

    def test_pause_blocks_ingest(self):
        s = mem_store()
        s.set_paused(True)
        self.assertIsNone(s.add("secret meeting notes", app="Notes"))
        s.set_paused(False)
        self.assertIsNotNone(s.add("secret meeting notes", app="Notes"))

    def test_deny_list_blocks_app(self):
        s = mem_store()
        s.set_deny_list(["1Password"])
        self.assertIsNone(s.add("vault contents", app="1Password"))
        self.assertIsNone(s.add("vault contents", app="1password"))  # case-insensitive
        self.assertIsNotNone(s.add("vault contents", app="Notes"))

    def test_redaction_applied_before_store(self):
        s = mem_store()
        cid = s.add("deploy key AKIAIOSFODNN7EXAMPLE done", app="Terminal")
        self.assertNotIn("AKIA", s.get(cid).text)

    def test_purge_and_delete_all(self):
        s = mem_store()
        old = time.time() - 40 * 86400
        s.add("ancient thing", app="Mail", ts=old)
        s.add("recent thing", app="Mail")
        self.assertEqual(s.purge(30), 1)
        self.assertEqual(s.stats()["captures"], 1)
        s.delete_all()
        self.assertEqual(s.stats()["captures"], 0)


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.s = mem_store()
        self.s.add("Stripe webhook retries causing duplicate charges",
                   app="Visual Studio Code", window="api.py")
        self.s.add("Lunch menu: tacos on Tuesday", app="Slack",
                   window="#random")
        self.s.add("Acme contract renewal pricing uplift 8 percent",
                   app="Google Chrome", window="Docs")

    def test_keyword_hits_right_doc(self):
        results = self.s.hybrid_search("webhook duplicate charges")
        self.assertTrue(results)
        self.assertIn("Stripe", results[0].text)

    def test_semantic_ish_hit(self):
        results = self.s.hybrid_search("contract pricing renewal")
        self.assertIn("Acme", results[0].text)

    def test_since_filter(self):
        s = mem_store()
        s.add("old news about webhooks", app="Mail",
              ts=time.time() - 10 * 86400)
        s.add("fresh news about webhooks", app="Mail")
        recent = s.hybrid_search("webhooks", since=time.time() - 86400)
        self.assertEqual(len(recent), 1)
        self.assertIn("fresh", recent[0].text)

    def test_fts_query_injection_safe(self):
        # FTS5 operators/quotes in user input must not crash the query
        for q in ['"unclosed', "a AND OR NOT", "col:val", "x*", "((("]:
            self.s.hybrid_search(q)  # must not raise


class TestEmbeddings(unittest.TestCase):
    def test_similar_texts_closer(self):
        e = HashEmbedder()
        a = e.embed("billing webhook retry duplicate charge")
        b = e.embed("duplicate charges from webhook retries in billing")
        c = e.embed("taco tuesday lunch menu salsa")
        self.assertGreater(cosine(a, b), cosine(a, c))


class TestRoutines(unittest.TestCase):
    def test_schedule_parsing_and_next_fire(self):
        base = dt.datetime(2026, 7, 8, 9, 0).timestamp()  # a Wednesday
        nxt = next_fire_after("daily 08:30", base)
        self.assertEqual(dt.datetime.fromtimestamp(nxt).hour, 8)
        self.assertGreater(nxt, base)
        nxt = next_fire_after("weekly fri 16:30", base)
        self.assertEqual(dt.datetime.fromtimestamp(nxt).weekday(), 4)
        with self.assertRaises(ValueError):
            next_fire_after("fortnightly", base)

    def test_is_due_idempotent_per_period(self):
        now = dt.datetime(2026, 7, 8, 9, 0).timestamp()
        self.assertTrue(is_due("daily 08:30", None, now))       # never ran
        just_ran = dt.datetime(2026, 7, 8, 8, 31).timestamp()
        self.assertFalse(is_due("daily 08:30", just_ran, now))  # already fired
        yesterday = dt.datetime(2026, 7, 7, 8, 31).timestamp()
        self.assertTrue(is_due("daily 08:30", yesterday, now))  # next period

    def test_run_records_output_and_last_run(self):
        s = mem_store()
        s.add("worked on billing migration all day", app="VS Code")
        r = Routines(s)
        r.ensure_defaults()
        out = r.run("daily-briefing", ExtractiveAnswerer())
        self.assertIn("billing", out)
        name, sched, prompt, last = [x for x in r.list()
                                     if x[0] == "daily-briefing"][0]
        self.assertIsNotNone(last)
        # output stored as a searchable note
        notes = s.hybrid_search("Routine daily-briefing output")
        self.assertTrue(any(p.source == "note" for p in notes))


class TestEndToEnd(unittest.TestCase):
    """Real-world scenario: a simulated workday, then questions about it."""

    def setUp(self):
        self.s = mem_store()
        day = dt.date(2026, 7, 8)
        stored, skipped = self.s.add_jsonl(to_jsonl(workday(day)).splitlines())
        self.stored, self.skipped = stored, skipped

    def test_ingest_dedupes_and_redacts(self):
        self.assertGreaterEqual(self.skipped, 1)  # the duplicate Mail frame
        hits = self.s.hybrid_search("stripe api key")
        joined = " ".join(p.text for p in hits)
        self.assertNotIn("sk_live", joined)       # secret never persisted

    def test_questions_are_grounded(self):
        ans = ExtractiveAnswerer()
        qa = [
            ("what are my action items from the billing go/no-go meeting",
             "migration PR #218"),
            ("when is the Acme contract deadline for legal redlines",
             "July 20"),
            ("what was june cloud spend", "18,420"),
        ]
        for q, expect in qa:
            out = ans.answer(q, self.s.hybrid_search(q))
            self.assertIn(expect, out, f"Q: {q}\nA: {out}")


if __name__ == "__main__":
    unittest.main()
