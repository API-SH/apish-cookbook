# Google Maps lead list with emails and phones

Builds a CSV of local businesses for outreach: one row per business with its phone, the best email from its own
website, its Facebook, Instagram and LinkedIn pages, its rating and review count, and a link back to the Maps listing.
Change two arguments and it works for any trade in any town.

**Who it's for:** agencies, B2B sales teams and freelancers who sell to local businesses (roofers, dentists, gyms, cafes).

## How it works

1. **Search several towns in one call.** [`/google-maps/v1/bulk-search`](https://api.sh/docs/google-maps-bulk-search?utm_source=github&utm_medium=readme)
   takes up to 20 searches and returns up to 20 businesses for each. Searching each town around a city covers the
   whole metro area and finds businesses one big search never reaches. Duplicates (the same roofer ranking in two
   towns) are removed by Google's own `business_id`. A town whose search fails is retried once.
2. **Filter before you pay to enrich.** Only businesses with a website, a rating of at least `--min-rating` and at
   least `--min-reviews` reviews go on.
3. **Read each website.** [`/google-maps/v1/contacts`](https://api.sh/docs/google-maps-contacts?utm_source=github&utm_medium=readme) reads the home
   page and the contact page of up to 20 businesses per call and returns emails, phone numbers and social profiles.
   Three calls run at a time.
4. **Pick the right email.** Emails on the business's own domain come first; anything else found (a web agency's
   address in the footer, say) goes into `other_emails` for you to check.
5. **Write the CSV**, best leads first: those with an email, then the most reviewed.

## Run it

```sh
pip install -r requirements.txt
export APISH_API_KEY="ash_live_..."

python lead_list.py --keyword "roofing contractors" --areas "Denver, CO|Aurora, CO|Lakewood, CO"
python lead_list.py --keyword "dentists" --areas "Austin, TX" --min-rating 4.7 --max-leads 30 --out dentists.csv
```

| Option | Default | |
| --- | --- | --- |
| `--keyword` | roofing contractors | what to search for |
| `--areas` | six towns around Denver | towns or neighbourhoods, separated by `\|` |
| `--min-rating`, `--min-reviews` | 4.5, 20 | the filter in step 2 |
| `--max-leads` | 0 (all) | enrich at most this many businesses, most reviewed first |
| `--out` | leads.csv | |

## Cost

About 1 credit per town searched plus about 1 credit per business enriched, at the time of writing. The sample
below (2 towns, 10 businesses) used 12 credits. Live prices are on the
[Google Maps API page](https://api.sh/google-maps-api?utm_source=github&utm_medium=readme). Failed calls are free.

## Sample output

[`sample-output/console.txt`](sample-output/console.txt) and the first rows of
[`sample-output/leads.csv`](sample-output/leads.csv), from a live run on 11 Nov 2026
(`--areas "Denver, CO|Aurora, CO" --max-leads 10`). Emails and profiles that name a person were replaced with
placeholders.

```
roofing contractors in Denver, CO             20 places
roofing contractors in Aurora, CO             20 places
38 unique businesses (2 credits)
10 pass the filters
contacts for 10 businesses (10 credits)
3 leads with an email, 10 with a phone, no answer from 0 of their websites
```

Your numbers will differ: Maps reorders results all the time.

## Going further

- Bigger areas: [`/google-maps/v1/search`](https://api.sh/docs/google-maps-search?utm_source=github&utm_medium=readme)
  takes `lat`, `lng` and `radius` (or a `bbox`) and returns up to 200 businesses per call with `limit`.
- Only some categories: pass `subtypes` (for example `Roofing contractor`) so the gutter cleaner ranking next to
  the roofers is left out. `verified=false` keeps only businesses that haven't claimed their listing.
- One call instead of two: `extract_emails_and_contacts=True` on a search reads every website in the results,
  but you then pay to enrich the businesses you would have filtered out.
- No code: the [n8n template](../../n8n/google-maps-lead-list.json) does the same into a Google Sheet.

## Before you send anything

The data comes from public listings and public websites, but what you do with it is regulated. Commercial email in
the US must follow CAN-SPAM (honest headers, a working opt-out, your postal address). In the EU and the UK, the GDPR
and the electronic marketing rules apply to emails sent to identifiable people (`firstname@company.com` is personal
data). Keep your list to businesses, keep the `maps_link` as the source of each lead, and remove anyone who asks.
