#include <iostream>
#include <vector>
#include <unordered_map>
#include <string>
#include <fstream>
#include <algorithm>
#include <random>

#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/reader.h>

/**
 * Native Converter: Parquet -> LightGBM CSV + Query files.
 * Implements Grouped Random Split (80/20).
 */

struct QueryKey {
    int64_t ids[5];
    bool operator==(const QueryKey& other) const {
        for(int i=0; i<5; ++i) if(ids[i] != other.ids[i]) return false;
        return true;
    }
};

struct QueryKeyHash {
    std::size_t operator()(const QueryKey& k) const {
        std::size_t h = 0;
        for(int i=0; i<5; ++i) h ^= std::hash<int64_t>{}(k.ids[i]) + 0x9e3779b9 + (h << 6) + (h >> 2);
        return h;
    }
};

class ParquetToLGBM {
public:
    void convert(const std::string& input_path, const std::string& out_prefix) {
        std::cout << "[C++] Pass 1: Mapping groups..." << std::endl;
        
        arrow::MemoryPool* pool = arrow::default_memory_pool();
        std::shared_ptr<arrow::io::ReadableFile> infile;
        PARQUET_ASSIGN_OR_THROW(infile, arrow::io::ReadableFile::Open(input_path));

        std::unique_ptr<parquet::arrow::FileReader> reader;
        auto open_result = parquet::arrow::OpenFile(infile, pool);
        if (!open_result.ok()) throw std::runtime_error("Open failed");
        reader = std::move(open_result).ValueOrDie();

        std::shared_ptr<arrow::Table> table;
        PARQUET_THROW_NOT_OK(reader->ReadTable(&table));

        auto query_ids_list = std::static_pointer_cast<arrow::ListArray>(table->GetColumnByName("query_movie_ids")->chunk(0));
        int64_t num_rows = table->num_rows();

        std::vector<QueryKey> row_to_query(num_rows);
        std::unordered_map<QueryKey, int, QueryKeyHash> query_counts;
        std::vector<QueryKey> unique_queries;

        for (int64_t i = 0; i < num_rows; i++) {
            QueryKey key;
            auto q_values = std::static_pointer_cast<arrow::Int64Array>(query_ids_list->values());
            int64_t start = query_ids_list->value_offset(i);
            for(int j=0; j<5; ++j) key.ids[j] = q_values->Value(start + j);
            
            row_to_query[i] = key;
            if (query_counts[key] == 0) unique_queries.push_back(key);
            query_counts[key]++;
        }

        std::cout << "[C++] Found " << unique_queries.size() << " unique queries. Splitting..." << std::endl;

        std::shuffle(unique_queries.begin(), unique_queries.end(), std::mt19937{42});
        size_t train_size = (size_t)(unique_queries.size() * 0.8);
        
        std::unordered_map<QueryKey, bool, QueryKeyHash> is_train;
        for(size_t i=0; i<train_size; ++i) is_train[unique_queries[i]] = true;

        std::cout << "[C++] Pass 2: Writing files..." << std::endl;
        
        std::ofstream f_train_data(out_prefix + ".train");
        std::ofstream f_test_data(out_prefix + ".test");
        std::ofstream f_train_query(out_prefix + ".train.query");
        std::ofstream f_test_query(out_prefix + ".test.query");

        auto labels = std::static_pointer_cast<arrow::Int64Array>(table->GetColumnByName("label")->chunk(0));
        auto f1 = std::static_pointer_cast<arrow::FloatArray>(table->GetColumnByName("feat_avg_query_rating")->chunk(0));
        auto f2 = std::static_pointer_cast<arrow::FloatArray>(table->GetColumnByName("feat_genre_overlap")->chunk(0));
        auto f3 = std::static_pointer_cast<arrow::FloatArray>(table->GetColumnByName("feat_candidate_avg_rating")->chunk(0));
        auto f4 = std::static_pointer_cast<arrow::Int32Array>(table->GetColumnByName("feat_candidate_rating_count")->chunk(0));

        std::unordered_map<QueryKey, int, QueryKeyHash> current_group_counts;
        std::vector<QueryKey> train_order, test_order;

        for (int64_t i = 0; i < num_rows; i++) {
            QueryKey key = row_to_query[i];
            std::ostream& out = is_train[key] ? f_train_data : f_test_data;
            
            out << labels->Value(i) << "," 
                << f1->Value(i) << "," << f2->Value(i) << "," 
                << f3->Value(i) << "," << f4->Value(i) << "\n";
            
            if (current_group_counts[key] == 0) {
                if (is_train[key]) train_order.push_back(key);
                else test_order.push_back(key);
            }
            current_group_counts[key]++;
        }

        for(auto& k : train_order) f_train_query << query_counts[k] << "\n";
        for(auto& k : test_order) f_test_query << query_counts[k] << "\n";

        std::cout << "[C++] Conversion complete." << std::endl;
    }
};

int main(int argc, char** argv) {
    if (argc < 3) return 1;
    try {
        ParquetToLGBM conv;
        conv.convert(argv[1], argv[2]);
    } catch (const std::exception& e) {
        std::cerr << e.what() << std::endl;
        return 1;
    }
    return 0;
}