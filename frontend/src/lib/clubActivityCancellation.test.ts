import assert from "node:assert/strict";
import test from "node:test";
import { canCancelClubActivity } from "./clubActivityCancellation.ts";

const now = new Date("2026-09-29T12:00:00Z");

test("only an upcoming uncancelled activity can be cancelled", () => {
  assert.equal(
    canCancelClubActivity({ start_time: "2026-09-30T12:00:00Z", cancelled_at: null }, now),
    true,
  );
  assert.equal(
    canCancelClubActivity({ start_time: "2026-09-29T12:00:00Z", cancelled_at: null }, now),
    false,
  );
  assert.equal(
    canCancelClubActivity(
      { start_time: "2026-09-30T12:00:00Z", cancelled_at: "2026-09-28T12:00:00Z" },
      now,
    ),
    false,
  );
});
