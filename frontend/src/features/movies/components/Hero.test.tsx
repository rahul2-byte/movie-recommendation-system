import { act, fireEvent, render, screen } from "@testing-library/react"
import { Hero } from "./Hero"

const movies = [
  {
    movieId: 1,
    tmdbId: 1,
    title: "The First Feature",
    year: 2026,
    genres: ["Drama"],
    posterUrl: null,
    backdropUrl: null,
    rating: 8.1,
  },
  {
    movieId: 2,
    tmdbId: 2,
    title: "The Next Feature",
    year: 2026,
    genres: ["Adventure"],
    posterUrl: null,
    backdropUrl: null,
    rating: 7.8,
  },
]

test("automatically advances the featured movie rail", () => {
  jest.useFakeTimers()
  render(<Hero movie={movies[0]} movies={movies} />)

  expect(screen.getByText("The First Feature")).toBeInTheDocument()

  act(() => {
    jest.advanceTimersByTime(5000)
  })

  expect(screen.getByText("The Next Feature")).toBeInTheDocument()
  jest.useRealTimers()
})

test("continues autoplay when the hero is hovered", () => {
  jest.useFakeTimers()
  render(<Hero movie={movies[0]} movies={movies} />)
  fireEvent.mouseEnter(screen.getByRole("region", { name: "Featured movies" }))

  act(() => {
    jest.advanceTimersByTime(5000)
  })

  expect(screen.getByText("The Next Feature")).toBeInTheDocument()
  jest.useRealTimers()
})
