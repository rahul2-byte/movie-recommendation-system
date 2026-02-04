#include <iostream>
#include <vector>
#include <unordered_map>
#include <string>
#include <algorithm>

#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/reader.h>
#include <parquet/arrow/writer.h>
#include <parquet/exception.h>

/**
 * High-Performance Native Feature Generator for Ranking Dataset.
 * Performs fast joins and set operations (overlaps) using Arrow/Parquet.
 */

struct MovieMeta {
    float vote_average;
    int32_t vote_count;
    std::vector<std::string> genres;
};

class RankerFeatureGen {
public:
    void load_metadata(const std::string& path) {
        std::cout << "[C++] Loading movie metadata from " << path << "..." << std::endl;
        
        arrow::MemoryPool* pool = arrow::default_memory_pool();
        std::shared_ptr<arrow::io::ReadableFile> infile;
        PARQUET_ASSIGN_OR_THROW(infile, arrow::io::ReadableFile::Open(path));

        std::unique_ptr<parquet::arrow::FileReader> reader;
        // Arrow 14+ OpenFile returns Result
        auto open_result = parquet::arrow::OpenFile(infile, pool);
        if (!open_result.ok()) {
            throw std::runtime_error("Failed to open metadata: " + open_result.status().ToString());
        }
        reader = std::move(open_result).ValueOrDie();

        std::shared_ptr<arrow::Table> table;
        PARQUET_THROW_NOT_OK(reader->ReadTable(&table));

        auto movie_ids = std::static_pointer_cast<arrow::Int64Array>(table->GetColumnByName("movie_id")->chunk(0));
        auto genres_col = std::static_pointer_cast<arrow::ListArray>(table->GetColumnByName("genres")->chunk(0));
        auto vote_avg = std::static_pointer_cast<arrow::DoubleArray>(table->GetColumnByName("vote_average")->chunk(0));
        auto vote_cnt = std::static_pointer_cast<arrow::Int64Array>(table->GetColumnByName("vote_count")->chunk(0));

        for (int64_t i = 0; i < table->num_rows(); i++) {
            MovieMeta meta;
            meta.vote_average = (float)vote_avg->Value(i);
            meta.vote_count = (int32_t)vote_cnt->Value(i);

            int64_t start = genres_col->value_offset(i);
            int64_t end = genres_col->value_offset(i + 1);
            auto genre_values = std::static_pointer_cast<arrow::StringArray>(genres_col->values());
            for (int64_t j = start; j < end; j++) {
                meta.genres.push_back(genre_values->GetString(j));
            }

            metadata_[movie_ids->Value(i)] = meta;
        }
        std::cout << "[C++] Loaded " << metadata_.size() << " movies into memory." << std::endl;
    }

