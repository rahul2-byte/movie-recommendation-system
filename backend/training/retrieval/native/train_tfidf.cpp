#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>
#include <map>
#include <unordered_map>
#include <armadillo>

// --- Logging Utils ---
void log_header(const std::string& title) {
    std::cout << "\n======================================================\n";
    std::cout << "   " << title << "\n";
    std::cout << "======================================================\n" << std::endl;
}

void log_info(const std::string& msg) {
    std::cout << "[TF-IDF] [INFO] " << msg << std::endl;
}

void log_error(const std::string& msg) {
    std::cerr << "[TF-IDF] [ERROR] " << msg << std::endl;
}

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

int main() {
    log_header("Starting TF-IDF Training (Armadillo)");
    
    // Optimization for stdio
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string movies_path = "../../../data/raw/movies.csv";
    std::string output_dir = "../../../artifacts/native/";

    std::ifstream file(movies_path);
    if (!file.is_open()) {
        log_error("Could not open " + movies_path);
        return 1;
    }

    std::string line;
    std::getline(file, line); // Skip header

    // Data containers
    std::vector<int> movie_ids;
    // We need to build the matrix. Since we don't know vocab size yet, 
    // we'll store docs as list of genre indices after first pass.
    std::map<std::string, int> genre_vocab;
    int vocab_idx = 0;
    
    // Temporary storage for processing
    struct Doc {
        int id;
        std::vector<int> genre_indices;
    };
    std::vector<Doc> docs;

    // 1. Read and Build Vocab
    log_info("Step 1/3: Reading Movies & Building Vocabulary...");
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        
        size_t first_comma = line.find(',');
        size_t last_comma = line.find_last_of(',');
        
        if (first_comma == std::string::npos || last_comma == std::string::npos || first_comma == last_comma) {
            continue; 
        }

        int id = std::stoi(line.substr(0, first_comma));
        std::string genres_str = line.substr(last_comma + 1);
        if (!genres_str.empty() && genres_str.back() == '\r') genres_str.pop_back();

        auto genres = split(genres_str, '|');
        Doc d;
        d.id = id;
        
        for (auto& g : genres) {
            if (g == "(no genres listed)") continue;
            if (genre_vocab.find(g) == genre_vocab.end()) {
                genre_vocab[g] = vocab_idx++;
            }
            d.genre_indices.push_back(genre_vocab[g]);
        }
        docs.push_back(d);
        movie_ids.push_back(id);
    }
    file.close();

    int num_movies = docs.size();
    int vocab_size = genre_vocab.size();
    log_info("Loaded " + std::to_string(num_movies) + " movies.");
    log_info("Vocabulary Size (Genres): " + std::to_string(vocab_size));

    // 2. Build TF-IDF with Armadillo
    log_info("Step 2/3: Calculating TF-IDF...");
    std::vector<arma::uword> rows;
    std::vector<arma::uword> cols;
    std::vector<double> values;

    // A. Count Frequencies (TF) and Doc Frequencies (DF)
    arma::vec df(vocab_size, arma::fill::zeros);
    
    for (int i = 0; i < num_movies; ++i) {
        const auto& d = docs[i];
        if (d.genre_indices.empty()) continue;
        
        double tf = 1.0 / std::max(1.0, (double)d.genre_indices.size());
        
        for (int g_idx : d.genre_indices) {
            rows.push_back(i); // Document is Row
            cols.push_back(g_idx); // Term is Col
            values.push_back(tf); 
            df[g_idx] += 1.0;
        }
    }

    // B. Calculate IDF
    arma::vec idf(vocab_size);
    for (int i = 0; i < vocab_size; ++i) {
        idf[i] = std::log((double)(num_movies + 1) / (df[i] + 1)) + 1.0;
    }

    // C. Apply IDF and Build Matrix
    for (size_t i = 0; i < values.size(); ++i) {
        int term_idx = cols[i];
        values[i] *= idf[term_idx];
    }

    // Create Sparse Matrix
    arma::umat locations(2, rows.size());
    arma::vec vals(values.size());
    for(size_t i=0; i<rows.size(); ++i) {
        locations(0, i) = rows[i];
        locations(1, i) = cols[i];
        vals(i) = values[i];
    }

    arma::sp_mat tfidf(locations, vals, num_movies, vocab_size);

    // D. L2 Normalization (Row-wise)
    log_info("Normalizing matrix...");
    arma::mat dense_tfidf(tfidf);
    
    // Row-wise normalization
    for (int i = 0; i < num_movies; ++i) {
        double n = arma::norm(dense_tfidf.row(i), 2);
        if (n > 1e-9) {
            dense_tfidf.row(i) /= n;
        }
    }

    // 3. Save
    log_info("Step 3/3: Saving Artifacts...");
    std::string cmd = "mkdir -p " + output_dir;
    system(cmd.c_str());

    std::string out_path = output_dir + "tfidf_matrix.bin";
    dense_tfidf.save(out_path, arma::raw_binary);
    
    std::ofstream meta(output_dir + "tfidf_meta.txt");
    meta << dense_tfidf.n_rows << " " << dense_tfidf.n_cols << "\n";
    meta.close();
    
    std::ofstream map_file(output_dir + "tfidf_movie_ids.txt");
    for (int id : movie_ids) map_file << id << "\n";
    map_file.close();
    
    std::ofstream vocab_file(output_dir + "tfidf_vocab.txt");
    for (const auto& pair : genre_vocab) vocab_file << pair.first << "," << pair.second << "\n";
    vocab_file.close();

    log_info("Success! Saved " + std::to_string(dense_tfidf.n_rows) + "x" + std::to_string(dense_tfidf.n_cols) + " embeddings.");
    return 0;
}
