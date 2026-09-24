import { useEffect, useState } from "react";

const read = (name: string) =>
  `rgb(${getComputedStyle(document.documentElement).getPropertyValue(name).trim()})`;

/**
 * A design token (an RGB-channel CSS variable) as a concrete color string, for
 * libraries like Recharts that write SVG attributes where var() is unreliable.
 * Re-reads when the theme flips.
 */
export function useTokenColor(name: string) {
  const [color, setColor] = useState(() => read(name));
  useEffect(() => {
    const update = () => setColor(read(name));
    const mo = new MutationObserver(update);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", update);
    return () => { mo.disconnect(); mq.removeEventListener("change", update); };
  }, [name]);
  return color;
}
