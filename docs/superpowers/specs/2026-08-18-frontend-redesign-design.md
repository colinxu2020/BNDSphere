# BNDSphere Frontend Redesign — Design

**Date:** 2026-08-18
**Target branch:** `origin/release/26.08.21` (React 19 rewrite)
**Status:** Approved design. Implementation planning not yet started.

## 1. Context

### 1.1 Which frontend this describes

BNDSphere has two frontends. This design targets the React one.

- `master` holds a Vue 3 app (110 SFCs, PrimeVue + shadcn-vue/reka-ui + Tailwind v4).
  Since the 2026-06-11 merge base, **every commit touching `frontend/` on master has been
  dependabot** — 4 of them as of 2026-08-18 (`#23` esbuild, `#25` js-yaml, `#34`
  openapi-ts, `#35` npm_and_yarn group), and no human commit at all. Treat it as
  abandoned.
- `release/26.08.21` replaced that frontend wholesale in commit `413c48d`
  (2026-08-18, *更新前端功能与工作台界面*): 211 files, +23,429 / −16,498. React 19,
  react-router-dom 7, Tailwind v4, `motion`, `@tabler/icons-react`, 15 pages under
  `frontend/src/pages/`, and one hand-rolled `components/ui/AppPrimitives.tsx`
  (285 lines) in place of a component library.

The branches are **diverged, not fast-forward**. `release/26.08.21` does not contain
master's `#29` (VerificationMixin club-president approval) or `#32` (avatar/logo URL
upload security fix). Reconciling that is outside this design's scope but must not be
forgotten.

### 1.2 Goal

A new visual direction — not a consolidation of the existing one. Energetic and
youthful, appropriate to a school club platform, supporting desktop and mobile with
light and dark schemes that follow the operating system preference.

### 1.3 Verified starting state

Measured in a worktree at `413c48d`; the branch builds clean (1.68s, 36.82 kB CSS,
596.38 kB JS).

| Property | Value |
|---|---|
| Hardcoded palette utilities in `src/` | 500, across 19 files |
| `dark:` variants in `src/` | 0 |
| Semantic token layer | none |
| `primary` ramp steps defined | 50, 100, 500, 600 |
| `secondary` ramp steps defined | 50, 500, 600 |
| Test framework | none |
| ESLint | not installed |
| `lint` script | `tsc --noEmit`, not run in CI |
| CI gate on `frontend/**` | Docker image build only (`docker.yml`) |

Two utilities referenced by `AppPrimitives` produce **no rule at all** in the compiled
CSS, confirmed by grepping `dist/assets/*.css` (0 occurrences of either token):

| Class | Used by | Effect |
|---|---|---|
| `text-primary-700` | `Badge tone="primary"` | badge text has no colour; inherits surrounding colour |
| `border-secondary-100` | `Badge tone="blue"` | border colour falls back to `currentColor` |

Tailwind v4 emits nothing for a utility referencing an undefined theme step and does
not warn. Both classes look plausible and compile clean.

## 2. Typography

### 2.1 Problem

- `src/index.css:1` loads Inter and Space Grotesk from `https://fonts.googleapis.com`.
  There are no local font files in the repository (`public/` contains only
  `LOGO_FULL.png` and `LOGO_SQUARE.png`; no `.woff2` anywhere).
- The font stack is `"Inter", ui-sans-serif, system-ui, sans-serif` — **no CJK family
  at any position**.
- `index.html` declares `lang="en"`.

Effectively all UI text is Chinese (发现社团, 社联工作台, 星级评价, 处理中…).

Google Fonts availability in mainland China is not reliable enough to be a production
dependency for this audience, so core typography must not depend on it. Independently
of reachability, neither Inter nor Space Grotesk contains CJK glyphs, so they can only
ever style Latin text and numerals; every Chinese character falls through to an
unspecified OS default (PingFang SC on Apple, Microsoft YaHei on Windows, Noto/Roboto
on Android), with different weights and vertical metrics per platform. `lang="en"`
degrades the browser's CJK font selection further.

