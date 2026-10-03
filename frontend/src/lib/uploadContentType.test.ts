import assert from "node:assert/strict";
import test from "node:test";
import { uploadContentType } from "./uploadContentType.ts";

test("JPEG files without a browser MIME type retain an uploadable content type", () => {
  const file = new File([new Uint8Array([0xff, 0xd8, 0xff])], "活动.JPG");
  assert.equal(uploadContentType(file), "image/jpeg");
});

test("generic MIME falls back only for supported image extensions", () => {
  for (const [name, expected] of [
    ["photo.jpeg", "image/jpeg"],
    ["photo.png", "image/png"],
    ["photo.webp", "image/webp"],
    ["photo.gif", "application/octet-stream"],
    ["photo.jpg.exe", "application/octet-stream"],
    ["photo", "application/octet-stream"],
  ]) {
    assert.equal(uploadContentType({ name, type: "application/octet-stream" }), expected);
  }
});

test("an explicit MIME type is preserved rather than overwritten by the filename", () => {
  assert.equal(uploadContentType({ name: "photo.jpg", type: "text/plain" }), "text/plain");
  assert.equal(uploadContentType({ name: "photo.webp", type: "image/webp" }), "image/webp");
  assert.equal(
    uploadContentType({ name: "proof.pdf", type: "application/pdf" }),
    "application/pdf",
  );
});

test("unrecognized files with empty MIME retain the generic fallback", () => {
  assert.equal(uploadContentType({ name: "archive.bin", type: "" }), "application/octet-stream");
});
