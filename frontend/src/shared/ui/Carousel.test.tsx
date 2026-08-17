import { fireEvent, render, screen } from "@testing-library/react"
import { Carousel } from "./Carousel"

test("keeps the horizontal gallery clean without a native scrollbar", () => {
  render(
    <Carousel>
      <span>Movie</span>
    </Carousel>
  )

  const viewport = screen.getByText("Movie").parentElement
  expect(viewport).toHaveClass(
    "[-ms-overflow-style:none]",
    "[scrollbar-width:none]",
    "[&::-webkit-scrollbar]:hidden"
  )
})

test("keeps focused cards inside the horizontal viewport", () => {
  render(
    <Carousel>
      <button type="button">Movie</button>
    </Carousel>
  )

  const card = screen.getByRole("button", { name: "Movie" })
  const viewport = card.parentElement
  if (!viewport) throw new Error("Carousel viewport missing")

  Object.defineProperty(viewport, "scrollLeft", {
    configurable: true,
    writable: true,
    value: 0,
  })
  viewport.getBoundingClientRect = () => ({ left: 0, right: 100 }) as DOMRect
  card.getBoundingClientRect = () => ({ left: 0, right: 150 }) as DOMRect

  fireEvent.focus(card)

  expect(viewport.scrollLeft).toBe(66)
})
