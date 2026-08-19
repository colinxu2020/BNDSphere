# BNDSphere Frontend Redesign — Design

**Date:** 2026-08-18
**Target branch:** `origin/release/26.08.21` (React 19 rewrite)
**Status:** Approved design, largely implemented on `design/frontend-redesign-26.08.21`.
Phases 0–5 complete; Phase 6 partially complete; Phase 7 (Gate 4) outstanding, since it
requires human review across the platform × scheme matrix. Sections marked
"as built" / "Phase N finding" record where implementation corrected this document.

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

### 1.1b Upstream integration — done, and a correction (2026-08-19)

**An earlier version of this section was wrong.** It stated that `release/26.08.21`
lacked master's `4f670e7` (社长审核新社员入社, VerificationMixin) and `733f948`
(头像/徽标 URL 上传验证漏洞), and recorded a merge-order dependency on that basis. That
inference came from `master` being ahead of the merge base, which is not the same as the
release branch lacking those commits — it was never verified with `--is-ancestor`.

In fact **upstream had already integrated them.** `origin/release/26.08.21` moved on from
`413c48d`, where this branch forked, via `8e2e85a` (merge master) and `f1ce657` (repair
release merge integration). Both fixes are ancestors of its current tip. No master
integration was ever required.

Also: the `#29`/`#32` numbers come from squash-merge commit *subjects*. Since this repo
mirrors from `gitee.com/bjbnds/BNDSphere` they are most likely **Gitee** PR numbers and do
not resolve on GitHub. Refer to upstream work by SHA and subject.

**This branch has now merged its parent** (`2df8da5`), so it carries both fixes. 23
conflicts, resolved by category — see the merge commit for the full account. Two worth
noting here:

- `ClubDetail` needed a real **port**, not a side-take: upstream's join flow POSTs
  `/clubs/{club_id}/membership-requests` with a message, because joining is now a request
  a president approves. Taking our side blindly would have left the join button calling a
  superseded endpoint.
- `package.json` must take **upstream's build toolchain**. Merging ours over theirs kept
  `vite ^6.2.3` against their `@vitejs/plugin-react ^6.0.5` and broke the build with
  `ERR_PACKAGE_PATH_NOT_EXPORTED`. It is now vite 8.2.1 / plugin-react 6.0.5.

Upstream's **ESLint and Prettier** stack now applies here. All 49 errors it reported are
fixed; 14 warnings remain (react-refresh on helper modules, and one `exhaustive-deps` on a
dependency array preserved verbatim from before the refactor). `verify` runs `typecheck`
and `lint` before the build and the design gates.

### 1.2 Goal### 1.2 Goal

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

### 1.4 Implementation status

| Phase | State |
|---|---|
| Mobile auth-nav bugfix (§5.3) | done — shipped first, standalone |
| 0 Scaffold cleanup | done |
| 1 Typography foundation | done |
| 2 Token layer + Gates 1–3 | done |
| 3 Semantic sweep + dark scheme | done — 502 raw utilities → 0 |
| 4 Shell rebuild | done, plus three further mobile defects (§5.2) |
| 5 Identity + visual language | done — §4.6 |
| 6 Workflow extraction → decomposition | partial — §6.1b, §6.1c |
| 7 Gate 4 validation | **partly automated** — see §7 Gate 4 |
| 8 Layout restructure (A+B) | done — §10b |

Nothing in Phases 1–6 has been visually reviewed on a real device in either scheme. The
gates prove the tokens resolve and the types hold; they say nothing about whether it looks
right. That is Gate 4's entire purpose and it has not been run.

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

**Colour decision (2026-08-19, supersedes "brand hue" below).** Rank uses its own warm
**gold** family, not brand teal. Category colour already carries club identity and teal
carries product emphasis, so an institutional achievement must read as neither — in brand
teal an honour looked like a call to action.

The values were measured rather than taken off a ramp, because the obvious gold
(`yellow-500` `#eab308`) is only **1.85:1** on a warm chip and would have failed non-text
contrast for the glyphs. Against their own chip background: light — label 6.84:1, earned
4.84:1, unearned 3.87:1; dark — 10.11:1 / 8.73:1 / 3.48:1. Unearned outlines clear 3:1
too, so the *shape* of the rank is perceivable, not only its filled portion. Progression,
seal treatment and the always-present textual level are unchanged.

