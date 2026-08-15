# Recommendation System Glossary

These terms are shared by data preparation, training, evaluation, and
serving.

| Term | Meaning |
| --- | --- |
| Seed movie | A movie selected by the user as preference evidence. |
| Candidate movie | A movie returned by at least one retriever before ranking. |
| Retriever | A model or algorithm that generates candidate movies. |
| Retrieval rank | A candidate's position within one retriever's output. |
| Retrieval score | The numerical score produced by one retriever. |
| Fusion score | The score used to combine evidence from multiple retrievers. |
| Ranking feature | A numeric input supplied to the LightGBM ranker. |
| Ranking score | The ranker's predicted relevance score for a candidate. |
| Ground truth | Held-out movies used to measure recommendation quality. |
| Model artifact | A serialized model/index and its manifest. |
| Model bundle | The immutable release containing all retrievers, the ranker, and feature state. |
| Cold-start movie | A movie without interaction history; content metadata can still retrieve it. |

Movie identifiers in the online API and model contracts are TMDB IDs. Dataset
row positions are internal implementation details and must not cross that
boundary.
