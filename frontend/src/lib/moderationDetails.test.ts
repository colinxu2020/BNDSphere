import assert from "node:assert/strict";
import test from "node:test";
import { moderationDetails } from "./moderationDetails.ts";

test("club logo and activity image clears remain distinct from untouched fields", () => {
  assert.deepEqual(
    moderationDetails(
      ["logo_uri"],
      [
        ["summary", "简介", null],
        ["logo_uri", "Logo", null],
      ],
    ),
    [["Logo", "清空"]],
  );
  assert.deepEqual(
    moderationDetails(
      ["picture_urls"],
      [
        ["name", "名称", null],
        ["picture_urls", "图片", [].join("\n")],
      ],
    ),
    [["图片", "清空"]],
  );
});

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
