import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { extractId } from "@/lib/slug";
import { getCompetition, getCompetitionFixtures } from "@/lib/api";
import Link from "next/link";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const competitionId = extractId(slug);
  if (!competitionId) return { title: "Fixtures Not Found" };

  const competition = await getCompetition(competitionId).catch(() => null);
  if (!competition) return { title: "Fixtures Not Found" };

  return {
    title: `${competition.name} Fixtures — ${competition.season}`,
    description: `Upcoming fixtures for ${competition.name} (${competition.country}).`,
  };
}

export default async function CompetitionFixturesPage({ params }: Props) {
  const { slug } = await params;
  const competitionId = extractId(slug);

  if (!competitionId) notFound();

  const competition = await getCompetition(competitionId).catch(() => null);
  if (!competition) notFound();

  const fixtures = await getCompetitionFixtures(competitionId).catch(() => []);

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
            Fixtures · {competition.country} · {competition.season}
          </p>
        </div>
      </header>

      <section>
        <h2 className="mb-4 text-xl font-bold">Upcoming Fixtures</h2>
        {fixtures.length === 0 ? (
          <p className="text-zinc-400">No upcoming fixtures.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm divide-y divide-zinc-100">
              <thead>
                <tr className="border-b border-zinc-200 text-left text-zinc-400">
                  <th className="pb-2 pr-4 font-medium">Date</th>
                  <th className="pb-2 pr-4 font-medium">Home</th>
                  <th className="pb-2 pr-2 font-medium text-center">Score</th>
                  <th className="pb-2 pr-4 font-medium">Away</th>
                  <th className="pb-2 pr-4 font-medium text-center">Kickoff</th>
                  <th className="pb-2 pr-4 font-medium text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {fixtures.map((match) => (
                  <tr
                    key={match.id}
                    className="border-b border-zinc-100 last:border-b-0"
                  >
                    <td className="py-2.5 pr-4 text-zinc-500">{match.date}</td>
                    <td className="py-2.5 pr-4 font-medium">{match.home_team.name}</td>
                    <td className="py-2.5 pr-2 text-center tabular-nums">
                      {match.home_score} — {match.away_score}
                    </td>
                    <td className="py-2.5 pr-4 font-medium">{match.away_team.name}</td>
                    <td className="py-2.5 pr-4 text-center">{match.kickoff_time.slice(0, 5)}</td>
                    <td className="py-2.5 pr-4 text-center">
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
        )}
      </section>
    </div>
  );
}
