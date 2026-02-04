CXX = g++
CXXFLAGS = -O3 -std=c++17 -pthread -Wall -fopenmp -I$(CONDA_PREFIX)/include
LDFLAGS = -L$(CONDA_PREFIX)/lib -larmadillo -Wl,-rpath,$(CONDA_PREFIX)/lib

TARGETS = train_als train_tfidf train_content train_two_tower

all: $(TARGETS)

train_als: train_als.cpp common.hpp
	$(CXX) $(CXXFLAGS) -o train_als train_als.cpp $(LDFLAGS)

train_tfidf: train_tfidf.cpp common.hpp
	$(CXX) $(CXXFLAGS) -o train_tfidf train_tfidf.cpp $(LDFLAGS)

train_content: train_content.cpp common.hpp
	$(CXX) $(CXXFLAGS) -o train_content train_content.cpp $(LDFLAGS)

train_two_tower: train_two_tower.cpp common.hpp
	$(CXX) $(CXXFLAGS) -o train_two_tower train_two_tower.cpp $(LDFLAGS)

clean:
	rm -f $(TARGETS)