The repository is mirrored from `gitee.com/bjbnds/BNDSphere` (`main.yaml`), which
establishes a mainland-China-oriented deployment context. It does not by itself
demonstrate anything about the school network's access to Google's CDN; the
self-hosting decision rests on audience reliability, not on that inference.

### 2.2 Decisions

1. **Self-host the Latin faces**, served from our own origin with `font-display: swap`,
   removing the render-blocking CDN `@import` and the third-party dependency.

   *Implementation note (Phase 1, as built):* rather than hand-subsetting `woff2` into
   `public/fonts/`, this uses the `@fontsource/inter` and `@fontsource/space-grotesk`
   packages and imports only the latin-subset weights actually used — Inter 400/500/600/700
   and Space Grotesk 600/700 (the only two display weights referenced in source). Vite
   emits the files into `dist/assets/` with hashed names, so they are still served from our
   origin, and the packages carry correct `unicode-range` metadata that hand-subsetting
   would have to reproduce. Same guarantees, less bespoke tooling.
2. **Specify the CJK stack explicitly** rather than letting each OS improvise: system
   CJK faces (`PingFang SC`, `Microsoft YaHei`, `Noto Sans SC`) after the Latin face,
   so numerals and Latin words still receive Inter's treatment while CJK glyphs get a
   named family. Font-family order alone achieves this — no JavaScript, no per-glyph
   classes, no CJK webfont download.
3. **Tune heading and body metrics for CJK explicitly.** Do not inherit Latin-oriented
   tight tracking. The current `tracking-tight` on headings actively harms Chinese
   glyphs; CJK needs looser tracking and slightly greater line-height than the
   Latin-tuned values in use. Metrics are validated visually across target platforms
   (§7, Gate 4), not assumed.
4. **`lang="zh-CN"`** in `index.html`.
5. **Display face used honestly.** Space Grotesk cannot set a Chinese heading. Hierarchy
   is carried primarily by weight and tracking; Space Grotesk is retained for the Latin
   eyebrow labels and numerics it already styles well.

### 2.3 Risk

Once the CJK stack is explicit, headings will render differently from what the author of
`413c48d` currently sees locally, because today's rendering is an accidental fallback.
This is a correction but will read as a change; tell them before it lands.

## 3. Token layer

### 3.1 Structure

**Tier 1 — primitive ramps.** Complete `primary` and `secondary` to 50–950, generated
from the existing hues (`#14b8a6`, `#3b82f6`), holding every currently-defined step at
its exact present value so nothing visible shifts. This eliminates the missing-utility
class of bug in §1.3.

Full ramps are **primitive-only**. They exist for consistency and to remove silent
failures; they are not the public API. App-authored components migrate toward semantic
tokens rather than reaching for ramp steps.

**Tier 2 — semantic tokens.** Register the utility vocabulary with `@theme inline`,
backed by ordinary semantic CSS variables redefined under
`@media (prefers-color-scheme: dark)`. This keeps Tailwind's utility namespace separate
from the actual light/dark values:

```css
@theme inline {
  --color-surface: var(--surface);
  --color-surface-raised: var(--surface-raised);
  --color-content: var(--content);
  --color-content-muted: var(--content-muted);
  --color-edge: var(--edge);
}

:root { --surface: #fff; /* … */ }

@media (prefers-color-scheme: dark) {
  :root { --surface: #0b1220; /* … */ }
}
```

This is the pattern master's `src/assets/main.css` already used (`@theme inline` over
`:root`/`.dark`), so it carries forward the half of this repository that got tokens
right.

Because utilities compile to `var(--*)` references, the scheme switch is centralized in
one media query and requires no `dark:` variant in app code. **This makes the
implementation low-cost, not free** — see §3.3.

