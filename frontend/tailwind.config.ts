import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f3f6fa",
        ink: "#13253f",
        scientific: {
          50: "#f2f7ff",
          100: "#dbe8fb",
          200: "#b8d2f6",
          300: "#8fb7ef",
          400: "#5e93e3",
          500: "#356fca",
          600: "#2958a7",
          700: "#1f457f",
          800: "#18345f",
          900: "#102442"
        }
      },
      borderRadius: {
        panel: "30px",
        card: "18px",
        pill: "999px"
      },
      boxShadow: {
        glass: "0 12px 38px rgba(21, 43, 76, 0.16)",
        soft: "0 8px 24px rgba(26, 41, 67, 0.1)"
      },
      fontFamily: {
        display: ["'Noto Serif SC'", "'Source Serif 4'", "serif"],
        body: ["'Source Sans 3'", "'PingFang SC'", "sans-serif"]
      }
    }
  },
  plugins: []
} satisfies Config;
