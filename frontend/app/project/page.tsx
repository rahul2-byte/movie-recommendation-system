export default function ProjectPage() {
    return (
      <main className="mx-auto max-w-4xl px-6 py-10 prose prose-invert">
        <h1>System Design</h1>
  
        <h2>Architecture</h2>
        <p>
          This system follows a multi-stage recommender pipeline:
          Recall → Rank → Re-rank.
        </p>
  
        <ul>
          <li>ALS & Two-Tower models for recall</li>
          <li>FAISS ANN indices for fast candidate retrieval</li>
          <li>LightGBM for ranking</li>
        </ul>
  
        <p>
          Frontend strictly consumes ranked MovieLens IDs and enriches via TMDB.
        </p>
      </main>
    )
  }
  