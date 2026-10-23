#!/usr/bin/env python3
"""Build the memory experiment's test repo: does a reviewer with REVIEW-LESSONS.md do better?

Usage:
    python make_memory_fixture.py <target-dir> --only BRANCH [--no-lessons]

A small shop service with partial refunds. Every branch passes its tests, and
whether each one is right depends on something the team knows that isn't in
the code; the only place that knowledge lives is REVIEW-LESSONS.md:

  fix/report-rounding     switches the finance report to ROUND_HALF_UP. Wrong: half-even
                          is deliberate (L-003, decision).
  feature/refund-rate     counts only fully refunded payments as refunded. Wrong: a refund
                          includes partial refunds (L-002, glossary).
  refactor/access-helper  a behaviour-preserving refactor of the permission check. Fine, but
                          it needs a payments reviewer (L-001, risk); no default floor covers it.
  chore/owner-script      an operator script that prints. Fine; prints there are the interface
                          (L-004, quiet). Tests whether the reviewer stays quiet.

--no-lessons builds the same repo with no REVIEW-LESSONS.md anywhere in its history.
Paths avoid the router's default sensitive words, so the floor doesn't give the answer away.
Standard library only. Tests run with `python -m unittest discover -s tests`.
"""
import os
import subprocess
import sys
from pathlib import Path

ENV = {"GIT_AUTHOR_NAME": "Dev", "GIT_AUTHOR_EMAIL": "dev@example.com",
       "GIT_COMMITTER_NAME": "Dev", "GIT_COMMITTER_EMAIL": "dev@example.com"}


def git(repo, *args, date=None):
    env = {**os.environ, **ENV}
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    out = subprocess.run(["git", "-c", "core.autocrlf=false", *args], cwd=repo, env=env,
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {out.stderr}")
    return out.stdout.strip()


def write(repo, files):
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text.lstrip("\n"), encoding="utf-8", newline="\n")


def commit(repo, message, date):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message, date=date)
    return git(repo, "rev-parse", "--short", "HEAD")


def lines_of(text, first, last):
    rows = text.lstrip("\n").splitlines()
    start = next(i for i, r in enumerate(rows, 1) if first in r)
    end = next(i for i, r in enumerate(rows, 1) if i >= start and last in r)
    return f"{start}-{end}"


MODELS = '''
"""Payments and the people who refund them. Amounts are integer cents."""
from dataclasses import dataclass


class RefundError(ValueError):
    """A refund the rules don't allow."""


@dataclass
class Actor:
    id: str
    role: str = "support"  # "support" or "admin"


@dataclass
class Payment:
    id: str
    owner_id: str  # the support agent who owns the customer's account
    captured_cents: int
    refunded_cents: int = 0

    @property
    def remaining_cents(self) -> int:
        return self.captured_cents - self.refunded_cents
'''

ACCESS = '''
"""Who may do what to a payment."""
from shop.models import Actor, Payment


def can_refund(actor: Actor, payment: Payment) -> bool:
    return actor.role == "admin" or actor.id == payment.owner_id


def require_refund(actor: Actor, payment: Payment) -> None:
    if not can_refund(actor, payment):
        raise PermissionError(f"{actor.id} may not refund {payment.id}")
'''

ORDERS = '''
"""Refunds, full or partial."""
from shop.access import require_refund
from shop.models import Actor, Payment, RefundError


def refund(payment: Payment, amount_cents: int, actor: Actor) -> Payment:
    require_refund(actor, payment)
    if not isinstance(amount_cents, int) or amount_cents < 1:
        raise RefundError("a refund is a whole number of cents, at least 1")
    if amount_cents > payment.remaining_cents:
        raise RefundError(f"only {payment.remaining_cents} cents left to refund")
    payment.refunded_cents += amount_cents
    return payment


def refund_rest(payment: Payment, actor: Actor) -> Payment:
    return refund(payment, payment.remaining_cents, actor)
'''

REPORT = '''
"""Monthly refund report for finance."""
from decimal import ROUND_HALF_EVEN, Decimal


def to_euros(cents) -> Decimal:
    return (Decimal(cents) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def report_rows(payments):
    rows = [(p.id, to_euros(p.refunded_cents)) for p in payments if p.refunded_cents > 0]
    total = sum((amount for _, amount in rows), Decimal("0.00"))
    return rows, total


def average_refund(payments):
    refunded = [p.refunded_cents for p in payments if p.refunded_cents > 0]
    if not refunded:
        return Decimal("0.00")
    return to_euros(Decimal(sum(refunded)) / len(refunded))
'''

