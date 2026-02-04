#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <armadillo>
#include <mlpack/methods/cf/cf.hpp>
#include <mlpack/methods/cf/decomposition_policies/regularized_svd_method.hpp>

// --- Logging Utils ---
void log_header(const std::string& title) {
    std::cout << "\n======================================================\n";
    std::cout << "   " << title << "\n";
    std::cout << "======================================================\n" << std::endl;
}

void log_info(const std::string& msg) {
    std::cout << "[ALS] [INFO] " << msg << std::endl;
}

void log_error(const std::string& msg) {
    std::cerr << "[ALS] [ERROR] " << msg << std::endl;
}

// -------------------------------------------------------------------------
// CONSTANTS
// -------------------------------------------------------------------------
const int EMBEDDING_DIM = 64;
const int MAX_ITERATIONS = 20;

// -------------------------------------------------------------------------
// MAIN
// -------------------------------------------------------------------------
int main(int argc, char** argv) {
    log_header("Starting ALS (RegSVD) Training");
    
    // Optimization for stdio
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // 1. Read Binary Data
    log_info("Reading Binary Data from Pipeline...");
    int32_t num_movies, num_users;
    int64_t num_interactions;

    if (!std::cin.read(reinterpret_cast<char*>(&num_movies), sizeof(int32_t))) {
        log_error("Failed to read header from stdin.");
        return 1;
    }
    std::cin.read(reinterpret_cast<char*>(&num_users), sizeof(int32_t));
    std::cin.read(reinterpret_cast<char*>(&num_interactions), sizeof(int64_t));

    log_info("Header: " + std::to_string(num_movies) + " movies, " + std::to_string(num_users) + " users, " + std::to_string(num_interactions) + " interactions.");

    // Read ID Mapping
    std::vector<int32_t> idx_to_movie(num_movies);
    std::cin.read(reinterpret_cast<char*>(idx_to_movie.data()), num_movies * sizeof(int32_t));

    // Read COO Vectors
    std::vector<int32_t> item_indices(num_interactions);
    std::vector<int32_t> user_indices(num_interactions);
    std::cin.read(reinterpret_cast<char*>(item_indices.data()), num_interactions * sizeof(int32_t));
    std::cin.read(reinterpret_cast<char*>(user_indices.data()), num_interactions * sizeof(int32_t));

    // 2. Prepare Data for Mlpack
    log_info("Preparing Data Matrix (3 x " + std::to_string(num_interactions) + ")...");
    arma::mat data(3, num_interactions);
    
    for (int64_t i = 0; i < num_interactions; ++i) {
        data(0, i) = static_cast<double>(user_indices[i]);
        data(1, i) = static_cast<double>(item_indices[i]);
        data(2, i) = 1.0; 
    }

    // 3. Train Model
    log_info("Training Model (Rank " + std::to_string(EMBEDDING_DIM) + ", Iter " + std::to_string(MAX_ITERATIONS) + ")...");
    mlpack::RegSVDPolicy policy(MAX_ITERATIONS);
    
    mlpack::CFType<mlpack::RegSVDPolicy> cf(data, 
                                            policy, 
                                            5, 
                                            EMBEDDING_DIM, 
                                            MAX_ITERATIONS);

    // 4. Extract Embeddings
    const arma::mat& W = cf.Decomposition().W();
    const arma::mat& H = cf.Decomposition().H();

    log_info("Training complete.");
    log_info("Item Factors (W): " + std::to_string(W.n_rows) + "x" + std::to_string(W.n_cols));
    log_info("User Factors (H): " + std::to_string(H.n_rows) + "x" + std::to_string(H.n_cols));

    // 5. Save Artifacts
    log_info("Saving Artifacts...");
    std::string output_dir = "../../../artifacts/native/";
    
    // Attempt mkdir with absolute path check if needed, but relative should work if CWD is correct.
    // Use simple system call.
    int ret = system(("mkdir -p " + output_dir).c_str());
    if (ret != 0) {
        log_error("Failed to create directory " + output_dir);
        // Try absolute path based on assumption? No, keep going, maybe exists.
    }

    std::string emb_path = output_dir + "als_item_embeddings.bin";
    W.save(emb_path, arma::raw_binary);
    
    std::ofstream meta(output_dir + "als_embeddings_meta.txt");
    meta << W.n_rows << " " << W.n_cols << "\n";
    meta.close();

    std::ofstream map_file(output_dir + "als_movie_ids.txt");
    for (int32_t id : idx_to_movie) {
        map_file << id << "\n";
    }
    map_file.close();
    
    log_info("Success! Saved artifacts to " + output_dir);
    return 0;
}
