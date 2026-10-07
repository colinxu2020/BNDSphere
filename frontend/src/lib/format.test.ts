import assert from "node:assert/strict";
import test from "node:test";

import { stringifyBackendValue } from "./format.ts";

test("untrusted browser origin errors have a Chinese message", () => {
  const message = "请求来源校验失败，请从本站页面重试";
  assert.equal(
    stringifyBackendValue({
      error_code: "UNTRUSTED_ORIGIN",
      message_key: "error.auth.untrusted_origin",
      details: {},
    }),
    message,
  );
  assert.equal(stringifyBackendValue({ error_code: "UNTRUSTED_ORIGIN" }), message);
  assert.equal(stringifyBackendValue({ message_key: "error.auth.untrusted_origin" }), message);
});