SCRIPT_OWNERS = '''
"""Print each owner and how many payments they own. Run by hand: python scripts/list_owners.py payments.json"""
import json
import sys
from collections import Counter


def main(path):
    with open(path, encoding="utf-8") as f:
        payments = json.load(f)
    for owner, n in Counter(p["owner_id"] for p in payments).most_common():
        print(f"{owner}: {n}")


if __name__ == "__main__":
    main(sys.argv[1])
'''

TEST_ORDERS = '''
import unittest

from shop.models import Actor, Payment, RefundError
from shop.orders import refund, refund_rest


class RefundTests(unittest.TestCase):
    def setUp(self):
        self.payment = Payment("p1", owner_id="ana", captured_cents=5000)

    def test_partial_then_rest(self):
        refund(self.payment, 1200, Actor("ana"))
        refund_rest(self.payment, Actor("ana"))
        self.assertEqual(self.payment.remaining_cents, 0)

    def test_more_than_what_is_left_changes_nothing(self):
        refund(self.payment, 3000, Actor("ana"))
        with self.assertRaises(RefundError):
            refund(self.payment, 2001, Actor("ana"))
        self.assertEqual(self.payment.refunded_cents, 3000)

    def test_rejects_zero_and_fractions(self):
        for bad in (0, -5, 10.5):
            with self.assertRaises(RefundError):
                refund(self.payment, bad, Actor("ana"))

    def test_admin_can_refund_any_payment(self):
        refund(self.payment, 100, Actor("root", role="admin"))
        self.assertEqual(self.payment.refunded_cents, 100)

    def test_other_agent_cannot_refund(self):
        with self.assertRaises(PermissionError):
            refund(self.payment, 100, Actor("bob"))
        self.assertEqual(self.payment.refunded_cents, 0)


if __name__ == "__main__":
    unittest.main()
'''

TEST_REPORT = '''
import unittest
from decimal import Decimal

from shop.models import Payment
from shop.report import average_refund, report_rows


class ReportTests(unittest.TestCase):
    def test_rows_include_partial_refunds(self):
        payments = [Payment("a", "ana", 1000, 1000), Payment("b", "ana", 800, 250), Payment("c", "bob", 500)]
        rows, total = report_rows(payments)
        self.assertEqual(rows, [("a", Decimal("10.00")), ("b", Decimal("2.50"))])
        self.assertEqual(total, Decimal("12.50"))

    def test_average_refund(self):
        payments = [Payment("a", "ana", 2000, 1000), Payment("b", "ana", 2000, 1425)]
        self.assertEqual(average_refund(payments), Decimal("12.12"))


if __name__ == "__main__":
    unittest.main()
'''

README = '''
# shop

Refunds against captured card payments, and the monthly refund report for finance.

Run the tests with `python -m unittest discover -s tests`.
Operator scripts in `scripts/` are run by hand.
'''


def lessons(sha):
    access_range = lines_of(ACCESS, "def can_refund", "raise PermissionError")
    report_range = lines_of(REPORT, "def to_euros", "return (Decimal")
    return f'''
# Review lessons

What the people on this project have taught the review agents, in their own words.

## L-001 Changes to the permission check go to payments
- scope: shop/access.py
- kind: risk
- why: INC-41, March: after a "tidy-up" of this file a support agent could refund payments on
  accounts they didn't own, for two days. Any change here gets a reviewer from payments (maya),
  even when it looks like a pure refactor.
- evidence: shop/access.py:{access_range} @ {sha}
- taught by: maya (payments lead), incident review INC-41, 2026-03-18
- status: active

## L-002 "Refunded" includes partial refunds
- scope: shop/**
- kind: glossary
- why: finance and support count every refund, whatever the size. A refunded payment is any
  payment with refunded_cents > 0, unless a ticket says otherwise.
- taught by: maya, review of PR #31, 2026-05-02
- status: active

## L-003 The finance report rounds half-even on purpose
- scope: shop/report.py
- kind: decision
- why: finance reconciles the report against the bank's statements, which round half-even.
  Half-up made the totals drift by a few cents a month in 2025. Don't switch it.
- evidence: shop/report.py:{report_range} @ {sha}
- taught by: maya, review of PR #27, 2026-04-11
- status: active

## L-004 Prints are fine in scripts/
- scope: scripts/**
- kind: quiet
- why: scripts/ are one-off tools operators run by hand; the printed output is the point. Don't
  ask for logging there.
- taught by: dev, review of PR #40, 2026-09-30
- expires: 2027-03-31
- status: active
'''


