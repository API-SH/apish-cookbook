// Dry runs of the Node recipes: every API call is answered from tests/fixtures, nothing goes online.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Apish } from "@api.sh/sdk";

import { run as track, compare } from "../recipes/amazon-price-tracker/track.mjs";
import { run as vet, parseCreator, dropPinned, score } from "../recipes/creator-vetting/vet.mjs";
import { run as monitor, mentions } from "../recipes/reddit-brand-monitor/monitor.mjs";

const fixtures = new URL("./fixtures/", import.meta.url);

/** An Apish client whose fetch answers /<platform>/v1/<endpoint> from tests/fixtures/<platform>-<endpoint>.json. */
function fakeApi(overrides = {}) {
  const calls = [];
  const fetch = async (input) => {
    const url = new URL(String(input));
    calls.push({ route: url.pathname, params: Object.fromEntries(url.searchParams) });
    const body = overrides[url.pathname]
      ? overrides[url.pathname](Object.fromEntries(url.searchParams))
      : JSON.parse(await readFile(new URL(`${url.pathname.slice(1).replace("/v1/", "-").replaceAll("/", "-")}.json`, fixtures)));
    return new Response(JSON.stringify(body), {
      status: 200, headers: { "content-type": "application/json", "x-credits-used": "1", "x-request-id": "test" },
    });
  };
  return { apish: new Apish({ apiKey: "test-key", fetch, maxRetries: 0 }), calls };
}

const tmp = () => mkdtemp(join(tmpdir(), "cookbook-"));
const quiet = () => {};

test("amazon tracker: first run records prices, second run reports the drop", async () => {
  const dir = await tmp();
  const watchlist = join(dir, "watchlist.json");
  await writeFile(watchlist, JSON.stringify([{ asin: "B0BDHWDR12", target: 199 }]));
  const files = { watchlist, state: join(dir, "prices.json"), history: join(dir, "history.csv"), log: quiet };
  await writeFile(files.state, JSON.stringify({ B0BDHWDR12: { price: 229.99 } }));
  const { apish, calls } = fakeApi();
  const { alerts, credits } = await track({ apish, ...files });
  assert.equal(calls[0].route, "/amazon/v1/product");
  assert.equal(calls[0].params.url, "B0BDHWDR12");
  assert.equal(credits, 1);
  assert.deepEqual(alerts.map((a) => a.text), ["down 17.4% from 229.99 to 189.99", "at or below your target of 199"]);
  const state = JSON.parse(await readFile(files.state, "utf8"));
  assert.equal(state.B0BDHWDR12.price, 189.99);
  assert.equal((await readFile(files.history, "utf8")).trim().split("\n").length, 2);
});

test("amazon tracker: compare", () => {
  assert.deepEqual(compare({}, { price_value: 10 }, { price: null }, 0).alerts, ["back in stock at 10"]);
  assert.deepEqual(compare({}, { price_value: 9.9 }, { price: 10 }, 5).alerts, []);
  assert.deepEqual(compare({}, { price_value: null }, { price: 10 }, 0).inStock, false);
});

test("creator vetting: TikTok and Instagram rows with engagement", async () => {
  const dir = await tmp();
  const { apish, calls } = fakeApi();
  const rows = await vet({ apish, creators: [parseCreator("tiktok:nasa"), parseCreator("https://www.instagram.com/nasa/")],
    out: join(dir, "report.csv"), log: quiet });
  assert.deepEqual(calls.map((c) => c.route).sort(), ["/instagram/v1/user", "/tiktok/v1/channel", "/tiktok/v1/profile"]);
  const tiktok = rows.find((r) => r.platform === "tiktok");
  assert.equal(tiktok.posts_sampled, 8);
  assert.ok(tiktok.median_views > 0 && tiktok.engagement_rate_pct > 0, "stats arrive as strings and are counted");
  const csv = (await readFile(join(dir, "report.csv"), "utf8")).trim().split("\n");
  assert.equal(csv.length, 3);
});

test("creator vetting: handles, pinned posts and flags", () => {
  assert.deepEqual(parseCreator("https://www.tiktok.com/@Some.User?lang=en"), { platform: "tiktok", handle: "some.user" });
  assert.deepEqual(parseCreator("instagram:@natgeo"), { platform: "instagram", handle: "natgeo" });
  assert.equal(parseCreator("# comment"), null);
  assert.throws(() => parseCreator("youtube:x"));
  const day = 86_400_000;
  const posts = [{ at: 0 }, { at: 10 * day }, { at: 9 * day }, { at: 8 * day }, { at: 7 * day }];
  assert.equal(dropPinned(posts).length, 4);
  const s = score({ followers: 1000, posts: [{ at: 0, likes: 1, comments: 0 }], now: 40 * day });
  assert.match(s.flags, /inactive/);
  assert.match(s.flags, /low engagement/);
});

test("reddit monitor: reports only new, real mentions", async () => {
  const dir = await tmp();
  const files = { state: join(dir, "seen.json"), out: join(dir, "mentions.csv"), log: quiet };
  const { apish, calls } = fakeApi();
  const first = await monitor({ apish, brand: "Notion", ...files });
  assert.equal(calls[0].params.engine, "web");
  assert.deepEqual(first.fresh.map((m) => m.id).sort(), ["t1_c1", "t3_post1", "t3_post3"]);
  const second = await monitor({ apish: fakeApi().apish, brand: "Notion", ...files });
  assert.equal(second.fresh.length, 0);
  assert.equal((await readFile(files.out, "utf8")).trim().split("\n").length, 4);
});

test("reddit monitor: mentions", () => {
  assert.ok(mentions("Moved to Notion.", "Notion"));
  assert.ok(!mentions("a notion of it", "Notion"));
  assert.ok(mentions("a notion of it", "Notion", [], true));
  assert.ok(!mentions("Notional value", "Notion"));
  assert.ok(!mentions("Linear algebra homework", "Linear", ["linear algebra"]));
});
