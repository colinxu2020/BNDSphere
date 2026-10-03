import assert from "node:assert/strict";
import test from "node:test";

import { formatWorkspaceLoadErrors } from "./workspaceErrors.ts";

test("workspace load errors use localized section labels and messages", () => {
  assert.deepEqual(
    formatWorkspaceLoadErrors({
      club: { error_code: "CLUB_NOT_FOUND" },
      workspace: { error_code: "UNKNOWN_INTERNAL_CODE" },
    }),
    [
      { key: "club", text: "社团信息：没有找到这个社团" },
      { key: "workspace", text: "工作台：操作没有完成，请稍后重试" },
    ],
  );
});

test("unknown workspace keys and backend identifiers are not exposed", () => {
  const entries = formatWorkspaceLoadErrors({
    internalBucket: { message_key: "error.unknown.internal" },
  });

  assert.deepEqual(entries, [
    { key: "internalBucket", text: "其他内容：操作没有完成，请稍后重试" },
  ]);
  assert.equal(entries[0]?.text.includes("internalBucket"), false);
  assert.equal(entries[0]?.text.includes("error.unknown.internal"), false);
});

test("workspace errors without a readable message are omitted", () => {
  assert.deepEqual(formatWorkspaceLoadErrors({ club: null }), []);
});
