"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-lg px-4 py-16 text-center">
      <h2 className="text-xl font-bold text-red-600">Failed to load</h2>
      <p className="mt-2 text-sm text-zinc-500">{error.message || "An unexpected error occurred."}</p>
      <button
        onClick={reset}
        className="mt-4 rounded-lg bg-black px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 transition-colors"
      >
        Try again
      </button>
    </div>
  );
}