**Tier 3 — one tone vocabulary.** Two vocabularies currently disagree: `Badge` takes
colour names (`slate | primary | yellow | green | red | blue`) while `StatusMessage`
takes semantic names (`error | success | info`). `InlineError` and `DangerButton`
hardcode a third variant of the same red. `Federation.tsx:1315` holds a private
`getAuditTone` doing this mapping for one page.

Collapse to one semantic set:

```
neutral | brand | info | success | warning | danger
```

Each is defined once as a token triple (background / text / edge) and consumed by every
component with a tone. Colour names disappear from component APIs.

**`brand` and `info` are distinct concerns and must stay distinct even where their
initial hues are similar.** `brand` means identity and emphasis — this product, this
club, this call to action. `info` means a system or informational state — a neutral
notice, an in-progress condition, a non-urgent status. They may diverge later; code
that conflates them now would have to be untangled then.

### 3.2 Status vocabulary mapping

The label maps in `src/lib/labels.ts` define five state families. Each maps onto the
tone set once, in a table, rather than per call site:

| State | Tone |
|---|---|
| 已封禁 (`ban`), 已驳回 (`rejected`) | `danger` |
| 待审核 (`pending`), 待确认 (membership `pending`), 未审核 (`unreviewed`) | `warning` |
| 已通过 (`approved`), 正常运行 (`normal`) | `success` |
| 社长 (`president`), 副社长 (`vice_president`) | `brand` |
| 已归档 (`archived`), 已退出 (`left`), 已被替代 (`superseded`) | `neutral` |

**Activity levels (校级 / 大型 / 社联) are deliberately not in this table.** They are not
a state — they are a small fixed taxonomy, like club categories, and they serve as the
identity chip on activity cards (§4.4). They therefore receive an identity treatment
under §4.3's rules, not a status tone. Treating them as `info` would put them in the
workbench's state vocabulary and break the §4.4 rule that colour means state in the
workbench and identity in public surfaces.

`CATEGORY_MAP` and `STAR_LEVEL_MAP` are currently defined twice — in `lib/labels.ts`
and again locally at `ClubDetail.tsx:19` and `ClubDetail.tsx:30`. The duplicates are
deleted; `lib/labels.ts` is the single source.

### 3.3 Dark scheme is centralized, not automatic

A variable swap does not by itself get these right, and each is gated in §7:

- **Interaction states** — `hover:bg-slate-100`, `active:scale-[0.98]`,
  `focus:ring-primary-500/20`, `disabled:opacity-70`. Opacity-based states that read
  well on white can vanish on dark surfaces.
- **Elevation** — the current `shadow-sm` / `shadow-md` / `shadow-primary-500/20` idiom
  is close to invisible on dark backgrounds. Dark schemes need border or
  surface-lightness elevation instead. This is a design decision, not a token swap.
- **The 1.5px border override** in `index.css` — thick borders are load-bearing in this
  aesthetic and border contrast behaves differently inverted.
- **Logos** — `LOGO_FULL.png` and `LOGO_SQUARE.png` are raster assets sitting on a white
  header; a dark surface needs a variant or an inversion decision.
- **All six status tones and all eight category treatments** need dark pairs. The
  `-50` background / `-700` text formula that works on light inverts to something muddy;
  dark typically wants a translucent-hue background with `-300`/`-400` text.
- **User-supplied imagery** — posters and avatars need a consistent frame treatment on
  dark surfaces.

### 3.4 Colour space

Stay with hex. Master's Vue branch used oklch; converting buys nothing visible here and
costs diff readability. No oklch migration.

## 4. Visual identity

### 4.1 Thesis

What makes this product specific to the school is not a palette — any template can be
teal. It is that BNDSphere has institutional structures no generic app has: a seven-tier
club honours system, an eight-category taxonomy, a 社联 federation with its own
workbench, and a notice board as the front door. All four currently render as grey text
in identical badges. The identity work is making those structures visible.

### 4.2 Star level — the signature element

