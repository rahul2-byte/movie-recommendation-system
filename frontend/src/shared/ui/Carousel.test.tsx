import { render, screen } from "@testing-library/react"
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
