#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <unordered_map>
#include <vector>

// Define the structure for an interaction
// Must match the Python struct.pack format
// Use #pragma pack to prevent padding bytes
#pragma pack(push, 1)
struct Interaction {
  int32_t userId;
  int32_t movieId;
  float rating;
  int64_t timestamp;
};
#pragma pack(pop)

// Stats containers
struct EntityStats {
  double sum = 0.0;
  int count = 0;
};

int main() {
  // Optimize I/O operations
  std::ios_base::sync_with_stdio(false);
  std::cin.tie(NULL);

  std::vector<Interaction> interactions;
  interactions.reserve(
      50000000); // Pre-allocate for ~50M records to avoid reallocations

  // 1. Read binary stream from stdin
  Interaction temp;
  while (std::cin.read(reinterpret_cast<char *>(&temp), sizeof(Interaction))) {
    interactions.push_back(temp);
  }

  std::cerr << "Loaded " << interactions.size() << " interactions into memory."
            << std::endl;

  // 2. Compute Aggregates (Pass 1)
  std::unordered_map<int32_t, EntityStats> userStats;
  std::unordered_map<int32_t, EntityStats> movieStats;
  // Pre-allocate maps if possible (estimation)
  userStats.reserve(300000);
  movieStats.reserve(60000);

  for (const auto &record : interactions) {
    // Update User Stats
    userStats[record.userId].sum += record.rating;
    userStats[record.userId].count++;

    // Update Movie Stats
    movieStats[record.movieId].sum += record.rating;
    movieStats[record.movieId].count++;
  }

  std::cerr << "Computed stats for " << userStats.size() << " users and "
            << movieStats.size() << " movies." << std::endl;

  // 3. Generate Features & Output CSV (Pass 2)
  // CSV Header
  std::cout << "userId,movieId,rating,timestamp,user_mean,user_count,movie_"
               "mean,movie_count"
            << std::endl;

  // Output formatting
  std::cout << std::fixed << std::setprecision(4);

  for (const auto &record : interactions) {
    double userMean = 0.0;
    int userCount = 0;
    if (userStats.find(record.userId) != userStats.end()) {
      userCount = userStats[record.userId].count;
      userMean = userStats[record.userId].sum / userCount;
    }

    double movieMean = 0.0;
    int movieCount = 0;
    if (movieStats.find(record.movieId) != movieStats.end()) {
      movieCount = movieStats[record.movieId].count;
      movieMean = movieStats[record.movieId].sum / movieCount;
    }

    std::cout << record.userId << "," << record.movieId << "," << record.rating
              << "," << record.timestamp << "," << userMean << "," << userCount
              << "," << movieMean << "," << movieCount << "\n";
  }

  std::cerr << "Processing complete." << std::endl;

  return 0;
}
