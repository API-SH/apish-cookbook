# Google rank tracker

Checks where your site ranks on Google for each of your keywords, compares with the last run, and warns you about
drops. Every run is appended to `rankings.csv`, which becomes your ranking history.

**Who it's for:** SEO freelancers, content teams and site owners who want rank tracking without a monthly SEO-suite seat.

## How it works

1. Reads keywords from arguments or `--keywords-file`.
2. Runs each through [`/google/v1/search`](https://api.sh/docs/google-search?utm_source=github&utm_medium=readme), three at a time, for the
   `--country` you choose (and a city with `--location`, e.g. `"Austin,Texas,United States"`, for local SEO).
3. Finds the first organic result on your domain or any of its subdomains (`docs.python.org` counts for
   `python.org`).
4. Prints today's position next to the last one, appends the run to `rankings.csv`, and reports a `DROP` for every
   keyword that fell by `--alert` places or more, or out of the checked results.

## Run it

```sh
pip install -r requirements.txt
export APISH_API_KEY="ash_live_..."

python rank.py --domain python.org --keywords-file keywords.txt
python rank.py --domain example.com "best crm for startups" "crm pricing" --depth 30 --country gb
```

Weekly: `0 7 * * 1 cd /path/to/google-rank-tracker && python rank.py --domain example.com --keywords-file keywords.txt`.

## Cost

About 3 credits per keyword for the top 10, and 3 more for each further 10 results (`--depth 30` is about 9 per
keyword), at the time of writing. Live prices are on the [Google API page](https://api.sh/google-api?utm_source=github&utm_medium=readme).

## Sample output

From a live run on 11 Nov 2026 with the included [`keywords.txt`](keywords.txt) (a first run, so there is no
"before" yet). CSV: [`sample-output/rankings.csv`](sample-output/rankings.csv).

```
keyword                               now before  url
python tutorial                         1      -  https://docs.python.org/3/tutorial/index.html
learn python                            -      -  

1 of 2 keywords in the top 10, average position 1.0
appended to rankings.csv (6 credits)
```

No code: the [n8n template](../../n8n/google-rank-tracker.json) keeps keywords and history in a Google Sheet and
emails the drops.
