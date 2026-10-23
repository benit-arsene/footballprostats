import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { extractId } from "@/lib/slug";
import { getCompetition, getCompetitionStandings } from "@/lib/api";
import Link from "next/link";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const competitionId = extractId(slug);
  if (!competitionId) return { title: "Standings Not Found" };

  const competition = await getCompetition(competitionId).catch(() => null);
  if (!competition) return { title: "Standings Not Found" };

  return {
    title: `${competition.name} Standings — ${competition.season}`,
    description: `League table for ${competition.name} (${competition.country}).`,
  };
}

export default async function CompetitionStandingsPage({ params }: Props) {
  const { slug } = await params;
  const competitionId = extractId(slug);

  if (!competitionId) notFound();

  const competition = await getCompetition(competitionId).catch(() => null);
  if (!competition) notFound();

  const standings = await getCompetitionStandings(competitionId).catch(() => []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <nav className="mb-6">
        <Link
          href={`/competitions/${slug}`}
          className="inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-900 transition-colors"
        >
          <span aria-hidden="true">&larr;</span> Back to {competition.name}
        </Link>
      </nav>

      <header className="mb-8 flex items-center gap-6">
        <img src={competition.logo_url} alt="" className="h-16 w-16" />
        <div>
          <h1 className="text-3xl font-bold">{competition.name}</h1>
          <p className="text-zinc-500">
            Standings · {competition.country} · {competition.season}
          </p>
        </div>
      </header>

      <section>
        <h2 className="mb-4 text-xl font-bold">League Table</h2>
        {standings.length === 0 ? (
          <p className="text-zinc-400">Standings data not yet available.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-left text-zinc-400">
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
                {standings.map((row) => (
                  <tr
                    key={row.team.id}
                    className="border-b border-zinc-100 last:border-b-0"
                  >
                    <td className="py-2.5 pr-2 tabular-nums text-zinc-400 font-medium">
                      {row.position}
                    </td>
                    <td className="py-2.5 pr-4">
                      <Link
                        href={`/clubs/${row.team.slug}`}
                        className="font-medium hover:text-blue-600 transition-colors"
                      >
                        {row.team.name}
                      </Link>
                    </td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.played}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.won}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.drawn}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.lost}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.gf}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">{row.ga}</td>
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
    </div>
  );
}
