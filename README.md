# 🎬 Movie Recommendation System

A scalable, production-ready movie recommendation system built using modern ML techniques.
Designed to demonstrate **senior-level ML engineering** skills: data pipelines, retrieval & ranking models,
feature engineering, evaluation, and deployment.

---

## 🚀 Key Features

- Large-scale data processing (MovieLens 25M)
- Retrieval + ranking architecture (Two-Tower, MF, ANN)
- GPU-accelerated feature engineering
- Sparse matrix & embedding-based models
- Modular, production-oriented codebase
- Designed for deployment (API + model serving)

---

## 🧠 Model Architecture

- **Retrieval (Fast)**
  - Two-Tower Neural Network
  - Matrix Factorization (ALS)
  - ANN search (FAISS / HNSW)

- **Ranking (Accurate)**
  - Neural Collaborative Filtering
  - Gradient-boosted ranking models
  - Feature-rich pointwise / pairwise learning

---

## 📂 Project Structure

```text
movie-recommender/
│
├── data/
│   ├── raw/                # Original datasets (ignored)
│   ├── processed/          # Feature artifacts (ignored)
│
├── features/               # Feature engineering pipelines
│
├── retrieval/
│   ├── two_tower/
│   ├── matrix_factorization/
│
├── ranking/
│
├── evaluation/
│
├── api/                    # FastAPI inference service
│
├── configs/                # YAML / JSON configs
│
├── scripts/                # CLI & orchestration scripts
│
├── notebooks/              # Experiments & analysis
│
├── tests/                  # Unit & integration tests
│
├── requirements.txt
├── environment.yml
├── .gitignore
├── .gitattributes
├── LICENSE
└── README.md
