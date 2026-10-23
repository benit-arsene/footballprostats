import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { extractId } from "@/lib/slug";
import { getCompetition } from "@/lib/api";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const competitionId = extractId(slug);
  if (!competitionId) return { title: "Competition Not Found" };

  const competition = await getCompetition(competitionId).catch(() => null);
  if (!competition) return { title: "Competition Not Found" };

  return {
    title: `${competition.name} — Standings, Results & Top Scorers`,
    description: `${competition.name} (${competition.country}). Full standings, top scorers, and season calendar.`,
  };
}

export default async function CompetitionPage({ params }: Props) {
  const { slug } = await params;
  const competitionId = extractId(slug);

  if (!competitionId) notFound();

  const competition = await getCompetition(competitionId).catch(() => null);
  if (!competition) notFound();

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* ─── Competition Header ───────────────────────────────────── */}
      <header className="mb-8 flex items-center gap-6">
        <img src={competition.logo_url} alt="" className="h-16 w-16" />
        <div>
          <h1 className="text-3xl font-bold">{competition.name}</h1>
          <p className="text-zinc-500">
            {competition.country} · {competition.season}
          </p>
        </div>
      </header>

      {/* ─── Standings Table ─────────────────────────────────── */}
      <section className="mb-8">
        <h2 className="mb-4 text-xl font-bold">Standings</h2>
        {competition.standings.length === 0 ? (
          <p className="text-zinc-400">Standings data not yet available.</p>
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
                  <th className="pb-2 pr-2 font-medium text-center">GD</th>
                  <th className="pb-2 pr-4 font-medium text-center">Pts</th>
                  <th className="pb-2 font-medium">Form</th>
                </tr>
              </thead>
              <tbody>
                {competition.standings.map((row) => (
                  <tr
                    key={row.team.id}
                    className="border-b border-zinc-100 last:border-b-0 dark:border-zinc-800"
                  >
                    <td className="py-2.5 pr-2 tabular-nums text-zinc-400">
                      {row.position}
                    </td>
                    <td className="py-2.5 pr-4">
                      <a
                        href={`/clubs/${row.team.slug}`}
                        className="font-medium hover:text-blue-600 dark:hover:text-blue-400"
                      >
                        {row.team.name}
                      </a>
                    </td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.played}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.won}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.drawn}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.lost}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">
                      {row.gd > 0 ? `+${row.gd}` : row.gd}
                    </td>
                    <td className="py-2.5 pr-4 text-center font-bold tabular-nums">
                      {row.points}
                    </td>
                    <td className="py-2.5 flex gap-0.5">
                      {row.form.map((f, i) => (
                        <span
                          key={i}
                          className={`inline-flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold text-white ${
                            f === "W"
                              ? "bg-green-500"
                              : f === "D"
                                ? "bg-zinc-400"
                                : "bg-red-500"
                          }`}
                        >
                          {f}
                        </span>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ─── Top Scorers ─────────────────────────────────────── */}
      <section className="mb-8">
        <h2 className="mb-4 text-xl font-bold">Top Scorers</h2>
        {competition.top_scorers.length === 0 ? (
          <p className="text-zinc-400">No scorer data available.</p>
        ) : (
          <div className="space-y-2">
            {competition.top_scorers.map((ts, i) => (
              <a
                key={ts.player.id}
                href={`/players/${ts.player.slug}`}
                className="flex items-center gap-4 rounded-xl border border-zinc-200 bg-white p-3 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-zinc-800 dark:hover:border-blue-700 dark:hover:bg-blue-950/30"
              >
                <span className="w-6 text-center font-bold text-zinc-400">{i + 1}</span>
                <div className="flex-1">
                  <div className="font-medium">{ts.player.name}</div>
                  <div className="text-xs text-zinc-400">{ts.team.name}</div>
                </div>
                <div className="text-right">
                  <div className="font-bold tabular-nums">{ts.goals}</div>
                  <div className="text-xs text-zinc-400">goals</div>
                </div>
              </a>
            ))}
          </div>
        )}
      </section>

      {/* ─── Season Calendar ─────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-xl font-bold">Season Calendar</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm divide-y divide-zinc-100">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-zinc-400 dark:border-zinc-800">
                <th className="pb-2 pr-2 font-medium">Date</th>
                <th className="pb-2 pr-4 font-medium">Home</th>
                <th className="pb-2 pr-2 font-medium text-center">Score</th>
                <th className="pb-2 pr-4 font-medium">Away</th>
                <th className="pb-2 pr-4 font-medium text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {competition.fixtures.map((match) => (
                <tr
                  key={match.id}
                  className="border-b border-zinc-100 last:border-b-0 dark:border-zinc-800"
                >
                  <td className="py-2.5 pr-4 text-zinc-500">{match.date}</td>
                  <td className="py-2.5 pr-4 font-medium">{match.home_team.name}</td>
                  <td className="py-2.5 pr-2 text-center tabular-nums">
                    {match.home_score} — {match.away_score}
                  </td>
                  <td className="py-2.5 pr-4 font-medium">{match.away_team.name}</td>
                  <td className="py-2.5 pr-4 font-medium text-center">
                    <span
                      className={`inline-flex h-6 w-6 items-center justify-center rounded text-[10px] font-bold text-white ${
                        match.status === "live"
                          ? "bg-emerald-500"
                          : match.status === "finished"
                            ? "bg-zinc-500"
                            : "bg-blue-500"
                      }`}
                    >
                      {match.status === "live"
                        ? match.minute + "'"
                        : match.status === "finished"
                          ? "FT"
                          : match.kickoff_time.slice(0, 5)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