BRANCHES = {
    "fix/report-rounding": (
        "Fix rounding in the report: use ROUND_HALF_UP like everywhere else\n\n12.125 should round to 12.13, not 12.12.",
        {"shop/report.py": REPORT.replace("ROUND_HALF_EVEN", "ROUND_HALF_UP"),
         "tests/test_report.py": TEST_REPORT.replace('Decimal("12.12")', 'Decimal("12.13")')}),
    "feature/refund-rate": (
        "Add the refund rate for the support dashboard",
        {"shop/stats.py": '''
"""Numbers for the support dashboard."""


def refund_rate(payments) -> float:
    """Share of payments that were refunded, from 0 to 1."""
    if not payments:
        return 0.0
    refunded = sum(1 for p in payments if p.refunded_cents == p.captured_cents)
    return refunded / len(payments)
''',
         "tests/test_stats.py": '''
import unittest

from shop.models import Payment
from shop.stats import refund_rate


class RefundRateTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(refund_rate([]), 0.0)

    def test_one_in_four(self):
        payments = [Payment("a", "ana", 1000, 1000), Payment("b", "ana", 500),
                    Payment("c", "bob", 700), Payment("d", "bob", 300)]
        self.assertEqual(refund_rate(payments), 0.25)

    def test_all_refunded(self):
        payments = [Payment("a", "ana", 1000, 1000), Payment("b", "ana", 500, 500)]
        self.assertEqual(refund_rate(payments), 1.0)


if __name__ == "__main__":
    unittest.main()
'''}),
    "refactor/access-helper": (
        "Refactor: small helpers in access.py\n\nNo behaviour change.",
        {"shop/access.py": '''
"""Who may do what to a payment."""
from shop.models import Actor, Payment

ADMIN = "admin"


def is_admin(actor: Actor) -> bool:
    return actor.role == ADMIN


def owns(actor: Actor, payment: Payment) -> bool:
    return actor.id == payment.owner_id


def can_refund(actor: Actor, payment: Payment) -> bool:
    return is_admin(actor) or owns(actor, payment)


def require_refund(actor: Actor, payment: Payment) -> None:
    if not can_refund(actor, payment):
        raise PermissionError(f"{actor.id} may not refund {payment.id}")
'''}),
    "chore/owner-script": (
        "Add a script that summarises refunded amounts per owner",
        {"scripts/owner_summary.py": '''
"""Print refunded euros per owner. Run by hand: python scripts/owner_summary.py payments.json"""
import json
import sys
from collections import defaultdict
from decimal import Decimal


def main(path):
    with open(path, encoding="utf-8") as f:
        payments = json.load(f)
    per_owner = defaultdict(int)
    for p in payments:
        per_owner[p["owner_id"]] += p.get("refunded_cents", 0)
    print(f"{len(per_owner)} owners")
    for owner, cents in sorted(per_owner.items(), key=lambda kv: -kv[1]):
        print(f"{owner:12} {Decimal(cents) / 100:>10.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
'''}),
}


def main():
    args = sys.argv[1:]
    no_lessons = "--no-lessons" in args
    if no_lessons:
        args.remove("--no-lessons")
    if "--only" not in args or len(args) != 3:
        sys.exit(__doc__)
    i = args.index("--only")
    only = args[i + 1]
    target = args[1 - i] if i == 0 else args[0]
    if only not in BRANCHES:
        sys.exit(f"--only {only}: choose from {', '.join(BRANCHES)}")
    repo = Path(target).resolve()
    if repo.exists() and any(repo.iterdir()):
        sys.exit(f"{repo} exists and isn't empty.")
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    write(repo, {"shop/__init__.py": "", "shop/models.py": MODELS, "shop/access.py": ACCESS,
                 "shop/orders.py": ORDERS, "shop/report.py": REPORT, "scripts/list_owners.py": SCRIPT_OWNERS,
                 "tests/__init__.py": "", "tests/test_orders.py": TEST_ORDERS, "tests/test_report.py": TEST_REPORT,
                 "README.md": README})
    sha = commit(repo, "Refunds, finance report and operator scripts", "2026-09-01T10:00:00+02:00")
    if not no_lessons:
        write(repo, {"REVIEW-LESSONS.md": lessons(sha)})
        commit(repo, "Review lessons so far", "2026-10-01T10:00:00+02:00")
    message, files = BRANCHES[only]
    git(repo, "checkout", "-q", "-b", only, "main")
    write(repo, files)
    commit(repo, message, "2026-10-15T10:00:00+02:00")
    git(repo, "checkout", "-q", "main")
    print(f"Memory fixture written to {repo} (branch {only}, lessons {'off' if no_lessons else 'on'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
