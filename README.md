# API.SH Cookbook

Runnable recipes for real jobs: lead lists, price tracking, real-estate comps, creator vetting, rank tracking,
brand monitoring, job-market research and review exports. Each recipe is a short script you can read in a few
minutes, run as is, and change to fit your own work.

API.SH turns public web pages from around 1,000 websites into clean JSON: search engines, social media,
e-commerce, real estate, jobs, travel, news and sports (Google, Amazon, TikTok, Zillow, LinkedIn and more).
These recipes use the official SDKs, [`apish-sdk`](https://pypi.org/project/apish-sdk/) for Python and
[`@api.sh/sdk`](https://www.npmjs.com/package/@api.sh/sdk) for Node.

## Recipes

| Recipe | What you get | Data from | Language | About |
| --- | --- | --- | --- | --- |
| [Google Maps lead list](recipes/google-maps-lead-list/) | Local businesses with phones, emails and social profiles, as a CSV | Google Maps, business websites | Python | 1 credit per town + 1 per business |
| [Amazon price-drop tracker](recipes/amazon-price-tracker/) | Alerts when a product drops, hits your target or is back in stock; price history | Amazon | Node | 3 credits per product per check |
| [Zillow comps](recipes/zillow-comps/) | Recently sold comparables for an address and a value estimate | Zillow | Python | 3 credits per address |
| [Creator vetting](recipes/creator-vetting/) | Real engagement, reach and posting rhythm for a creator shortlist | TikTok, Instagram | Node | 1-2 credits per creator |
| [Google rank tracker](recipes/google-rank-tracker/) | Your position per keyword, history and drop alerts | Google | Python | 3 credits per keyword (top 10) |
| [Reddit brand monitor](recipes/reddit-brand-monitor/) | New posts and comments that mention your brand | Reddit | Node | 2 credits per run |
| [Job-market snapshot](recipes/job-market-snapshot/) | Who is hiring, posted pay and remote share for a role and place | Indeed, LinkedIn | Python | 3 credits per snapshot |
| [Review export](recipes/review-export/) | A company's reviews in a CSV or a Google Sheet | Trustpilot | Python | 1 credit per 20 reviews |

Credit figures are approximate and were read from the live price list when the recipes were written; prices can
change. The current price of every endpoint is in the free catalog (`GET https://api.api.sh/catalog`) and on each
platform's page, for example the [Google Maps API](https://api.sh/google-maps-api?utm_source=github&utm_medium=readme). Every recipe was run against
the live API and ships with the trimmed output of that run in its `sample-output/` folder.

## Setup

1. Create a free account at [app.api.sh/signup](https://app.api.sh/signup?utm_source=github&utm_medium=readme). Every account gets free monthly
   credits, enough to try every recipe here.
2. Copy your API key and put it in the environment:

   ```sh
   export APISH_API_KEY="ash_live_..."
   ```

3. Python recipes (3.9+): `pip install -r requirements.txt` in the recipe's folder.
   Node recipes (18+): `npm install` in the recipe's folder.
4. Run the command at the top of the recipe's README.

Good to know:

- Every endpoint is a `GET` to `https://api.api.sh` with your key in the `x-api-key` header, returning JSON.
  Add `output=csv` or `output=ndjson` to get a file instead.
- Failed calls are free, and there are no rate limits: the recipes run a few calls in parallel to finish sooner.
- Responses are cached for 24 hours; pass `fresh` (as the price tracker does) when you need a live reading.

## No code: n8n templates

[`n8n/`](n8n/) has ready-made [n8n](https://n8n.io) workflows for four of these recipes (lead list, price alerts,
rank tracking and creator vetting) that read from and write to Google Sheets.

## Tests

The recipes are checked without network access or a key: every API call is answered from `tests/fixtures`.

```sh
pip install -r requirements-dev.txt && ruff check . && pytest
npm install && npm run lint && npm test
```

## Links

- Docs: [api.sh/docs](https://api.sh/docs?utm_source=github&utm_medium=readme) · SDKs: [api.sh/docs/sdks](https://api.sh/docs/sdks?utm_source=github&utm_medium=readme)
- MCP server for Claude Desktop, Cursor, ChatGPT and other AI clients: [api.sh/mcp](https://api.sh/mcp?utm_source=github&utm_medium=readme)
- Status: [status.api.sh](https://status.api.sh)

Have an idea for a recipe, or found one that broke? Open an issue.

## License

MIT, see [LICENSE](LICENSE).