The canonical progression is a **single ranked scale**:

```
无星级 → 一星 → 二星 → 三星 → 四星 → 五星 → 荣誉社团
```

荣誉社团 is the **highest level in that progression**, not a parallel honour.

Currently `STAR_LEVEL_MAP[club.star_level]` renders "三星社团" as badge text
(`ClubDetail.tsx:228`) and **no star is drawn anywhere in the application**, despite the
system having its own nav entry (星级评价) and its own applications pipeline
(`StarLevelApplications.tsx`).

A `StarLevel` component encodes the progression explicitly:

- Five star glyphs represent the numbered 1–5 scale, earned filled in the brand hue,
  unearned as hollow outlines.
- 荣誉社团 is an **elevated treatment built on top of the five-star state** — five filled
  stars plus a **seal** accent. **There is no sixth star.** The distinction is visual
  only; semantically it remains the top rank of the same scale. (Crown and laurel are
  the alternatives; they are visual variants of the same decision, compared on the
  specimen page in Phase 5. The seal is the default because it reads as institutional
  rather than gamified.)
- Sizes: inline (cards), large (club detail header), compact numeric (dense workbench and
  moderation tables).

**Accessibility rule, binding on every representation:** the textual level is always
retained alongside the glyphs. Stars and decorative marks are never the only carrier of
meaning.

### 4.3 Category identity

Each of the eight categories (科学, 人文, 艺术, 体育, 商业, 公益, 校园, 其他) maps to a
fixed hue defined as tone triples in the token layer, so a category reads the same
colour everywhere. Currently `ClubWorkspace.tsx:620` renders every category as
`<Badge tone="primary">` — all eight identical teal.

Two binding constraints:

- The eight hues must differ in **lightness as well as hue**, so they stay
  distinguishable for colour-blind users and survive the dark scheme.
- Category colour attaches only to **small elements** — a chip, a left border, an icon
  field — never to a large surface, or the browse page becomes visual noise.

其他 (other) stays neutral deliberately.

**Where the hue-to-category assignment is decided:** the specific hue for each of the
seven coloured categories is fixed in **Phase 2**, as part of defining the token triples,
not left to the components that consume them. It is reviewed against the lightness
constraint in Gate 4. This spec deliberately does not pin the seven hues, because they
must be chosen together as a set against the generated ramps and both schemes — choosing
them one at a time in prose is how eight-colour systems end up indistinguishable. The
constraints above are binding on that choice; the specific values are a Phase 2
deliverable.

### 4.4 Surfaces

- **The board (`Home`).** Not a marketing hero — a 展板 notice board
  (`lg:grid-cols-[1.55fr_0.85fr]`: poster carousel, club panel, activity rail). Keep the
  structure; give it presence. Poster carousel as the clear focal element with
  aspect-ratio discipline and readable overlaid captions; club showcase with
  category-coloured cards and visible star levels; activity rail with date-forward
  formatting. `EmptyPanel` states matter more here than anywhere, because a school
  platform is genuinely empty between terms.
- **Cards.** One card component, replacing the current per-page variants. Composition:
  logo, name, category chip, star level, member count, president, joined/pending state.
  Activity cards are the same skeleton with level replacing category and date replacing
  star level.
- **Workbench** (`ClubWorkspace`, `Federation`, `Admin`, `Moderation`). Deliberately
  quieter: `Surface` + `SectionTitle` remain the frame, density increases, colour
  recedes to status tones only.

**The rule:** colour means **state** in the workbench and **identity** in public
surfaces. A student browsing sees category colour; a 社联工作人员 processing 待审核 items
sees only status colour. This keeps an energetic palette from making administrative work
harder.

### 4.5 Motion

`motion` is already a dependency and already used for page-level fades (`Home.tsx`
`initial`/`animate`). Extend deliberately and sparingly: card hover lift, star level
animating in on first display of a club's rank, list stagger on load, poster carousel
transition. All behind `prefers-reduced-motion`. The existing `active:scale-[0.98]` on
buttons is a good instinct already present — keep it and apply it consistently.

