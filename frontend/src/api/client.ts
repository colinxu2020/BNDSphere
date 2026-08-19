import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const AUTH_STATE_CHANGED_EVENT = "bnd-auth-state-changed";

export function clearAuthToken() {
  if (!localStorage.getItem("bnd_token")) return;

  localStorage.removeItem("bnd_token");
  window.dispatchEvent(new Event(AUTH_STATE_CHANGED_EVENT));
}

export const client = createClient<paths>({
  // Pointing to current origin; in a real app this might be an external backend
  baseUrl: window.location.origin,
});

// Interceptor to attach auth token if available
client.use({
  onRequest({ request }) {
    const token = localStorage.getItem("bnd_token");
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
  onResponse({ response, schemaPath }) {
    if (response.status === 401 && schemaPath !== "/api/v1/auth/login") {
      clearAuthToken();
    }
  },
});
