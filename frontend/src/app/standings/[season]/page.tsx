import type { Metadata } from "next";
import Link from "next/link";
import { getStandingsBySeason, getSeasons } from "@/lib/api";

type Props = {
  params: Promise<{ season: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { season } = await params;
  return { title: `Premier League Standings — Season ${season}` };
}

export default async function StandingsPage({ params }: Props) {
  const { season } = await params;
  const seasonId = parseInt(season, 10);

  let seasons: { id: number; label: string }[] = [];
  let standings: Awaited<ReturnType<typeof getStandingsBySeason>> | null = null;
  try {
    seasons = await getSeasons(1);
  } catch {
    seasons = [];
  }
  try {
    standings = await getStandingsBySeason(seasonId);
  } catch {
    standings = null;
  }

  const currentLabel = seasons.find((s) => s.id === seasonId)?.label ?? `Season ${seasonId}`;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <nav className="mb-4">
        <Link href="/" className="inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-900">
          <span aria-hidden="true">&larr;</span> Back
        </Link>
      </nav>

      <h1 className="mb-2 text-3xl font-bold">Premier League {currentLabel} Standings</h1>

      {/* Season selector */}
      {seasons.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          {seasons.map((s) => (
            <Link
              key={s.id}
              href={`/standings/${s.id}`}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                s.id === seasonId
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              {s.label}
            </Link>
          ))}
        </div>
      )}

      {!standings ? (
        <p className="text-zinc-400">Standings data not yet available for this season.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-zinc-400 dark:border-zinc-800">
                <th className="pb-2 pr-2 font-medium">#</th>
                <th className="pb-2 pr-4 font-medium">Team</th>
                <th className="pb-2 pr-2 font-medium text-center">P</th>
                <th className="pb-2 pr-2 font-medium text-center">W</th>
                <th className="pb-2 pr-2 font-medium text-center">D</th>
                <th className="pb-2 pr-2 font-medium text-center">L</th>
                <th className="pb-2 pr-2 font-medium text-center">GF</th>
                <th className="pb-2 pr-2 font-medium text-center">GA</th>
                <th className="pb-2 pr-2 font-medium text-center">GD</th>
                <th className="pb-2 pr-4 font-medium text-center">Pts</th>
                <th className="pb-2 font-medium">Form</th>
              </tr>
            </thead>
            <tbody>
              {standings.rows.map((row) => (
                <tr
                  key={row.team.id}
                  className="border-b border-zinc-100 last:border-b-0 dark:border-zinc-800"
                >
                  <td className="py-2.5 pr-2 tabular-nums text-zinc-400">{row.position}</td>
                  <td className="py-2.5 pr-4">
                    <Link
                      href={`/teams/${row.team.slug}`}
                      className="font-medium hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      {row.team.name}
                    </Link>
                  </td>
                  <td className="py-2.5 pr-2 text-center tabular-nums">{row.played}</td>
                  <td className="py-2.5 pr-2 text-center tabular-nums">{row.won}</td>
                  <td className="py-2.5 pr-2 text-center tabular-nums">{row.drawn}</td>
                  <td className="py-2.5 pr-2 text-center tabular-nums">{row.lost}</td>
                  <td className="py-2.5 pr-2 text-center tabular-nums">{row.goals_for}</td>
                  <td className="py-2.5 pr-2 text-center tabular-nums">{row.goals_against}</td>
                  <td className="py-2.5 pr-2 text-center tabular-nums">{row.goal_difference > 0 ? `+${row.goal_difference}` : row.goal_difference}</td>
                  <td className="py-2.5 pr-4 text-center font-bold tabular-nums">{row.points}</td>
                  <td className="py-2.5">
                    <div className="flex gap-1">
                      {(row.form.includes(",")
                        ? row.form.split(",")
                        : row.form.split("")
                      )
                        .filter(Boolean)
                        .map((f, i) => (
                          <span
                            key={i}
                            className={`inline-flex h-6 w-6 items-center justify-center rounded-md text-[11px] font-bold text-white shadow-sm ${
                              f === "W"
                                ? "bg-emerald-500"
                                : f === "D"
                                  ? "bg-zinc-400"
                                  : "bg-red-500"
                            }`}
                          >
                            {f}
                          </span>
                        ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}