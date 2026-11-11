# Trustpilot review export to CSV and Google Sheets

Exports a company's Trustpilot reviews, newest first, with rating, title, text, date, reviewer country,
verification and the company's reply, into a CSV and, if you like, into a Google Sheet that a weekly run keeps
up to date without duplicates.

**Who it's for:** customer-experience and product teams, agencies reporting on reputation, and anyone comparing
competitors' reviews.

## How it works

1. [`/trustpilot/v1/company`](https://api.sh/docs/trustpilot-company?utm_source=github&utm_medium=readme) gives the TrustScore, star distribution and
   the first 20 reviews in one call.
2. [`/trustpilot/v1/reviews`](https://api.sh/docs/trustpilot-reviews?utm_source=github&utm_medium=readme) reads further pages, up to `--pages`, and
   stops early once reviews are older than `--since`, so a weekly run only pays for new pages.
3. Writes `<domain>-reviews.csv`.
4. With `--sheet`, appends to a worksheet named after the domain (created if missing), skipping review ids already
   in it.

## Run it

```sh
pip install -r requirements.txt
export APISH_API_KEY="ash_live_..."

python export_reviews.py notion.so --pages 3
python export_reviews.py notion.so --since 2026-10-01 --sheet "https://docs.google.com/spreadsheets/d/<id>/edit"
```

### Google Sheets setup (only for `--sheet`)

1. In Google Cloud, create a service account, enable the Google Sheets and Google Drive APIs, and download its
   JSON key.
2. Share your sheet with the service account's email (as an editor).
3. `export GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/key.json`

Writing to the sheet uses [gspread](https://docs.gspread.org/); the CSV needs nothing beyond the SDK.

## Cost

About 1 credit per page of 20 reviews, at the time of writing. Live prices are on the
[Trustpilot API page](https://api.sh/trustpilot-api?utm_source=github&utm_medium=readme).

## Sample output

From a live run on 11 Nov 2026 (`--pages 2`). The CSV
([`sample-output/notion.so-reviews.csv`](sample-output/notion.so-reviews.csv)) is trimmed to 8 reviews, with
reviewer names and review links replaced by placeholders.

```
Notion (notion.so): TrustScore 2.2, 444 reviews, 104 in the last 12 months
  stars: 5: 142  4: 47  3: 24  2: 36  1: 195
exported 40 reviews (2026-04-29 to 2026-11-09), average 2.1 stars, 0 with a company reply
wrote notion.so-reviews.csv (2 credits)
```