    void process(const std::string& input_path, const std::string& output_path) {
        std::cout << "[C++] Processing dataset: " << input_path << " -> " << output_path << std::endl;

        arrow::MemoryPool* pool = arrow::default_memory_pool();
        std::shared_ptr<arrow::io::ReadableFile> infile;
        PARQUET_ASSIGN_OR_THROW(infile, arrow::io::ReadableFile::Open(input_path));

        std::unique_ptr<parquet::arrow::FileReader> reader;
        auto open_result = parquet::arrow::OpenFile(infile, pool);
        if (!open_result.ok()) {
            throw std::runtime_error("Failed to open dataset: " + open_result.status().ToString());
        }
        reader = std::move(open_result).ValueOrDie();

        std::shared_ptr<arrow::Table> table;
        PARQUET_THROW_NOT_OK(reader->ReadTable(&table));

        auto query_ids_list = std::static_pointer_cast<arrow::ListArray>(table->GetColumnByName("query_movie_ids")->chunk(0));
        auto candidate_ids = std::static_pointer_cast<arrow::Int64Array>(table->GetColumnByName("candidate_movie_id")->chunk(0));
        auto labels = std::static_pointer_cast<arrow::Int64Array>(table->GetColumnByName("label")->chunk(0));

        int64_t num_rows = table->num_rows();

        arrow::FloatBuilder f1(pool), f2(pool), f3(pool);
        arrow::Int32Builder i1(pool);

        for (int64_t i = 0; i < num_rows; i++) {
            int64_t cand_id = candidate_ids->Value(i);
            
            int64_t start = query_ids_list->value_offset(i);
            int64_t end = query_ids_list->value_offset(i + 1);
            auto q_values = std::static_pointer_cast<arrow::Int64Array>(query_ids_list->values());
            
            float q_sum_rating = 0;
            int q_count = 0;
            std::unordered_map<std::string, bool> query_genres;

            for (int64_t j = start; j < end; j++) {
                int64_t mid = q_values->Value(j);
                if (metadata_.count(mid)) {
                    q_sum_rating += metadata_[mid].vote_average;
                    q_count++;
                    for (const auto& g : metadata_[mid].genres) query_genres[g] = true;
                }
            }

            float cand_rating = 0;
            int32_t cand_votes = 0;
            int genre_overlap = 0;

            if (metadata_.count(cand_id)) {
                cand_rating = metadata_[cand_id].vote_average;
                cand_votes = metadata_[cand_id].vote_count;
                for (const auto& g : metadata_[cand_id].genres) {
                    if (query_genres.count(g)) genre_overlap++;
                }
            }

            f1.Append(q_count > 0 ? q_sum_rating / q_count : 0);
            f2.Append((float)genre_overlap);
            f3.Append(cand_rating);
            i1.Append(cand_votes);
        }

        std::shared_ptr<arrow::Array> a1, a2, a3, a4;
        f1.Finish(&a1); f2.Finish(&a2); f3.Finish(&a3); i1.Finish(&a4);

        auto c1 = std::make_shared<arrow::ChunkedArray>(a1);
        auto c2 = std::make_shared<arrow::ChunkedArray>(a2);
        auto c3 = std::make_shared<arrow::ChunkedArray>(a3);
        auto c4 = std::make_shared<arrow::ChunkedArray>(a4);

        std::shared_ptr<arrow::Table> final_table;
        PARQUET_ASSIGN_OR_THROW(final_table, table->AddColumn(table->num_columns(), arrow::field("feat_avg_query_rating", arrow::float32()), c1));
        PARQUET_ASSIGN_OR_THROW(final_table, final_table->AddColumn(final_table->num_columns(), arrow::field("feat_genre_overlap", arrow::float32()), c2));
        PARQUET_ASSIGN_OR_THROW(final_table, final_table->AddColumn(final_table->num_columns(), arrow::field("feat_candidate_avg_rating", arrow::float32()), c3));
        PARQUET_ASSIGN_OR_THROW(final_table, final_table->AddColumn(final_table->num_columns(), arrow::field("feat_candidate_rating_count", arrow::int32()), c4));

        std::shared_ptr<arrow::io::FileOutputStream> outfile;
        PARQUET_ASSIGN_OR_THROW(outfile, arrow::io::FileOutputStream::Open(output_path));
        
        auto writer_props = parquet::WriterProperties::Builder().compression(parquet::Compression::SNAPPY)->build();
        auto arrow_props = parquet::ArrowWriterProperties::Builder().store_schema()->build();
        
        PARQUET_THROW_NOT_OK(parquet::arrow::WriteTable(*final_table, pool, outfile, 1024 * 1024, writer_props, arrow_props));

        std::cout << "[C++] Successfully wrote " << num_rows << " rows with features." << std::endl;
    }

private:
    std::unordered_map<int64_t, MovieMeta> metadata_;
};

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <input_parquet> <output_parquet> [metadata_parquet]" << std::endl;
        return 1;
    }
    std::string input = argv[1];
    std::string output = argv[2];
    std::string meta = (argc > 3) ? argv[3] : "backend/data/processed/movies_enriched.parquet";

    try {
        RankerFeatureGen gen;
        gen.load_metadata(meta);
        gen.process(input, output);
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}