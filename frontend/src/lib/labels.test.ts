import assert from "node:assert/strict";
import test from "node:test";

import { ROLE_MAP, ROLE_OPTIONS } from "./labels.ts";

test("the moderator role is consistently labeled as reviewer", () => {
  assert.equal(ROLE_MAP.moderator, "审核员");
  assert.equal(ROLE_OPTIONS.find((option) => option.value === "moderator")?.label, "审核员");
});
