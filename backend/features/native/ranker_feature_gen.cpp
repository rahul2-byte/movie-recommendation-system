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
    float runtime_minutes;
    float release_year;
    float popularity_score;
    float imdb_rating;
    float imdb_votes;
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
        auto runtime_col = std::static_pointer_cast<arrow::Int64Array>(table->GetColumnByName("runtime_minutes")->chunk(0));
        auto release_year_col = std::static_pointer_cast<arrow::DoubleArray>(table->GetColumnByName("release_year")->chunk(0));
        auto popularity_col = std::static_pointer_cast<arrow::DoubleArray>(table->GetColumnByName("popularity_score")->chunk(0));
        
        // Handle potentially missing columns for imdb
        std::shared_ptr<arrow::DoubleArray> imdb_rating_col = nullptr;
        std::shared_ptr<arrow::DoubleArray> imdb_votes_col = nullptr;
        
        auto imdb_rating_field = table->GetColumnByName("imdb_rating");
        if (imdb_rating_field) imdb_rating_col = std::static_pointer_cast<arrow::DoubleArray>(imdb_rating_field->chunk(0));
        
        auto imdb_votes_field = table->GetColumnByName("imdb_votes");
        if (imdb_votes_field) imdb_votes_col = std::static_pointer_cast<arrow::DoubleArray>(imdb_votes_field->chunk(0));

        for (int64_t i = 0; i < table->num_rows(); i++) {
            MovieMeta meta;
            meta.vote_average = (float)vote_avg->Value(i);
            meta.vote_count = (int32_t)vote_cnt->Value(i);
            meta.runtime_minutes = (float)runtime_col->Value(i);
            meta.release_year = (float)release_year_col->Value(i);
            meta.popularity_score = (float)popularity_col->Value(i);
            
            meta.imdb_rating = (imdb_rating_col && !imdb_rating_col->IsNull(i)) ? (float)imdb_rating_col->Value(i) : 0.0f;
            meta.imdb_votes = (imdb_votes_col && !imdb_votes_col->IsNull(i)) ? (float)imdb_votes_col->Value(i) : 0.0f;

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

        arrow::FloatBuilder f_avg_q_rating(pool), f_avg_q_year(pool), f_avg_q_runtime(pool);
        arrow::FloatBuilder f_genre_overlap(pool);
        arrow::FloatBuilder f_cand_rating(pool), f_cand_votes(pool), f_cand_runtime(pool);
        arrow::FloatBuilder f_cand_year(pool), f_cand_pop(pool), f_cand_imdb_rating(pool), f_cand_imdb_votes(pool);
        arrow::FloatBuilder f_year_diff(pool), f_runtime_diff(pool);

        for (int64_t i = 0; i < num_rows; i++) {
            int64_t cand_id = candidate_ids->Value(i);
            
            int64_t start = query_ids_list->value_offset(i);
            int64_t end = query_ids_list->value_offset(i + 1);
            auto q_values = std::static_pointer_cast<arrow::Int64Array>(query_ids_list->values());
            
            float q_sum_rating = 0, q_sum_year = 0, q_sum_runtime = 0;
            int q_count_rating = 0, q_count_year = 0, q_count_runtime = 0;
            std::unordered_map<std::string, bool> query_genres;

            for (int64_t j = start; j < end; j++) {
                int64_t mid = q_values->Value(j);
                if (metadata_.count(mid)) {
                    const auto& m = metadata_[mid];
                    q_sum_rating += m.vote_average;
                    q_count_rating++;
                    
                    if (m.release_year > 0) {
                        q_sum_year += m.release_year;
                        q_count_year++;
                    }
                    if (m.runtime_minutes > 0) {
                        q_sum_runtime += m.runtime_minutes;
                        q_count_runtime++;
                    }

                    for (const auto& g : m.genres) query_genres[g] = true;
                }
            }

            float avg_q_rating = q_count_rating > 0 ? q_sum_rating / q_count_rating : 0;
            float avg_q_year = q_count_year > 0 ? q_sum_year / q_count_year : 0;
            float avg_q_runtime = q_count_runtime > 0 ? q_sum_runtime / q_count_runtime : 0;

            float cand_rating = 0, cand_votes = 0, cand_runtime = 0, cand_year = 0, cand_pop = 0, cand_imdb_r = 0, cand_imdb_v = 0;
            int genre_overlap = 0;

            if (metadata_.count(cand_id)) {
                const auto& m = metadata_[cand_id];
                cand_rating = m.vote_average;
                cand_votes = (float)m.vote_count;
                cand_runtime = m.runtime_minutes;
                cand_year = m.release_year;
                cand_pop = m.popularity_score;
                cand_imdb_r = m.imdb_rating;
                cand_imdb_v = m.imdb_votes;

                for (const auto& g : m.genres) {
                    if (query_genres.count(g)) genre_overlap++;
                }
            }

            f_avg_q_rating.Append(avg_q_rating);
            f_avg_q_year.Append(avg_q_year);
            f_avg_q_runtime.Append(avg_q_runtime);
            f_genre_overlap.Append((float)genre_overlap);
            f_cand_rating.Append(cand_rating);
            f_cand_votes.Append(cand_votes);
            f_cand_runtime.Append(cand_runtime);
            f_cand_year.Append(cand_year);
            f_cand_pop.Append(cand_pop);
            f_cand_imdb_rating.Append(cand_imdb_r);
            f_cand_imdb_votes.Append(cand_imdb_v);
            f_year_diff.Append(avg_q_year > 0 && cand_year > 0 ? std::abs(cand_year - avg_q_year) : 0);
            f_runtime_diff.Append(avg_q_runtime > 0 && cand_runtime > 0 ? std::abs(cand_runtime - avg_q_runtime) : 0);
        }

        std::shared_ptr<arrow::Table> final_table = table;
        
        auto append_col = [&](const std::string& name, arrow::FloatBuilder& builder) {
            std::shared_ptr<arrow::Array> arr;
            builder.Finish(&arr);
            auto chunked_arr = std::make_shared<arrow::ChunkedArray>(arr);
            PARQUET_ASSIGN_OR_THROW(final_table, final_table->AddColumn(final_table->num_columns(), arrow::field(name, arrow::float32()), chunked_arr));
        };

        append_col("feat_avg_query_rating", f_avg_q_rating);
        append_col("feat_avg_query_year", f_avg_q_year);
        append_col("feat_avg_query_runtime", f_avg_q_runtime);
        append_col("feat_genre_overlap", f_genre_overlap);
        append_col("feat_candidate_avg_rating", f_cand_rating);
        append_col("feat_candidate_rating_count", f_cand_votes);
        append_col("feat_candidate_runtime", f_cand_runtime);
        append_col("feat_candidate_year", f_cand_year);
        append_col("feat_candidate_popularity", f_cand_pop);
        append_col("feat_candidate_imdb_rating", f_cand_imdb_rating);
        append_col("feat_candidate_imdb_votes", f_cand_imdb_votes);
        append_col("feat_year_diff", f_year_diff);
        append_col("feat_runtime_diff", f_runtime_diff);

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