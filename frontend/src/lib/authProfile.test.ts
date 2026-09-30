import assert from "node:assert/strict";
import test from "node:test";
import { watchAuthProfile } from "./authProfile.ts";

function setup(loggedIn = false) {
  const events = new EventTarget();
  const pending: { resolve: (user: string) => void; reject: (error: Error) => void }[] = [];
  const updates: unknown[] = [];
  const stop = watchAuthProfile({
    events,
    authEvent: "auth",
    authStorageKey: "bnd_authed",
    isAuthenticated: () => loggedIn,
    fetchUser: () => new Promise<string>((resolve, reject) => pending.push({ resolve, reject })),
    update: (authed, user) => updates.push([authed, user]),
  });
  return {
    events,
    pending,
    updates,
    stop,
    setAuthenticated(value: boolean) {
      loggedIn = value;
    },
    storage(key: string | null) {
      events.dispatchEvent(Object.assign(new Event("storage"), { key }));
    },
  };
}

test("mount loads once; navigation and unrelated storage do not refetch", () => {
  const state = setup(true);
  state.events.dispatchEvent(new Event("popstate"));
  state.storage("theme");
  assert.equal(state.pending.length, 1);
  state.stop();
});

test("login loads the profile and logout discards its pending response", async () => {
  const state = setup();
  assert.equal(state.pending.length, 0);
  state.setAuthenticated(true);
  state.events.dispatchEvent(new Event("auth"));
  assert.equal(state.pending.length, 1);
  state.setAuthenticated(false);
  state.events.dispatchEvent(new Event("auth"));
  state.pending[0].resolve("old-user");
  await Promise.resolve();
  assert.deepEqual(state.updates, [
    [false, null],
    [true, null],
    [false, null],
  ]);
  state.stop();
});

test("a new session refreshes even when the auth hint stays true", async () => {
  const state = setup(true);
  state.events.dispatchEvent(new Event("auth"));
  assert.equal(state.pending.length, 2);
  state.pending[1].resolve("new-user");
  await Promise.resolve();
  state.pending[0].resolve("old-user");
  await Promise.resolve();
  assert.deepEqual(state.updates.at(-1), [true, "new-user"]);
  state.stop();
});

test("other-tab auth changes and storage clear synchronize the profile", async () => {
  const state = setup();
  state.setAuthenticated(true);
  state.storage("bnd_authed");
  state.pending[0].resolve("user");
  await Promise.resolve();
  assert.deepEqual(state.updates.at(-1), [true, "user"]);
  state.setAuthenticated(false);
  state.storage(null);
  assert.deepEqual(state.updates.at(-1), [false, null]);
  state.stop();
});

test("disposal ignores pending responses and removes both listeners", async () => {
  const state = setup(true);
  state.stop();
  state.pending[0].resolve("user");
  await Promise.resolve();
  state.events.dispatchEvent(new Event("auth"));
  state.storage("bnd_authed");
  assert.equal(state.pending.length, 1);
  assert.deepEqual(state.updates, [[true, null]]);
});

test("network failure clears the profile without an unhandled rejection", async () => {
  const state = setup(true);
  state.pending[0].reject(new Error("offline"));
  await Promise.resolve();
  assert.deepEqual(state.updates.at(-1), [true, null]);
  state.stop();
});