### 4.6 Out of scope

Illustrated empty-state artwork (needs an illustrator; icon plus good copy gets most of
the value), a mascot, and per-club custom theming (unmanageable at 8 categories × 7 star
levels).

## 5. Shell

### 5.1 Verified defects in `RootLayout.tsx`

1. **The hamburger button does nothing.** Line 204 renders
   `<button aria-label="打开导航">` with no `onClick` and no state; the file's only
   `onClick` is logout at line 191. It announces itself to assistive technology as a
   navigation control and is inert.
2. **The user menu is unreachable on touch and by keyboard.** It opens purely on
   `group-hover`, and the trigger has no click handler. On a phone, 个人主页,
   我管理的社团, 社联工作台, 管理员控制台 and 退出登录 are all inaccessible — the mobile
   bottom bar carries only the three public `navLinks`. Keyboard users are equally
   locked out, since `visibility: hidden` removes the menu from tab order.
3. **`<main>` does not account for the fixed bottom bar.** Line 212 is `py-6`; the bar at
   line 216 is `fixed bottom-0`. **13 of 15 pages carry a hand-written `pb-20`** to
   compensate. `Login` and `Register` do not, and are clipped on mobile. The `pb-20`s are
   unconditional rather than `md:pb-0`, so every page also carries 5rem of dead space on
   desktop.

Defect 3 is the pattern worth naming: a layout concern with no home in the layout,
patched thirteen times. The fix is `pb-24 md:pb-6` on `<main>` once, deleting thirteen
workarounds — a net-negative diff that fixes two pages and desktop simultaneously.

### 5.2 Rebuild

State-driven mobile navigation that the hamburger actually opens; the user menu
converted to click/tap with focus management and `Escape` to dismiss; logged-in
destinations reachable from the mobile bar or drawer.

### 5.3 Pulled out as a standalone bugfix

Defect 2 means a logged-in student on a phone cannot log out or reach club management.
That is a live functional bug affecting real users, independent of any redesign, and
**ships as a standalone functional fix before Phase 0** rather than waiting for Phase 4.

## 6. Decomposition

Driven by responsibility and shared workflow, not file length. Sorted that way, the three
large pages are large for different reasons and one barely needs work:

| Page | Lines | Actual state |
|---|---|---|
| `Admin.tsx` | 1305 | **Already decomposed internally** — `UsersAdmin`, `ClubsAdmin`, `TermsAdmin`, `ActivitiesAdmin`, `AnnouncementsAdmin`, plus shared `AdminGrid` / `ItemList` / `FormHeader`. Boundaries drawn; file extraction only, near-zero risk. |
| `Federation.tsx` | 1319 | **1,015 lines in one function body** with three fused workflows (activity requests, audit records, star applications) and 10+ `useState`. |
| `ClubWorkspace.tsx` | 1274 | **1,177 lines in one function**, one helper. Worst cohesion in the codebase. |

### 6.1 Root cause: three cross-cutting workflows have no home

1. **Action-result feedback.** `useState<"error" | "success">` paired with a message
   string appears **9 times across 6 files** (`messageTone`, `actionTone`, `updateTone`,
   `clubTone`, `recordTone`, `starCreateTone`, `starUpdateTone`); `ClubWorkspace` alone
   has four. One `useActionFeedback` hook replaces all nine.
2. **The audit queue.** "List items filtered by `AuditStatus`, approve or reject with a
   reason" recurs in `Federation` (twice — `recordStatus` and `starStatus`),
   `Moderation`, `ClubWorkspace` and `GeneralActivityDetail` — **19 approve/reject sites
   across 4 files**. One `AuditQueue` component parameterised by endpoint and item
   renderer.
3. **Status→tone mapping**, already present privately as `getAuditTone`
   (`Federation.tsx:1315`) — the table §3.2 centralizes.

