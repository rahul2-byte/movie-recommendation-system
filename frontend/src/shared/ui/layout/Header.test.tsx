import { render, screen } from "@testing-library/react"
import { Header } from "./Header"

jest.mock("next/navigation", () => ({
  usePathname: () => "/",
}))

test("exposes the primary discovery navigation", () => {
  render(<Header />)

  expect(screen.getByRole("link", { name: "Skip to content" })).toHaveAttribute(
    "href",
    "#main-content"
  )
  expect(screen.getByRole("banner")).toHaveClass("absolute")
  expect(
    screen.getByRole("navigation", { name: "Primary" })
  ).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Discover" })).toHaveAttribute(
    "href",
    "/"
  )
  expect(screen.getByRole("link", { name: "Browse" })).toHaveAttribute(
    "href",
    "/catalog"
  )
  expect(screen.getByRole("link", { name: "About" })).toHaveAttribute(
    "href",
    "/about"
  )
})
