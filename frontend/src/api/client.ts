import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const AUTH_STATE_CHANGED_EVENT = "bnd-auth-state-changed";

// The session itself lives in an HttpOnly cookie that scripts cannot read, so
// this flag is only a UI hint: it tells the app whether to render the
// logged-in chrome and whether asking /users/me is worth a round trip. It is
// not a credential — forging it gets you a 401 from the next request, nothing
// more.
const AUTH_FLAG_KEY = "bnd_authed";
const LEGACY_TOKEN_KEY = "bnd_token";

// Remove the old script-readable JWT when upgrading to cookie sessions.
localStorage.removeItem(LEGACY_TOKEN_KEY);

export function isAuthenticated() {
  return localStorage.getItem(AUTH_FLAG_KEY) === "1";
}

export function markAuthenticated() {
  localStorage.setItem(AUTH_FLAG_KEY, "1");
  window.dispatchEvent(new Event(AUTH_STATE_CHANGED_EVENT));
}

export function clearAuthState() {
  localStorage.removeItem(LEGACY_TOKEN_KEY);
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

export async function logout(): Promise<boolean> {
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  // Keep the UI and HttpOnly cookie in agreement. Failure leaves the session
  // available for a retry; callers display it instead of claiming sign-out.
  try {
    const { response } = await client.POST("/api/v1/auth/logout");
    if (response.status !== 204) return false;
    clearAuthState();
    return true;
  } catch {
    return false;
  }
}

client.use({
  async onResponse({ response, schemaPath }) {
    // The cookie expired or was revoked server-side: drop the stale UI flag so
    // the app stops pretending to be signed in.
    if (response.status === 401 && schemaPath !== "/api/v1/auth/login") {
      const body = await response
        .clone()
        .json()
        .catch(() => null);
      if (body?.error_code === "AUTH_TOKEN_INVALID") clearAuthState();
    }
  },
});
