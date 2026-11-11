# Amazon price-drop tracker

Checks a list of Amazon products, remembers the last price of each, and tells you when one drops, falls to your
target price or comes back in stock. Every check is also appended to a CSV, so you build a price history as you go.

**Who it's for:** shoppers waiting for a deal, resellers and e-commerce teams watching competitors' prices.

## How it works

1. Reads `watchlist.json`: ASINs or product links, each with an optional `target` price, `domain`
   (`co.uk`, `de`, `in`, ...) and `zip` (prices and stock for that delivery location).
2. Fetches each product with [`/amazon/v1/product`](https://api.sh/docs/amazon-product?utm_source=github&utm_medium=readme), four at a time, with
   `fresh` so the price is live rather than from the 24-hour cache.
3. Compares with `prices.json` from the last run and reports drops of at least `--drop` percent, products at or below
   their target, and products back in stock. A product that couldn't be checked is skipped and tried again next run.
4. Saves the new prices to `prices.json` and appends every reading to `price-history.csv`. With
   `ALERT_WEBHOOK_URL` set, alerts are also POSTed as JSON (`{"text": ..., "alerts": [...]}`), which Slack, Discord,
   Zapier and n8n incoming webhooks accept.

## Run it

```sh
npm install
export APISH_API_KEY="ash_live_..."

node track.mjs                 # first run: records prices
node track.mjs --drop 5        # later runs: report drops of 5% or more
```

Run it daily with cron (`0 8 * * * cd /path/to/amazon-price-tracker && node track.mjs`).

## Cost

About 3 credits per product checked, at the time of writing: the three products in the sample watchlist cost 9
credits a run. Live prices are on the [Amazon API page](https://api.sh/amazon-api?utm_source=github&utm_medium=readme). Failed calls are free.

## Sample output

From a live run on 11 Nov 2026 with the included [`watchlist.json`](watchlist.json) (the first run, so there is
nothing to compare with yet). Files: [`sample-output/`](sample-output/).

```
B0BDHWDR12     246.56 $    Apple AirPods Pro (2nd Gen) Wireless Earbuds, Up to 2X Mo...
B09B8V1LZ3      79.99 $    Amazon Echo Dot - Vibrant sounding speaker, Designed for ...
B0CX23V2ZK          -      Apple 2024 MacBook Air 13-inch Laptop with M3 chip: Built...

no price drops since the last run
(9 credits)
```

A product with no price (`-`) is out of stock; when it returns you get a "back in stock" alert.

No code: the [n8n template](../../n8n/amazon-price-drop-alerts.json) keeps the watchlist in a Google Sheet and emails
the alerts.
