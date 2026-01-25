import { fetchRecommendations } from "@/lib/api/recommendations"
import { RecommendationState, MAX_LIKED_MOVIES } from "./state"

export async function submitRecommendations(state: RecommendationState) {
    if (state.likedMovies.length === 0) {
        throw new Error("Select at least one movie")
    }

    if (state.likedMovies.length > MAX_LIKED_MOVIES) {
        throw new Error("Maximum 5 movies allowed")
    }

    return fetchRecommendations({
        user_preferences: {
            genres: state.genres,
            moods: state.moods,
            liked_movies: state.likedMovies.map(m => ({
                movie_id: m.movieId,
                tmdb_id: m.tmdbId,
            })),
        },
        limit: 20,
    })
}
