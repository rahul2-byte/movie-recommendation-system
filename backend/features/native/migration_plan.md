# C++ Native ML Library Migration Plan

## 1. Analysis of Current Implementation
The current `backend/features/native/` modules use standard C++ (`std::vector`, `std::unordered_map`) to perform data processing tasks:
- **`content_vectorizer.cpp`**: Manually computes TF-IDF-style vectors and performs L2 normalization.
- **`interaction_matrix_builder.cpp`**: Manually constructs a Coordinate (COO) format sparse matrix.
- **`sequence_builder.cpp`** & **`processor.cpp`**: Perform sliding window sequences and aggregation.

**Current Limitations:**
- **Manual Math**: Normalization and vector math are written from scratch.
- **No Training**: The C++ code is strictly for *preprocessing*; it does not train models.
- **Scalability**: Manual `std::vector` handling for matrices is less efficient than optimized Sparse Matrix libraries.

## 2. Library Selection: Mlpack + Armadillo
To satisfy the requirement of using "Native ML Libraries", **Mlpack** is the optimal choice.

*   **Why Mlpack?**
    *   It is built on **Armadillo**, a high-quality C++ Linear Algebra library (similar to NumPy).
    *   It contains specific modules for **Recommender Systems** (`mlpack::cf`).
    *   It supports **Sparse Matrices** natively.

*   **Alternatives Considered:**
    *   *LibTorch*: Too heavyweight (hundreds of MBs) and focused on Deep Learning. Overkill for this stage.
    *   *Dlib*: Good, but Mlpack's API for Matrix Factorization is more direct.
    *   *Eigen*: Good for math, but lacks the higher-level ML algorithms of Mlpack.

## 3. Proposed Changes

### A. Environment
Install `mlpack`, `armadillo`, and `pkg-config` in the `rsys` environment.

### B. `content_vectorizer.cpp` (Refactor)
*   **Goal**: Replace manual vector math.
*   **Changes**:
    *   Use `arma::RowVec` to store feature vectors.
    *   Use `arma::norm(vec, 2)` for L2 normalization.
    *   Use `mlpack::data::Save` (optional) or `arma::save` for outputting standard formats.

### C. `interaction_matrix_builder.cpp` (Refactor & Upgrade)
*   **Goal**: Replace manual matrix construction and enable Training.
*   **Changes**:
    *   Use `arma::sp_mat` (Sparse Matrix) to store interactions.
    *   **Major Upgrade**: Instead of just dumping the matrix, we can use `mlpack::cf::CF` to **train an ALS model** directly in C++, outputting the user/item matrices ($W$ and $H$)!
    *   *Note*: This changes the pipeline from "Python does training" to "C++ does training".

## 4. Execution Plan
1.  Install dependencies.
2.  Update `Makefile` to link against `mlpack` and `armadillo`.
3.  Rewrite `interaction_matrix_builder.cpp` to use Armadillo/Mlpack.
