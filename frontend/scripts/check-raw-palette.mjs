#!/usr/bin/env node
/**
 * Gate 2 — forbidden raw-palette check.
 *
 * Application code should style with semantic tokens (bg-surface,
 * text-content-muted, border-edge), not raw Tailwind palette steps
 * (bg-slate-50, text-red-700). Raw steps are fixed values that no variable can
 * redirect, so every one of them is a hole in the dark scheme.
 *
 * The 502 raw utilities this project started with accumulated one
 * reasonable-looking line at a time, so this ran as a ratchet during the sweep:
 * fail if the count goes up, lower BASELINE as it drops.
 *
 * The sweep is complete and BASELINE is 0, so this is now a ban: any raw palette
 * step reintroduced into src/ fails CI. If one is ever genuinely justified, add
 * the file to ALLOWLIST with a comment saying why, rather than raising BASELINE.
 *
 * It checks two shapes: named palette steps (bg-slate-50) and literal colours
 * inside arbitrary values (shadow-[...rgba(...)], bg-[#14b8a6]). The second was
 * added after five rgba-bearing arbitrary shadows were found by hand, having
 * passed a gate that reported zero.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, extname } from "node:path";

/**
 * Permitted raw-palette utilities. The sweep is complete, so this is 0 and must
 * stay 0. Never raise it.
 */
const BASELINE = 0;

const SRC = "src";

const PALETTE = [
  "slate",
  "gray",
  "zinc",
  "neutral",
  "stone",
  "red",
  "orange",
  "amber",
  "yellow",
  "lime",
  "green",
  "emerald",
  "teal",
  "cyan",
  "sky",
  "blue",
  "indigo",
  "violet",
  "purple",
  "fuchsia",
  "pink",
  "rose",
];

const PROPERTIES =
  "bg|text|border|border-t|border-r|border-b|border-l|border-x|border-y|ring|outline|divide|shadow|fill|stroke|decoration|accent|caret|placeholder|from|via|to";

const pattern = new RegExp(
  String.raw`\b(?:${PROPERTIES})-(?:${PALETTE.join("|")})-\d{2,3}\b`,
  "g",
);

/**
 * Literal colours inside arbitrary values, e.g.
 * `shadow-[inset_0_0_0_1.5px_rgba(148,163,184,0.18)]` or `bg-[#14b8a6]`.
 *
 * These slipped past the palette check entirely — they name no palette step — while
 * being exactly the same defect: a fixed colour that no variable can redirect, so
 * it cannot follow the dark scheme. Five of them were found by hand in arbitrary
 * shadow values after the sweep had supposedly reached zero.
 *
 * `drop-shadow` is exempt: a text halo over user-uploaded imagery has to stay dark
 * in both schemes to keep the text legible, so a literal there is correct.
 */
const literalColorPattern =
  /(?<![\w-])(?!drop-shadow)[a-z-]+-\[[^\]]*(?:rgba?\(|#[0-9a-fA-F]{3,8}|hsla?\()[^\]]*\]/g;

/**
 * Files exempt from the ratchet. The specimen page renders raw palette swatches
 * on purpose, to show what the tokens are built from.
 */
const ALLOWLIST = [join("src", "dev", "Specimen.tsx")];

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if ([".ts", ".tsx", ".css", ".js", ".jsx"].includes(extname(p)))
      out.push(p);
  }
  return out;
}

const perFile = [];
let total = 0;

for (const file of walk(SRC)) {
  if (ALLOWLIST.includes(file)) continue;
  const text = readFileSync(file, "utf8");
  const hits =
    (text.match(pattern) ?? []).length +
    (text.match(literalColorPattern) ?? []).length;
  if (hits > 0) {
    perFile.push({ file, hits });
    total += hits;
  }
}

perFile.sort((a, b) => b.hits - a.hits);

console.log(`gate2: ${total} raw-palette utilities (baseline ${BASELINE})`);
for (const { file, hits } of perFile) {
  console.log(`  ${String(hits).padStart(4)}  ${file}`);
}

if (total > BASELINE) {
  console.error(
    `\ngate2 FAILED — raw-palette usage rose from ${BASELINE} to ${total}.` +
      `\nStyle with semantic tokens instead; a raw palette step cannot follow the` +
      `\ndark scheme.\n`,
  );
  process.exit(1);
}

if (total < BASELINE) {
  console.log(
    `gate2: OK — ${BASELINE - total} fewer than baseline. Lower BASELINE to ${total} in ${import.meta.url
      .split("/")
      .pop()}.`,
  );
} else {
  console.log("gate2: OK — no increase");
}
