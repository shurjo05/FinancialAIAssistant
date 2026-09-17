/** @type {import('tailwindcss').Config} */
const rgb = (v) => `rgb(var(${v}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: rgb("--bg"),
        surface: rgb("--surface"),
        card: rgb("--card"),
        line: rgb("--line"),
        "line-soft": rgb("--line-soft"),
        text: rgb("--text"),
        muted: rgb("--muted"),
        faint: rgb("--faint"),
        accent: { a: rgb("--accent-a"), b: rgb("--accent-b") },
        up: rgb("--up"),
        down: rgb("--down"),
        // Kept so any not-yet-reskinned view using brand-* stays on-palette.
        brand: {
          50: "#f5f0fd", 100: "#ead9fb", 500: "#a736d6",
          600: "#7a28c9", 700: "#651fa8",
        },
      },
      fontFamily: {
        display: ["Sora", "system-ui", "sans-serif"],
        sans: ["Instrument Sans", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgb(20 19 31 / 0.04), 0 8px 24px rgb(20 19 31 / 0.05)",
        pop: "0 12px 40px rgb(122 40 201 / 0.20)",
      },
    },
  },
  plugins: [],
};
