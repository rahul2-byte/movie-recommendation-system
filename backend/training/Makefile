CXX = g++
CXXFLAGS = -O3 -march=native -std=c++17 -Wall -fopenmp -I$(CONDA_PREFIX)/include
LDFLAGS = -L$(CONDA_PREFIX)/lib -larmadillo -lparquet -larrow -Wl,-rpath,$(CONDA_PREFIX)/lib -lpthread

RETRIEVAL_DIR = retrieval/native
RANKING_DIR = ranking/native
BIN_DIR = bin

TARGETS = $(BIN_DIR)/train_als $(BIN_DIR)/train_two_tower $(BIN_DIR)/train_content $(BIN_DIR)/train_tfidf $(BIN_DIR)/converter

all: $(BIN_DIR) $(TARGETS)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(BIN_DIR)/train_als: $(RETRIEVAL_DIR)/train_als.cpp
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

$(BIN_DIR)/train_two_tower: $(RETRIEVAL_DIR)/train_two_tower.cpp
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

$(BIN_DIR)/train_content: $(RETRIEVAL_DIR)/train_content.cpp
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

$(BIN_DIR)/train_tfidf: $(RETRIEVAL_DIR)/train_tfidf.cpp
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

$(BIN_DIR)/converter: $(RANKING_DIR)/converter.cpp
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -rf $(BIN_DIR)
