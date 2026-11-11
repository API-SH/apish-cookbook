// Amazon price-drop tracker: checks a watchlist of products, remembers the last price of each,
// and reports drops (and products that came back in stock). Run it once a day from cron.
//
//   node track.mjs                        # uses watchlist.json, keeps state in prices.json
//   node track.mjs --watchlist my.json --drop 5
//
// watchlist.json: [{ "asin": "B0D1XD1ZV3", "target": 199 }, { "asin": "https://www.amazon.co.uk/dp/...", "domain": "co.uk" }]
// Set ALERT_WEBHOOK_URL to also POST the alerts as JSON (Slack, Discord, Zapier, n8n and most chat tools take one).

import { readFile, writeFile, appendFile, access } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { parseArgs } from "node:util";
import { Apish } from "@api.sh/sdk";

const exists = (path) => access(path).then(() => true, () => false);
const readJson = async (path, fallback) => ((await exists(path)) ? JSON.parse(await readFile(path, "utf8")) : fallback);

/** Compares one fresh product reading with the last one and says what changed. */
export function compare(item, product, last, dropPercent) {
  const price = product.price_value ?? null;
  const inStock = price !== null;
  const alerts = [];
  if (last?.price != null && price != null && price < last.price) {
    const pct = ((last.price - price) / last.price) * 100;
    if (pct >= dropPercent) alerts.push(`down ${pct.toFixed(1)}% from ${last.price} to ${price}`);
  }
  if (last && last.price == null && inStock) alerts.push(`back in stock at ${price}`);
  if (item.target != null && price != null && price <= item.target && !(last?.price <= item.target)) {
    alerts.push(`at or below your target of ${item.target}`);
  }
  return { price, inStock, alerts };
}

export async function run({ apish = new Apish(), watchlist = "watchlist.json", state = "prices.json",
  history = "price-history.csv", drop = 0, log = console.log } = {}) {
  const items = await readJson(watchlist, null);
  if (!Array.isArray(items) || !items.length) throw new Error(`${watchlist}: expected a JSON list of products`);
  const last = await readJson(state, {});
  const now = new Date().toISOString();
  const alerts = [];
  let credits = 0;

  // A few products at a time: there are no rate limits, but there is no need to hurry either.
  const results = [];
  for (let i = 0; i < items.length; i += 4) {
    const batch = items.slice(i, i + 4);
    results.push(...(await Promise.all(batch.map(async (item) => {
      try {
        const product = await apish.amazon.product({ url: item.asin, ...(item.domain && { domain: item.domain }),
          ...(item.zip && { zip: item.zip }) }, { raw: false, fresh: true });
        return { item, product };
      } catch (error) {
        return { item, error };
      }
    }))));
  }

  if (!(await exists(history))) await writeFile(history, "checked_at,asin,price,currency,availability\n");
  for (const { item, product, error } of results) {
    if (error) {
      log(`${item.asin}: not checked (${error.message}); failed calls are not charged`);
      continue;
    }
    credits += product.$meta.creditsUsed;
    const key = product.asin;
    const { price, alerts: found } = compare(item, product, last[key], drop);
    const currency = (product.price ?? "").replace(/[\d.,\s]/g, ""); // "$246.11" -> "$"
    const title = product.title.length > 60 ? `${product.title.slice(0, 57)}...` : product.title;
    log(`${key}  ${String(price ?? "-").padStart(9)} ${currency.padEnd(3)}  ${title}`);
    for (const text of found) alerts.push({ asin: key, title: product.title, url: product.url, price, text });
    last[key] = { price, title: product.title, checked_at: now };
    const availability = JSON.stringify(product.availability ?? "");
    await appendFile(history, `${now},${key},${price ?? ""},${currency},${availability}\n`);
  }

  await writeFile(state, JSON.stringify(last, null, 2) + "\n");
  log(alerts.length ? `\n${alerts.length} alert(s):` : "\nno price drops since the last run");
  for (const a of alerts) log(`- ${a.title.slice(0, 60)}: ${a.text}\n  ${a.url}`);
  log(`(${credits} credits)`);

  if (alerts.length && process.env.ALERT_WEBHOOK_URL) {
    const text = alerts.map((a) => `${a.title.slice(0, 80)}: ${a.text} ${a.url}`).join("\n");
    await fetch(process.env.ALERT_WEBHOOK_URL, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, alerts }) });
  }
  return { alerts, credits };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { values } = parseArgs({ options: {
    watchlist: { type: "string", default: "watchlist.json" },
    state: { type: "string", default: "prices.json" },
    history: { type: "string", default: "price-history.csv" },
    drop: { type: "string", default: "0" },
  } });
  run({ ...values, drop: Number(values.drop) }).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
