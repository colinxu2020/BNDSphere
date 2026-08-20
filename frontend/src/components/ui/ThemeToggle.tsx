import { useEffect, useState } from "react";
import { Moon, Monitor, Sun } from "@/src/components/ui/Icons";

type Theme = "light" | "dark" | "auto";

const STORAGE_KEY = "bnd_theme";
const order: Theme[] = ["light", "dark", "auto"];
const labels: Record<Theme, string> = { light: "浅色", dark: "深色", auto: "跟随系统" };
const icons = { light: Sun, dark: Moon, auto: Monitor };

function readTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" ? stored : "auto";
}

/** Keep in sync with the pre-paint bootstrap in index.html. */
function applyTheme(theme: Theme = readTheme()) {
  const dark =
    theme === "dark" ||
    (theme === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);

  useEffect(() => {
    applyTheme(theme);
    if (theme !== "auto") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("auto");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [theme]);

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
