import Link from "next/link";
import { getSeasons } from "@/lib/api";

export default async function StandingsIndexPage() {
  let seasons: { id: number; label: string }[] = [];
  try {
    seasons = await getSeasons(1);
  } catch {
    seasons = [];
  }

  const latest = seasons.length > 0 ? seasons[seasons.length - 1] : null;

  // Default to the latest season (highest id)
  const leagues = [
    { id: 1, name: "Premier League", country: "England", slug: "premier-league", crest: "PL", hasData: true },
    { id: 2, name: "La Liga", country: "Spain", slug: "la-liga", crest: "LL", hasData: false },
    { id: 3, name: "Bundesliga", country: "Germany", slug: "bundesliga", crest: "BL", hasData: false },
    { id: 4, name: "Serie A", country: "Italy", slug: "serie-a", crest: "SA", hasData: false },
    { id: 5, name: "Ligue 1", country: "France", slug: "ligue-1", crest: "L1", hasData: false },
    { id: 6, name: "Champions League", country: "Europe", slug: "champions-league", crest: "CL", hasData: false },
  ];

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <nav className="mb-4">
        <Link href="/" className="inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-900">
          <span aria-hidden="true">&larr;</span> Back
        </Link>
      </nav>

      <h1 className="mb-2 text-3xl font-bold">Standings</h1>
      <p className="mb-8 text-zinc-500">Select a competition to view its standings table.</p>

      {/* Competition list */}
      <div className="mb-8 space-y-3">
        {leagues.map((league) => (
          <Link
            key={league.id}
            href={league.hasData && latest ? `/standings/${latest.id}` : `/leagues/${league.slug}-${league.id}`}
            className="flex items-center gap-4 rounded-xl border border-zinc-200 bg-white p-4 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-zinc-800 dark:hover:border-blue-700 dark:hover:bg-blue-950/30"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-100 text-xs font-bold text-zinc-500">
              {league.crest}
            </div>
            <div className="flex-1">
              <div className="font-semibold text-zinc-800">{league.name}</div>
              <div className="text-xs text-zinc-400">{league.country}</div>
            </div>
            {!league.hasData && (
              <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-medium text-zinc-400">
                Live data
              </span>
            )}
            <svg className="h-5 w-5 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        ))}
      </div>

      {/* Available seasons */}
      {seasons.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-bold">Premier League — Available Seasons</h2>
          <div className="flex flex-wrap gap-2">
            {seasons.map((s) => (
              <Link
                key={s.id}
                href={`/standings/${s.id}`}
                className="rounded-lg bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-200"
              >
                {s.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}