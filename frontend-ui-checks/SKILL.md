---
name: frontend-ui-checks
description: Headless rendered-page UI verification - multi-width matrices, visibility vs rects, keyboard order, contrast/type floors, truthful state, and checker engineering with per-failure IDs. Use when building UI checkers, hardening a frontend before launch, or diagnosing "looks fine but is broken" UI bugs. NOT for visual design decisions or styling preferences.
format: reference
version: 1.0.0
---

# Skill: Rendered-Page UI Checks (headless, per-ID, multi-width)

## 1. Core model

Static greps and "it looks fine" miss the bugs that matter: elements with
nonzero rects that are invisible and untabbable, cards that vanish per-width,
text under 12px, 2.9:1 contrast, single-`boolean` status lies. Rendered checks
in headless Chrome against a production build are the only layer that catches
them. Measured on one real launch (PeekPeak, Oct 2026): round 1 found **78**
failures on a "done" site; round 2's wider matrix found **115** (incl. a nav
invisible on desktop); round 4 found **49** more in `<head>` alone.

**Rule: a UI task is done when the rendered checker prints ALL PASSED against
localhost AND the preview/prod — not when it looks right.**

## 2. Visibility vs rects (the closed-`<details>` trap)

`getBoundingClientRect()` returns real boxes for links inside a **closed**
`<details>`: the UA hides non-summary content via the `::details-content`
slot (`content-visibility: hidden`), which author CSS on the *child* cannot
undo. Result: rects pass, `checkVisibility()` is false, links are skipped in
the Tab order — invisible nav on every desktop for days.

- Assert visibility with `el.checkVisibility({ visibilityProperty: true,
  opacityProperty: true, contentVisibilityAuto: true })`, never rects alone.
- If a component must be always-visible, render it twice (plain row +
  disclosure) and hide each copy with `display:none` on the other breakpoint —
  `display:none` removes it from tab order and a11y tree cleanly.
- Don't fight the UA slot with `content-visibility` overrides; they're patchy.

## 3. The width matrix

One phone width and one desktop width are not enough. Real breakage lived at
1023/768 (tablet squeeze), 640, 414, 360. Use
`1440, 1280, 1024, 1023, 768, 640, 390` (+ 360 for band-wrap checks).

- Assert **structure per width**: nav links exactly-once visible ≥641px,
  hamburger-only ≤640; grid columns n-up ≥768, 1-up below; stacks vs
  side-by-side transitions at the right pixel.
- Prefer **container queries** for component-width rules (a hero stat strip
  that orphans at 2+1 needs the *column* width, not the viewport's).
- `min-width: 0` on every grid/flex child whose sibling holds a `<pre>` or
  `<table>` — otherwise intrinsic width re-creates horizontal overflow.

## 4. Keyboard order

After focus/blur + scrollTo(0,0), Tab through the first N stops and assert
the sequence (`nav:/ → nav:/start → nav:/dashboard …`). Catches: focus traps,
`display:none` copies still focusable, skip-link regressions, and the
invisible-nav class of bug above. Also assert `:focus-visible` rings exist
and are **contrast-checked against the element's fill** — a brand-orange ring
on a brand-orange gradient button is 1:1 invisible; white ring there.

## 5. Checker engineering

- **Per-failure IDs** (`FAIL [N1] width path: …`) so a run greps per task.
- Each round's checker is a **superset** that re-runs all previous checks —
  the do-not-regress list is executable, not prose.
- Conditional checks **SKIP loudly** (`info SKIP … condition absent`) instead
  of silently passing.
- Measure against the **live protocol state** where relevant: read the
  contract/RPC for thresholds (e.g. min-execution cost) so the UI's derived
  labels are compared to truth, halving volatile inputs (gas price) so a
  wobble can't flap the verdict.
- Run: local production build → preview → prod. Some checks (og:image on a
  not-yet-deployed asset) need a rebase mode: assert the canonical URL, fetch
  the bytes from the host under test.
- Briefs can be **pre-validated** by injecting the proposed CSS/DOM into the
  live page (`SIM=` module) and running the checker — proves the fix satisfies
  every check before the repo is touched.

## 6. A11y floors (all asserted, all measured)

| Floor | Assertion |
|---|---|
| Tap targets | nav/footer links and controls >= 44px tall (48px in open mobile menus) |
| Type | nothing renders under 12px; body copy >= 14px; scale via tokens |
| Contrast | every text node >= 4.5:1 (3:1 large) against the **composited** bg it actually sits on |
| Zoom | text inputs use 16px — iOS Safari auto-zooms on smaller |
| Name | accessible name == visible label (drop `aria-label` overrides; WCAG 2.5.3) |
| Overflow | 0px horizontal scroll at every width |

Token discipline first (`--faint` at 2.9:1 fails everywhere; fix the token,
not each usage), then the checker enforces it forever.

## 7. Truthful state, not raw flags

A protocol's storage flag can be true while the thing is inert: an on-chain
job `isActive` stays true even with zero escrow, because the flip only happens
on the next execution attempt that never comes. Display state must mirror the
**protocol's own precheck** (`escrow >= (gasLimit + 2*overhead) * gasPrice +
tip`), computed from live reads, with the derivation in the tooltip
("needs ≈ 0.0065 AVAX"). And counts must derive from the same truth: "active"
= funded-and-runnable, with a separate amber state for
`NEEDS FUNDS`-style conditions (plain-English, not protocol jargon like
"unfunded").

Formatting tells the truth too: `0.0000 AVAX` hides zero — print `0 AVAX`,
and `<0.0001 AVAX` for dust.

## 8. Wrapping, separators, and copy in the DOM

- A separator must **ride with the phrase after it**: `{" "}` between spans
  and `· ` inside the following `.nowrap` span — never `{" · "}` freestanding
  (wraps orphan the dot).
- Pluralize in the DOM (`plural(n, "job")`) and grep for `/\b1 (jobs|executions)\b/`.
- Copy buttons: uppercase labels, state text (`COPIED`, `COPY FAILED`),
  no `aria-label` override.
- Never put secrets on command lines users will copy: `--interactive`
  (cast/forge) instead of `--private-key 0xYOUR_KEY`.
- Validation errors fire on **submit**, never mid-typing.
- Long hex ids: display full with `break-all` + COPY buttons for the raw id
  and the ready-to-run command built from real values.

## 9. Process directives

- One commit per task ID, message referencing the checker ID it satisfies.
- **Never** run `git add/commit` in the same parallel tool block as the file
  edits it commits — the commit races the edits and scrambles history
  (observed: task B's diff landed in task A's commit).
- A checker that passes once proves nothing about the widths you didn't test,
  the `<head>` you didn't parse, or the keyboard you didn't press — cover all
  three or the next round will.
