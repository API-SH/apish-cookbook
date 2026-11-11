# n8n templates

Import a file in n8n (**Workflows → Import from file**), install the verified API.SH node when n8n asks, and follow
the setup note on the canvas. Each one reads from and writes to a Google Sheet.

- [`google-maps-lead-list.json`](google-maps-lead-list.json): a form takes a business type and location, and qualified Google Maps leads are upserted into a sheet.
- [`amazon-price-drop-alerts.json`](amazon-price-drop-alerts.json): every morning, checks the Amazon products in a sheet and emails price drops.
- [`google-rank-tracker.json`](google-rank-tracker.json): every Monday, logs your Google position for each keyword in a sheet and emails drops.
- [`tiktok-instagram-creator-vetting.json`](tiktok-instagram-creator-vetting.json): scores the TikTok and Instagram creators listed in a sheet and writes the results back.

More about the node: [api.sh/integrations/n8n](https://api.sh/integrations/n8n?utm_source=github&utm_medium=readme).
