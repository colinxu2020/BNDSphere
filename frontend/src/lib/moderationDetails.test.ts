import assert from "node:assert/strict";
import test from "node:test";
import { moderationDetails } from "./moderationDetails.ts";

test("explicit clears remain visible while untouched fields are omitted", () => {
  assert.deepEqual(
    moderationDetails(
      ["avatar_uri", "description", "grade"],
      [
        ["username", "用户名", "unchanged"],
        ["avatar_uri", "头像", null],
        ["description", "简介", ""],
        ["grade", "年级", null],
      ],
    ),
    [
      ["头像", "清空"],
      ["简介", "清空"],
      ["年级", "清空"],
    ],
  );
});

test("legacy requests match the backend non-null fallback", () => {
  for (const fields of [undefined, []]) {
    assert.deepEqual(
      moderationDetails(fields, [
        ["avatar_uri", "头像", null],
        ["description", "简介", ""],
        ["username", "用户名", "new-name"],
      ]),
      [
        ["简介", "清空"],
        ["用户名", "new-name"],
      ],
    );
  }
});

test("localized grade and club fields preserve their display values", () => {
  assert.deepEqual(moderationDetails(["grade"], [["grade", "年级", "高一"]]), [["年级", "高一"]]);
  assert.deepEqual(
    moderationDetails(undefined, [
      ["summary", "简介", ""],
      ["logo_uri", "Logo", null],
    ]),
    [["简介", "清空"]],
  );
});
