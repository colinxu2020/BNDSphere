import type { components } from "../api/schema";

export type TwoFactorMethod = components["schemas"]["TwoFactorMethodEnum"];

export type TwoFactorChallenge = { token: string; methods: TwoFactorMethod[] };

const METHODS: readonly string[] = ["totp", "sms", "recovery"] satisfies TwoFactorMethod[];

/**
 * Turn the login response's error envelope into a challenge, or null.
 *
 * The 401 carries no schema in the OpenAPI document — it is the error envelope
 * every route shares — so the shape has to be checked at runtime.
 */
export function readTwoFactorChallenge(error: unknown): TwoFactorChallenge | null {
  if (!error || typeof error !== "object") return null;
  const envelope = error as Record<string, unknown>;
  if (envelope.error_code !== "TWO_FACTOR_REQUIRED") return null;
  const details = envelope.details;
  if (!details || typeof details !== "object") return null;
  const { two_factor_token: token, methods } = details as Record<string, unknown>;
  if (typeof token !== "string" || !Array.isArray(methods)) return null;
  const known = methods.filter((method): method is TwoFactorMethod =>
    METHODS.includes(method as string),
  );
  return known.length ? { token, methods: known } : null;
}
