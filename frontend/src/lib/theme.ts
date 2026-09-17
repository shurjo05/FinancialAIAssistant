import { useEffect, useState } from "react";

export type Theme = "light" | "dark";
const KEY = "jomoney-theme";

/** Stored preference, defaulting to dark (JoMoney is dark-first). */
export function getStoredTheme(): Theme {
  try {
    const t = localStorage.getItem(KEY);
    if (t === "light" || t === "dark") return t;
  } catch {
    /* storage blocked — fall through to default */
  }
  return "dark";
}

export function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

/** Theme state + toggle; persists and applies on change. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getStoredTheme);
  useEffect(() => {
    applyTheme(theme);
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);
  return { theme, setTheme, toggle: () => setTheme((t) => (t === "dark" ? "light" : "dark")) };
}
