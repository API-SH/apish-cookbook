"""Job-market snapshot: one role in one place, across Indeed and LinkedIn. Who is hiring, what they pay,
how much is remote, and the postings themselves in one CSV.

    python snapshot.py "data engineer" "Austin, TX"
    python snapshot.py "nurse practitioner" "Denver, CO" --days 7 --linkedin-pages 2

Indeed gives salaries and the total number of postings; LinkedIn adds employers that only post there.
The same job on both boards is counted once.
"""

import argparse
import csv
import re
import statistics
import sys
from collections import Counter

from apish import Apish

FIELDS = ["source", "title", "company", "location", "salary_min_yearly", "salary_max_yearly", "work_mode", "posted",
          "url"]
HOURS_PER_YEAR = 2080


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Snapshot of the job market for one role in one place.")
    p.add_argument("role")
    p.add_argument("location", help='city and state, e.g. "Austin, TX"')
    p.add_argument("--days", choices=["1", "3", "7", "14"], help="only jobs posted in the last N days")
    p.add_argument("--linkedin-pages", type=int, default=1, help="LinkedIn result pages to read (10 jobs each)")
    p.add_argument("--out", default="jobs.csv")
    return p.parse_args(argv)


def yearly(amount, period):
    if amount is None:
        return None
    return round(amount * HOURS_PER_YEAR) if period == "HOURLY" else round(amount) if period == "YEARLY" else None


def work_mode(*texts):
    """remote, hybrid or on-site, from the labels and location text a board shows."""
    text = " ".join(t for t in texts if t).lower()
    return "remote" if "remote" in text else "hybrid" if "hybrid" in text else "on-site"


def key(title, company):
    """Same company and same title (ignoring case, punctuation and level numerals) = same job."""
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()  # noqa: E731
    return norm(company), re.sub(r"\b(i{1,3}|iv|[1-5])$", "", norm(title)).strip()


def indeed_jobs(apish, args):
    params = {"q": args.role, "l": args.location}
    if args.days:
        params["date"] = args.days
    res = apish.indeed.search(**params, options={"raw": False})
    jobs = [{
        "source": "indeed",
        "title": j["title"],
        "company": j.get("company") or "",
        "location": j.get("location") or "",
        "salary_min_yearly": yearly(j.get("salary_min"), j.get("salary_type")),
        "salary_max_yearly": yearly(j.get("salary_max"), j.get("salary_type")),
        "work_mode": "remote" if j.get("remote") else work_mode(
            j.get("location"), *(a.get("label") for a in j.get("attributes") or [])),
        "posted": (j.get("pub_date") or "")[:10],
        "url": j["url"],
    } for j in res["jobs"]]
    return jobs, res.get("total_results"), res.meta.credits_used


def linkedin_jobs(apish, args):
    params = {"keywords": args.role, "location": args.location}
    if args.days:
        params["posted"] = "24h" if args.days == "1" else "week" if args.days in ("3", "7") else "month"
    jobs, credits, start = [], 0, 0
    for _ in range(args.linkedin_pages):
        res = apish.linkedin.jobs(**params, start=start, options={"raw": False})
        credits += res.meta.credits_used
        jobs += [{
            "source": "linkedin",
            "title": j["title"],
            "company": j.get("company") or "",
            "location": j.get("address") or "",
            "salary_min_yearly": None,
            "salary_max_yearly": None,
            "work_mode": work_mode(j.get("address"), j.get("title")),
            "posted": j.get("listed_at") or "",
            "url": j["job_url"],
        } for j in res["jobs"]]
        start = res.get("next_start")
        if not start:
            break
    return jobs, credits


def main(argv=None, apish=None):
    args = parse_args(argv)
    apish = apish or Apish()  # reads APISH_API_KEY

    indeed, indeed_total, c1 = indeed_jobs(apish, args)
    linkedin, c2 = linkedin_jobs(apish, args)
    seen, jobs = set(), []
    for j in indeed + linkedin:  # Indeed first: it has the salaries
        k = key(j["title"], j["company"])
        if k not in seen:
            seen.add(k)
            jobs.append(j)
    dupes = len(indeed) + len(linkedin) - len(jobs)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(jobs)

    print(f"{args.role} in {args.location}")
    if indeed_total:
        print(f"  Indeed lists {indeed_total:,} postings in all")
    print(f"  read {len(indeed)} from Indeed and {len(linkedin)} from LinkedIn; {dupes} on both, {len(jobs)} unique")

    pay = [(j["salary_min_yearly"] + j["salary_max_yearly"]) / 2 for j in jobs
           if j["salary_min_yearly"] and j["salary_max_yearly"]]
    if pay:
        qs = statistics.quantiles(pay, n=4) if len(pay) >= 4 else [min(pay), statistics.median(pay), max(pay)]
        print(f"  pay (midpoint of the posted range, {len(pay)} of {len(jobs)} postings show one): "
              f"median ${statistics.median(pay):,.0f}, middle half ${qs[0]:,.0f} to ${qs[-1]:,.0f} a year")
    if not jobs:
        print("  no postings found")
        return jobs
    modes = Counter(j["work_mode"] for j in jobs)
    print("  " + ", ".join(f"{m}: {modes[m]} ({modes[m] / len(jobs):.0%})" for m in ("on-site", "hybrid", "remote")))

    print("  most postings:")
    for company, n in Counter(j["company"] for j in jobs if j["company"]).most_common(8):
        print(f"    {n:>3}  {company}")
    print(f"wrote {args.out} ({c1 + c2} credits)")
    return jobs


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