The canonical progression is a **single ranked scale**:

```
无星级 → 一星 → 二星 → 三星 → 四星 → 五星 → 荣誉社团
```

荣誉社团 is the **highest level in that progression**, not a parallel honour.

Currently `STAR_LEVEL_MAP[club.star_level]` renders "三星社团" as badge text
(`ClubDetail.tsx:228`), despite the system having its own nav entry (星级评价) and its own
applications pipeline (`StarLevelApplications.tsx`).

*Correction (Phase 3).* This section originally said "no star is drawn anywhere in the
application". That was imprecise: a single `Sparkles` glyph did render beside the level in
`ClubDetail` and `ExploreClubs`. But it was identical for 一星 and 五星, so it marked
*that* a club had a rank while conveying nothing about *which* — which is arguably worse
than nothing, since it looks like information. It is what `StarLevel` replaces.

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

### 4.6 The visual language, as built (Phase 5)

The direction approved in design — energetic, youthful — was implemented as **posted
objects on a 展板**, grounded in the subject: club recruitment at this school happens on a
board of colour-coded, stamped posters, and `Home` is already structured that way.

Four decisions, all of which live in `index.css` rather than in components:

- **Shape.** The radius scale is redefined in `@theme`, so all 165 `rounded-md` call sites
  moved at once. The default step is 12px rather than Tailwind's 6px; cards read as posted
  objects rather than table cells.
- **Elevation — hard offsets, no blur.** `--shadow-*` is redefined to offsets against a
  scheme-aware `--shadow-ink`. This replaces the blurred-drop-shadow idiom, which read as
  generic and was nearly invisible on dark surfaces — the weakness §3.3 flagged and could
  not otherwise fix. An offset is a drawn edge, so it survives inversion, and it completes
  the instinct already in the codebase: the global 1.5px border override.
- **The category spine.** Club cards carry a thick left edge in their category colour;
  activity cards carry a level spine. An edge, not a fill, so §4.3's small-element rule
  holds.
- **Type.** Page titles `text-4xl md:text-5xl`, section titles `text-2xl`; the eyebrow
  label uses Space Grotesk with wider tracking, since it is the one Latin-only element in
  a Chinese interface and therefore the one place a Latin display face belongs.

**Restraint.** The boldness is spent on the offset and the spine. Everything else stays
quiet, and the offsets are deliberately small (2-4px) to stay short of decorative
neo-brutalism.

**Clarification to the §4.4 colour rule.** "Colour means state in the workbench" holds for
queue and list rows, but a *club header* inside the workbench exists to tell you which club
you are managing, so it takes the full identity treatment. Identity where you are
identifying something; state everywhere else.

**Activity level tokens.** §3.2 established that activity levels are a taxonomy rather than
a status. They are implemented as their own `--lvl-*` triples (校级 / 大型 / 社联) rather
than borrowing category hues, which would make a 校级 activity chip look like a 科学 club
chip.

### 4.7 Out of scope

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
   line 216 is `fixed bottom-0`. **14 pages carry a hand-written `pb-20`** to
   compensate (stated as 13 during design; the exact count is 14). `Login` and `Register` do not, and are clipped on mobile. The `pb-20`s are
   unconditional rather than `md:pb-0`, so every page also carries 5rem of dead space on
   desktop.

Defect 3 is the pattern worth naming: a layout concern with no home in the layout,
patched thirteen times. The fix is `pb-24 md:pb-6` on `<main>` once, deleting thirteen
workarounds — a net-negative diff that fixes two pages and desktop simultaneously.

### 5.2 Rebuild

The user menu converted to click/tap with focus management and `Escape` to dismiss, so
logged-in destinations are reachable on touch and by keyboard. *(Shipped early — §5.3.)*

*Phase 4 decision — no drawer was built.* This section originally called for
"state-driven mobile navigation that the hamburger actually opens". On inspection there is
nothing left for a drawer to carry: the three public links are already in the fixed
mobile bottom bar, every authenticated destination is in the (now working) user menu, and
登录 / 注册 sit in the header. A drawer would duplicate navigation that is already complete
on mobile.

