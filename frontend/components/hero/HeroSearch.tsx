"use client"


export function HeroSearch() {
  return (
    <section
      className="relative flex h-[75vh] items-center justify-center bg-cover bg-center"
      style={{
        backgroundImage: "url('/hero-bg.jpg')",
      }}
    >
      {/* Dark overlay */}
      <div className="absolute inset-0 bg-black/70" />

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-3xl text-center px-6">
        <h1 className="text-5xl font-bold leading-tight">
          Find your next{" "}
          <span className="text-pink-500">favorite story</span>
        </h1>

        <p className="mt-4 text-gray-300">
          Discover top-rated movies and hidden gems curated just for you.
        </p>

        <div className="mt-8 flex overflow-hidden rounded-full bg-neutral-800">
          <input
            className="flex-1 bg-transparent px-6 py-4 outline-none text-white"
            placeholder="Search for movies, TV shows, or actors..."
          />
          <button className="bg-pink-500 px-8 font-semibold">
            Search
          </button>
        </div>
      </div>
    </section>
  )
}

