#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <algorithm>
#include <cmath>
#include <random>
#include <omp.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <cstring>
#include <atomic>
#include <iomanip>
#include <armadillo>

// --- Configuration ---
const int EMBEDDING_DIM = 64;
const int BATCH_SIZE = 1024; 
const float LEARNING_RATE = 0.01f; 
const int EPOCHS = 5;

// --- Memory Mapped Data Structure ---
template <typename T>
struct MappedArray {
    T* data;
    size_t size;
    int fd;

    MappedArray(const std::string& path) {
        fd = open(path.c_str(), O_RDONLY);
        if (fd == -1) {
            std::cerr << "Error opening " << path << std::endl;
            exit(1);
        }
        struct stat sb;
        fstat(fd, &sb);
        size = sb.st_size / sizeof(T);
        data = (T*)mmap(NULL, sb.st_size, PROT_READ, MAP_SHARED, fd, 0);
        if (data == MAP_FAILED) {
            std::cerr << "mmap failed for " << path << std::endl;
            exit(1);
        }
    }
    ~MappedArray() { if (fd != -1) close(fd); }
    const T& operator[](size_t i) const { return data[i]; }
};

// SIMD-friendly Adagrad Update
inline void adagrad_update(float* __restrict__ w, float* __restrict__ g_accum, const float* __restrict__ grad, float val, int dim) {
    // We update 'dim' elements.
    // val is the feature value (scalar scaling for the gradient vector)
    for (int d = 0; d < dim; ++d) {
        float g = grad[d] * val;
        // Atomic update not strictly required for HOGWILD, but good to be aware.
        // For max speed, we accept race conditions (Hogwild).
        g_accum[d] += g * g;
        w[d] -= LEARNING_RATE * g / (std::sqrt(g_accum[d]) + 1e-7f);
    }
}

