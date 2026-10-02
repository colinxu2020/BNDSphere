import assert from "node:assert/strict";
import test from "node:test";
import type { Element, Root } from "hast";
import { visit } from "unist-util-visit";
import { rehypeSanitizeWithFragments } from "./markdown.ts";

function sanitizeLinks(ids: string[], hrefs: string[]) {
  const tree: Root = {
    type: "root",
    children: [
      ...ids.map((id): Element => ({
        type: "element",
        tagName: "h2",
        properties: { id },
        children: [],
      })),
      ...hrefs.map((href): Element => ({
        type: "element",
        tagName: "a",
        properties: { href },
        children: [],
      })),
    ],
  };
  const result = rehypeSanitizeWithFragments()(tree);
  const links: (string | undefined)[] = [];
  const targets: string[] = [];
  visit(result, "element", (node) => {
    if (node.tagName === "a") links.push(node.properties.href as string | undefined);
    if (node.properties.id) targets.push(String(node.properties.id));
  });
  return { links, targets };
}

test("heading and footnote links follow sanitized IDs, including existing prefixes", () => {
  const { links, targets } = sanitizeLinks(
    ["hello", "user-content-fn-1", "user-content-fnref-1"],
    ["#hello", "#user-content-fn-1", "#user-content-fnref-1"],
  );
  assert.deepEqual(targets, [
    "user-content-hello",
    "user-content-user-content-fn-1",
    "user-content-user-content-fnref-1",
  ]);
  assert.deepEqual(
    links,
    targets.map((id) => `#${id}`),
  );
});

test("encoded Chinese fragments resolve while external and missing targets stay intact", () => {
  const fragment = encodeURIComponent("社团介绍");
  const { links } = sanitizeLinks(
    ["社团介绍"],
    [`#${fragment}`, "#missing", "#invalid%", "https://example.com/#hello"],
  );
  assert.deepEqual(links, [
    `#user-content-${fragment}`,
    "#missing",
    "#invalid%",
    "https://example.com/#hello",
  ]);
});

test("fragment rewriting retains sanitization and DOM clobbering protection", () => {
  const { links, targets } = sanitizeLinks(["location"], ["#location", "javascript:alert(1)"]);
  assert.deepEqual(targets, ["user-content-location"]);
  assert.deepEqual(links, ["#user-content-location", undefined]);
  const tree: Root = {
    type: "root",
    children: [
      { type: "element", tagName: "script", properties: {}, children: [] },
      {
        type: "element",
        tagName: "img",
        properties: { src: "x", onError: "alert(1)" },
        children: [],
      },
    ],
  };
  const result = rehypeSanitizeWithFragments()(tree);
  assert.deepEqual(result.children, [
    { type: "element", tagName: "img", properties: { src: "x" }, children: [] },
  ]);
});