So the inert button was **removed** rather than wired up. It had an
`aria-label="打开导航"` and no handler, which misrepresented itself to assistive
technology; deleting it removes a control that lied about what it did. If a future
information architecture genuinely needs more mobile navigation than the bottom bar can
hold (see §4.4 on restructuring), a drawer can be added then, with real destinations to
put in it.

`<main>` takes the bottom-bar clearance once, matching the bar's own `md:hidden`, and the
14 per-page `pb-20` workarounds are deleted.

*Three further mobile defects found while implementing (Phase 4b), all correctness rather
than style:*

- The fixed bottom bar sat **underneath the iOS home indicator**. `env()` reports nothing
  without `viewport-fit=cover`, which was missing from the viewport meta. The bar now pads
  by `env(safe-area-inset-bottom)` and `<main>` clears both bar and inset via
  `calc(6rem + env(safe-area-inset-bottom))`.
- Bottom-bar links, the login/register buttons and the avatar trigger were **36–40px**
  tall, below the 44px touch minimum. They are now ≥44px on phones and keep tighter
  desktop sizing above `md`.
- Active navigation was conveyed by **colour alone** in both nav sets. Both now set
  `aria-current="page"`.

*And one in the board panel:* it auto-advanced every five seconds with no way to stop it,
failing **WCAG 2.2.2 (Pause, Stop, Hide)** and ignoring `prefers-reduced-motion`. It now
holds still under reduced motion, pauses on hover or focus, and its indicators are real
buttons, so the board is keyboard-operable.

### 5.2b Destination coverage audit (2026-08-19)

§5.2 argued no drawer was needed because the bottom bar plus the user menu covered every
mobile destination. **Auditing that against the router found it was not true**:
`/moderation` had no link anywhere in the shell, so 版主 could not reach their own queue on
*any* viewport.

Fixed by adding it to the user menu, gated on the role set the **backend actually
enforces** — the moderations router is mounted behind
`RoleChecker([moderator, admin, dev])` — rather than a guessed predicate, so the link never
appears for someone who would be refused. Menu rows and the logout control were also ~36px
and are now ≥44px on phones, since that menu is the only path to five role-gated
destinations there.

With moderation added, the conclusion in §5.2 holds: bottom bar (3 public) + user menu
(5 role-gated + logout) + header (login/register) covers every route. A drawer would still
only duplicate it.

### 5.2c Carousel: WCAG 2.2.2 re-check (2026-08-19)

The earlier claim that the board panel satisfied 2.2.2 was **wrong**. Hover and focus
pausing is a courtesy, not a conforming mechanism: 2.2.2 asks for a control the user can
operate, and a keyboard or touch user cannot "hover away". There is now an explicit
pause/resume button with `aria-pressed`, and auto-advance additionally never starts under
reduced motion.

Related: Framer Motion does **not** honour `prefers-reduced-motion` by default, so every
page fade and list stagger in the app was animating regardless — CSS-driven card lifts
respected it while JS-driven motion did not. Fixed globally with
`<MotionConfig reducedMotion="user">`, plus `usePrefersReducedMotion` for motion we drive
ourselves, which *subscribes* to the query rather than reading it once so a mid-session
change takes effect.

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

### 6.1b Status (Phase 6, as built)

**Done — workflow extraction.** `useActionFeedback` replaces all **twelve** hand-rolled
feedback pairs across seven pages (the count in §6.1 said nine; the exact number is
twelve, six of them in `ClubWorkspace` alone). `Admin`'s local `setResult` helper was
exactly the hook's `report`, so its 27 call sites now route through it via the existing
`RefreshContext` value rather than renaming the context API.

The status→tone table turned out to exist **four** times, not the two §6.1 implies:
`getAuditTone` in `Federation`, an identical `getAuditTone` in `ClubWorkspace`, a local
`AUDIT_TONE` const in `StarLevelApplications`, and the same ternary inlined in
`Moderation`, `GeneralActivityDetail` and `ClubWorkspace`. All now read `lib/tones.ts`.

