#include <algorithm>
#include <armadillo>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// -------------------------------------------------------------------------
// CONSTANTS
// -------------------------------------------------------------------------
const int TOP_N_TAGS = 10000;

// -------------------------------------------------------------------------
// DATA STRUCTURES
// -------------------------------------------------------------------------
struct MovieRaw {
  int32_t id;
  std::vector<std::string> genres;
  std::vector<std::string> tags;
  std::vector<float> numericals; // release_year, vote_average, popularity
};

// -------------------------------------------------------------------------
// HELPER FUNCTIONS
// -------------------------------------------------------------------------
std::vector<std::string> split(const std::string &s, char delimiter) {
  std::vector<std::string> tokens;
  std::string token;
  std::istringstream tokenStream(s);
  while (std::getline(tokenStream, token, delimiter)) {
    if (!token.empty()) {
      tokens.push_back(token);
    }
  }
  return tokens;
}

// -------------------------------------------------------------------------
// MAIN
// -------------------------------------------------------------------------
int main(int argc, char *argv[]) {
  // Optimization for stdio
  std::ios_base::sync_with_stdio(false);
  std::cin.tie(NULL);

  std::cerr << "[C++] Starting Content Vectorizer (Armadillo)..." << std::endl;

  // Maps for Vocabulary
  std::unordered_map<std::string, int> genre_to_idx;
  std::unordered_map<std::string, int> tag_count_map;

  // Store raw data in memory
  std::vector<MovieRaw> movies;
  movies.reserve(60000);

  // 1. First Pass: Read Input and Build Vocabularies
  // Input Format (Tab separated):
  // id 	 genre1|genre2 	 tag1|tag2 	 val1|val2|val3

  std::string line;
  while (std::getline(std::cin, line)) {
    std::stringstream ss(line);
    std::string segment;
    std::vector<std::string> parts;

    while (std::getline(ss, segment, '\t')) {
      parts.push_back(segment);
    }

    if (parts.size() < 4)
      continue;

    MovieRaw m;
    try {
      m.id = std::stoi(parts[0]);
    } catch (...) {
      continue; // Skip invalid IDs
    }

    m.genres = split(parts[1], '|');
    m.tags = split(parts[2], '|');

    std::vector<std::string> nums = split(parts[3], '|');
    for (const auto &n : nums) {
      try {
        m.numericals.push_back(std::stof(n));
      } catch (...) {
        m.numericals.push_back(0.0f);
      }
    }

    // Update Vocabs
    for (const auto &g : m.genres) {
      if (genre_to_idx.find(g) == genre_to_idx.end()) {
        genre_to_idx[g] = genre_to_idx.size();
      }
    }
    for (const auto &t : m.tags) {
      tag_count_map[t]++;
    }

    movies.push_back(m);
  }

  std::cerr << "[C++] Loaded " << movies.size() << " movies." << std::endl;
  std::cerr << "[C++] Found " << genre_to_idx.size() << " unique genres."
            << std::endl;

  // Filter Top N Tags
  std::vector<std::pair<std::string, int>> tag_counts(tag_count_map.begin(),
                                                      tag_count_map.end());
  std::sort(tag_counts.begin(), tag_counts.end(),
            [](const auto &a, const auto &b) {
              return a.second > b.second; // Descending
            });

  std::unordered_map<std::string, int> tag_to_idx;
  int limit = std::min((int)tag_counts.size(), TOP_N_TAGS);
  for (int i = 0; i < limit; ++i) {
    tag_to_idx[tag_counts[i].first] = i;
  }
  std::cerr << "[C++] Selected top " << tag_to_idx.size() << " tags."
            << std::endl;

  // Calculate Vector Dimension
  // [Genres One-Hot] + [Tags One-Hot] + [Numericals]
  int dim_genres = genre_to_idx.size();
  int dim_tags = tag_to_idx.size();
  int dim_numericals = (movies.empty()) ? 0 : movies[0].numericals.size();
  int total_dim = dim_genres + dim_tags + dim_numericals;

  std::cerr << "[C++] Output Vector Dimension: " << total_dim << std::endl;
  std::cerr << "      Genres: " << dim_genres << ", Tags: " << dim_tags
            << ", Numeric: " << dim_numericals << std::endl;

  // 2. Second Pass: Construct and Output Vectors
  for (const auto &m : movies) {
    // Use Armadillo fvec (float vector)
    arma::fvec vec(total_dim, arma::fill::zeros);

    // Fill Genres
    for (const auto &g : m.genres) {
      if (genre_to_idx.count(g)) {
        vec[genre_to_idx[g]] = 1.0f;
      }
    }

    // Fill Tags
    for (const auto &t : m.tags) {
      if (tag_to_idx.count(t)) {
        vec[dim_genres + tag_to_idx[t]] = 1.0f;
      }
    }

    // Fill Numericals
    for (int i = 0; i < dim_numericals; ++i) {
      vec[dim_genres + dim_tags + i] = m.numericals[i];
    }

    // L2 Normalization using Armadillo
    // arma::norm(vec, 2) computes L2 norm
    float n = arma::norm(vec, 2);
    if (n > 1e-9) {
      vec /= n;
    }

    // Output Raw Binary: [MovieID (int32)] [Vector (float * total_dim)]
    std::cout.write(reinterpret_cast<const char *>(&m.id), sizeof(int32_t));
    // memptr() returns pointer to the memory
    std::cout.write(reinterpret_cast<const char *>(vec.memptr()),
                    vec.n_elem * sizeof(float));
  }

  std::cerr << "[C++] Finished writing vectors." << std::endl;
  return 0;
}
