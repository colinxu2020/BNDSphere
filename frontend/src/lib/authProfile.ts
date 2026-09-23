export function watchAuthProfile<T>(options: {
  events: EventTarget;
  authEvent: string;
  authStorageKey: string;
  isAuthenticated: () => boolean;
  fetchUser: () => Promise<T | null>;
  update: (loggedIn: boolean, user: T | null) => void;
}): () => void {
  let generation = 0;
  const sync = () => {
    const current = ++generation;
    const loggedIn = options.isAuthenticated();
    options.update(loggedIn, null);
    if (!loggedIn) return;
    options.fetchUser().then(
      (user) => {
        if (current === generation && options.isAuthenticated()) options.update(true, user);
      },
      () => {
        if (current === generation && options.isAuthenticated()) options.update(true, null);
      },
    );
  };
  const onStorage = (event: Event) => {
    const { key } = event as StorageEvent;
    if (key === options.authStorageKey || key === null) sync();
  };
  // A login can replace the session while the UI hint remains true.
  // Always refresh on an explicit auth event; never try to read the cookie.
  options.events.addEventListener("storage", onStorage);
  options.events.addEventListener(options.authEvent, sync);
  sync();
  return () => {
    generation++;
    options.events.removeEventListener("storage", onStorage);
    options.events.removeEventListener(options.authEvent, sync);
  };
}
