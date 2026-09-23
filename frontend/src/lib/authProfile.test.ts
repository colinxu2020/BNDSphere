import assert from "node:assert/strict";
import test from "node:test";
import { watchAuthProfile } from "./authProfile.ts";

test("account switches discard old responses and disposal removes listeners", async () => {
  const events = new EventTarget();
  let token = "first";
  const pending: ((user: string) => void)[] = [];
  const updates: unknown[] = [];
  const stop = watchAuthProfile({
    events,
    authEvent: "auth",
    readToken: () => token,
    fetchUser: () => new Promise<string>((resolve) => pending.push(resolve)),
    update: (loggedIn, user) => updates.push([loggedIn, user]),
  });
  token = "second";
  events.dispatchEvent(new Event("auth"));
  pending[1]("second-user");
  await Promise.resolve();
  pending[0]("first-user");
  await Promise.resolve();
  assert.deepEqual(updates.at(-1), [true, "second-user"]);
  stop();
  token = "third";
  events.dispatchEvent(new Event("auth"));
  assert.equal(pending.length, 2);
});

test("failed profile requests settle without an unhandled rejection", async () => {
  const updates: unknown[] = [];
  const stop = watchAuthProfile({
    events: new EventTarget(),
    authEvent: "auth",
    readToken: () => "token",
    fetchUser: async () => {
      throw new Error("offline");
    },
    update: (loggedIn, user) => updates.push([loggedIn, user]),
  });
  await Promise.resolve();
  assert.deepEqual(updates.at(-1), [true, null]);
  stop();
});

test("loads on login, ignores navigation and unchanged storage, clears on logout", async () => {
  const events = new EventTarget();
  let token: string | null = null;
  let calls = 0;
  const updates: unknown[] = [];
  const stop = watchAuthProfile({
    events,
    authEvent: "auth",
    readToken: () => token,
    fetchUser: async () => {
      calls++;
      return "user";
    },
    update: (loggedIn, user) => updates.push([loggedIn, user]),
  });
  assert.equal(calls, 0);
  token = "token";
  events.dispatchEvent(new Event("auth"));
  await Promise.resolve();
  assert.deepEqual(updates.at(-1), [true, "user"]);
  events.dispatchEvent(new Event("popstate"));
  events.dispatchEvent(new Event("storage"));
  assert.equal(calls, 1);
  token = null;
  events.dispatchEvent(new Event("auth"));
  assert.deepEqual(updates.at(-1), [false, null]);
  stop();
});

test("mount loads once and stale responses cannot restore a logged-out user", async () => {
  const events = new EventTarget();
  let token: string | null = "token";
  let resolve!: (value: string) => void;
  let calls = 0;
  const updates: unknown[] = [];
  const stop = watchAuthProfile({
    events,
    authEvent: "auth",
    readToken: () => token,
    fetchUser: () => {
      calls++;
      return new Promise<string>((done) => {
        resolve = done;
      });
    },
    update: (loggedIn, user) => updates.push([loggedIn, user]),
  });
  assert.equal(calls, 1);
  token = null;
  events.dispatchEvent(new Event("storage"));
  resolve("old-user");
  await Promise.resolve();
  assert.deepEqual(updates.at(-1), [false, null]);
  stop();
});
