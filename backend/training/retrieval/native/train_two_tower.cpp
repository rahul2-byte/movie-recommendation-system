#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>
#include <map>
#include <unordered_map>
#include <thread>
#include <mutex>
#include <atomic>
#include <random>
#include <armadillo>
#include <iomanip>
#include <omp.h>

// --- Logging Utils ---
void log_header(const std::string& title) {
    std::cout << "\n======================================================\n";
    std::cout << "   " << title << "\n";
    std::cout << "======================================================\n" << std::endl;
}

void log_info(const std::string& msg) {
    std::cout << "[Two-Tower] [INFO] " << msg << std::endl;
}

void log_error(const std::string& msg) {
    std::cerr << "[Two-Tower] [ERROR] " << msg << std::endl;
}

// Constants
const int TOP_N_TAGS = 10000; 
const int EMBEDDING_DIM = 64;
const float LEARNING_RATE = 0.001f;
const int EPOCHS = 5; 
const int BATCH_SIZE = 1024; 
const int NUM_NEGATIVES = 2;
const float GRAD_CLIP_NORM = 5.0f; // Gradient Clipping

// --- Sparse Feature Structure ---
struct SparseFeatureVec {
    arma::uvec indices;
    arma::fvec values;
};

struct Sequence {
    std::vector<int> query_ids; 
    int pos_id; 
};

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

std::vector<std::string> parse_csv_line(const std::string& line) {
    return split(line, ',');
}

inline float sigmoid(float x) {
    return 1.0f / (1.0f + std::exp(-x));
}

// --- Sparse Operations ---
inline arma::fvec forward_sparse(const arma::fmat& W, const arma::fvec& b, const SparseFeatureVec& x) {
    arma::fvec y = b;
    for(size_t i=0; i < x.indices.n_elem; ++i) {
        y += W.col(x.indices[i]) * x.values[i];
    }
    return y;
}

inline void backward_sparse_W(arma::fmat& W_grad, const arma::fvec& dL_dy, const SparseFeatureVec& x) {
    for(size_t i=0; i < x.indices.n_elem; ++i) {
        W_grad.col(x.indices[i]) += dL_dy * x.values[i];
    }
}

