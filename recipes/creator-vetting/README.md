# TikTok and Instagram creator vetting

Scores a list of creators on what their recent posts actually do, not on follower count: median views, likes and
comments, engagement rate, posting frequency and days since the last post, with flags for the usual warning signs.
Writes one CSV row per creator, best fit first.

**Who it's for:** brands and agencies shortlisting influencers, and creators benchmarking themselves.

## How it works

1. Reads `creators.txt` (or arguments): `tiktok:handle`, `instagram:handle` or a profile link per line.
2. TikTok: [`/tiktok/v1/profile`](https://api.sh/docs/tiktok-profile?utm_source=github&utm_medium=readme) for the exact follower count and
   [`/tiktok/v1/channel`](https://api.sh/docs/tiktok-channel?utm_source=github&utm_medium=readme) for the latest videos with views, likes, comments and
   shares. Instagram: [`/instagram/v1/user`](https://api.sh/docs/instagram-user?utm_source=github&utm_medium=readme), which includes the recent posts.
3. Leaves out pinned posts (they stay at the top whatever their age) and uses medians, so one viral post doesn't
   make an account look better than it is.
4. Computes:
   - `engagement_rate_pct`: median likes + comments + shares per post, as a % of followers.
   - `engagement_by_views_pct` (TikTok): the same, as a % of median views.
   - `views_per_follower` (TikTok): how much of the audience a typical video reaches.
   - `posts_per_week`, `days_since_last_post`.
5. Flags `low engagement` (below 0.5% of followers), `inactive 30+ days`, `views far below followers` and
   `no comments`. The thresholds are constants at the top of `vet.mjs`: big accounts have lower rates, so tune them
   to the creator size you hire.

## Run it

```sh
npm install
export APISH_API_KEY="ash_live_..."

node vet.mjs                                     # reads creators.txt
node vet.mjs tiktok:duolingo https://www.instagram.com/natgeo/ --out shortlist.csv
```

## Cost

About 2 credits per TikTok creator and 1 per Instagram creator, at the time of writing (the sample's three creators
used 5). Live prices: [TikTok API](https://api.sh/tiktok-api?utm_source=github&utm_medium=readme), [Instagram API](https://api.sh/instagram-api?utm_source=github&utm_medium=readme).

## Sample output

From a live run on 11 Nov 2026 with the included [`creators.txt`](creators.txt). The CSV is in
[`sample-output/creators-report.csv`](sample-output/creators-report.csv).

```
tiktok:nasa                2171681 followers    0.8% engagement  2.8 posts/week
tiktok:duolingo           18480246 followers   0.49% engagement  6.3 posts/week  [low engagement]
instagram:duolingo         5399126 followers   0.29% engagement  8.7 posts/week  [low engagement]
wrote creators-report.csv (3 creators, 5 credits)
```

Large brand accounts sit near the low-engagement line; for them, `engagement_by_views_pct` (12% for Duolingo's
TikTok) says more.

No code: the [n8n template](../../n8n/tiktok-instagram-creator-vetting.json) reads handles from a Google Sheet and
writes the scores back.
