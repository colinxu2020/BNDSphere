import { useEffect, useState } from "react";
import { Moon, Sun } from "@/src/components/ui/Icons";

type Theme = "light" | "dark";

const STORAGE_KEY = "bnd_theme";
const labels: Record<Theme, string> = { light: "浅色", dark: "深色" };
const icons = { light: Sun, dark: Moon };

function readTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

/** Keep in sync with the pre-paint bootstrap in index.html. */
function applyTheme(theme: Theme = readTheme()) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const cycle = () => {
    const next = theme === "light" ? "dark" : "light";
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
