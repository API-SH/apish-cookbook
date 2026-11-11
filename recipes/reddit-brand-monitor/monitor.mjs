// Reddit brand-mention monitor: new posts and comments that mention your brand, without the ones
// you've already seen. Run it from cron every few hours; each run reports only what's new.
//
//   node monitor.mjs --brand "Notion"
//   node monitor.mjs --brand "Linear" --exclude "linear algebra,linear regression" --time day
//   node monitor.mjs --brand "figma" --ignore-case
//
// New mentions are printed, appended to mentions.csv, and POSTed as JSON to ALERT_WEBHOOK_URL if it is set.

import { readFile, writeFile, appendFile, access } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { parseArgs } from "node:util";
import { Apish } from "@api.sh/sdk";

const exists = (path) => access(path).then(() => true, () => false);
const csvCell = (v) => (v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * True if the text names the brand as a whole word, minus excluded phrases. Case counts by default, because
 * brand names are capitalised and many are also ordinary words: "Notion" matches, "the notion that" doesn't.
 */
export function mentions(text, brand, exclude = [], ignoreCase = false) {
  const body = text ?? "";
  if (exclude.some((phrase) => body.toLowerCase().includes(phrase.toLowerCase()))) return false;
  return new RegExp(`(^|[^\\p{L}\\p{N}])${escape(brand)}($|[^\\p{L}\\p{N}])`, ignoreCase ? "iu" : "u").test(body);
}

export async function run({ apish = new Apish(), brand, exclude = [], ignoreCase = false, time = "week", subreddit,
  state = "seen.json", out = "mentions.csv", log = console.log }) {
  const seen = new Set((await exists(state)) ? JSON.parse(await readFile(state, "utf8")) : []);
  const scope = subreddit ? { subreddit } : {};
  // engine=web: reddit.com's own search, with votes and comment counts.
  const [posts, comments] = await Promise.all([
    apish.reddit.search({ q: brand, sort: "new", time, engine: "web", ...scope }, { raw: false }),
    apish.reddit.searchComments({ q: brand, sort: "new", time, ...scope }, { raw: false }),
  ]);
  const credits = posts.$meta.creditsUsed + comments.$meta.creditsUsed;

  const found = [
    ...posts.posts.map((p) => ({ id: p.id, kind: "post", subreddit: p.subreddit, created: p.published,
      score: p.score, text: `${p.title}\n${p.text ?? ""}`, url: p.url })),
    ...comments.comments.map((c) => ({ id: c.id, kind: "comment", subreddit: c.subreddit?.name,
      created: c.created_at, score: c.score, text: c.body, url: c.url })),
  ];
  const fresh = found
    .filter((m) => !seen.has(m.id) && mentions(m.text, brand, exclude, ignoreCase))
    .sort((a, b) => String(b.created).localeCompare(String(a.created)));

  if (!(await exists(out))) await writeFile(out, "found_at,kind,subreddit,created,score,url,text\n");
  const now = new Date().toISOString();
  for (const m of fresh) {
    const snippet = m.text.replace(/\s+/g, " ").trim().slice(0, 280);
    await appendFile(out, [now, m.kind, m.subreddit, m.created, m.score, m.url, snippet].map(csvCell).join(",") + "\n");
    log(`${m.kind.padEnd(7)} r/${String(m.subreddit).padEnd(20)} ${String(m.created).slice(0, 16)}  ${snippet.slice(0, 90)}`);
  }
  for (const m of found) seen.add(m.id); // also remember non-matches, so they aren't checked again
  await writeFile(state, JSON.stringify([...seen].slice(-5000)) + "\n");
  log(`${fresh.length} new mention(s) of "${brand}" out of ${found.length} search results (${credits} credits)`);

  if (fresh.length && process.env.ALERT_WEBHOOK_URL) {
    const text = fresh.map((m) => `r/${m.subreddit}: ${m.text.replace(/\s+/g, " ").slice(0, 140)} ${m.url}`).join("\n");
    await fetch(process.env.ALERT_WEBHOOK_URL, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, mentions: fresh }) });
  }
  return { fresh, credits };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { values } = parseArgs({ options: {
    brand: { type: "string" },
    exclude: { type: "string", default: "" },
    "ignore-case": { type: "boolean", default: false },
    time: { type: "string", default: "week" },
    subreddit: { type: "string" },
    state: { type: "string", default: "seen.json" },
    out: { type: "string", default: "mentions.csv" },
  } });
  if (!values.brand) {
    console.error('usage: node monitor.mjs --brand "Your brand" [--exclude "phrase,phrase"] [--time hour|day|week|month]');
    process.exit(1);
  }
  const exclude = values.exclude.split(",").map((s) => s.trim()).filter(Boolean);
  run({ ...values, exclude, ignoreCase: values["ignore-case"] }).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
