import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const AUTH_STATE_CHANGED_EVENT = "bnd-auth-state-changed";

// The session itself lives in an HttpOnly cookie that scripts cannot read, so
// this flag is only a UI hint: it tells the app whether to render the
// logged-in chrome and whether asking /users/me is worth a round trip. It is
// not a credential — forging it gets you a 401 from the next request, nothing
// more.
const AUTH_FLAG_KEY = "bnd_authed";

export function isAuthenticated() {
  return localStorage.getItem(AUTH_FLAG_KEY) === "1";
}

export function markAuthenticated() {
  localStorage.setItem(AUTH_FLAG_KEY, "1");
  window.dispatchEvent(new Event(AUTH_STATE_CHANGED_EVENT));
}

export function clearAuthState() {
  if (!localStorage.getItem(AUTH_FLAG_KEY)) return;

  localStorage.removeItem(AUTH_FLAG_KEY);
  window.dispatchEvent(new Event(AUTH_STATE_CHANGED_EVENT));
}

export const client = createClient<paths>({
  // Same origin as the page, so the browser attaches the session cookie by
  // itself. Pointing this at another origin would additionally need
  // `credentials: "include"` here and a matching CORS_ORIGIN on the backend.
  baseUrl: window.location.origin,
});

export async function logout() {
  // Must go through the server: clearing the flag alone would leave the
  // session row and its cookie alive, so "signed out" would only be true in
  // this tab. Errors are ignored — an unreachable backend must not strand the
  // user in a half-signed-in UI, and the cookie expires on its own.
  try {
    await client.POST("/api/v1/auth/logout");
  } finally {
    clearAuthState();
  }
}

client.use({
  onResponse({ response, schemaPath }) {
    // The cookie expired or was revoked server-side: drop the stale UI flag so
    // the app stops pretending to be signed in.
    if (response.status === 401 && schemaPath !== "/api/v1/auth/login") {
      clearAuthState();
    }
  },
});
