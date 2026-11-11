// TikTok and Instagram creator vetting: real reach and engagement from each creator's recent posts,
// not just the follower count, with flags for the usual warning signs. Writes a CSV, best fit first.
//
//   node vet.mjs                            # reads creators.txt
//   node vet.mjs tiktok:duolingo https://www.instagram.com/natgeo/
//
// creators.txt: one creator per line, as "tiktok:handle", "instagram:handle" or a profile link.

import { readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { parseArgs } from "node:util";
import { Apish } from "@api.sh/sdk";

const DAY = 86_400_000;
// Flag thresholds: change them to suit your niche and creator size.
const LOW_ENGAGEMENT_PCT = 0.5; // median likes + comments + shares per post, as a % of followers
const INACTIVE_DAYS = 30;

/** "tiktok:handle", "@handle on a TikTok link" or an Instagram profile link -> { platform, handle }. */
export function parseCreator(line) {
  const text = line.trim();
  if (!text || text.startsWith("#")) return null;
  const tiktok = text.match(/tiktok\.com\/@([\w.]+)/i);
  if (tiktok) return { platform: "tiktok", handle: tiktok[1].toLowerCase() };
  const insta = text.match(/instagram\.com\/([\w.]+)/i);
  if (insta) return { platform: "instagram", handle: insta[1].toLowerCase() };
  const [platform, handle] = text.split(":");
  if (!handle || !["tiktok", "instagram"].includes(platform.toLowerCase())) {
    throw new Error(`can't read "${text}": use tiktok:handle, instagram:handle or a profile link`);
  }
  return { platform: platform.toLowerCase(), handle: handle.replace(/^@/, "").toLowerCase() };
}

const median = (xs) => {
  const s = xs.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!s.length) return null;
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
};
const round = (x, digits = 2) => (x == null ? null : Math.round(x * 10 ** digits) / 10 ** digits);
const num = (x) => (x == null || x === "" ? undefined : Number(x));

/** Pinned posts sit at the top of a profile whatever their age: leave out leading posts older than the 4th. */
export function dropPinned(posts) {
  const fourth = posts[3]?.at;
  if (!fourth) return posts;
  return posts.filter((p, i) => i >= 3 || !(p.at < fourth));
}

/** The numbers that matter, from a list of { at, likes, comments, shares, views } posts. */
export function score({ followers, posts, now = Date.now() }) {
  const dated = posts.filter((p) => Number.isFinite(p.at)).sort((a, b) => b.at - a.at);
  const span = dated.length > 1 ? (dated[0].at - dated[dated.length - 1].at) / DAY : null;
  const interactions = posts.map((p) => (p.likes ?? 0) + (p.comments ?? 0) + (p.shares ?? 0));
  const views = median(posts.map((p) => p.views));
  const engagement = followers ? (median(interactions) / followers) * 100 : null;
  const row = {
    posts_sampled: posts.length,
    posts_per_week: span ? round(((dated.length - 1) / span) * 7, 1) : null,
    days_since_last_post: dated.length ? Math.floor((now - dated[0].at) / DAY) : null,
    median_views: views,
    median_likes: median(posts.map((p) => p.likes)),
    median_comments: median(posts.map((p) => p.comments)),
    engagement_rate_pct: round(engagement),
    engagement_by_views_pct: views ? round((median(interactions) / views) * 100) : null,
    views_per_follower: views != null && followers ? round(views / followers) : null,
  };
  const flags = [];
  if (row.days_since_last_post != null && row.days_since_last_post > INACTIVE_DAYS) flags.push(`inactive ${INACTIVE_DAYS}+ days`);
  if (engagement != null && engagement < LOW_ENGAGEMENT_PCT) flags.push("low engagement");
  if (row.views_per_follower != null && row.views_per_follower < 0.02) flags.push("views far below followers");
  if (posts.length && median(posts.map((p) => p.comments)) === 0) flags.push("no comments");
  row.flags = flags.join("; ");
  return row;
}

async function tiktok(apish, handle) {
  const [profile, channel] = await Promise.all([
    apish.tiktok.profile({ username: handle }, { raw: false }),
    apish.tiktok.channel({ username: handle }, { raw: false }),
  ]);
  const posts = dropPinned(channel.videos.filter((v) => !v.pinned).map((v) => ({
    at: Date.parse(v.create_time), likes: num(v.stats.diggCount), comments: num(v.stats.commentCount),
    shares: num(v.stats.shareCount), views: num(v.stats.playCount),
  })));
  return {
    name: profile.nickname, verified: profile.verified, followers: profile.followers, url: profile.url, posts,
    credits: profile.$meta.creditsUsed + channel.$meta.creditsUsed,
  };
}

async function instagram(apish, handle) {
  const user = await apish.instagram.user({ username: handle }, { raw: false });
  if (user.is_private) throw new Error("private account");
  const posts = dropPinned((user.recent_posts ?? []).filter((p) => !p.pinned).map((p) => ({
    at: Date.parse(p.taken_at), likes: num(p.likes), comments: num(p.comments), views: num(p.views),
  })));
  return { name: user.name, verified: user.is_verified, followers: user.followers, url: user.url, posts,
    credits: user.$meta.creditsUsed };
}

const COLUMNS = ["platform", "handle", "name", "verified", "followers", "posts_sampled", "posts_per_week",
  "days_since_last_post", "median_views", "median_likes", "median_comments", "engagement_rate_pct", "engagement_by_views_pct",
  "views_per_follower", "flags", "url"];
const csvCell = (v) => (v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));

export async function run({ apish = new Apish(), creators, out = "creators-report.csv", log = console.log }) {
  const rows = [];
  let credits = 0;
  // Three creators at a time.
  for (let i = 0; i < creators.length; i += 3) {
    await Promise.all(creators.slice(i, i + 3).map(async ({ platform, handle }) => {
      try {
        const c = platform === "tiktok" ? await tiktok(apish, handle) : await instagram(apish, handle);
        credits += c.credits;
        rows.push({ platform, handle, name: c.name, verified: c.verified, followers: c.followers,
          ...score({ followers: c.followers, posts: c.posts }), url: c.url });
      } catch (error) {
        log(`${platform}:${handle}: skipped (${error.message})`);
      }
    }));
  }
  // Best fit first: no flags, then the highest engagement.
  rows.sort((a, b) => (a.flags ? 1 : 0) - (b.flags ? 1 : 0) || (b.engagement_rate_pct ?? 0) - (a.engagement_rate_pct ?? 0));
  await writeFile(out, [COLUMNS.join(","), ...rows.map((r) => COLUMNS.map((c) => csvCell(r[c])).join(","))].join("\n") + "\n");
  for (const r of rows) {
    log(`${`${r.platform}:${r.handle}`.padEnd(22)} ${String(r.followers).padStart(11)} followers  `
      + `${String(r.engagement_rate_pct ?? "-").padStart(5)}% engagement  ${r.posts_per_week ?? "-"} posts/week`
      + `${r.flags ? `  [${r.flags}]` : ""}`);
  }
  log(`wrote ${out} (${rows.length} creators, ${credits} credits)`);
  return rows;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: {
    file: { type: "string", default: "creators.txt" },
    out: { type: "string", default: "creators-report.csv" },
  } });
  const lines = positionals.length ? positionals : (await readFile(values.file, "utf8")).split("\n");
  run({ creators: lines.map(parseCreator).filter(Boolean), out: values.out }).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
