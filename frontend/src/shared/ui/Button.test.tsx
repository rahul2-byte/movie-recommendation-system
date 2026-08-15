import { render, screen } from "@testing-library/react"
import { Button } from "./Button"

describe("Button", () => {
  it("renders a button with the correct text", () => {
    render(<Button>Hello World</Button>)
    const buttonElement = screen.getByText(/hello world/i)
    expect(buttonElement).toBeInTheDocument()
  })

  it("renders a disabled button", () => {
    render(<Button disabled>Click Me</Button>)
    const buttonElement = screen.getByText(/click me/i)
    expect(buttonElement).toBeDisabled()
  })
})
