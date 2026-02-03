import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(0 0% 0%)",
        foreground: "hsl(0 0% 100%)",
        card: {
          DEFAULT: "hsl(0 0% 5%)",
          foreground: "hsl(0 0% 100%)",
        },
        popover: {
          DEFAULT: "hsl(0 0% 5%)",
          foreground: "hsl(0 0% 100%)",
        },
        primary: {
          DEFAULT: "hsl(0 0% 100%)",
          foreground: "hsl(0 0% 0%)",
        },
        secondary: {
          DEFAULT: "hsl(0 0% 10%)",
          foreground: "hsl(0 0% 100%)",
        },
        muted: {
          DEFAULT: "hsl(0 0% 10%)",
          foreground: "hsl(0 0% 60%)",
        },
        accent: {
          DEFAULT: "hsl(0 0% 15%)",
          foreground: "hsl(0 0% 100%)",
        },
        destructive: {
          DEFAULT: "hsl(0 0% 30%)",
          foreground: "hsl(0 0% 100%)",
        },
        border: "hsl(0 0% 20%)",
        input: "hsl(0 0% 20%)",
        ring: "hsl(0 0% 100%)",
      },
      borderRadius: {
        lg: "0.5rem",
        md: "0.375rem",
        sm: "0.25rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
