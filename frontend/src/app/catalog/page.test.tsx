import { fireEvent, render, screen } from "@testing-library/react"
import CatalogPage from "./page"

const replace = jest.fn()

jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}))

jest.mock("@/features/movies/api", () => ({
  discoverMovies: jest.fn(),
  getGenres: jest.fn().mockResolvedValue([{ id: 18, name: "Drama" }]),
  getNewReleases: jest.fn(),
  getPopularMovies: jest.fn(),
  getTrendingMovies: jest.fn().mockResolvedValue([
    {
      movieId: 603,
      tmdbId: 603,
      title: "The Matrix",
      year: 1999,
      genres: ["Action"],
      posterUrl: null,
      rating: 8.2,
    },
  ]),
}))

test("updates catalog filters immediately without an apply button", async () => {
  render(await CatalogPage({ searchParams: Promise.resolve({}) }))

  fireEvent.change(screen.getByLabelText("Minimum rating"), {
    target: { value: "8" },
  })

  expect(replace).toHaveBeenCalledWith("/catalog?rating=8&sort=popularity", {
    scroll: false,
  })
  expect(
    screen.queryByRole("button", { name: "Apply filters" })
  ).not.toBeInTheDocument()
})