**Order: extract the workflows first; the pages shrink as a consequence.** Splitting by
length first would yield smaller files each still carrying its own copy of the feedback
state and the audit queue — more files, identical duplication, and the extraction still
to do across more places. `Federation` and `ClubWorkspace` are largely *made of* these
three workflows, which is why they are the largest.

### 6.2 Scope boundary

This is decomposition and restyling, **not a data-layer refactor**. The `client.GET` /
`client.POST` calls, the `AUTH_STATE_CHANGED_EVENT` pattern, and the per-page fetch
effects stay as they are. They are worth revisiting; not inside a UI redesign.

### 6.3 Coordination

`ClubWorkspace` and `Federation` are where commit `413c48d` landed. Extracting them will
conflict with anything still in flight; coordinate with its author before that step.

## 7. Verification

No test framework exists and none is added — a restyle does not justify vitest or
playwright. Four gates: three automated and cheap, one manual and honest.

### Gate 1 — compiled-CSS validation of the token contract

After `vite build`, compare utilities referenced in `src/` against selectors emitted in
`dist/assets/*.css`, and fail on any that produced no rule.

**Scope it to our design-token namespaces and known static variant maps** — it must not
attempt to become a general Tailwind parser. Tailwind scans source as text and discards
candidates it cannot map to real utilities; dynamic class construction and
escaped/arbitrary variants make a universal source→selector comparison far harder than
it first appears. The contract under test is narrow: utilities depending on
`primary` / `secondary` / `surface` / `content` / `edge` / tone / category namespaces.

This is the check that found `text-primary-700` and `border-secondary-100`. A
source-level lint rule would need a hand-maintained list of valid steps to do the same
job less reliably.

### Gate 2 — forbidden raw-palette check

After the sweep, `-(slate|gray|red|emerald|amber|…)-\d+` in `src/` should be zero. Fail
on reintroduction, with a small allowlist file for deliberate exceptions. The 500
utilities accumulated one reasonable-looking line at a time; this is what stops that
recurring.

*Phase 2 implementation notes.* The gate runs as a **ratchet** rather than a ban while the
sweep is in progress: it fails if the count rises, and `BASELINE` is lowered as the count
drops, reaching 0 when the sweep completes. This makes it useful during the sweep instead
of only after it. Its authoritative count is **502**, not the 500 quoted in §1.3: the gate
checks a wider property list (including `border-t`/`outline`/`placeholder`/`caret` and
friends) than the exploratory grep did, and it counts the two raw utilities in
`index.css`'s own `body` rule. Where the two figures differ, the gate's number governs.
`src/dev/Specimen.tsx` is allowlisted, since it renders raw primitive ramps deliberately.

### Gate 3 — `tsc --noEmit` as a separate CI step

Required. `vite build` transpiles TypeScript but does **not** type-check it, so the
Docker build is not a type-safety gate. The script already exists and never runs
automatically.

*Phase 2 finding — the gate was weaker than this section assumed.* `@types/react` and
`@types/react-dom` were **not installed at all**, and with `allowJs: true` TypeScript was
inferring React's API from its JavaScript instead of erroring. So `tsc --noEmit` passed
while barely type-checking the React surface: `React` namespace references failed, `key`
was rejected on custom components, and `import.meta.env` was untyped. Fixed by adding
`@types/react`, `@types/react-dom` and `"types": ["vite/client"]` to `tsconfig.json`.
Existing code turned out to be type-correct — the error count went from 0 (unchecked) to
0 (checked) — so this cost no cleanup, but it means Gate 3 only became a real gate in
Phase 2. Enabling `strict` remains deliberately out of scope.

### Gate 4 — cross-platform and dark validation

Matrix: **macOS / Windows / iOS Safari / Android Chrome × light / dark**.

Made tractable by a **dev-only specimen route** (`/_dev/specimen`) rendering the whole
system on one page, turning eight combinations across fifteen pages into one screenshot
per combination. It doubles as the design system's living documentation.

