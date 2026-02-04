#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <string>
#include <sstream>
#include <unordered_set>

// -------------------------------------------------------------------------
// CONSTANTS & CONFIGURATION
// -------------------------------------------------------------------------
const int WINDOW_SIZE = 5;       // The "5 seed movies"
const int NEGATIVE_SAMPLES = 2;  // For every positive, generate N negatives (Hard negatives/Random)
const float MIN_RATING = 3.5;    // Only consider movies liked by user as "valid history"

// -------------------------------------------------------------------------
// DATA STRUCTURES
// -------------------------------------------------------------------------
#pragma pack(push, 1)
struct Interaction {
    int32_t userId;
    int32_t movieId;
    float rating;
    int64_t timestamp;
};
#pragma pack(pop)

struct OutputSample {
    std::string query_ids;
    int32_t candidate_id;
    int label; // 1 = Positive, 0 = Negative
};

// -------------------------------------------------------------------------
// HELPER FUNCTIONS
// -------------------------------------------------------------------------
std::string join_ids(const std::vector<int32_t>& window) {
    std::stringstream ss;
    for (size_t i = 0; i < window.size(); ++i) {
        ss << window[i];
        if (i < window.size() - 1) ss << "|";
    }
    return ss.str();
}

// -------------------------------------------------------------------------
// MAIN
// -------------------------------------------------------------------------
int main() {
    // Optimize I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cerr << "[C++] Starting Sequence Builder..." << std::endl;

    // 1. Load Data
    std::vector<Interaction> interactions;
    interactions.reserve(50000000); // 50M reserve
    
    // Also keep track of all unique movies for negative sampling
    std::vector<int32_t> unique_movies;
    std::unordered_set<int32_t> unique_movies_set;

    Interaction temp;
    while (std::cin.read(reinterpret_cast<char*>(&temp), sizeof(Interaction))) {
        interactions.push_back(temp);
        if (unique_movies_set.find(temp.movieId) == unique_movies_set.end()) {
            unique_movies_set.insert(temp.movieId);
            unique_movies.push_back(temp.movieId);
        }
    }
    std::cerr << "[C++] Loaded " << interactions.size() << " interactions." << std::endl;
    std::cerr << "[C++] Found " << unique_movies.size() << " unique movies." << std::endl;

    // 2. Sort by User -> Timestamp
    std::sort(interactions.begin(), interactions.end(), [](const Interaction& a, const Interaction& b) {
        if (a.userId != b.userId) return a.userId < b.userId;
        return a.timestamp < b.timestamp;
    });
    std::cerr << "[C++] Sorting complete." << std::endl;

    // 3. Process Sliding Windows
    // Random Number Generator for Negatives
    std::mt19937 rng(42);
    std::uniform_int_distribution<int> dist(0, unique_movies.size() - 1);

    std::cout << "query_movie_ids,candidate_movie_id,label" << std::endl;

    size_t start_idx = 0;
    size_t n = interactions.size();

    while (start_idx < n) {
        int32_t current_user = interactions[start_idx].userId;
        size_t end_idx = start_idx;
        
        // Find end of current user block
        while (end_idx < n && interactions[end_idx].userId == current_user) {
            end_idx++;
        }

        // Extract valid timeline (only "liked" movies)
        // If we include disliked movies in history, the model might think we LIKE them.
        // Strategy: Only use Positive interactions for the "Seed Query"
        std::vector<int32_t> user_history;
        for (size_t i = start_idx; i < end_idx; ++i) {
            if (interactions[i].rating >= MIN_RATING) {
                user_history.push_back(interactions[i].movieId);
            }
        }

        // Generate Windows
        // Need at least WINDOW_SIZE + 1 items (5 seeds + 1 target)
        if (user_history.size() >= WINDOW_SIZE + 1) {
            for (size_t i = 0; i <= user_history.size() - WINDOW_SIZE - 1; ++i) {
                // Window: [i, i+WINDOW_SIZE-1]
                std::vector<int32_t> window;
                for (int w = 0; w < WINDOW_SIZE; ++w) {
                    window.push_back(user_history[i + w]);
                }
                
                // 1. Positive Sample (The next movie in history)
                int32_t positive_target = user_history[i + WINDOW_SIZE];
                
                std::string query_str = join_ids(window);
                
                // Output Positive
                std::cout << query_str << "," << positive_target << ",1\n";

                // 2. Negative Samples
                for (int neg = 0; neg < NEGATIVE_SAMPLES; ++neg) {
                    int32_t negative_id = unique_movies[dist(rng)];
                    // Simple check: unlikely to be the exact same positive target
                    // For perfect strictness, we'd check against user history, but for 47M scale, 
                    // collision probability is low enough to ignore for speed.
                    if (negative_id != positive_target) {
                        std::cout << query_str << "," << negative_id << ",0\n";
                    }
                }
            }
        }

        // Move to next user
        start_idx = end_idx;
    }

    std::cerr << "[C++] Sequence generation complete." << std::endl;
    return 0;
}
