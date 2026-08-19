#!/usr/bin/env node
/**
 * Gate 1 — compiled-CSS validation of the design-token utility contract.
 *
 * Tailwind emits nothing for a utility that references an undefined theme value,
 * and does not warn. That is how `text-primary-700` and `border-secondary-100`
 * shipped as silent no-ops: plausible class, clean build, no colour.
 *
 * This checks the narrow contract we actually own: every statically-written
 * utility in the source that depends on one of OUR token namespaces must appear
 * as a real selector in the built CSS.
 *
 * Deliberately NOT a general Tailwind parser. Tailwind scans source as text and
 * discards candidates it cannot map to a utility; dynamic class construction and
 * arbitrary/escaped variants make a universal source-to-selector comparison much
 * harder than it looks. Scoping to our namespaces keeps the check honest: within
 * this scope a missing selector is always a real defect, never a parser gap.
 *
 * Run after `vite build`.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, extname } from "node:path";

const SRC = "src";
const DIST_ASSETS = "dist/assets";

/**
 * Token namespaces this project defines in index.css, split by whether the
 * namespace alone is a complete utility.
 *
 * `bg-surface` and `text-content` are valid on their own; `tone` and `cat` never
 * are, and neither is a bare `primary`/`secondary` without a step. Requiring a
 * suffix for the second group keeps prose out of the results — "Status-to-tone
 * mapping" in a comment would otherwise be read as the utility `to-tone`.
 */
const NAMESPACES_STANDALONE = ["surface", "content", "edge", "brand"];
const NAMESPACES_SUFFIXED = ["primary", "secondary", "tone", "category", "level", "star", "accent"];

// NOTE: these two lists are the gate's entire scope. When a token family is added
// or renamed, add it here in the same commit — renaming `cat` to `category` once
// silently dropped 32 utilities from the check while every gate still reported OK.

/** Utility prefixes that resolve against a colour token. */
const PROPERTIES = [
  "bg",
  "text",
  "border",
  "border-t",
  "border-r",
  "border-b",
  "border-l",
  "border-x",
  "border-y",
  "ring",
  "outline",
  "divide",
  "shadow",
  "fill",
  "stroke",
  "decoration",
  "accent",
  "caret",
  "placeholder",
  "from",
  "via",
  "to",
];

const candidatePattern = new RegExp(
  // optional variant chain (hover:, md:, group-hover:, dark:, ...)
  String.raw`((?:[a-z][a-z0-9-]*:)*)` +
    // property prefix
    String.raw`(${PROPERTIES.join("|")})-` +
    // our namespace, plus any token path segments
    String.raw`((?:(?:${NAMESPACES_STANDALONE.join("|")})(?:-[a-z0-9]+)*` +
    String.raw`|(?:${NAMESPACES_SUFFIXED.join("|")})(?:-[a-z0-9]+)+))` +
    // optional /opacity modifier
    String.raw`(\/\d{1,3})?`,
  "g",
);

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if ([".ts", ".tsx", ".css", ".js", ".jsx"].includes(extname(p))) out.push(p);
  }
  return out;
}

/** Tailwind escapes `:` and `/` when turning a class name into a selector. */
function toSelector(cls) {
  return "." + cls.replace(/[:/]/g, (ch) => "\\" + ch);
}

const cssFiles = readdirSync(DIST_ASSETS).filter((f) => f.endsWith(".css"));
if (cssFiles.length === 0) {
  console.error("gate1: no CSS found in dist/assets — run `vite build` before this check");
  process.exit(2);
}
const css = cssFiles.map((f) => readFileSync(join(DIST_ASSETS, f), "utf8")).join("\n");

const found = new Map(); // class -> Set of "file:line"
for (const file of walk(SRC)) {
  const lines = readFileSync(file, "utf8").split("\n");
  lines.forEach((line, i) => {
    for (const m of line.matchAll(candidatePattern)) {
      const cls = m[0];
      if (!found.has(cls)) found.set(cls, new Set());
      found.get(cls).add(`${file}:${i + 1}`);
    }
  });
}

const missing = [];
for (const [cls, sites] of found) {
  if (!css.includes(toSelector(cls))) missing.push({ cls, sites: [...sites] });
}

console.log(
  `gate1: checked ${found.size} token-dependent utilities against ${cssFiles.join(", ")}`,
);

if (missing.length > 0) {
  console.error(`\ngate1 FAILED — ${missing.length} utility/utilities produce no CSS rule:\n`);
  for (const { cls, sites } of missing.sort((a, b) => a.cls.localeCompare(b.cls))) {
    console.error(`  ${cls}`);
    for (const s of sites) console.error(`      ${s}`);
  }
  console.error(
    "\nThe referenced token step is not defined in index.css, so Tailwind emitted" +
      "\nnothing and the element silently has no colour. Define the token or fix" +
      "\nthe class name.\n",
  );
  process.exit(1);
}

console.log("gate1: OK — every token-dependent utility resolves to a real rule");
