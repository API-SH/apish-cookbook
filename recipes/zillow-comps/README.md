# Zillow comps for an address

Finds recently sold homes like a given one (same ZIP code, one bedroom either way, similar size), keeps the nearest,
and estimates the home's value from their median price per square foot, next to Zillow's own Zestimate and the list
price.

**Who it's for:** buyers sanity-checking an asking price, agents preparing a quick CMA, and investors screening deals.

## How it works

1. An address goes through [`/zillow/v1/autocomplete`](https://api.sh/docs/zillow-autocomplete?utm_source=github&utm_medium=readme) to find the home's
   Zillow id; a Zillow link or zpid is used as is.
2. [`/zillow/v1/property`](https://api.sh/docs/zillow-property?utm_source=github&utm_medium=readme) gives the facts: beds, baths, living area, year
   built, home type, status, price and Zestimate.
3. [`/zillow/v1/search`](https://api.sh/docs/zillow-search?utm_source=github&utm_medium=readme) with `status=sold` finds homes sold in the same ZIP code
   with similar bedrooms, size (`--size-range`) and the same home type.
4. Keeps sales from the last `--months`, sorts them by distance, keeps the nearest `--comps`, and prices the subject
   at their median price per square foot, with the middle half of the comps as a range.

## Run it

```sh
pip install -r requirements.txt
export APISH_API_KEY="ash_live_..."

python comps.py "149 NW 80th St, Seattle, WA 98117"
python comps.py https://www.zillow.com/homedetails/48748070_zpid/ --months 12 --comps 15
```

Sale prices are public in most US states but not all: in non-disclosure states such as Texas and Utah, Zillow
shows no sold price, so few or no comps come back.

## Cost

About 3 credits per address (autocomplete, property and one search page), 2 with a Zillow link, at the time of
writing. Live prices are on the [Zillow API page](https://api.sh/zillow-api?utm_source=github&utm_medium=readme).

## Sample output

From a live run on 11 Nov 2026 on a home listed for sale. CSV: [`sample-output/comps.csv`](sample-output/comps.csv).

```
149 NW 80th Street, Seattle, WA 98117
  2 bd, 1 ba, 1610 sq ft, built 1925, for sale, listed at $789,000, Zestimate $768,200

10 comparable sales in the last 6 months, nearest first:
  153 NW 78th St, Seattle, WA 98117             $799,999  2026-09-11  3 bd  1270 sq ft  $630/sq ft  0.1 mi
  323 NW 83rd Street, Seattle, WA 98117         $785,000  2026-09-30  2 bd  1310 sq ft  $599/sq ft  0.17 mi
  8311 3rd Avenue NW, Seattle, WA 98117         $580,000  2026-09-15  2 bd  1300 sq ft  $446/sq ft  0.2 mi
  310 NW 75th Street, Seattle, WA 98117         $910,000  2026-09-18  2 bd  1920 sq ft  $474/sq ft  0.23 mi
  343 NW 74th Street, Seattle, WA 98117         $730,000  2026-10-30  2 bd  1470 sq ft  $497/sq ft  0.32 mi
  8040 Dibble Avenue NW, Seattle, WA 98117    $1,090,000  2026-10-05  3 bd  1940 sq ft  $562/sq ft  0.33 mi
  347 NW 74th Street, Seattle, WA 98117       $1,195,000  2026-09-15  3 bd  1850 sq ft  $646/sq ft  0.33 mi
  7418 8th Avenue NW, Seattle, WA 98117         $908,775  2026-09-09  2 bd  1570 sq ft  $579/sq ft  0.36 mi
  8313 C 12th Avenue NW, Seattle, WA 98117      $899,000  2026-10-01  3 bd  1840 sq ft  $489/sq ft  0.56 mi
  8323 A 12th Avenue NW, Seattle, WA 98117      $825,000  2026-10-16  3 bd  1870 sq ft  $441/sq ft  0.58 mi

median $530/sq ft -> estimated value $852,495 (middle half of comps: $751,870 to $976,868)
wrote comps.csv (3 credits)
```

This is a quick price-per-square-foot check, not an appraisal: it doesn't adjust for condition, lot, views or
renovations.
