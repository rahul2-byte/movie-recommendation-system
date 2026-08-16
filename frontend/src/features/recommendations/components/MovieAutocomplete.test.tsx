import { fireEvent, render, screen } from "@testing-library/react"
import { MovieAutocomplete } from "./MovieAutocomplete"
import { useRecommendationStore } from "@/features/recommendations/store"
import { useMovieSearch } from "@/features/recommendations/hooks/useMovieSearch"

jest.mock("@/features/recommendations/hooks/useMovieSearch")

const mockedUseMovieSearch = jest.mocked(useMovieSearch)

beforeEach(() => {
  useRecommendationStore.setState({ selectedMovies: [] })
  mockedUseMovieSearch.mockReturnValue({
    query: "matrix",
    setQuery: jest.fn(),
    results: [
      {
        movieId: 603,
        tmdbId: 603,
        title: "The Matrix",
        year: 1999,
        genres: ["Action"],
        posterUrl: null,
        rating: 8.2,
      },
    ],
    isLoading: false,
    isError: false,
  })
})

test("selects the active search result with the keyboard", () => {
  render(<MovieAutocomplete />)

  const search = screen.getByRole("combobox", { name: "Search movies" })
  fireEvent.keyDown(search, { key: "ArrowDown" })
  fireEvent.keyDown(search, { key: "Enter" })

  expect(useRecommendationStore.getState().selectedMovies).toEqual([
    { tmdbId: 603, title: "The Matrix", posterUrl: null },
  ])
})
