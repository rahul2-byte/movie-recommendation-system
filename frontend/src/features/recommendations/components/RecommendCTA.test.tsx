import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { RecommendCTA } from "./RecommendCTA"
import { useRecommendationStore } from "@/features/recommendations/store"

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}))

beforeEach(() => {
  useRecommendationStore.setState({
    selectedMovies: [{ tmdbId: 603, title: "The Matrix", posterUrl: null }],
    recommendations: [],
    error: null,
  })
})

test("enables recommendations after one seed movie", () => {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <RecommendCTA />
    </QueryClientProvider>
  )

  expect(screen.getByRole("button", { name: "Create my lineup" })).toBeEnabled()
})
