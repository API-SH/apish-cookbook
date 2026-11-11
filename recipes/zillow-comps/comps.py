"""Zillow comps: recently sold homes like a given one, nearest first, and a value estimate from them.

    python comps.py "149 NW 80th St, Seattle, WA 98117"
    python comps.py https://www.zillow.com/homedetails/149-NW-80th-St-Seattle-WA-98117/48748070_zpid/

Flow: find the home (address -> Zillow id), read its facts, search homes sold in the same ZIP code with
similar bedrooms and size, keep the closest ones, and price the subject from their median price per sq ft.
"""

import argparse
import csv
import math
import statistics
import sys
import time

from apish import Apish

FIELDS = ["address", "sold_price", "sold_date", "beds", "baths", "sqft", "price_per_sqft", "miles_away", "url"]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Recently sold comparables for a home on Zillow.")
    p.add_argument("home", help="street address, Zillow link or zpid")
    p.add_argument("--comps", type=int, default=10, help="how many comparables to keep (nearest first)")
    p.add_argument("--months", type=int, default=6, help="only homes sold in the last N months")
    p.add_argument("--size-range", type=float, default=0.3, help="living area within this share (0.3 = +-30%%)")
    p.add_argument("--out", default="comps.csv")
    return p.parse_args(argv)


def miles(lat1, lng1, lat2, lng2):
    """Great-circle distance in miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def find_home(apish, home):
    """A Zillow link or zpid is used as is; an address goes through Zillow's own autocomplete first."""
    if "zillow.com" in home or home.isdigit():
        return home, 0
    res = apish.zillow.autocomplete(q=home)
    match = next((r for r in res["results"] if r.get("zpid")), None)
    if not match:
        raise SystemExit(f"Zillow doesn't know the address {home!r}: try the home's Zillow link instead")
    return str(match["zpid"]), res.meta.credits_used


def money(x):
    return f"${x:,.0f}" if x else "-"


def main(argv=None, apish=None):
    args = parse_args(argv)
    apish = apish or Apish()  # reads APISH_API_KEY

    zpid, credits = find_home(apish, args.home)
    home = apish.zillow.property(url=zpid, options={"raw": False})
    credits += home.meta.credits_used
    beds, sqft = home.get("bedrooms"), home.get("livingArea")
    print(f"{home['streetAddress']}, {home['city']}, {home['state']} {home['zipcode']}")
    print(f"  {beds} bd, {home.get('bathrooms')} ba, {sqft or '?'} sq ft, built {home.get('yearBuilt') or '?'}, "
          f"{home.get('homeStatus', '').replace('_', ' ').lower()}"
          f"{', listed at ' + money(home.get('price')) if home.get('homeStatus') == 'FOR_SALE' else ''}, "
          f"Zestimate {money(home.get('zestimate'))}")
    if not sqft:
        raise SystemExit("Zillow has no living area for this home, so there's nothing to compare price per sq ft with")

    # Homes sold in the same ZIP code, one bedroom either way, similar size.
    filters = {"location": home["zipcode"], "status": "sold", "min_sqft": int(sqft * (1 - args.size_range)),
               "max_sqft": int(sqft * (1 + args.size_range))}
    if beds:
        filters.update(beds=max(beds - 1, 0), max_beds=beds + 1)
    if home.get("homeType") in ("SINGLE_FAMILY", "CONDO", "TOWNHOUSE"):
        filters["home_type"] = {"SINGLE_FAMILY": "house", "CONDO": "condo", "TOWNHOUSE": "townhouse"}[home["homeType"]]
    sold = apish.zillow.search(**filters, options={"raw": False})
    credits += sold.meta.credits_used

    since = (time.time() - args.months * 30.5 * 86400) * 1000
    comps = []
    for h in sold["homes"]:
        price, area = h.get("unformatted_price"), h.get("living_area") or h.get("area")
        if str(h.get("zpid")) == str(home["zpid"]) or not price or not area or (h.get("date_sold") or 0) < since:
            continue
        comps.append({
            "address": h["address"],
            "sold_price": price,
            "sold_date": time.strftime("%Y-%m-%d", time.gmtime(h["date_sold"] / 1000)),
            "beds": h.get("beds"),
            "baths": h.get("baths"),
            "sqft": area,
            "price_per_sqft": round(price / area),
            "miles_away": round(miles(home["latitude"], home["longitude"], h["latitude"], h["longitude"]), 2),
            "url": h["url"],
        })
    comps.sort(key=lambda c: c["miles_away"])
    comps = comps[:args.comps]
    if len(comps) < 3:
        raise SystemExit(f"only {len(comps)} comparable sales found: try --months 12 or --size-range 0.5")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(comps)

    print(f"\n{len(comps)} comparable sales in the last {args.months} months, nearest first:")
    for c in comps:
        print(f"  {c['address'][:42]:<42} {money(c['sold_price']):>11}  {c['sold_date']}  "
              f"{c['beds']} bd {c['sqft']:>5} sq ft  ${c['price_per_sqft']}/sq ft  {c['miles_away']} mi")

    ppsf = [c["price_per_sqft"] for c in comps]
    low, high = (statistics.quantiles(ppsf, n=4)[::2]) if len(ppsf) >= 4 else (min(ppsf), max(ppsf))
    print(f"\nmedian ${statistics.median(ppsf):,.0f}/sq ft -> estimated value {money(statistics.median(ppsf) * sqft)} "
          f"(middle half of comps: {money(low * sqft)} to {money(high * sqft)})")
    print(f"wrote {args.out} ({credits} credits)")
    return comps


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
