import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "@/src/components/ui/Icons";

type Theme = "light" | "dark" | "auto";

const STORAGE_KEY = "bnd_theme";

const labels: Record<Theme, string> = { light: "浅色", dark: "深色", auto: "自动" };
const icons = { light: Sun, dark: Moon, auto: Monitor };
const order: Theme[] = ["light", "dark", "auto"];

const media = () => window.matchMedia("(prefers-color-scheme: dark)");

function readTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "auto") return stored;
  return "auto";
}

/** Keep in sync with the pre-paint bootstrap in index.html. */
function applyTheme(theme: Theme = readTheme()) {
  const dark = theme === "auto" ? media().matches : theme === "dark";
  document.documentElement.classList.toggle("dark", dark);
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);

  useEffect(() => {
    applyTheme(theme);
    if (theme !== "auto") return;
    const mql = media();
    const onChange = () => applyTheme("auto");
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [theme]);

  // Keep React state in sync when another tab changes the stored preference.
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY) return;
      const value = event.newValue;
      if (value === "light" || value === "dark" || value === "auto") setTheme(value);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const cycle = () => {
    const next = order[(order.indexOf(theme) + 1) % order.length];
    localStorage.setItem(STORAGE_KEY, next);
    setTheme(next);
  };

  const Icon = icons[theme];
  return (
    <button
      type="button"
      onClick={cycle}
      title={`主题：${labels[theme]}`}
      aria-label={`主题：${labels[theme]}，点击切换`}
      className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900"
    >
      <Icon size={18} />
    </button>
  );
}