**Done — `Admin`.** Decomposed along the boundaries its author had already drawn: a
115-line shell plus `context.tsx`, `primitives.tsx` and one file per section, none over
300 lines. A move plus import bookkeeping, no behaviour change.

**Deferred — `Federation` and `ClubWorkspace`.** `ClubWorkspace`'s state surface is
reduced (55 `useState` → 43) as the spec's prerequisite, but the splits themselves are
**not done**, deliberately. Both are single functions of ~1,000+ lines whose sections share
state in ways that are not visible without tracing every setter, and this project has no
test framework by design (§7). Splitting them is the one remaining task where a subtle
break would not be caught by any gate — `tsc`, the build, Gate 1 and Gate 2 all pass
happily through a mis-scoped state variable. It wants a reviewer, not an unattended pass.

**Not done — `AuditQueue`.** The 19 approve/reject sites still each carry their own list
and handler. Extracting a shared component means settling a common shape for six different
endpoints, which is design work rather than mechanical extraction, and it is entangled with
the two deferred splits above.

### 6.1c Decomposition status (2026-08-19)

**`Federation`: 1,313 → 594 lines**, four modules extracted:
`federation/shared.tsx` (view helpers), `federation/starReview.ts` (pure review logic),
`federation/StarApplicationsPanel.tsx` (369), `federation/ClubRecordsPanel.tsx` (251).

The boundaries were established by mapping every state variable against the four concerns
and confirming each group is referenced only inside its own; the loader writes only shared
state and the preview effect reads only star state. Each extraction was verified past the
type checker — dependency arrays compared byte-for-byte, no orphaned identifiers, props
wired — because a mis-scoped hook typechecks perfectly.

**Two concerns remain in `Federation`**: the general-activity editor and the club-activity
request queues. An extraction attempt was **backed out to the last green commit**: it left
an unmoved `deleteActivity` handler, prop renames unapplied inside moved JSX, and a state
range that did not cover everything. Not a boundary problem — the boundaries are sound —
but the mechanical assembly of six discontiguous regions is where scripted surgery stops
being reliable, and a half-correct result is worse than none.

**`Federation`: complete (2026-08-19).** 1,313 → **154** lines: data loading, layout and
four panels. `ActivityEditorPanel`, `StarApplicationsPanel` (369), `ClubRecordsPanel`
(251), `ActivityRequestsPanel` (98), plus `shared.tsx` (218) and `starReview.ts` (75).

What made the difference on the second attempt: **assert every region boundary before
moving anything** — first and last line of each state block, memo, handler run and JSX
block, plus the presence of each named handler — instead of trusting line numbers. And
verify behaviourally afterwards: submitting the create form through the extracted
`ActivityEditorPanel` took the API from 3 activities to 4 and returned the new record, so
the move demonstrably preserved behaviour rather than merely type-checking.

**`ClubWorkspace`: complete (2026-08-19).** 1,225 → **194** lines — data loading, layout
and six sections:

| Module | Lines | Concern |
|---|---|---|
| `ClubWorkspace.tsx` | **194** | shell |
| `ClubActivitiesSection` | 409 | 社团活动申请 |
| `ClubStarApplicationsSection` | 308 | 星级申请 |
| `ClubRecordsSection` | 281 | 综评活动记录 |
| `displaySections` | 120 | load errors, club header, star rating |
| `ClubProfileRequestSection` | 114 | 社团资料变更申请 |
| `helpers` | 42 | `EditorHeader`, `sameStringArray` |

Three rules made this work after two back-outs, and they are the transferable part:

1. **Move each concern's derived values and selection handlers with its state group.**
   A state group is not a concern. 综评活动记录 failed the first time because two memos
   and the form-filling handler stayed behind.
2. **Assert every region boundary before moving** — first and last line of each block,
   and each named handler present — rather than trusting line numbers.
3. **Read types from the file being changed.** `StarLevelApplicationInfo` and
   `StarRatingResponse` were both different from the names they seemed to have.

By the last extraction this produced **zero type errors on the first pass**.

