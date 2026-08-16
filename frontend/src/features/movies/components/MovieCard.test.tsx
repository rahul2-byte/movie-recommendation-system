import { fireEvent, render, screen } from "@testing-library/react"
import { MovieCard } from "./MovieCard"

const movie = {
  movieId: 603,
  tmdbId: 603,
  title: "The Matrix",
  year: 1999,
  genres: ["Action", "Science Fiction"],
  posterUrl: null,
  rating: 8.2,
}

test("renders a keyboard-accessible movie details link", () => {
  render(<MovieCard movie={movie} />)

  expect(
    screen.getByRole("link", { name: "View details for The Matrix" })
  ).toHaveAttribute("href", "/movies/603")
  expect(screen.getByText("8.2")).toBeInTheDocument()
})

test("replaces a failed poster with the branded fallback", () => {
  render(
    <MovieCard
      movie={{
        ...movie,
        posterUrl: "https://image.tmdb.org/t/p/w342/missing.jpg",
      }}
    />
  )

  fireEvent.error(screen.getByRole("img", { name: "The Matrix" }))

  expect(screen.getByText("Artwork unavailable")).toBeInTheDocument()
})
