"""Google Maps lead list: local businesses with phones, emails and social profiles, written to a CSV.

    python lead_list.py --keyword "roofing contractors" --areas "Denver, CO|Aurora, CO|Lakewood, CO"

Flow: one bulk Maps search per batch of up to 20 areas, filter, then read each kept business's
website for emails and social profiles (20 businesses per call), then write the CSV best leads first.
"""

import argparse
import csv
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from apish import Apish

EMAIL = re.compile(r"[a-z0-9][a-z0-9._%+-]*@[a-z0-9.-]+\.[a-z]{2,}")
FIELDS = [
    "name", "phone", "email", "other_emails", "website", "city", "rating", "reviews",
    "facebook", "instagram", "linkedin", "website_answered", "maps_link",
]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Build a lead list from Google Maps.")
    p.add_argument("--keyword", default="roofing contractors", help="what to search for")
    p.add_argument("--areas", default="Denver, CO|Aurora, CO|Lakewood, CO|Littleton, CO|Arvada, CO|Westminster, CO",
                   help="towns or neighbourhoods, separated by |")
    p.add_argument("--min-rating", type=float, default=4.5)
    p.add_argument("--min-reviews", type=int, default=20)
    p.add_argument("--max-leads", type=int, default=0, help="enrich at most this many businesses (0 = all)")
    p.add_argument("--out", default="leads.csv")
    return p.parse_args(argv)


def chunks(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


def search_areas(apish, keyword, areas):
    """Every area searched once. A query that failed is retried once, live."""
    found, credits = {}, 0
    for batch in chunks(areas, 20):
        queries = [f"{keyword} in {area}" for area in batch]
        res = apish.google_maps.bulk_search(queries="|".join(queries), business_status="OPEN")
        credits += res.meta.credits_used
        results = res["results"]
        failed = [r["query"] for r in results if r.get("error")]
        if failed:
            retry = apish.google_maps.bulk_search(queries="|".join(failed), business_status="OPEN",
                                                  options={"fresh": True})
            credits += retry.meta.credits_used
            again = {r["query"]: r for r in retry["results"]}
            results = [again.get(r["query"], r) for r in results]
        for r in results:
            places = r.get("places") or []
            note = f"  ({r['error']})" if r.get("error") else ""
            print(f"{r['query']:<45} {len(places)} places{note}")
            for place in places:
                found.setdefault(place["business_id"], place)  # one business often ranks in two areas
    return found, credits


def fetch_contacts(apish, leads):
    """Emails and social profiles, 20 businesses per call, three calls at a time."""
    def one(batch):
        return apish.google_maps.contacts(business_id=",".join(p["business_id"] for p in batch))

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(one, chunks(leads, 20)))
    by_id = {b["business_id"]: b.get("emails_and_contacts") or {} for r in results for b in r["businesses"]}
    return by_id, sum(r.meta.credits_used for r in results)


def domain(url):
    host = urlparse(url or "").hostname or ""
    return host[4:] if host.startswith("www.") else host


def best_email(emails, site):
    """The business's own-domain email first, then anything else that looks like an email."""
    clean = sorted({e.lower() for e in emails if EMAIL.fullmatch(e.lower())})
    own = [e for e in clean if domain(site) and e.split("@")[1].endswith(domain(site))]
    return (own or clean or [""])[0], clean


def to_row(place, contacts):
    email, all_emails = best_email(contacts.get("emails") or [], place.get("website"))
    return {
        "name": place["name"],
        "phone": place.get("phone_number") or "",
        "email": email,
        "other_emails": " ".join(e for e in all_emails if e != email),
        "website": (place.get("website") or "").split("?")[0],  # without tracking parameters
        "city": place.get("city") or "",
        "rating": place.get("rating"),
        "reviews": place.get("review_count"),
        "facebook": contacts.get("facebook") or "",
        "instagram": contacts.get("instagram") or "",
        "linkedin": contacts.get("linkedin") or "",
        "website_answered": bool(contacts.get("pages_checked")),
        "maps_link": place.get("place_link") or "",
    }


def main(argv=None, apish=None):
    args = parse_args(argv)
    apish = apish or Apish()  # reads APISH_API_KEY
    areas = [a.strip() for a in args.areas.split("|") if a.strip()]

    found, search_credits = search_areas(apish, args.keyword, areas)
    print(f"{len(found)} unique businesses ({search_credits} credits)")

    # Filter before paying to read websites.
    leads = [
        p for p in found.values()
        if p.get("website") and (p.get("rating") or 0) >= args.min_rating
        and (p.get("review_count") or 0) >= args.min_reviews
    ]
    leads.sort(key=lambda p: -(p.get("review_count") or 0))
    if args.max_leads:
        leads = leads[:args.max_leads]
    print(f"{len(leads)} pass the filters")
    if not leads:
        return []

    by_id, contact_credits = fetch_contacts(apish, leads)
    print(f"contacts for {len(by_id)} businesses ({contact_credits} credits)")

    rows = [to_row(p, by_id.get(p["business_id"]) or {}) for p in leads]
    rows.sort(key=lambda r: (r["email"] == "", -(r["reviews"] or 0)))  # an email first, then most reviews
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{sum(1 for r in rows if r['email'])} leads with an email, "
          f"{sum(1 for r in rows if r['phone'])} with a phone, "
          f"no answer from {sum(1 for r in rows if not r['website_answered'])} of their websites")
    print(f"wrote {args.out} ({search_credits + contact_credits} credits in total)")
    return rows


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