Each extraction was verified behaviourally, not by type check. The most useful lesson
came from getting that wrong: for 社团活动申请 the first check looked for "申请" in the
page text, which is trivially present in the section's own title, so it passed while
nothing had happened — the form was still open with an empty required field silently
blocking submit. Redone by filling every field, asserting `checkValidity()`, submitting
via `requestSubmit()` and then reading the API: `club_activity_create_requests` went
0 → 1. **A verification that cannot fail is not a verification.**

**§6.1's `AuditQueue` is deliberately not built.** The genuinely demonstrated shared
mechanics — the status→tone table and the feedback hook — are extracted and adopted
everywhere. What remains differs per flow: six endpoints with different payloads,
different preview behaviour, and different approval fields. A component parameterised
across all of that would be the over-configurable mega-component this spec should warn
against, so the shared parts are shared and the domain flows stay separate.

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

*Extension (Phase 5).* The gate originally checked only named palette steps, and therefore
reported **zero while five violations were live**: arbitrary values carrying literal
colours, e.g. `shadow-[inset_0_0_0_1.5px_rgba(148,163,184,0.18)]`. These name no palette
step but are the identical defect — a fixed colour no variable can redirect, so it cannot
follow the dark scheme. The gate now checks literal `rgb()`/`rgba()`/`hsl()`/hex inside
arbitrary values too, verified by planting a violation and watching it fail. `drop-shadow`
is exempt: a text halo over user-uploaded posters must stay dark in both schemes to remain
legible.

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

**Automated portion (2026-08-19).** `scripts/check-scheme-contrast.mjs` reads the built CSS
and asserts the two parts of this matrix that do not need eyes, being the two most likely
to be got wrong quietly:

- **Scheme completeness** — every semantic token defined in *both* schemes. A token defined
  only in `:root` keeps its light value on a dark surface, which looks deliberate.
  Currently 88/88.
- **Asserted contrast** — 30 foreground/background pairs the system relies on, at 4.5:1 for
  text and 3:1 for non-text, in both schemes.

It found a failure that predates this branch on first run: white on the brand teal is
**2.49:1**, so the primary action of every form failed WCAG 1.4.3. Fixed by darkening the
text rather than the fill (`#042f2e` on `#14b8a6` = 5.81:1), which keeps the vivid teal the
direction is built on and matches what dark mode already did. Hover therefore brightens
rather than darkens. `--brand-strong` was added for thin non-text accents and all focus
rings, since the vivid teal is below the 3:1 that 1.4.11 asks of focus indicators.

It runs in `npm run verify` and CI. It cannot tell you how the type sits, how PingFang
renders a heading, whether the gold reads as an honour, or how the offsets look on an OLED
phone.

Gate 4's human portion covers:

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

*Progress is recorded in §1.4 below.*

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

## 8b. API additions (2026-08-19)

The A+B layout needed two things the API could not provide. Both are additive; the
existing endpoints are unchanged.

**`GET /api/v1/moderations/summary`** — pending counts per queue, plus a total.
The four moderation list endpoints take only `page`/`size`, with **no status
filter**, so a navigation badge otherwise meant fetching all four full lists on
every page load; `Page.total` cannot help because it counts every request rather
than the pending ones. Explicit `ModerationPendingSummary` response model. Counts
come from `SELECT count()` per repository, not from loading rows. Authorization is
inherited from the parent router's existing
`RoleChecker([moderator, admin, dev])`, so nothing new is exposed — verified 401
anonymous, 403 for a plain user, correct counts for an admin.

Deliberately narrow: only the counts the UI renders. Not a statistics endpoint, and
no change to how any queue is read or moderated.

**`GET /api/v1/clubs/summary`** — the card/list representation. `ClubInfo` embeds
`members`, `club_activities` and `general_activity_records`, so a browse grid
downloaded every member of every club to render a count — and the 展板 wall shows
more cards at once than the old list did. `ClubSummaryInfo` carries the card fields
plus `member_count`.

A separate path rather than a `?view=` switch, so each operation has one response
model and the generated client gets exact types instead of a union. Declared before
`/{club_id}`, which takes an `int` and would otherwise reject `"summary"` as an
invalid id.

