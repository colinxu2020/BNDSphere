export function watchAuthProfile<T>(options: {
  events: EventTarget;
  authEvent: string;
  readToken: () => string | null;
  fetchUser: () => Promise<T | null>;
  update: (loggedIn: boolean, user: T | null) => void;
}): () => void {
  let generation = 0;
  let token: string | null | undefined;
  const sync = () => {
    const next = options.readToken();
    if (next === token) return;
    token = next;
    const current = ++generation;
    options.update(Boolean(next), null);
    if (!next) return;
    options.fetchUser().then(
      (user) => {
        if (current === generation && options.readToken() === next) options.update(true, user);
      },
      () => {
        if (current === generation && options.readToken() === next) options.update(true, null);
      },
    );
  };
  options.events.addEventListener("storage", sync);
  options.events.addEventListener(options.authEvent, sync);
  sync();
  return () => {
    generation++;
    options.events.removeEventListener("storage", sync);
    options.events.removeEventListener(options.authEvent, sync);
  };
}