int main(int argc, char** argv) {
    std::cout << "--- [Fast Two-Tower V4] Matrix-Optimized & Vectorized ---" << std::endl;
    
    std::string base_dir = "backend/data/binary_cache/";
    if (argc > 1) base_dir = argv[1];
    std::string artifact_dir = "backend/artifacts/native/";
    if (argc > 2) artifact_dir = argv[2];

    // 1. Load Meta
    int num_movies = 0, num_features = 0;
    std::ifstream meta_file(base_dir + "features_meta.bin", std::ios::binary);
    if (!meta_file.is_open()) {
        std::cerr << "Error: Could not open features_meta.bin" << std::endl;
        return 1;
    }
    meta_file.read((char*)&num_movies, sizeof(int));
    meta_file.read((char*)&num_features, sizeof(int));
    meta_file.close();

    MappedArray<int> offsets(base_dir + "features_offsets.bin");
    MappedArray<int> indices(base_dir + "features_indices.bin");
    MappedArray<float> values(base_dir + "features_values.bin");
    MappedArray<int> train_data(base_dir + "train_data.bin");
    size_t num_samples = train_data.size / 6;
    std::cout << "Samples: " << num_samples << " | Features: " << num_features << std::endl;

    // 2. Initialize Weights
    arma::fmat weights(EMBEDDING_DIM, num_features, arma::fill::randn);
    weights *= 0.01f;
    arma::fmat grad_accum(EMBEDDING_DIM, num_features, arma::fill::zeros);
    grad_accum.fill(1e-6f); // Avoid div by zero
    
    std::vector<int> sample_indices(num_samples);
    for(size_t i=0; i<num_samples; ++i) sample_indices[i] = i;
    std::mt19937 rng(42);

    // 3. Training Loop
    for (int epoch = 0; epoch < EPOCHS; ++epoch) {
        std::shuffle(sample_indices.begin(), sample_indices.end(), rng);
        double epoch_loss = 0;
        std::atomic<int> processed(0);

        #pragma omp parallel
        {
            // Thread-local scratchpads
            arma::fmat q_batch(EMBEDDING_DIM, BATCH_SIZE);
            arma::fmat p_batch(EMBEDDING_DIM, BATCH_SIZE);
            arma::fmat scores(BATCH_SIZE, BATCH_SIZE);
            arma::fmat grad_scores(BATCH_SIZE, BATCH_SIZE);
            arma::fmat q_grads(EMBEDDING_DIM, BATCH_SIZE);
            arma::fmat p_grads(EMBEDDING_DIM, BATCH_SIZE);

            #pragma omp for schedule(static) reduction(+:epoch_loss)
            for (size_t i = 0; i < num_samples; i += BATCH_SIZE) {
                int cur_batch = std::min((size_t)BATCH_SIZE, num_samples - i);
                
                // A. Forward Pass (Gather Embeddings)
                // Zero out only used columns
                if (cur_batch < BATCH_SIZE) {
                    q_batch.cols(0, cur_batch-1).zeros();
                    p_batch.cols(0, cur_batch-1).zeros();
                } else {
                    q_batch.zeros();
                    p_batch.zeros();
                }

                for (int b = 0; b < cur_batch; ++b) {
                    const int* row = &train_data.data[sample_indices[i + b] * 6];
                    
                    // Query (Average of 5 seeds)
                    float* q_col_ptr = q_batch.colptr(b);
                    int valid = 0;
                    for (int s = 0; s < 5; ++s) {
                        int mid = row[s]; 
                        if (mid < 0 || mid >= num_movies) continue; // Should use 0 check if 0 is padding
                        // Assuming 0 is padding or handled by offsets being empty/dummy
                        if (mid == 0) continue; 

                        valid++;
                        int start = offsets[mid], end = offsets[mid+1];
                        for (int k = start; k < end; ++k) {
                            int f_idx = indices[k];
                            float val = values[k];
                            const float* w_ptr = weights.colptr(f_idx);
                            for(int d=0; d<EMBEDDING_DIM; ++d) q_col_ptr[d] += w_ptr[d] * val;
                        }
                    }
                    if (valid > 0) {
                        float inv_valid = 1.0f / valid;
                        for(int d=0; d<EMBEDDING_DIM; ++d) q_col_ptr[d] *= inv_valid;
                    }

                    // Positive Item
                    int pos_id = row[5];
                    float* p_col_ptr = p_batch.colptr(b);
                    int start = offsets[pos_id], end = offsets[pos_id+1];
                    for (int k = start; k < end; ++k) {
                        int f_idx = indices[k];
                        float val = values[k];
                        const float* w_ptr = weights.colptr(f_idx);
                        for(int d=0; d<EMBEDDING_DIM; ++d) p_col_ptr[d] += w_ptr[d] * val;
                    }
                }

                // B. Scoring & Loss (BLAS Level 3)
                // Use submatrices for actual batch size
                arma::fmat q_sub = q_batch.cols(0, cur_batch - 1);
                arma::fmat p_sub = p_batch.cols(0, cur_batch - 1);
                
                // scores = Q^T * P
                arma::fmat batch_scores = q_sub.t() * p_sub; // (Batch x Batch)

                // Softmax & Gradient Computation
                // dL/dS = Softmax(S) - Identity
                float batch_loss = 0;
                arma::fmat batch_grad_scores(cur_batch, cur_batch);
                
                for (int r = 0; r < cur_batch; ++r) {
                    arma::fvec row_scores = batch_scores.row(r).t();
                    float max_s = row_scores.max();
                    // Numerical stability
                    arma::fvec exps = arma::exp(row_scores - max_s);
                    float sum_exps = arma::sum(exps);
                    
                    // Log-Softmax Loss for the diagonal (positive)
                    float prob = exps(r) / sum_exps;
                    batch_loss -= std::log(std::max(prob, 1e-7f));

                    // Gradient w.r.t Scores
                    arma::fvec grads = exps / sum_exps;
                    grads(r) -= 1.0f; // Subtract 1 for target
                    batch_grad_scores.row(r) = grads.t();
                }
                epoch_loss += batch_loss;

                // C. Compute Gradients (BLAS Level 3)
                // Q_grads = P * GradScores^T
                // P_grads = Q * GradScores
                
                // Subviews
                arma::fmat q_grads_sub = p_sub * batch_grad_scores.t();
                arma::fmat p_grads_sub = q_sub * batch_grad_scores;

                // D. Update Weights (Sparse + Hogwild)
                for (int b = 0; b < cur_batch; ++b) {
                    const int* row = &train_data.data[sample_indices[i + b] * 6];
                    
                    // 1. Query Updates
                    int valid = 0;
                    for(int s=0; s<5; ++s) if(row[s]!=0) valid++;
                    float q_scale = (valid > 0) ? (1.0f/valid) : 0;
                    
                    if (q_scale > 0) {
                        const float* q_grad_ptr = q_grads_sub.colptr(b);
                        for (int s = 0; s < 5; ++s) {
                            int mid = row[s]; if (mid == 0) continue;
                            int start = offsets[mid], end = offsets[mid+1];
                            for (int k = start; k < end; ++k) {
                                int f_idx = indices[k];
                                float val = values[k] * q_scale;
                                adagrad_update(weights.colptr(f_idx), grad_accum.colptr(f_idx), q_grad_ptr, val, EMBEDDING_DIM);
                            }
                        }
                    }

                    // 2. Positive Item Updates
                    int mid = row[5];
                    int start = offsets[mid], end = offsets[mid+1];
                    const float* p_grad_ptr = p_grads_sub.colptr(b);
                    for (int k = start; k < end; ++k) {
                        int f_idx = indices[k];
                        float val = values[k];
                        adagrad_update(weights.colptr(f_idx), grad_accum.colptr(f_idx), p_grad_ptr, val, EMBEDDING_DIM);
                    }
                }
                
                // Progress Log
                int p = processed.fetch_add(cur_batch) + cur_batch;
                if (p % 200000 < BATCH_SIZE * omp_get_num_threads()) {
                     // Approximate check to avoid too much locking
                     if (omp_get_thread_num() == 0) {
                         float pct = (float)p / num_samples;
                         std::cout << "\rEpoch " << epoch+1 << " " << (int)(pct * 100) << "% | Loss: " << (epoch_loss / p) << "   " << std::flush;
                     }
                }
            }
        }
        std::cout << std::endl;
    }

    // 4. Save
    std::cout << "Saving artifacts..." << std::endl;
    arma::fmat final_embs(EMBEDDING_DIM, num_movies);
    
    // Parallelize final embedding generation
    #pragma omp parallel for schedule(static)
    for (int mid = 0; mid < num_movies; ++mid) {
        float* emb_ptr = final_embs.colptr(mid);
        std::memset(emb_ptr, 0, EMBEDDING_DIM * sizeof(float)); // Initialize to 0
        
        // Handle 0th item (often padding) or just ensure offsets checks are safe
        if (mid >= (int)offsets.size - 1) continue; 
        
        int start = offsets[mid], end = offsets[mid+1];
        for (int k = start; k < end; ++k) {
            int f_idx = indices[k];
            float val = values[k];
            const float* w_ptr = weights.colptr(f_idx);
            for(int d=0; d<EMBEDDING_DIM; ++d) emb_ptr[d] += w_ptr[d] * val;
        }
    }
    
    arma::fmat final_embs_t = final_embs.t();
    final_embs_t.save(artifact_dir + "two_tower_embeddings.bin", arma::raw_binary);
    weights.save(artifact_dir + "two_tower_weights.bin", arma::raw_binary);
    std::cout << "Success!" << std::endl;
    return 0;
}