`member_count` is a **correlated scalar subquery** applied through `apaginate`'s
`transformer` hook. Verified against SQL ground truth (13/1/6/1/1/1) and by
`EXPLAIN ANALYZE`: `SubPlan → Aggregate → Bitmap Heap Scan` with
`Recheck Cond: (club_id = clubs.id)`. Postgres aggregates and returns one integer
per row; no member rows reach Python. It is one indexed subplan per club row,
bounded by page size.

`member_count` counts **all** membership rows, matching what clients previously
computed from `len(members)`. Narrowing it to active members would change a number
already shown in the product, so that stays a separate decision.

The OpenAPI client is regenerated from the live spec and a `generate:api` script
records the invocation.

## 10b. Layout restructure — A+B (2026-08-19)

Phases 0–7 changed the design system and deliberately preserved the layout. This phase
changed the layout, after three working prototypes were built as dev-only routes and the
hybrid was chosen from screens rather than descriptions.

**Shell — rail + drawer.** A persistent 240px navigation rail replaces the topbar. Nine
destinations across six roles were previously three links plus five hidden in an avatar
dropdown, with `/moderation` in neither. One `nav.ts` definition renders as the rail on
desktop and inside the drawer on mobile, so the two cannot drift; role predicates mirror
what the backend enforces. The mobile bottom bar is gone — it could hold three of nine —
and the hamburger returns with something real to open. `main` is a bare flex container so
master–detail pages can fill it; the standard pages carry their own container.

Verified by walking **every role** against real `/users/me` responses, which found that a
banned account saw the same rail as a normal user: it holds a valid token but `/users/me`
answers 403, so authenticated items keyed off the token alone. Those items now require a
resolved profile, while the footer still keys off the token so 退出登录 stays reachable.

**Home — the 展板 wall.** One scannable masonry surface of posted things: poster tile at
poster proportions, notices slip, club cards with category spine and gold rank, activity
tiles, month grid. CSS columns rather than a grid, so tiles of different heights pack.

**Explore and 审核台 — master–detail.** List and item side by side, selection in the query
string so it is linkable and survives reload; single pane below `xl`. For the moderation
queues this replaced a stack of fully expanded request cards, and it is where the shape
pays off most.

Clicking through 审核台 for real found two feedback bugs, one of them pre-existing and
significant: `fetchQueue()` began with `action.clear()` and `moderate()` calls it on
success, so **moderators had never received confirmation that an approval landed.**

**Pages verified after the restructure:** all 14 routes render with the rail and no
crashes, in light and dark, at 1512px and 390px/2×.

## 8c. Release checklist (2026-08-19)

Decisions taken for this release, recorded so they are not relitigated:

- [ ] **Gate 4 real-device pass.** Typography, CJK rendering, gold/contrast, hard-offset
      elevation and responsive behaviour on real macOS / Windows / iOS / Android in both
      schemes. `/_dev/specimen` puts the whole system on one page. **No further
      speculative visual tweaks are to be made in a dev environment** — this is a
      device-verification task, not a design task.
- [x] **Upstream security fix integrated.** §1.1b. Both fixes present via the parent
      merge; migrations applied including `c3d9f1a2b7e4` and upstream's `e1a4b6c8d0f2`
      head merge.
- [x] **Critical paths re-verified after integration.** Application submit and moderation
      approve, both through the UI against the live API — see §8d.
- [x] **`member_count` semantics unchanged.** It still counts all membership rows, matching
      what clients previously computed from `len(members)`. Switching to active-members-only
      is a product/data-semantics change and is explicitly **out of scope for this
      release**; handle it separately.

## 8d. Critical-path verification after integration (2026-08-19)

**Application submit** — a non-member on `/club/4` presses 加入社团: the prompt collects a
message, the request POSTs to `/clubs/{club_id}/membership-requests`, 「加入申请已提交」
renders, the button stops offering to join, and the backend shows the request pending with
its message against the right applicant. Verified at both API and UI level.

**Moderation approve** — on `/moderation`, selecting a pending 社团资料 request and pressing
通过 took `club_update_requests` 1 → 0 and the total 1 → 0, the item left the queue, the
detail pane fell back to its empty state, and **「操作已完成」 stayed visible**.

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
