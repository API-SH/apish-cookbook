# Reddit brand-mention monitor

Finds new Reddit posts and comments that mention your brand, drops the ones you've already seen and the ones that
only use your brand name as an ordinary word, and reports what's left. Run it every few hours from cron.

**Who it's for:** founders, community and support teams, and marketers who want to answer threads while they're fresh.

## How it works

1. Two searches, newest first: [`/reddit/v1/search`](https://api.sh/docs/reddit-search?utm_source=github&utm_medium=readme) for posts (with
   `engine=web`, Reddit's own search, with votes and comment counts) and
   [`/reddit/v1/search/comments`](https://api.sh/docs/reddit-search-comments?utm_source=github&utm_medium=readme) for comments.
2. Keeps only text that names the brand **as a whole word, with its capitals**: "Notion" matches, "the notion that"
   and "Notional" don't. Use `--ignore-case` for brands written in lower case, and `--exclude` for phrases that
   aren't you (`--brand Linear --exclude "linear algebra,linear regression"`). Posts are matched on their title and
   any text the search returns.
3. Remembers every result id in `seen.json`, so each run reports only what's new.
4. Prints the new mentions, appends them to `mentions.csv` and, if `ALERT_WEBHOOK_URL` is set, POSTs them as JSON
   (`{"text": ..., "mentions": [...]}`) to Slack, Discord, Zapier, n8n or any webhook.

## Run it

```sh
npm install
export APISH_API_KEY="ash_live_..."

node monitor.mjs --brand "Notion"
node monitor.mjs --brand "Notion" --subreddit productivity --time week
```

`--time` is `hour`, `day`, `week` (default) or `month`. Every 2 hours: `0 */2 * * * cd /path/to/reddit-brand-monitor && node monitor.mjs --brand "Notion" --time day`.

## Cost

About 2 credits per run (one post search and one comment search), at the time of writing. Live prices are on the
[Reddit API page](https://api.sh/reddit-api?utm_source=github&utm_medium=readme).

## Sample output

Shape of the output from a run on 11 Nov 2026 (Reddit's search returned 17 results for "notion" in the last day).
The post texts and links below are examples, to keep other people's posts out of this repo; the CSV is in
[`sample-output/mentions.csv`](sample-output/mentions.csv).

```
comment r/productivity          2026-11-11T00:40  We moved our meeting notes into Notion last month and the team actually reads them now.
comment r/Notion                2026-11-11T00:39  Is there a way to make a Notion database view that only shows this week's tasks?
post    r/startups              2026-11-11T00:36  What do you use for internal docs: Notion, Confluence or plain Markdown?
3 new mention(s) of "Notion" out of 17 search results (2 credits)
```

A whole-word, case-sensitive match keeps out most uses of the ordinary word ("a vague notion"), but a sentence that
starts with the word still matches, which is why the CSV keeps a link to every mention.
