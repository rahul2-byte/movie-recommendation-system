#pragma once

#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <fstream>
#include <cmath>
#include <algorithm>
#include <map>
#include <unordered_map>
#include <random>
#include <chrono>
#include <iomanip>
#include <cstring>

// --- Logging ---
#define LOG_INFO(msg) std::cout << "[INFO] " << msg << std::endl
#define LOG_ERROR(msg) std::cerr << "[ERROR] " << msg << std::endl

// --- String Utils ---
inline std::vector<std::string> split(const std::string& s, char delimiter) {
    std::vector<std::string> tokens;
    std::string token;
    std::istringstream tokenStream(s);
    while (std::getline(tokenStream, token, delimiter)) {
        tokens.push_back(token);
    }
    return tokens;
}

// --- CSV Parsing ---
// Naive CSV parser (handles simple cases, no quotes containing commas)
inline std::vector<std::string> parse_csv_line(const std::string& line) {
    // This dataset seems simple enough (no quoted commas in genres/titles observed in head)
    // But title "Toy Story (1995)" is fine.
    // If complex CSV needed, this needs upgrade.
    return split(line, ',');
}

// --- Data Structures ---
struct Matrix {
    int rows;
    int cols;
    std::vector<float> data;

    Matrix(int r, int c) : rows(r), cols(c), data(r * c, 0.0f) {}

    float& at(int r, int c) { return data[r * cols + c]; }
    const float& at(int r, int c) const { return data[r * cols + c]; }
    
    // Initialize with random small values
    void randomize(float scale = 0.1f) {
        std::mt19937 gen(42);
        std::normal_distribution<float> dist(0.0f, scale);
        for (auto& v : data) v = dist(gen);
    }
};

// --- NPY Saving Utils ---
// Basic NPY version 1.0 writer
// Header: \x93NUMPY\x01\x00 + <16-bit header len> + <header dict> + padding
inline void save_npy(const std::string& filename, const float* data, int rows, int cols) {
    std::ofstream out(filename, std::ios::binary);
    if (!out) {
        LOG_ERROR("Could not open " << filename << " for writing.");
        return;
    }

    const char magic[] = "\x93NUMPY";
    out.write(magic, 6);
    char version[] = {1, 0};
    out.write(version, 2);

    // Create header dict: {'descr': '<f4', 'fortran_order': False, 'shape': (rows, cols), }
    std::stringstream header_ss;
    header_ss << "{'descr': '<f4', 'fortran_order': False, 'shape': (" << rows << ", " << cols << "), }";
    std::string header_str = header_ss.str();

    // Pad with spaces to make total len (magic + ver + len) divisible by 64
    // Magic(6) + Ver(2) + Len(2) = 10 bytes prefix.
    int padding_needed = 64 - ((10 + header_str.size() + 1) % 64); // +1 for newline
    for (int i = 0; i < padding_needed; ++i) header_str += ' ';
    header_str += '\n';

    uint16_t header_len = static_cast<uint16_t>(header_str.size());
    // Little endian length
    out.write(reinterpret_cast<const char*>(&header_len), 2);
    out.write(header_str.data(), header_len);

    // Write data
    out.write(reinterpret_cast<const char*>(data), rows * cols * sizeof(float));
    out.close();
    LOG_INFO("Saved " << filename << " (" << rows << "x" << cols << ")");
}

inline void save_npy_matrix(const std::string& filename, const Matrix& m) {
    save_npy(filename, m.data.data(), m.rows, m.cols);
}

// --- Math Utils ---
inline float dot_product(const float* a, const float* b, int size) {
    float sum = 0.0f;
    for (int i = 0; i < size; ++i) sum += a[i] * b[i];
    return sum;
}

// Sigmoid
inline float sigmoid(float x) {
    return 1.0f / (1.0f + std::exp(-x));
}
