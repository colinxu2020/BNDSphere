import assert from "node:assert/strict";
import test from "node:test";
import { canCancelClubActivity, countCurrentTermActivities } from "./clubActivityCancellation.ts";

test("uncancelled activities remain reachable regardless of the device clock", () => {
  assert.equal(canCancelClubActivity({ cancelled_at: null }), true);
  assert.equal(canCancelClubActivity({ cancelled_at: "2026-09-28T12:00:00Z" }), false);
});

test("public and workspace totals exclude cancelled and other-term activities", () => {
  assert.equal(
    countCurrentTermActivities([
      { cancelled_at: null, academic_term: { is_current: true } },
      { cancelled_at: "2026-10-01", academic_term: { is_current: true } },
      { cancelled_at: null, academic_term: { is_current: false } },
    ]),
    1,
  );
});
