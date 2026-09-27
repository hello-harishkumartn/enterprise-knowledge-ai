import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f5ff",
          100: "#dfe9ff",
          500: "#3557e8",
          600: "#2843c9",
          700: "#1f34a0",
          900: "#141f5e",
        },
      },
    },
  },
  plugins: [],
};

export default config;
