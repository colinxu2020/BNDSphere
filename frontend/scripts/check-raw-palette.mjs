#!/usr/bin/env node
/**
 * Gate 2 — forbidden raw-palette check.
 *
 * Application code should style with semantic tokens (bg-surface,
 * text-content-muted, border-edge), not raw Tailwind palette steps
 * (bg-slate-50, text-red-700). Raw steps are fixed values that no variable can
 * redirect, so every one of them is a hole in the dark scheme.
 *
 * The 500 raw utilities this project started with accumulated one
 * reasonable-looking line at a time, so this runs as a ratchet: it fails if the
 * count goes UP. During the semantic sweep, lower BASELINE as it drops. When the
 * sweep is finished BASELINE becomes 0 and the ratchet turns into a ban.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, extname } from "node:path";

/**
 * Remaining raw-palette utilities. Lower this as the sweep progresses; never
 * raise it. 0 once the sweep is complete.
 */
const BASELINE = 324;

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
  const hits = (readFileSync(file, "utf8").match(pattern) ?? []).length;
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
