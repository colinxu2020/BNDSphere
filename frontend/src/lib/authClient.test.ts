import assert from "node:assert/strict";
import test from "node:test";

const storage = new Map<string, string>([
  ["bnd_token", "legacy-jwt-fixture"],
  ["bnd_authed", "1"],
  ["unrelated-preference", "keep"],
]);
const browser = Object.assign(new EventTarget(), {
  location: { origin: "https://forum.example.com" },
});
Object.defineProperty(globalThis, "window", { value: browser, configurable: true });
Object.defineProperty(globalThis, "localStorage", {
  value: {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  },
  configurable: true,
});
let respond: () => Response = () => new Response(null, { status: 204 });
globalThis.fetch = async () => respond();
const {
  client,
  clearAuthState,
  isAuthenticated,
  logout,
  markAuthenticated,
  AUTH_STATE_CHANGED_EVENT,
} = await import("../api/client.ts");

test("client initialization removes the legacy credential without clearing the session hint", () => {
  assert.equal(storage.has("bnd_token"), false);
  assert.equal(isAuthenticated(), true);
  assert.equal(storage.get("unrelated-preference"), "keep");
});

test("auth cleanup removes legacy credentials even without a session hint", () => {
  storage.delete("bnd_authed");
  storage.set("bnd_token", "legacy-jwt-fixture");
  clearAuthState();
  assert.equal(storage.has("bnd_token"), false);
  assert.equal(isAuthenticated(), false);
});

test("wrong reauthentication password preserves the current session hint", async () => {
  markAuthenticated();
  respond = () => Response.json({ error_code: "INCORRECT_USER_PASSWD" }, { status: 401 });
  const { error } = await client.POST("/api/v1/verification/email/send", {
    body: { email: "student@example.com", password: "wrong" },
  });
  assert.equal(isAuthenticated(), true);
  assert.equal((error as { error_code: string }).error_code, "INCORRECT_USER_PASSWD");
});

test("invalid session clears the hint and notifies the current tab", async () => {
  markAuthenticated();
  let notifications = 0;
  const listener = () => notifications++;
  browser.addEventListener(AUTH_STATE_CHANGED_EVENT, listener);
  respond = () => Response.json({ error_code: "AUTH_TOKEN_INVALID" }, { status: 401 });
  await client.GET("/api/v1/users/me");
  assert.equal(isAuthenticated(), false);
  assert.equal(notifications, 1);
  browser.removeEventListener(AUTH_STATE_CHANGED_EVENT, listener);
});

test("failed logout preserves state for retry; only 204 completes sign-out", async () => {
  markAuthenticated();
  storage.set("bnd_token", "legacy-jwt-fixture");
  respond = () => Response.json({ detail: "unavailable" }, { status: 503 });
  assert.equal(await logout(), false);
  assert.equal(storage.has("bnd_token"), false);
  assert.equal(isAuthenticated(), true);
  storage.set("bnd_token", "legacy-jwt-fixture");
  respond = () => {
    throw new TypeError("network unavailable");
  };
  assert.equal(await logout(), false);
  assert.equal(storage.has("bnd_token"), false);
  assert.equal(isAuthenticated(), true);
  storage.set("bnd_token", "legacy-jwt-fixture");
  respond = () => new Response(null, { status: 204 });
  assert.equal(await logout(), true);
  assert.equal(storage.has("bnd_token"), false);
  assert.equal(isAuthenticated(), false);
});
