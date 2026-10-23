---
name: frontend-share-cards
description: Link-preview metadata (Open Graph / Twitter cards), canonical URLs, favicons, robots and sitemap for Next.js App Router sites. Use when shipping or auditing a site's share cards, scrape tags, or the favicon/robots/sitemap 404s. NOT for general styling, components, or SPA routing.
version: 1.0.0
---

# Skill: Share Cards & Scrape-Surface Files (Next.js App Router)

## 1. Core model

A share card is rendered by **crawlers that never execute your app**: X/Twitter,
LinkedIn, Facebook, WhatsApp, Slack, Discord, iMessage. They read only the
static `<head>` on a cold GET. Consequences:

- Client-side anything (routing, effects) is invisible to them.
- They cache aggressively — a card scraped once is not re-scraped until you
  force it in each provider's validator.
- Some won't follow **any** redirect, including your apex→www 308.

Real-world cost (PeekPeak, Oct 2026): a polished site shipped with **no og:image
on any subpage** and a bare brand name on home — every subpage link shared as a
text-only card. Three rounds of pixel-perfect UI checks never looked at `<head>`.

## 2. The replace-not-merge rule (the #1 Next.js failure)

A page-level `openGraph` or `twitter` object **replaces** the layout's — Next
does not deep-merge them. A subpage that exports `openGraph: { title, url }`
silently drops the layout's `images` and `type`. Same for `twitter`.

**Rule: one helper builds the full per-page metadata; every page uses it.**

```ts
// lib/seo.ts
export const SITE_URL = "https://www.example.com"; // canonical origin
export const SHARE_IMAGE = { url: "/brand/og-1200x630.jpg", width: 1200,
  height: 630, alt: "<>=10 chars describing the art>", type: "image/jpeg" };

export function pageMetadata({ path, title, description, shareTitle,
  shareDescription }: PageMetaInput): Metadata {
  return {
    title, description,
    alternates: { canonical: path },
    openGraph: { type: "website", siteName: "<Brand>", url: path,
      title: shareTitle, description: shareDescription, images: [SHARE_IMAGE] },
    twitter: { card: "summary_large_image", title: shareTitle,
      description: shareDescription,
      images: [{ url: SHARE_IMAGE.url, alt: SHARE_IMAGE.alt }] },
  };
}
```

- Layout keeps `metadataBase: new URL(SITE_URL)` plus bare defaults **only**
  for routes without their own export (404).
- Never put `alternates.canonical` in the layout — the 404 would inherit `/`.
- Do NOT also add `app/opengraph-image.*` file conventions; mixing the two
  emits duplicate tags.

## 3. Canonical and absolute URLs

- `og:image`/`twitter:image` must be **absolute on the canonical host** (www),
  because `metadataBase` resolves relatives and apex hosts 308. A redirecting
  image URL = no card in some tools.
- `og:url` must equal `<link rel="canonical">`: `SITE_URL + path`.
- Every real page gets its own `path`-derived canonical — duplicate canonicals
  or missing ones are SEO failures the checker catches.

## 4. The image itself

| Requirement | Value | Why |
|---|---|---|
| Dimensions | exactly 1200×630 | the 1.91:1 large-card standard |
| Declared | `og:image:width/height/alt/type` | render before download |
| Size | < 600 KB | WhatsApp drops larger |
| Edges | dark/branded to the edge | grey letterbox frames read as broken |
| Composition | safe margins survive a 2:1 center crop | X crops |
| Formats | JPEG or PNG (no WebP for OG) | crawler support |

Keep the old banner file in place; just stop referencing it in metadata.

## 5. The scrape-surface 404 trio

Browsers and crawlers request these even when your app never links them:

- `/favicon.ico` — a **real ICO** (multi-size 16/32/48; PNG-in-ICO is fine),
  even though `app/icon.svg` exists. Generate from the SVG via headless
  Chrome screenshots packed into an ICO container.
- `/robots.txt` — `app/robots.ts` (MetadataRoute): allow all + sitemap URL.
- `/sitemap.xml` — `app/sitemap.ts`: enumerate every route on SITE_URL.

## 6. Share copy style

- og:title is **descriptive**, not the bare brand (>= 25 chars, brand inside).
- og:description >= 70 chars; says what the product does.
- No colons and no en/em dashes in title/description — X renders them badly
  and checkers fail them. Plain hyphens only.
- twitter:title must equal og:title.

## 7. Verification

Headless, per page, against the production build (localhost, preview, prod):

1. Parse `<head>`: og:image / :width / :height / :alt / :type, og:url ==
   canonical, og:type == website, twitter:card/image/image:alt, unique
   og:titles per page.
2. Fetch the image with `redirect: "manual"` — **must be 200 direct**,
   `image/*`, decode PNG IHDR / JPEG SOFn and assert 1200×630.
3. Edge-luminance: mean of the outer ~6px ring (canvas in the browser);
   a light ring means the old grey-frame asset is still wired in.
4. After deploy: force one re-scrape each in the X Card Validator, LinkedIn
   Post Inspector, Facebook Sharing Debugger — they serve cached cards until
   told otherwise. Do this BEFORE the launch posts.

## 8. Directives

- Every page (deep pages included) carries the full card via the helper —
  never a partial `openGraph` export.
- One source of truth for the image and origin (`SITE_URL`, `SHARE_IMAGE`).
- The head check runs with the UI checks, not "later".
- Changing the card? Same rules; then re-scrape everywhere it was shared.
