"""Google rank tracker: where your site ranks for each keyword, and how that changed since the last run.

    python rank.py --domain python.org --keywords keywords.txt
    python rank.py --domain python.org "python tutorial" "learn python" --depth 20 --country gb

Each run appends to rankings.csv (date, keyword, position, url), so the file is your ranking history.
Run it weekly from cron; a keyword is reported as a drop when it falls by --alert places or more.
"""

import argparse
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse

from apish import Apish

FIELDS = ["checked_at", "keyword", "country", "position", "url", "title"]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Track Google rankings for a domain.")
    p.add_argument("keywords", nargs="*", help="keywords (or use --keywords-file)")
    p.add_argument("--domain", required=True, help="your site, e.g. example.com (subdomains count)")
    p.add_argument("--keywords-file", help="one keyword per line")
    p.add_argument("--depth", type=int, default=10, help="results to check per keyword, 10-100 (each 10 is one page)")
    p.add_argument("--country", default="us", help="two-letter country code")
    p.add_argument("--location", help='search as if from a place, e.g. "Austin,Texas,United States"')
    p.add_argument("--alert", type=int, default=3, help="report drops of this many places or more")
    p.add_argument("--history", default="rankings.csv")
    return p.parse_args(argv)


def host(url):
    h = (urlparse(url or "").hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def position_of(results, domain):
    """The first organic result on the domain or one of its subdomains."""
    domain = host("https://" + domain.split("://")[-1])
    for r in results:
        h = host(r.get("url"))
        if h == domain or h.endswith("." + domain):
            return r
    return None


def last_positions(path):
    """keyword -> the position from the most recent earlier run ('' = not in the checked results)."""
    if not os.path.exists(path):
        return {}
    last = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            last[(row["keyword"], row["country"])] = row["position"]
    return last


def main(argv=None, apish=None):
    args = parse_args(argv)
    apish = apish or Apish()  # reads APISH_API_KEY
    keywords = list(args.keywords)
    if args.keywords_file:
        with open(args.keywords_file, encoding="utf-8") as f:
            keywords += [k.strip() for k in f if k.strip() and not k.startswith("#")]
    if not keywords:
        raise SystemExit("no keywords: pass them as arguments or with --keywords-file")

    previous = last_positions(args.history)
    params = {"country": args.country, "limit": max(10, min(args.depth, 100))}
    if args.location:
        params["location"] = args.location

    def search(keyword):
        return keyword, apish.google.search(q=keyword, **params, options={"raw": False})

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(search, keywords))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, drops, credits = [], [], 0
    print(f"{'keyword':<36} {'now':>4} {'before':>6}  url")
    for keyword, res in results:
        credits += res.meta.credits_used
        hit = position_of(res["results"], args.domain)
        pos = hit["position"] if hit else ""
        before = previous.get((keyword, args.country), "")
        rows.append({"checked_at": now, "keyword": keyword, "country": args.country, "position": pos,
                     "url": hit["url"] if hit else "", "title": hit["title"] if hit else ""})
        print(f"{keyword[:36]:<36} {pos or '-':>4} {before or '-':>6}  {hit['url'] if hit else ''}")
        if before and (not pos or pos - int(before) >= args.alert):
            drops.append(f"{keyword}: {before} -> {pos or 'out of the top ' + str(params['limit'])}")

    new_file = not os.path.exists(args.history)
    with open(args.history, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)

    ranked = [r for r in rows if r["position"]]
    print(f"\n{len(ranked)} of {len(rows)} keywords in the top {params['limit']}"
          + (f", average position {sum(r['position'] for r in ranked) / len(ranked):.1f}" if ranked else ""))
    for d in drops:
        print(f"DROP {d}")
    print(f"appended to {args.history} ({credits} credits)")
    return rows


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
