import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: "#3674B5",
        brandSoft: "#578FCA",
        sand: "#F5F0CD",
        sun: "#FADA7A",
        ink: "#3674B5",
        paper: "#F5F0CD",
        ember: "#FADA7A",
        moss: "#3674B5",
        sky: "#578FCA",
      },
      boxShadow: {
        panel: "0 14px 32px rgba(54, 116, 181, 0.16), 0 2px 10px rgba(87, 143, 202, 0.08)",
        soft: "0 10px 26px rgba(54, 116, 181, 0.12), 0 2px 8px rgba(87, 143, 202, 0.06)",
        floating: "0 22px 46px rgba(54, 116, 181, 0.2), 0 8px 18px rgba(87, 143, 202, 0.12)",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
