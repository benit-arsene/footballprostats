import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { extractId } from "@/lib/slug";
import { getPlayer } from "@/lib/api";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const playerId = extractId(slug);
  if (!playerId) return { title: "Player Not Found" };

  const player = await getPlayer(playerId).catch(() => null);
  if (!player) return { title: "Player Not Found" };

  return {
    title: `${player.name} — Career Stats & Match Log`,
    description: `${player.name}'s career statistics, match-by-match logs, and key performance data.`,
  };
}

export default async function PlayerPage({ params }: Props) {
  const { slug } = await params;
  const playerId = extractId(slug);

  if (!playerId) notFound();

  const player = await getPlayer(playerId).catch(() => null);
  if (!player) notFound();

  const stats = player.career_stats;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* ─── Player Header ───────────────────────────────────── */}
      <header className="mb-8">
        <div className="flex items-center gap-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={player.team.crest_url} alt="" className="h-16 w-16" />
          <div>
            <h1 className="text-3xl font-bold">{player.name}</h1>
            <p className="text-zinc-500">
              {player.position} · {player.team.name} · #{player.number ?? "—"}
            </p>
            <p className="text-sm text-zinc-400">
              {player.nationality} · {player.foot} foot · DOB: {player.date_of_birth}
            </p>
          </div>
        </div>
      </header>

      {/* ─── Career Stats Cards ──────────────────────────────── */}
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

      {/* ─── Match-by-Match Log ──────────────────────────────── */}
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
