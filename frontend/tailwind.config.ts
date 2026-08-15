import type { Config } from "tailwindcss"
import tailwindcssAnimate from "tailwindcss-animate"

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  plugins: [tailwindcssAnimate],
}

export default config
