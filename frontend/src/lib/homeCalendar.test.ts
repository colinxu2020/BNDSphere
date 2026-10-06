import assert from "node:assert/strict";
import test from "node:test";
import { buildMonthCalendar } from "./homeCalendar.ts";

const today = new Date(2026, 9, 10);

test("cancelled club activities leave no scheduled calendar dot or tooltip", () => {
  const calendar = buildMonthCalendar(
    [],
    [
      {
        id: 1,
        name: "Cancelled",
        description: "",
        start_time: "2026-10-15T09:00:00",
        cancelled_at: "2026-10-01",
      },
      {
        id: 2,
        name: "Scheduled",
        description: "",
        start_time: "2026-10-15T15:00:00",
        cancelled_at: null,
      },
    ],
    today,
  );
  assert.deepEqual(
    calendar.days.flatMap((day) => day.activities).map((activity) => activity.name),
    ["Scheduled"],
  );
});

test("general and club activities on the same day retain distinct identities", () => {
  const calendar = buildMonthCalendar(
    [
      {
        id: 1,
        name: "School festival",
        description: "Festival description",
        starts_at: "2026-10-15T09:00:00",
        created_at: "2026-09-01T09:00:00",
      },
    ],
    [
      {
        id: 1,
        name: "Club workshop",
        description: "Workshop description",
        start_time: "2026-10-15T15:00:00",
        cancelled_at: null,
      },
    ],
    today,
  );
  const activities = calendar.days.find((day) => day.date?.getDate() === 15)?.activities;

  assert.deepEqual(
    activities?.map(({ key, name, description }) => ({ key, name, description })),
    [
      { key: "general-1", name: "School festival", description: "Festival description" },
      { key: "club-1", name: "Club workshop", description: "Workshop description" },
    ],
  );
});

test("the calendar includes all supplied club activities in the current month", () => {
  const calendar = buildMonthCalendar(
    [],
    [
      "2026-09-01",
      "2026-10-01",
      "2026-10-05",
      "2026-10-10",
      "2026-10-20",
      "2026-10-30",
      "2026-11-01",
    ].map((date, index) => ({
      id: index,
      name: `Workshop ${index}`,
      description: "",
      start_time: `${date}T15:00:00`,
      cancelled_at: null,
    })),
    today,
  );

  assert.deepEqual(
    calendar.days.filter((day) => day.activities.length).map((day) => day.date?.getDate()),
    [1, 5, 10, 20, 30],
  );
});

test("without joined clubs, general activities keep their existing date fallback", () => {
  const calendar = buildMonthCalendar(
    [
      {
        id: 1,
        name: "School festival",
        description: "",
        starts_at: null,
        created_at: "2026-10-15T09:00:00",
      },
    ],
    [],
    today,
  );

  assert.deepEqual(
    calendar.days.flatMap((day) => day.activities).map((activity) => activity.key),
    ["general-1"],
  );
  assert.equal(calendar.days.find((day) => day.activities.length)?.date?.getDate(), 15);
});
