import { migrateRecommendationStorage, useRecommendationStore } from "./store"

test("migrates saved recommendations without retaining an expired session", () => {
  expect(
    migrateRecommendationStorage(
      {
        selectedMovies: [{ tmdbId: 603, title: "The Matrix" }],
        recommendations: [{ tmdbId: 604, title: "The Matrix Reloaded" }],
      },
      3
    )
  ).toMatchObject({
    selectedMovies: [{ tmdbId: 603, title: "The Matrix" }],
    recommendations: [{ tmdbId: 604, title: "The Matrix Reloaded" }],
    recommendationSessionId: null,
    recommendationNextOffset: null,
    recommendationHasMore: false,
    error: null,
  })
})

test("appends a progressive recommendation page without duplicate movies", () => {
  useRecommendationStore.getState().setRecommendationPage({
    sessionId: "lineup-1",
    recommendations: [{ tmdbId: 1, title: "One", genres: [] }],
    nextOffset: 24,
    hasMore: true,
  })

  useRecommendationStore.getState().appendRecommendationPage({
    sessionId: "lineup-1",
    recommendations: [
      { tmdbId: 1, title: "One", genres: [] },
      { tmdbId: 2, title: "Two", genres: [] },
    ],
    nextOffset: null,
    hasMore: false,
  })

  expect(
    useRecommendationStore
      .getState()
      .recommendations.map((movie) => movie.tmdbId)
  ).toEqual([1, 2])
  expect(useRecommendationStore.getState().recommendationHasMore).toBe(false)
})
