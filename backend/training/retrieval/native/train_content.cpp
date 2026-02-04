#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>
#include <map>
#include <unordered_map>
#include <iomanip>
#include <armadillo>
#include <omp.h>

// --- Logging Utils ---
void log_header(const std::string& title) {
    std::cout << "\n======================================================\n";
    std::cout << "   " << title << "\n";
    std::cout << "======================================================\n" << std::endl;
}

void log_info(const std::string& msg) {
    std::cout << "[Content-Based] [INFO] " << msg << std::endl;
}

void log_error(const std::string& msg) {
    std::cerr << "[Content-Based] [ERROR] " << msg << std::endl;
}

// Constants
const int TOP_N_TAGS = 10000; // Increased to 10000 as requested

struct MovieStats {
    double sum_rating = 0;
    int count_rating = 0;
};

// Helper for splitting strings
std::vector<std::string> split(const std::string& s, char delimiter) {
    std::vector<std::string> tokens;
    std::string token;
    std::istringstream tokenStream(s);
    while (std::getline(tokenStream, token, delimiter)) {
        tokens.push_back(token);
    }
    return tokens;
}

// Naive CSV parser
std::vector<std::string> parse_csv_line(const std::string& line) {
    return split(line, ',');
}

int main() {
    log_header("Starting Content-Based Model Training (High-Dim)");
    
    // Optimization for stdio
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string movies_path = "../../../data/raw/movies.csv";
    std::string ratings_path = "../../../data/raw/ratings.csv";
    std::string tags_path = "../../../data/raw/tags.csv";
    std::string output_dir = "../../../artifacts/native/";

    // 1. Load Movies & Extract Year/Genres
    log_info("Step 1/5: Loading Movies...");
    std::unordered_map<int, std::vector<std::string>> movie_genres;
    std::unordered_map<int, int> movie_years;
    std::vector<int> all_movie_ids;
    std::map<std::string, int> genre_vocab;
    int genre_idx = 0;

    std::ifstream f_mov(movies_path);
    if (!f_mov.is_open()) { log_error("Failed to open " + movies_path); return 1; }
    std::string line;
    std::getline(f_mov, line); // header

    while (std::getline(f_mov, line)) {
        if (line.empty()) continue;
        size_t first_comma = line.find(',');
        size_t last_comma = line.find_last_of(',');
        if (first_comma == std::string::npos || last_comma == std::string::npos) continue;

        int id = std::stoi(line.substr(0, first_comma));
        std::string title = line.substr(first_comma + 1, last_comma - first_comma - 1);
        std::string genres_str = line.substr(last_comma + 1);
        if (!genres_str.empty() && genres_str.back() == '\r') genres_str.pop_back();

        all_movie_ids.push_back(id);

        // Extract Year
        int year = 0;
        size_t open_paren = title.find_last_of('(');
        size_t close_paren = title.find_last_of(')');
        if (open_paren != std::string::npos && close_paren != std::string::npos && close_paren > open_paren) {
            try {
                year = std::stoi(title.substr(open_paren + 1, close_paren - open_paren - 1));
            } catch (...) { year = 0; }
        }
        movie_years[id] = year;

        // Genres
        auto genres = split(genres_str, '|');
        std::vector<std::string> clean_g;
        for (auto& g : genres) {
            if (g == "(no genres listed)") continue;
            if (genre_vocab.find(g) == genre_vocab.end()) genre_vocab[g] = genre_idx++;
            clean_g.push_back(g);
        }
        movie_genres[id] = clean_g;
    }
    f_mov.close();
    log_info("Loaded " + std::to_string(all_movie_ids.size()) + " movies. Genre Vocab: " + std::to_string(genre_vocab.size()));

    // 2. Load Ratings (Aggregate)
    log_info("Step 2/5: Loading Ratings...");
    std::unordered_map<int, MovieStats> stats;
    std::ifstream f_rat(ratings_path);
    if (f_rat.is_open()) {
        std::getline(f_rat, line); // header
        while (std::getline(f_rat, line)) {
            auto t = parse_csv_line(line);
            if (t.size() < 3) continue;
            try {
                int mid = std::stoi(t[1]);
                float r = std::stof(t[2]);
                stats[mid].sum_rating += r;
                stats[mid].count_rating++;
            } catch(...) {}
        }
        f_rat.close();
    }

    // 3. Load Tags (Find Top N)
    log_info("Step 3/5: Loading Tags & Filtering Top " + std::to_string(TOP_N_TAGS) + "...");
    std::unordered_map<std::string, int> tag_counts;
    std::unordered_map<int, std::vector<std::string>> movie_tags;
    std::ifstream f_tag(tags_path);
    if (f_tag.is_open()) {
        std::getline(f_tag, line); // header
        while (std::getline(f_tag, line)) {
            auto t = parse_csv_line(line);
            if (t.size() < 3) continue;
            try {
                int mid = std::stoi(t[1]);
                std::string tag = t[2];
                // Lowercase
                std::transform(tag.begin(), tag.end(), tag.begin(), ::tolower);
                tag_counts[tag]++;
                movie_tags[mid].push_back(tag);
            } catch(...) {}
        }
        f_tag.close();
    }

    // Select Top Tags
    std::vector<std::pair<int, std::string>> sorted_tags;
    for (auto& p : tag_counts) sorted_tags.push_back({p.second, p.first});
    std::sort(sorted_tags.rbegin(), sorted_tags.rend()); // Descending
    
    std::map<std::string, int> top_tag_vocab;
    for (int i = 0; i < std::min((int)sorted_tags.size(), TOP_N_TAGS); ++i) {
        top_tag_vocab[sorted_tags[i].second] = i;
    }
    log_info("Top Tag selection complete.");

    // 4. Build Feature Vectors (Dense Float)
    // Using float (fmat) to save RAM: 87k * 10k * 4 bytes ~= 3.5 GB
    log_info("Step 4/5: Building Dense Feature Matrix (Float precision)...");
    int dim = genre_vocab.size() + top_tag_vocab.size() + 3;
    arma::fmat features(all_movie_ids.size(), dim, arma::fill::zeros);

    // Prepare scalers
    float max_year = 0, min_year = 3000;
    float max_pop = 0;
    
    for (int mid : all_movie_ids) {
        if (movie_years[mid] > 0) {
            if (movie_years[mid] > max_year) max_year = movie_years[mid];
            if (movie_years[mid] < min_year) min_year = movie_years[mid];
        }
        if (stats[mid].count_rating > max_pop) max_pop = stats[mid].count_rating;
    }

    int total_movies = all_movie_ids.size();
    
    // Parallel Feature Construction
    // OpenMP requires -fopenmp flag during compilation
    int processed = 0;
    
    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < total_movies; ++i) {
        int mid = all_movie_ids[i];
        
        // Feature: Genres
        if (movie_genres.count(mid)) {
            const auto& genres = movie_genres.at(mid);
            for (const auto& g : genres) {
                if (genre_vocab.count(g)) {
                    features(i, genre_vocab.at(g)) = 1.0f;
                }
            }
        }

        // Tags
        int tag_offset = genre_vocab.size();
        if (movie_tags.count(mid)) {
            const auto& tags = movie_tags.at(mid);
            for (const auto& t : tags) {
                if (top_tag_vocab.count(t)) {
                    features(i, tag_offset + top_tag_vocab.at(t)) = 1.0f;
                }
            }
        }

        // Numerical
        int num_offset = tag_offset + top_tag_vocab.size();
        
        float year = (float)movie_years[mid];
        if (year > 0) {
            features(i, num_offset) = (year - min_year) / (max_year - min_year + 1e-5f);
        }
        
        float avg_r = 0;
        if (stats.count(mid)) {
            const auto& s = stats.at(mid);
            if (s.count_rating > 0) avg_r = s.sum_rating / s.count_rating;
        }
        features(i, num_offset + 1) = avg_r / 5.0f;

        float count = 0;
        if (stats.count(mid)) count = (float)stats.at(mid).count_rating;
        float pop = std::log(count + 1.0f);
        features(i, num_offset + 2) = pop / std::log(max_pop + 1.0f);

        // L2 Normalize
        float sq_sum = 0;
        for(int c=0; c<dim; ++c) sq_sum += features(i, c) * features(i, c);
        if (sq_sum > 1e-9) {
            float scale = 1.0f / std::sqrt(sq_sum);
            for(int c=0; c<dim; ++c) features(i, c) *= scale;
        }

        #pragma omp atomic
        processed++;
        
        if (processed % 5000 == 0) {
            #pragma omp critical
            {
                std::cout << "\r[Content-Based] [INFO] Building features: " << (processed * 100 / total_movies) << "% (" << processed << "/" << total_movies << ")..." << std::flush;
            }
        }
    }
    std::cout << "\r[Content-Based] [INFO] Building features: 100%..." << std::endl;

    // 5. Save
    log_info("Step 5/5: Saving Artifacts...");
    std::string cmd = "mkdir -p " + output_dir;
    system(cmd.c_str());

    std::string out_path = output_dir + "content_embeddings.bin";
    // Saving float matrix
    features.save(out_path, arma::raw_binary);
    
    std::ofstream meta(output_dir + "content_embeddings_meta.txt");
    meta << features.n_rows << " " << features.n_cols << "\n";
    meta.close();
    
    std::ofstream map_file(output_dir + "content_movie_ids.txt");
    for (int id : all_movie_ids) map_file << id << "\n";
    map_file.close();

    log_info("Success! Saved " + std::to_string(features.n_rows) + "x" + std::to_string(features.n_cols) + " embeddings.");
    return 0;
}