export default function Loading() {
  return (
    <div className="mx-auto min-h-[60vh] w-full max-w-[1440px] px-4 py-12 sm:px-6 lg:px-10">
      <div className="h-5 w-28 animate-pulse rounded-full bg-line" />
      <div className="mt-4 h-14 w-full max-w-lg animate-pulse rounded-2xl bg-line/80" />
      <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
        {[...Array(6)].map((_, index) => (
          <div
            key={index}
            className="aspect-[2/3] animate-pulse rounded-2xl bg-line/70"
          />
        ))}
      </div>
    </div>
  )
}
