import assert from "node:assert/strict";
import test from "node:test";

import { changedRequiredText } from "./clubActivityUpdate.ts";

test("a cleared required activity field is sent as an empty string", () => {
  assert.equal(changedRequiredText("   ", "Original value"), "");
});

test("a changed required activity field is trimmed", () => {
  assert.equal(changedRequiredText("  New value  ", "Original value"), "New value");
});

test("an unchanged required activity field is omitted", () => {
  assert.equal(changedRequiredText("Original value", "Original value"), undefined);
});
