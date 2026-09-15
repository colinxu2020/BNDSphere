export function readAltchaPayload(form: HTMLFormElement): string | null {
  const payload = new FormData(form).get("altcha");
  return typeof payload === "string" && payload ? payload : null;
}
