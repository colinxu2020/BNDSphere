import { useEffect, useState } from "react";

/**
 * Colour-scheme choice.
 *
 * Three states, not two. A two-state toggle looks simpler but silently removes
 * the original behaviour: once you have picked light or dark there is no way back
 * to following the operating system, which is what most people want and what this
 * app shipped with. `system` stays the default and stays reachable.
 */
export type ThemeChoice = "light" | "dark" | "system";

const STORAGE_KEY = "bndsphere-theme";
const darkQuery = () => window.matchMedia("(prefers-color-scheme: dark)");

export const THEME_CHOICES: ThemeChoice[] = ["light", "dark", "system"];

/** Menu labels, and the accessible name of the trigger. */
export const THEME_LABELS: Record<ThemeChoice, string> = {
  light: "浅色",
  dark: "深色",
  system: "跟随系统",
};

function readChoice(): ThemeChoice {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

/**
 * Resolve a choice to a scheme and put it on <html>.
 *
 * Exported because index.html runs the same logic inline before first paint —
 * see the comment there. Keep the two in agreement: the storage key and the
 * `dark` class name are the shared contract.
 */
export function applyTheme(choice: ThemeChoice) {
  const isDark = choice === "dark" || (choice === "system" && darkQuery().matches);
  document.documentElement.classList.toggle("dark", isDark);
}

/**
 * Call this once, high in the tree, and pass the result down.
 *
 * Two instances would each hold their own `choice` and drift apart: whichever one
 * you did not click keeps showing the old selection. One caller today (the header
 * control), so this is a constraint on future callers rather than a live bug.
 */
export function useTheme() {
  const [choice, setChoice] = useState<ThemeChoice>(readChoice);

  useEffect(() => {
    applyTheme(choice);

    // Only `system` needs to keep watching. An explicit choice must not move
    // when the OS switches at sunset.
    if (choice !== "system") return;
    const query = darkQuery();
    const onSystemChange = () => applyTheme("system");
    query.addEventListener("change", onSystemChange);
    return () => query.removeEventListener("change", onSystemChange);
  }, [choice]);

  const chooseTheme = (next: ThemeChoice) => {
    // `system` is the default, so it is stored as the absence of a preference.
    // A stale "system" string would otherwise outlive a future default change.
    try {
      if (next === "system") localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage blocked. The choice still applies to this session; it just
      // will not survive a reload, which beats refusing to switch at all.
    }
    setChoice(next);
  };

  return { choice, chooseTheme };
}