**The specimen must be genuinely absent from the production bundle.** Guard both the
route registration and the import behind `import.meta.env.DEV` / a DEV-only lazy import
so Vite can tree-shake the specimen code out of production, rather than merely making
the URL unreachable.

**Interaction states must be deterministic** rather than relying on a screenshot
catching real `:hover` or `:focus`. Add specimen-only forced-state presentations for
hover / focus / disabled / open so every state is reviewable on one page.

Gate 4 covers:

- CJK typography at every type scale step
- mixed Chinese / Latin / numeric strings
- all seven star levels, including 荣誉社团
- all six semantic status tones
- all eight category treatments
- logos and user imagery on both schemes
- keyboard navigation and focus return for menus and drawers
- reduced-motion behaviour
- interaction states: hover, active, disabled, focus
- overlays and shadows/elevation

## 8. Sequencing

| # | Phase | Notes |
|---|---|---|
| — | **Mobile auth navigation bugfix** | §5.3. Standalone functional fix, ships first, independent of the redesign. |
| 0 | **Scaffold cleanup** | Unused `@google/genai`, `express`, `dotenv`, `@types/express`, `tsx`; `vite` duplicated across `dependencies` and `devDependencies`; package name `"react-example"`. **Separate commit from the token migration**, no design changes. |
| 1 | **Typography foundation** | §2. Self-hosted woff2, explicit CJK stack, `lang="zh-CN"`, CJK-tuned metrics. |
| 2 | **Token layer + gates** | §3. Full primitive ramps, `@theme inline` + semantic vars, tone table, Gates 1–3, specimen route. |
| 3 | **Semantic sweep + dark scheme** | 500 utilities → tokens across 19 files; dark scheme falls out; Gate 2 turns on. |
| 4 | **Shell rebuild** | §5.2. Mobile nav, user menu, delete 13 `pb-20`s. |
| 5 | **Identity components** | §4. `StarLevel`, category chips, unified cards, the board. |
| 6 | **Workflow extraction → decomposition** | §6. `useActionFeedback`, `AuditQueue`, tone table adoption; then `Admin` (cheap) → `Federation` → `ClubWorkspace`. |
| 7 | **Validation gate** | §7 Gate 4 across the platform × scheme matrix. |

Phases 2–3 are one reviewable unit in practice: the sweep is meaningless without the
tokens, and the dark scheme cannot be verified until both land. Phases 5 and 6 are
independent of each other and may run in parallel or in either order.

**This spec is too large for a single implementation plan, and should not become one.**
Each phase (with 2–3 taken together) gets its own plan, written when that phase starts,
so later plans can be informed by what earlier phases actually turned up — the semantic
sweep in particular will surface surfaces nobody has reviewed yet. The standalone bugfix
in §5.3 needs no plan; it is a small, self-contained fix.

## 9. Accepted risks

- Retuning Tier 2 values changes every screen at once, including screens not reviewed
  during design. The first build after the token change will look wrong in places until
  the sweep catches up. Expected, not a regression.
- Explicit CJK metrics will differ from what the author of `413c48d` sees locally today
  (§2.3).
- Phases 4–6 touch pages committed on 2026-08-18; coordinate before starting (§6.3).
- Eight category hues is at the edge of comfortable distinguishability; the
  lightness-variation constraint in §4.3 is what keeps it viable, and it is verified in
  Gate 4 rather than assumed.

## 10. Out of scope

- Reconciling `release/26.08.21` with master's backend commits `#29` and `#32` (§1.1).
- Data-layer refactoring (§6.2).
- oklch migration (§3.4).
- Illustration, mascot, per-club theming (§4.6).
- A full accessibility audit. Contrast for the palette, focus-visible states, keyboard
  reachability of menus and drawers, and reduced-motion are in scope because this design
  creates or already broke them; a comprehensive WCAG audit is separate work.
