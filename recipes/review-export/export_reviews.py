"""Trustpilot review export: a company's reviews in a CSV, and optionally in a Google Sheet.

    python export_reviews.py notion.so --pages 3
    python export_reviews.py notion.so --since 2026-10-01 --sheet "https://docs.google.com/spreadsheets/d/<id>/edit"

Reviews come newest first, 20 per page; --since stops paging once reviews get older than that date,
so a weekly run only pays for the new pages. With --sheet, rows go to a worksheet named after the
domain (created if needed), and reviews already in it are skipped.
"""

import argparse
import csv
import os
import sys

from apish import Apish

FIELDS = ["id", "published_at", "rating", "title", "text", "language", "author", "author_country",
          "verified", "replied", "reply", "url"]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Export Trustpilot reviews to CSV or Google Sheets.")
    p.add_argument("domain", help="the company's website domain, as in trustpilot.com/review/<domain>")
    p.add_argument("--pages", type=int, default=5, help="at most this many pages of 20 reviews")
    p.add_argument("--since", help="stop at reviews published before this date (YYYY-MM-DD)")
    p.add_argument("--out", help="CSV file (default: <domain>-reviews.csv)")
    p.add_argument("--sheet", help="Google Sheet link or id to append to (needs GOOGLE_SERVICE_ACCOUNT_FILE)")
    return p.parse_args(argv)


def to_row(r):
    reply = r.get("reply") or {}
    return {
        "id": r["id"],
        "published_at": (r.get("published_at") or "")[:10],
        "rating": r.get("rating"),
        "title": r.get("title") or "",
        "text": r.get("text") or "",
        "language": r.get("language") or "",
        "author": r.get("author") or "",
        "author_country": r.get("author_country") or "",
        "verified": bool(r.get("verified")),
        "replied": bool(reply),
        "reply": (reply.get("message") or reply.get("text") or "") if isinstance(reply, dict) else str(reply),
        "url": r.get("url") or "",
    }


def fetch_reviews(apish, domain, pages, since):
    """Page 1 comes with the company summary; later pages from the reviews endpoint."""
    first = apish.trustpilot.company(domain=domain, options={"raw": False})
    company, credits, rows = first["company"], first.meta.credits_used, []
    res, page = first, 1
    while True:
        batch = [to_row(r) for r in res.get("reviews") or []]
        rows += [r for r in batch if not since or r["published_at"] >= since]
        old = since and batch and batch[-1]["published_at"] < since
        if old or not res.get("next_page") or page >= pages:
            break
        page = res["next_page"]
        res = apish.trustpilot.reviews(domain=domain, page=page, options={"raw": False})
        credits += res.meta.credits_used
    return company, rows, credits


def append_to_sheet(sheet, domain, rows):
    """Append rows the worksheet doesn't have yet (matched on review id). Returns how many were added."""
    import gspread  # pip install gspread

    client = gspread.service_account(filename=os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"])
    book = client.open_by_url(sheet) if sheet.startswith("http") else client.open_by_key(sheet)
    try:
        ws = book.worksheet(domain)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(title=domain, rows=1000, cols=len(FIELDS))
        ws.append_row(FIELDS)
    have = set(ws.col_values(1)[1:])
    new = [[str(r[f]) for f in FIELDS] for r in rows if r["id"] not in have]
    if new:
        ws.append_rows(new, value_input_option="RAW")
    return len(new)


def main(argv=None, apish=None):
    args = parse_args(argv)
    if args.sheet and not os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE"):
        raise SystemExit("--sheet needs GOOGLE_SERVICE_ACCOUNT_FILE: see this recipe's README")
    apish = apish or Apish()  # reads APISH_API_KEY

    company, rows, credits = fetch_reviews(apish, args.domain, args.pages, args.since)
    dist = company.get("rating_distribution") or {}
    recent = company.get("reviews_last_12_months") or "?"
    print(f"{company['name']} ({args.domain}): TrustScore {company.get('trust_score')}, "
          f"{company.get('review_count'):,} reviews, {recent} in the last 12 months")
    if dist:
        print("  stars: " + "  ".join(f"{s}: {dist.get(str(s), dist.get(s, 0))}" for s in (5, 4, 3, 2, 1)))

    out = args.out or f"{args.domain}-reviews.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    if rows:
        avg = sum(r["rating"] for r in rows) / len(rows)
        replied = sum(1 for r in rows if r["replied"])
        print(f"exported {len(rows)} reviews ({rows[-1]['published_at']} to {rows[0]['published_at']}), "
              f"average {avg:.1f} stars, {replied} with a company reply")
    print(f"wrote {out} ({credits} credits)")

    if args.sheet:
        added = append_to_sheet(args.sheet, args.domain, rows)
        print(f"added {added} new reviews to the Google Sheet")
    return rows


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
