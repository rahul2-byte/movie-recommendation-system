#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <unordered_map>
#include <algorithm>
#include <cstdint>
#include <armadillo>

// -------------------------------------------------------------------------
// CONSTANTS
// -------------------------------------------------------------------------
const float MIN_RATING = 3.5;

// -------------------------------------------------------------------------
// MAIN
// -------------------------------------------------------------------------
int main(int argc, char* argv[]) {
    // Optimize I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cerr << "[C++] Starting Interaction Matrix Builder (Armadillo)..." << std::endl;

    std::unordered_map<int32_t, int32_t> user_to_idx;
    std::unordered_map<int32_t, int32_t> movie_to_idx;

    // We will collect triplets first, then build Armadillo Sparse Matrix
    // Armadillo batch constructor takes a matrix of locations (2xN) and a vector of values (N).
    // Using std::vector for dynamic growth, then convert.
    std::vector<arma::uword> loc_rows;
    std::vector<arma::uword> loc_cols;
    std::vector<double> values; // Armadillo elements are double by default for sp_mat

    #pragma pack(push, 1)
    struct InputInteraction {
        int32_t userId;
        int32_t movieId;
        float rating;
        int64_t timestamp;
    };
    #pragma pack(pop)

    InputInteraction input;
    size_t count = 0;

    while (std::cin.read(reinterpret_cast<char*>(&input), sizeof(InputInteraction))) {
        if (input.rating >= MIN_RATING) {
            // Map User ID
            if (user_to_idx.find(input.userId) == user_to_idx.end()) {
                user_to_idx[input.userId] = user_to_idx.size();
            }
            int32_t u_idx = user_to_idx[input.userId];

            // Map Movie ID
            if (movie_to_idx.find(input.movieId) == movie_to_idx.end()) {
                movie_to_idx[input.movieId] = movie_to_idx.size();
            }
            int32_t m_idx = movie_to_idx[input.movieId];

            // Rows = Items (Movies), Cols = Users
            loc_rows.push_back(m_idx);
            loc_cols.push_back(u_idx);
            values.push_back(1.0); // Implicit feedback
            
            count++;
        }
    }

    int32_t num_users = user_to_idx.size();
    int32_t num_movies = movie_to_idx.size();

    // Construct Armadillo objects
    arma::umat locations(2, count);
    arma::vec vals(count);

    for(size_t i=0; i<count; ++i) {
        locations(0, i) = loc_rows[i];
        locations(1, i) = loc_cols[i];
        vals(i) = values[i];
    }

    // Build Sparse Matrix
    // Note: If there are duplicate (row, col) entries, Armadillo sums the values.
    // This handles multiple interactions gracefully.
    arma::sp_mat X(locations, vals, num_movies, num_users);

    std::cerr << "[C++] Processed " << count << " raw interactions." << std::endl;
    std::cerr << "[C++] Built Sparse Matrix: " << X.n_rows << " movies x " << X.n_cols << " users (" << X.n_nonzero << " nz)." << std::endl;

    // Prepare Output Data
    // We need to output the non-zero elements in COO format (row_indices, col_indices)
    // Armadillo iterators traverse in Column-Major order (CSC-like)
    std::vector<int32_t> out_rows;
    std::vector<int32_t> out_cols;
    out_rows.reserve(X.n_nonzero);
    out_cols.reserve(X.n_nonzero);

    for (arma::sp_mat::const_iterator it = X.begin(); it != X.end(); ++it) {
        out_rows.push_back(static_cast<int32_t>(it.row()));
        out_cols.push_back(static_cast<int32_t>(it.col()));
    }

    int64_t num_interactions = out_rows.size();

    // Output Binary Data to Stdout

    // 1. Header: num_movies, num_users, num_interactions
    std::cout.write(reinterpret_cast<const char*>(&num_movies), sizeof(int32_t));
    std::cout.write(reinterpret_cast<const char*>(&num_users), sizeof(int32_t));
    std::cout.write(reinterpret_cast<const char*>(&num_interactions), sizeof(int64_t));

    // 2. Movie ID Mapping (Index -> MovieID)
    std::vector<int32_t> idx_to_movie(num_movies);
    for (const auto& pair : movie_to_idx) {
        idx_to_movie[pair.second] = pair.first;
    }
    std::cout.write(reinterpret_cast<const char*>(idx_to_movie.data()), num_movies * sizeof(int32_t));

    // 3. COO Data Indices
    std::cout.write(reinterpret_cast<const char*>(out_rows.data()), out_rows.size() * sizeof(int32_t));
    std::cout.write(reinterpret_cast<const char*>(out_cols.data()), out_cols.size() * sizeof(int32_t));

    std::cerr << "[C++] Finished writing matrix data." << std::endl;

    return 0;
}
