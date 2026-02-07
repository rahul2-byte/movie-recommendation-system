#include <iostream>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <string>
#include <fstream>
#include <algorithm>
#include <random>
#include <memory>
#include <numeric>
#include <stdexcept>

#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/reader.h>
#include <parquet/exception.h>

struct QueryKey {
    int64_t ids[5];
    bool operator==(const QueryKey& other) const {
        for(int i=0; i<5; ++i) if(ids[i] != other.ids[i]) return false;
        return true;
    }
    bool operator!=(const QueryKey& other) const {
        return !(*this == other);
    }
};

struct QueryKeyHash {
    std::size_t operator()(const QueryKey& k) const {
        std::size_t h = 0;
        for(int i=0; i<5; ++i) h ^= std::hash<int64_t>{}(k.ids[i]) + 0x9e3779b9 + (h << 6) + (h >> 2);
        return h;
    }
};

class StreamingConverter {
public:
    void run(const std::string& input_path, const std::string& out_prefix) {
        // --- Pass 1: Identify Queries for Split ---
        std::cout << "[C++] Pass 1: Streaming queries to determine split..." << std::endl;
        
        std::vector<QueryKey> all_queries;
        
        {
            // Scope for Reader 1
            auto reader = open_file(input_path);
            auto batch_reader = get_batch_reader(reader.get(), {"query_movie_ids"});
            
            std::shared_ptr<arrow::RecordBatch> batch;
            std::unordered_set<QueryKey, QueryKeyHash> seen;

            while (batch_reader->ReadNext(&batch).ok() && batch) {
                auto q_col = std::static_pointer_cast<arrow::ListArray>(batch->column(0));
                auto values = std::static_pointer_cast<arrow::Int64Array>(q_col->values());
                
                for (int64_t i = 0; i < batch->num_rows(); ++i) {
                    QueryKey key = {{0}};
                    int64_t offset = q_col->value_offset(i);
                    for(int j=0; j<5; ++j) key.ids[j] = values->Value(offset + j);
                    
                    if (seen.find(key) == seen.end()) {
                        seen.insert(key);
                        all_queries.push_back(key);
                    }
                }
            }
        } // Reader 1 closed

        std::cout << "[C++] Found " << all_queries.size() << " unique queries." << std::endl;
        
        // Split
        std::shuffle(all_queries.begin(), all_queries.end(), std::mt19937{42});
        size_t n_train = (size_t)(all_queries.size() * 0.8);
        std::unordered_set<QueryKey, QueryKeyHash> train_set;
        for(size_t i=0; i<n_train; ++i) train_set.insert(all_queries[i]);

        std::cout << "[C++] Train groups: " << train_set.size() << ", Test groups: " << (all_queries.size() - n_train) << std::endl;

        // --- Pass 2: Write Data ---
        std::cout << "[C++] Pass 2: Streaming full data and writing..." << std::endl;

        std::vector<std::string> feature_names = {
            "query_movie_ids", "label",
            "feat_avg_query_rating", "feat_avg_query_year", "feat_avg_query_runtime",
            "feat_genre_overlap", "feat_candidate_avg_rating", "feat_candidate_rating_count",
            "feat_candidate_runtime", "feat_candidate_year", "feat_candidate_popularity",
            "feat_candidate_imdb_rating", "feat_candidate_imdb_votes", "feat_year_diff", "feat_runtime_diff"
        };

        {
            // Scope for Reader 2
            auto reader = open_file(input_path);
            auto batch_reader = get_batch_reader(reader.get(), feature_names);
            
            std::shared_ptr<arrow::RecordBatch> batch;

            std::ofstream f_train(out_prefix + ".train");
            std::ofstream f_test(out_prefix + ".test");
            std::ofstream f_train_q(out_prefix + ".train.query");
            std::ofstream f_test_q(out_prefix + ".test.query");
            
            QueryKey last_key_train = {{0}}, last_key_test = {{0}};
            int count_train = 0, count_test = 0;
            bool first_train = true, first_test = true;

            while (batch_reader->ReadNext(&batch).ok() && batch) {
                auto q_col = std::static_pointer_cast<arrow::ListArray>(batch->column(0));
                auto q_vals = std::static_pointer_cast<arrow::Int64Array>(q_col->values());
                auto l_col = std::static_pointer_cast<arrow::Int64Array>(batch->column(1));
                
                std::vector<std::shared_ptr<arrow::FloatArray>> f_cols;
                for(size_t k=2; k<feature_names.size(); ++k) {
                    f_cols.push_back(std::static_pointer_cast<arrow::FloatArray>(batch->column(k)));
                }

                for (int64_t i = 0; i < batch->num_rows(); ++i) {
                    QueryKey key = {{0}};
                    int64_t offset = q_col->value_offset(i);
                    for(int j=0; j<5; ++j) key.ids[j] = q_vals->Value(offset + j);

                    bool is_train = (train_set.find(key) != train_set.end());
                    std::ofstream& out = is_train ? f_train : f_test;

                    out << l_col->Value(i);
                    for(auto& col : f_cols) out << "," << col->Value(i);
                    out << "\n";

                    if (is_train) {
                        if (!first_train && key != last_key_train) {
                            f_train_q << count_train << "\n";
                            count_train = 0;
                        }
                        last_key_train = key;
                        count_train++;
                        first_train = false;
                    } else {
                        if (!first_test && key != last_key_test) {
                            f_test_q << count_test << "\n";
                            count_test = 0;
                        }
                        last_key_test = key;
                        count_test++;
                        first_test = false;
                    }
                }
            }
            if (count_train > 0) f_train_q << count_train << "\n";
            if (count_test > 0) f_test_q << count_test << "\n";
        } // Reader 2 closed

        std::cout << "[C++] Conversion complete." << std::endl;
    }

private:
    std::unique_ptr<parquet::arrow::FileReader> open_file(const std::string& path) {
        arrow::MemoryPool* pool = arrow::default_memory_pool();
        std::shared_ptr<arrow::io::ReadableFile> infile;
        auto result = arrow::io::ReadableFile::Open(path);
        if (!result.ok()) throw std::runtime_error("Failed to open file: " + path);
        infile = result.ValueOrDie();

        // Fixed API Call
        auto open_result = parquet::arrow::OpenFile(infile, pool);
        if (!open_result.ok()) throw std::runtime_error("Failed to create parquet reader");
        return std::move(open_result).ValueOrDie();
    }

