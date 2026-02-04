import type { Config } from "tailwindcss"

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  plugins: [require("tailwindcss-animate")],
}

export default config
