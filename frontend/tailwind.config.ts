import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          500: "#2f5fe0",
          600: "#264dc0",
          700: "#1f3f9e",
        },
      },
    },
  },
  plugins: [],
};

export default config;
