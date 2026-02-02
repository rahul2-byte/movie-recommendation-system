import Link from "next/link"
import { Button } from "@/shared/ui/Button"

export default function ProjectPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-10 space-y-8">
      <h1 className="text-4xl font-bold text-center mb-10">
        Our Recommendation Engine
      </h1>

      <section className="bg-card p-8 rounded-lg shadow-md">
        <h2 className="text-2xl font-semibold mb-4">
          Unveiling the Magic Behind Your Perfect Movie Match
        </h2>
        <p className="text-lg text-muted-foreground">
          At Movies99, we believe finding your next favorite film should be an
          effortless and delightful experience. Our recommendation engine is
          crafted with cutting-edge machine learning to understand your unique
          tastes and deliver personalized suggestions you&apos;ll truly love.
        </p>
      </section>

      <section className="grid md:grid-cols-2 gap-8">
        <div className="bg-card p-8 rounded-lg shadow-md">
          <h3 className="text-xl font-semibold mb-3">
            Intelligent Multi-Stage Pipeline
          </h3>
          <p className="text-muted-foreground mb-4">
            Our system employs a sophisticated Recall, Rank, and Re-rank
            pipeline, meticulously designed to surface the most relevant films
            from a vast cinematic universe.
          </p>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>
              <strong>Recall:</strong> We use advanced ALS (Alternating Least
              Squares) and Two-Tower models to efficiently identify a broad set
              of potential movie candidates tailored to your preferences.
            </li>
            <li>
              <strong>Fast Retrieval:</strong> FAISS Approximate Nearest Neighbor
              (ANN) indices ensure lightning-fast candidate retrieval, so you
              never wait.
            </li>
            <li>
              <strong>Precision Ranking:</strong> A powerful LightGBM model
              then precisely ranks these candidates, prioritizing the films
              most likely to captivate you.
            </li>
          </ul>
        </div>

        <div className="bg-card p-8 rounded-lg shadow-md">
          <h3 className="text-xl font-semibold mb-3">
            Seamless Integration & Rich Data
          </h3>
          <p className="text-muted-foreground mb-4">
            The frontend seamlessly interacts with our robust backend, consuming
            ranked MovieLens IDs. This data is then richly enhanced with
            comprehensive information from The Movie Database (TMDB) to provide
            you with vibrant posters, detailed synopses, and more.
          </p>
          <p className="text-muted-foreground">
            This elegant architecture ensures that every recommendation is not
            just accurate, but also presented beautifully, offering you a
            glimpse into your next cinematic adventure.
          </p>
        </div>
      </section>

      <section className="text-center pt-8">
        <p className="text-lg text-muted-foreground mb-4">
          Ready to discover your next favorite movie?
        </p>
        <Link href="/">
          <Button size="lg" className="shadow-lg">
            Get Personalized Recommendations
          </Button>
        </Link>
      </section>
    </main>
  )
}