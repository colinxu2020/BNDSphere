import { useCallback, useState } from "react";
import type { Tone } from "./tones";

/**
 * Result feedback for a user-triggered action.
 *
 * Twelve hand-rolled copies of this existed across seven pages — a `useState`
 * for the message paired with a `useState<Tone>` for how to show it, and the
 * same `if (error) { setTone("danger"); setMessage(error) } else { ... }` block
 * written out at every call site. ClubWorkspace had six pairs on its own.
 *
 * The duplication was not just noise: each copy chose its own initial tone and
 * its own success wording, so the same failure looked different depending on
 * which page you were on.
 *
 * `report` captures the shape almost every call site actually wanted: hand it
 * the error and the data from a client call and it picks the tone.
 */
export function useActionFeedback(initialTone: Tone = "danger") {
  const [message, setMessage] = useState<unknown>(null);
  const [tone, setTone] = useState<Tone>(initialTone);

  const fail = useCallback((value: unknown) => {
    setTone("danger");
    setMessage(value);
  }, []);

  const succeed = useCallback((value: unknown) => {
    setTone("success");
    setMessage(value);
  }, []);

  const inform = useCallback((value: unknown) => {
    setTone("info");
    setMessage(value);
  }, []);

  const clear = useCallback(() => setMessage(null), []);

  /** Pass a client call's `error` and `data` straight through. */
  const report = useCallback(
    (error: unknown, data?: unknown) => {
      if (error) fail(error);
      else succeed(data ?? "操作已完成");
    },
    [fail, succeed],
  );

  return { message, tone, fail, succeed, inform, clear, report };
}