    std::shared_ptr<arrow::RecordBatchReader> get_batch_reader(parquet::arrow::FileReader* reader, const std::vector<std::string>& columns) {
        std::vector<int> all_row_groups(reader->num_row_groups());
        std::iota(all_row_groups.begin(), all_row_groups.end(), 0);

        std::vector<int> col_idxs;
        std::shared_ptr<arrow::Schema> arrow_schema;
        auto status = reader->GetSchema(&arrow_schema);
        if(!status.ok()) throw std::runtime_error("Failed to get schema");
        
        for(const auto& name : columns) {
            int idx = arrow_schema->GetFieldIndex(name);
            if (idx == -1) throw std::runtime_error("Column not found: " + name);
            col_idxs.push_back(idx);
        }

        std::shared_ptr<arrow::RecordBatchReader> rb_reader;
        // Suppress deprecation warning or just use it.
        // For new API (if available): reader->GetRecordBatchReader(..., &rb_reader) is deprecated?
        // Actually, the new API returns arrow::Result<std::shared_ptr<RecordBatchReader>>.
        // Let's try the Result version if the deprecated one fails or just assume it works.
        // The error log showed: deprecated, use Result version.
        // But the deprecated function should still work for now.
        status = reader->GetRecordBatchReader(all_row_groups, col_idxs, &rb_reader);
        if(!status.ok()) throw std::runtime_error("Failed to get batch reader");
        
        return rb_reader;
    }
};

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <input_parquet> <output_prefix>" << std::endl;
        return 1;
    }
    try {
        StreamingConverter app;
        app.run(argv[1], argv[2]);
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}