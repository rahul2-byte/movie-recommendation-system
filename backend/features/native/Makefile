CXX = g++
CXXFLAGS = -O3 -std=c++17 -Wall -I$(CONDA_PREFIX)/include
LDFLAGS = -L$(CONDA_PREFIX)/lib -larmadillo -lparquet -larrow -Wl,-rpath,$(CONDA_PREFIX)/lib

TARGETS = processor sequence_builder content_vectorizer interaction_matrix_builder ranker_feature_gen converter

all: $(TARGETS)

converter: ../../training/ranking/native/converter.cpp
	$(CXX) $(CXXFLAGS) -o ../../training/ranking/native/converter ../../training/ranking/native/converter.cpp $(LDFLAGS)

ranker_feature_gen: ranker_feature_gen.cpp
	$(CXX) $(CXXFLAGS) -o ranker_feature_gen ranker_feature_gen.cpp $(LDFLAGS)

processor: processor.cpp
	$(CXX) $(CXXFLAGS) -o processor processor.cpp
sequence_builder: sequence_builder.cpp
	$(CXX) $(CXXFLAGS) -o sequence_builder sequence_builder.cpp

content_vectorizer: content_vectorizer.cpp
	$(CXX) $(CXXFLAGS) -o content_vectorizer content_vectorizer.cpp $(LDFLAGS)

interaction_matrix_builder: interaction_matrix_builder.cpp
	$(CXX) $(CXXFLAGS) -o interaction_matrix_builder interaction_matrix_builder.cpp $(LDFLAGS)

clean:
	rm -f $(TARGETS)