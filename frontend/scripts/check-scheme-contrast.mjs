#!/usr/bin/env node
/**
 * Gate 4, the automatable part.
 *
 * The Gate 4 matrix in the design spec is a human review across platforms and
 * schemes, and most of it genuinely needs eyes on a device. Two parts of it do
 * not, and those are exactly the parts most likely to be got wrong quietly:
 *
 *   1. Every semantic token must be defined in BOTH schemes. A token defined only
 *      in :root silently keeps its light value on a dark surface, which looks
 *      deliberate and is not.
 *   2. Foreground/background pairs the design system actually asserts must meet
 *      their contrast threshold in both schemes — 4.5:1 for text, 3:1 for
 *      non-text (WCAG 1.4.3 and 1.4.11).
 *
 * This reads the built CSS rather than the source, so it checks the values that
 * ship, including anything the build resolves differently than the source implies.
 *
 * What it cannot tell you: whether the type sits well, whether the gold reads as
 * an honour, how PingFang renders a heading, whether the offsets look right on an
 * OLED phone. That remains a human pass.
 */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const css = readdirSync("dist/assets")
  .filter((f) => f.endsWith(".css"))
  .map((f) => readFileSync(join("dist/assets", f), "utf8"))
  .join("\n");

/** Pull `--name: value` pairs out of a block of declarations. */
function vars(block) {
  const out = {};
  for (const m of block.matchAll(/--([a-z0-9-]+)\s*:\s*([^;}]+)/g)) {
    out[m[1]] = m[2].trim();
  }
  return out;
}

function blockAfter(marker) {
  const i = css.indexOf(marker);
  if (i < 0) return "";
  const open = css.indexOf("{", i);
  let depth = 0;
  for (let j = open; j < css.length; j++) {
    if (css[j] === "{") depth++;
    else if (css[j] === "}" && --depth === 0) return css.slice(open, j);
  }
  return "";
}

/**
 * Everything before the dark override, then the dark override itself.
 *
 * The dark block used to be a `prefers-color-scheme` media query and is now
 * `:root.dark`, since a media query cannot be overridden by an explicit user
 * choice. Assert the marker rather than letting a miss fall through: `blockAfter`
 * answers "" for an absent marker, and a slice on indexOf's -1 would silently
 * fold the dark values into the light set and check one scheme twice.
 */
const DARK_SELECTOR = ":root.dark";
if (!css.includes(DARK_SELECTOR)) {
  console.error(
    `gate4a: no \`${DARK_SELECTOR}\` block in the built CSS. If the dark-scheme ` +
      "selector was renamed, update DARK_SELECTOR here in the same commit.",
  );
  process.exit(1);
}
const darkBlock = blockAfter(DARK_SELECTOR);
const lightBlock = css.slice(0, css.indexOf(DARK_SELECTOR));

const light = vars(lightBlock);
const dark = vars(darkBlock);

let failures = 0;

// ---- 1. every semantic token defined in both schemes ------------------------
const SEMANTIC = /^(surface|content|edge|brand|tone|category|level|star|accent|shadow-ink)/;
const semanticLight = Object.keys(light).filter((k) => SEMANTIC.test(k));
const missingInDark = semanticLight.filter((k) => !(k in dark));

console.log(
  `gate4a: ${semanticLight.length} semantic tokens in the light scheme, ${
    Object.keys(dark).filter((k) => SEMANTIC.test(k)).length
  } overridden in dark`,
);
if (missingInDark.length) {
  console.error(
    `\ngate4a FAILED — defined only for light, so these keep a light value on dark surfaces:\n`,
  );
  for (const k of missingInDark) console.error(`  --${k}: ${light[k]}`);
  failures++;
} else {
  console.log("gate4a: OK — every semantic token has a dark value");
}

// ---- 2. asserted contrast pairs ---------------------------------------------
function srgb(c) {
  const v = c / 255;
  return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}
function luminance(hex) {
  const h = hex.replace("#", "").trim();
  if (![3, 6, 8].includes(h.length)) return null;
  const full =
    h.length === 3
      ? h
          .split("")
          .map((x) => x + x)
          .join("")
      : h.slice(0, 6);
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
  return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b);
}
function ratio(fg, bg) {
  const a = luminance(fg);
  const b = luminance(bg);
  if (a == null || b == null) return null;
  const [hi, lo] = a > b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}

/** [foreground, background, minimum, description] */
const PAIRS = [
  ["content", "surface", 4.5, "body text on a panel"],
  ["content", "surface-sunken", 4.5, "body text on the page"],
  ["content-muted", "surface", 4.5, "secondary text on a panel"],
  ["content-muted", "surface-sunken", 4.5, "secondary text on the page"],
  ["brand-on", "brand", 4.5, "text on a brand fill"],
  ["brand-on", "brand-hover", 4.5, "text on a hovered brand fill"],
  ["brand-strong", "surface", 3.0, "focus ring / thin accent on a panel"],
  ["brand-strong", "surface-sunken", 3.0, "focus ring / thin accent on the page"],
  ["content-on-inverted", "surface-inverted", 4.5, "text on the inverted surface"],
  ["star-text", "star-bg", 4.5, "star level label"],
  ["star-earned", "star-bg", 3.0, "earned star glyph"],
  ["star-unearned", "star-bg", 3.0, "unearned star outline"],
  ["star-seal", "star-bg", 3.0, "honorary seal"],
  ...["neutral", "brand", "info", "success", "warning", "danger"].map((t) => [
    `tone-${t}-fg`,
    `tone-${t}-bg`,
    4.5,
    `${t} tone text`,
  ]),
  ...[
    "science",
    "humanity",
    "arts",
    "sports",
    "business",
    "charity",
    "campus",
    "other",
  ].map((c) => [`category-${c}-fg`, `category-${c}-bg`, 4.5, `${c} category chip`]),
  ...["school", "large", "federation"].map((l) => [
    `level-${l}-fg`,
    `level-${l}-bg`,
    4.5,
    `${l} level chip`,
  ]),
];

for (const [schemeName, scheme] of [
  ["light", light],
  ["dark", dark],
]) {
  const bad = [];
  let checked = 0;
  for (const [fg, bg, min, what] of PAIRS) {
    const f = scheme[fg];
    const b = scheme[bg];
    if (!f || !b) continue;
    const r = ratio(f, b);
    if (r == null) continue;
    checked++;
    if (r < min) bad.push({ what, fg, bg, r, min, f, b });
  }
  console.log(`gate4b/${schemeName}: ${checked} asserted pairs checked`);
  if (bad.length) {
    console.error(`\ngate4b/${schemeName} FAILED:\n`);
    for (const x of bad) {
      console.error(
        `  ${x.what}: --${x.fg} (${x.f}) on --${x.bg} (${x.b}) = ${x.r.toFixed(2)}:1, need ${x.min}`,
      );
    }
    failures++;
  } else {
    console.log(`gate4b/${schemeName}: OK — every asserted pair meets its threshold`);
  }
}

if (failures) process.exit(1);
console.log(
  "\ngate4: OK. This covers scheme completeness and asserted contrast only —\n" +
    "type rendering, CJK metrics and the platform matrix still need a human pass.",
);
