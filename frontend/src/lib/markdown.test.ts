import assert from "node:assert/strict";
import test from "node:test";
import type { Element, Root } from "hast";
import { visit } from "unist-util-visit";
import { markdownLengthError, rehypeSanitizeWithFragments } from "./markdown.ts";

function sanitizeLinks(ids: string[], hrefs: string[], namespace = "test") {
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
  const result = rehypeSanitizeWithFragments(namespace)(tree);
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
    "user-content-test-hello",
    "user-content-test-user-content-fn-1",
    "user-content-test-user-content-fnref-1",
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
    `#user-content-test-${fragment}`,
    "#missing",
    "#invalid%",
    "https://example.com/#hello",
  ]);
});

test("fragment rewriting retains sanitization and DOM clobbering protection", () => {
  const { links, targets } = sanitizeLinks(["location"], ["#location", "javascript:alert(1)"]);
  assert.deepEqual(targets, ["user-content-test-location"]);
  assert.deepEqual(links, ["#user-content-test-location", undefined]);
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
  const result = rehypeSanitizeWithFragments("test")(tree);
  assert.deepEqual(result.children, [
    { type: "element", tagName: "img", properties: { src: "x" }, children: [] },
  ]);
});

test("formatting that crosses either description limit is invalid until shortened", () => {
  for (const limit of [400, 4000]) {
    const value = "字".repeat(limit);
    assert.equal(markdownLengthError(value, limit), null);
    assert.ok(markdownLengthError(`**${value}**`, limit));
    assert.equal(markdownLengthError("", limit), null);
  }
});

test("identical headings and footnotes have separate targets in each namespace", () => {
  const ids = ["社团介绍", "user-content-fn-1", "user-content-fnref-1"];
  const hrefs = ids.map((id) => `#${encodeURIComponent(id)}`);
  const first = sanitizeLinks(ids, hrefs, "first");
  const second = sanitizeLinks(ids, hrefs, "second");
  assert.ok(first.targets.every((id) => !second.targets.includes(id)));
  for (const result of [first, second]) {
    assert.deepEqual(
      result.links.map((href) => decodeURIComponent(href!.slice(1))),
      result.targets,
    );
  }
});

test("accessible descriptions and labels use the same namespace as their targets", () => {
  const tree: Root = {
    type: "root",
    children: [
      { type: "element", tagName: "h2", properties: { id: "footnote-label" }, children: [] },
      {
        type: "element",
        tagName: "a",
        properties: {
          id: "user-content-fnref-1",
          ariaDescribedBy: ["footnote-label"],
          ariaLabelledBy: ["footnote-label"],
        },
        children: [],
      },
    ],
  };
  const result = rehypeSanitizeWithFragments("instance")(tree);
  const label = result.children[0] as Element;
  const link = result.children[1] as Element;
  assert.equal(label.properties.id, "user-content-instance-footnote-label");
  assert.deepEqual(link.properties.ariaDescribedBy, [label.properties.id]);
  assert.deepEqual(link.properties.ariaLabelledBy, [label.properties.id]);
});
