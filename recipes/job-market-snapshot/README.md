# Job-market snapshot from Indeed and LinkedIn

One role in one place, across both boards: how many postings there are, who is hiring most, what the posted pay
ranges say, and how much of it is on-site, hybrid or remote. The postings themselves go into one CSV, with jobs
listed on both boards counted once.

**Who it's for:** recruiters sizing a search, job seekers checking pay before an offer, and analysts tracking hiring.

## How it works

1. [`/indeed/v1/search`](https://api.sh/docs/indeed-search?utm_source=github&utm_medium=readme) gives the first page of Indeed results (about 40
   postings) with salaries and Indeed's total count for the search.
2. [`/linkedin/v1/jobs`](https://api.sh/docs/linkedin-jobs?utm_source=github&utm_medium=readme) adds LinkedIn's postings, 10 per page
   (`--linkedin-pages`).
3. The same company and title on both boards is kept once (the Indeed copy, which has the salary).
4. Hourly pay is turned into a yearly figure (2,080 hours), the midpoint of each posted range is used for the median
   and the middle half, and the work mode is read from each posting's labels and location.

## Run it

```sh
pip install -r requirements.txt
export APISH_API_KEY="ash_live_..."

python snapshot.py "data engineer" "Austin, TX"
python snapshot.py "registered nurse" "Denver, CO" --days 7 --linkedin-pages 3 --out nurses.csv
```

## Cost

About 3 credits per snapshot (one Indeed search and one LinkedIn page), plus about 1 for each extra LinkedIn page,
at the time of writing. Live prices: [Indeed API](https://api.sh/indeed-api?utm_source=github&utm_medium=readme), [LinkedIn API](https://api.sh/linkedin-api?utm_source=github&utm_medium=readme).

## Sample output

From a live run on 11 Nov 2026. CSV (first rows): [`sample-output/jobs.csv`](sample-output/jobs.csv).

```
data engineer in Austin, TX
  Indeed lists 2,327 postings in all
  read 39 from Indeed and 10 from LinkedIn; 3 on both, 46 unique
  pay (midpoint of the posted range, 20 of 46 postings show one): median $177,400, middle half $141,551 to $228,000 a year
  on-site: 28 (61%), hybrid: 11 (24%), remote: 7 (15%)
  most postings:
      4  DataAnnotation
      4  CrowdStrike
      4  The HT Group
      3  Aristocrat
      2  Apple
      1  Expedia
      1  Apgar
      1  Fortis Construction, Inc.
wrote jobs.csv (3 credits)
```

Pay comes from postings that show a range (here 20 of 46), so read it as "what advertised ranges say", not as the
market as a whole.