int main() {
    log_header("Starting Two-Tower Model Training (Sparse Optimized + Stable)");
    
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string movies_path = "../../../data/raw/movies.csv";
    std::string ratings_path = "../../../data/raw/ratings.csv";
    std::string tags_path = "../../../data/raw/tags.csv";
    std::string sequences_path = "../../../data/processed/training_sequences.csv";
    std::string output_dir = "../../../artifacts/native/";

    // --- 1. Feature Engineering ---
    log_info("Step 1/6: Loading Movies...");
    std::unordered_map<int, std::vector<std::string>> movie_genres;
    std::unordered_map<int, int> movie_years;
    std::vector<int> all_movie_ids;
    std::unordered_map<int, int> id_to_idx;
    std::map<std::string, int> genre_vocab;
    int genre_idx = 0;

    std::ifstream f_mov(movies_path);
    if (!f_mov.is_open()) return 1;
    std::string line;
    std::getline(f_mov, line); 

    while (std::getline(f_mov, line)) {
        if (line.empty()) continue;
        size_t first_comma = line.find(',');
        size_t last_comma = line.find_last_of(',');
        if (first_comma == std::string::npos || last_comma == std::string::npos) continue;

        int id = std::stoi(line.substr(0, first_comma));
        std::string title = line.substr(first_comma + 1, last_comma - first_comma - 1);
        std::string genres_str = line.substr(last_comma + 1);
        if (!genres_str.empty() && genres_str.back() == '\r') genres_str.pop_back();

        id_to_idx[id] = all_movie_ids.size();
        all_movie_ids.push_back(id);

        int year = 0;
        try {
            size_t open = title.find_last_of('(');
            size_t close = title.find_last_of(')');
            if (open != std::string::npos && close > open) 
                year = std::stoi(title.substr(open + 1, close - open - 1));
        } catch(...) {}
        movie_years[id] = year;

        auto genres = split(genres_str, '|');
        for (auto& g : genres) {
            if (g == "(no genres listed)") continue;
            if (genre_vocab.find(g) == genre_vocab.end()) genre_vocab[g] = genre_idx++;
            movie_genres[id].push_back(g);
        }
    }
    f_mov.close();

    log_info("Step 2/6: Loading Ratings...");
    std::unordered_map<int, MovieStats> stats;
    std::ifstream f_rat(ratings_path);
    if (f_rat.is_open()) {
        std::getline(f_rat, line);
        while (std::getline(f_rat, line)) {
            auto t = parse_csv_line(line);
            if (t.size() < 3) continue;
            try {
                int mid = std::stoi(t[1]);
                if (id_to_idx.count(mid)) {
                    stats[mid].sum_rating += std::stof(t[2]);
                    stats[mid].count_rating++;
                }
            } catch(...) {}
        }
        f_rat.close();
    }

    log_info("Step 3/6: Loading Tags...");
    std::unordered_map<std::string, int> tag_counts;
    std::unordered_map<int, std::vector<std::string>> movie_tags;
    std::ifstream f_tag(tags_path);
    if (f_tag.is_open()) {
        std::getline(f_tag, line);
        while (std::getline(f_tag, line)) {
            auto t = parse_csv_line(line);
            if (t.size() < 3) continue;
            try {
                int mid = std::stoi(t[1]);
                if (id_to_idx.count(mid)) {
                    std::string tag = t[2];
                    std::transform(tag.begin(), tag.end(), tag.begin(), ::tolower);
                    tag_counts[tag]++;
                    movie_tags[mid].push_back(tag);
                }
            } catch(...) {}
        }
        f_tag.close();
    }

    std::vector<std::pair<int, std::string>> sorted_tags;
    for (auto& p : tag_counts) sorted_tags.push_back({p.second, p.first});
    std::sort(sorted_tags.rbegin(), sorted_tags.rend());
    
    std::map<std::string, int> top_tag_vocab;
    for (int i = 0; i < std::min((int)sorted_tags.size(), TOP_N_TAGS); ++i) {
        top_tag_vocab[sorted_tags[i].second] = i;
    }

    // --- Build Sparse Feature Matrix ---
    log_info("Step 4/6: Building Sparse Features (Normalized)...");
    int input_dim = genre_vocab.size() + top_tag_vocab.size() + 3;
    std::vector<SparseFeatureVec> sparse_features(all_movie_ids.size());
    
    float max_year = 0, min_year = 3000, max_pop = 0;
    for (int mid : all_movie_ids) {
        if (movie_years[mid] > 0) {
            max_year = std::max(max_year, (float)movie_years[mid]);
            min_year = std::min(min_year, (float)movie_years[mid]);
        }
        max_pop = std::max(max_pop, (float)stats[mid].count_rating);
    }

    #pragma omp parallel for
    for (size_t i = 0; i < all_movie_ids.size(); ++i) {
        int mid = all_movie_ids[i];
        std::vector<arma::uword> idxs;
        std::vector<float> vals;
        idxs.reserve(32); vals.reserve(32);

        // Genres
        auto genres_it = movie_genres.find(mid);
        if (genres_it != movie_genres.end()) {
            for (const auto& g : genres_it->second) {
                auto v_it = genre_vocab.find(g);
                if (v_it != genre_vocab.end()) {
                    idxs.push_back(v_it->second);
                    vals.push_back(1.0f);
                }
            }
        }
        
        // Tags
        int tag_offset = genre_vocab.size();
        auto tags_it = movie_tags.find(mid);
        if (tags_it != movie_tags.end()) {
            for (const auto& t : tags_it->second) {
                auto v_it = top_tag_vocab.find(t);
                if (v_it != top_tag_vocab.end()) {
                    idxs.push_back(tag_offset + v_it->second);
                    vals.push_back(1.0f);
                }
            }
        }
        
        // Numerical
        int num_offset = tag_offset + top_tag_vocab.size();
        auto year_it = movie_years.find(mid);
        if (year_it != movie_years.end() && year_it->second > 0) {
            idxs.push_back(num_offset);
            vals.push_back((year_it->second - min_year) / (max_year - min_year + 1e-5f));
        }
        
        float avg_r = 0;
        auto stat_it = stats.find(mid);
        if (stat_it != stats.end() && stat_it->second.count_rating > 0) {
            avg_r = stat_it->second.sum_rating / stat_it->second.count_rating;
        }
        idxs.push_back(num_offset + 1);
        vals.push_back(avg_r / 5.0f);
        
        float count = (stat_it != stats.end()) ? (float)stat_it->second.count_rating : 0.0f;
        float pop = std::log(count + 1.0f);
        idxs.push_back(num_offset + 2);
        vals.push_back(pop / std::log(max_pop + 1.0f));

        // L2 Normalization (Crucial!)
        float sq_sum = 0.0f;
        for (float v : vals) sq_sum += v * v;
        if (sq_sum > 1e-9f) {
            float scale = 1.0f / std::sqrt(sq_sum);
            for (float& v : vals) v *= scale;
        }

        sparse_features[i].indices = arma::uvec(idxs);
        sparse_features[i].values = arma::fvec(vals);
    }
    log_info("Features Built. Total Movies: " + std::to_string(all_movie_ids.size()));

    // --- 2. Load Sequences ---
    log_info("Step 5/6: Loading Training Sequences...");
    std::vector<Sequence> sequences;
    std::ifstream f_seq(sequences_path);
    if (f_seq.is_open()) {
        std::getline(f_seq, line); 
        while (std::getline(f_seq, line)) {
            auto t = parse_csv_line(line);
            if (t.size() < 3) continue;
            if (t[2] != "1") continue; 

            Sequence seq;
            auto q_tokens = split(t[0], '|');
            for (auto& q : q_tokens) {
                try {
                    int qid = std::stoi(q);
                    auto it = id_to_idx.find(qid);
                    if (it != id_to_idx.end()) seq.query_ids.push_back(it->second);
                } catch(...) {}
            }
            try {
                int pid = std::stoi(t[1]);
                auto it = id_to_idx.find(pid);
                if (it != id_to_idx.end()) {
                    seq.pos_id = it->second;
                    sequences.push_back(seq);
                }
            } catch(...) {}
        }
        f_seq.close();
    }
    log_info("Loaded " + std::to_string(sequences.size()) + " positive sequences.");

    // --- 3. Init Weights ---
    arma::fmat W(EMBEDDING_DIM, input_dim, arma::fill::randn);
    W *= 0.05f;
    arma::fvec b(EMBEDDING_DIM, arma::fill::zeros);

    // --- 4. Training Loop ---
    unsigned int num_threads = std::thread::hardware_concurrency();
    if (num_threads == 0) num_threads = 2;
    log_info("Step 6/6: Training Model (Threads: " + std::to_string(num_threads) + ", Batch Size: " + std::to_string(BATCH_SIZE) + ")...");

    std::mt19937 global_rng(42);
    size_t total_batches = (sequences.size() + BATCH_SIZE - 1) / BATCH_SIZE;
    
    for (int epoch = 0; epoch < EPOCHS; ++epoch) {
        std::shuffle(sequences.begin(), sequences.end(), global_rng);
        double total_loss = 0;
        int processed_batches = 0;

        for (size_t batch_start = 0; batch_start < sequences.size(); batch_start += BATCH_SIZE) {
            size_t batch_end = std::min(batch_start + BATCH_SIZE, sequences.size());
            size_t current_batch_size = batch_end - batch_start;
            
            arma::fmat batch_W_grad(EMBEDDING_DIM, input_dim, arma::fill::zeros);
            arma::fvec batch_b_grad(EMBEDDING_DIM, arma::fill::zeros);
            std::atomic<double> batch_loss(0.0);
            std::mutex grad_mutex;

            auto worker = [&](size_t start, size_t end, int thread_id) {
                arma::fmat local_W_grad(EMBEDDING_DIM, input_dim, arma::fill::zeros);
                arma::fvec local_b_grad(EMBEDDING_DIM, arma::fill::zeros);
                std::mt19937 local_rng(42 + thread_id + epoch * 100);
                double local_loss = 0;

                for (size_t i = start; i < end; ++i) {
                    const auto& seq = sequences[i];
                    if (seq.query_ids.empty()) continue;

                    arma::fvec q_emb(EMBEDDING_DIM, arma::fill::zeros);
                    for(int q_idx : seq.query_ids) {
                        q_emb += forward_sparse(W, b, sparse_features[q_idx]);
                    }
                    float inv_n = 1.0f / seq.query_ids.size();
                    q_emb *= inv_n;
                    
                    arma::fvec p_emb = forward_sparse(W, b, sparse_features[seq.pos_id]);

                    for(int n=0; n<NUM_NEGATIVES; ++n) {
                        int neg_idx = local_rng() % sparse_features.size();
                        arma::fvec n_emb = forward_sparse(W, b, sparse_features[neg_idx]);

                        float s_pos = arma::dot(q_emb, p_emb);
                        float s_neg = arma::dot(q_emb, n_emb);
                        float diff = s_pos - s_neg;
                        float sig_diff = sigmoid(diff);
                        
                        if (std::isnan(sig_diff)) continue;
                        local_loss += -std::log(sig_diff + 1e-9f);

                        float grad_factor = sig_diff - 1.0f;
                        arma::fvec d_q = grad_factor * (p_emb - n_emb);
                        arma::fvec d_p = grad_factor * q_emb;
                        arma::fvec d_n = -grad_factor * q_emb;

                        local_b_grad += d_p + d_n + d_q;
                        backward_sparse_W(local_W_grad, d_p, sparse_features[seq.pos_id]);
                        backward_sparse_W(local_W_grad, d_n, sparse_features[neg_idx]);
                        
                        arma::fvec d_qi = d_q * inv_n;
                        for(int q_idx : seq.query_ids) {
                            local_b_grad += d_qi;
                            backward_sparse_W(local_W_grad, d_qi, sparse_features[q_idx]);
                        }
                    }
                }

                std::lock_guard<std::mutex> lock(grad_mutex);
                batch_W_grad += local_W_grad;
                batch_b_grad += local_b_grad;
                
                double current = batch_loss.load();
                while(!batch_loss.compare_exchange_weak(current, current + local_loss));
            };

            std::vector<std::thread> threads;
            size_t items_per_thread = (current_batch_size + num_threads - 1) / num_threads;
            
            for (unsigned int t = 0; t < num_threads; ++t) {
                size_t t_start = batch_start + t * items_per_thread;
                size_t t_end = std::min(t_start + items_per_thread, batch_end);
                if (t_start < t_end) threads.emplace_back(worker, t_start, t_end, t);
            }
            for (auto& t : threads) t.join();

            // Gradient Clipping
            float grad_norm = arma::norm(batch_W_grad, 2);
            if (grad_norm > GRAD_CLIP_NORM) {
                float scale = GRAD_CLIP_NORM / grad_norm;
                batch_W_grad *= scale;
                batch_b_grad *= scale;
            }

            W -= LEARNING_RATE * batch_W_grad;
            b -= LEARNING_RATE * batch_b_grad;
            total_loss += batch_loss.load();
            processed_batches++;

            if (processed_batches % 500 == 0 || processed_batches == (int)total_batches) {
                double avg_loss = total_loss / (processed_batches * BATCH_SIZE);
                std::cout << "\r[Two-Tower] [INFO] Epoch " << (epoch + 1) << "/" << EPOCHS 
                          << " | Batch " << processed_batches << "/" << total_batches 
                          << " | Loss: " << std::fixed << std::setprecision(4) << avg_loss
                          << "   " << std::flush;
            }
        }
        std::cout << std::endl;
    }

    // --- 5. Save Embeddings ---
    log_info("Generating all embeddings for export...");
    arma::fmat embeddings(EMBEDDING_DIM, all_movie_ids.size());
    
    #pragma omp parallel for
    for (size_t i = 0; i < all_movie_ids.size(); ++i) {
        embeddings.col(i) = forward_sparse(W, b, sparse_features[i]);
    }
    arma::fmat embeddings_t = embeddings.t(); 

    std::string cmd = "mkdir -p " + output_dir;
    system(cmd.c_str());

    std::string out_path = output_dir + "two_tower_embeddings.bin";
    embeddings_t.save(out_path, arma::raw_binary);
    
    std::ofstream meta(output_dir + "two_tower_embeddings_meta.txt");
    meta << embeddings_t.n_rows << " " << embeddings_t.n_cols << "\n";
    meta.close();
    
    std::ofstream map_file(output_dir + "two_tower_movie_ids.txt");
    for (int id : all_movie_ids) map_file << id << "\n";
    map_file.close();

    log_info("Training complete. Saved artifacts to " + output_dir);
    return 0;
}
