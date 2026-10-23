import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { extractId } from "@/lib/slug";
import { getPlayer } from "@/lib/api";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const playerId = extractId(slug);
  if (!playerId) return { title: "Statistics Not Found" };

  const player = await getPlayer(playerId).catch(() => null);
  if (!player) return { title: "Statistics Not Found" };

  return {
    title: `${player.name} — Statistics`,
    description: `${player.name}'s detailed season statistics.`,
  };
}

export default async function PlayerStatisticsPage({ params }: Props) {
  const { slug } = await params;
  const playerId = extractId(slug);

  if (!playerId) notFound();

  const player = await getPlayer(playerId).catch(() => null);
  if (!player) notFound();

  const stats = player.career_stats;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <nav className="mb-4">
        <Link href={`/players/${slug}`} className="inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-900">
          <span aria-hidden="true">&larr;</span> Back to Player
        </Link>
      </nav>

      <h1 className="mb-2 text-3xl font-bold">{player.name} — Statistics</h1>
      <p className="mb-8 text-zinc-500">
        {player.team.name} · {player.position} · Season {player.date_of_birth ? "Current" : "N/A"}
      </p>

      <section className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {[
          { label: "Apps", value: stats.appearances },
          { label: "Goals", value: stats.goals },
          { label: "Assists", value: stats.assists },
          { label: "Yellow", value: stats.yellow_cards },
          { label: "Red", value: stats.red_cards },
          { label: "Minutes", value: stats.minutes_played.toLocaleString() },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl border border-zinc-200 p-4 text-center dark:border-zinc-800"
          >
            <div className="text-2xl font-bold tabular-nums">{s.value}</div>
            <div className="mt-1 text-xs text-zinc-400">{s.label}</div>
          </div>
        ))}
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold">Match Log</h2>
        {player.match_logs.length === 0 ? (
          <p className="text-zinc-400">No match log data available.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-left text-zinc-400 dark:border-zinc-800">
                  <th className="pb-2 pr-4 font-medium">Date</th>
                  <th className="pb-2 pr-4 font-medium">Opponent</th>
                  <th className="pb-2 pr-4 font-medium">Result</th>
                  <th className="pb-2 pr-4 font-medium">G</th>
                  <th className="pb-2 pr-4 font-medium">A</th>
                  <th className="pb-2 font-medium">Rating</th>
                </tr>
              </thead>
              <tbody>
                {player.match_logs.map((log) => (
                  <tr
                    key={log.match_id}
                    className="border-b border-zinc-100 last:border-b-0 dark:border-zinc-800"
                  >
                    <td className="py-2.5 pr-4 text-zinc-500">{log.date}</td>
                    <td className="py-2.5 pr-4 font-medium">{log.opponent}</td>
                    <td className="py-2.5 pr-4">
                      <span
                        className={
                          log.result.startsWith("W")
                            ? "text-green-600"
                            : log.result.startsWith("L")
                              ? "text-red-500"
                              : "text-zinc-400"
                        }
                      >
                        {log.result}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 tabular-nums">{log.goals}</td>
                    <td className="py-2.5 pr-4 tabular-nums">{log.assists}</td>
                    <td className="py-2.5 tabular-nums">
                      {log.rating !== null ? log.rating.toFixed(1) : "—"}
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
