import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { extractId } from "@/lib/slug";
import { getTeam } from "@/lib/api";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const teamId = extractId(slug);
  if (!teamId) return { title: "Team Not Found" };

  const team = await getTeam(teamId).catch(() => null);
  if (!team) return { title: "Team Not Found" };

  return {
    title: `${team.name} — Squad, Fixtures & Results`,
    description: `${team.name} (${team.league.name}). Founded ${team.founded}. Venue: ${team.venue}.`,
  };
}

export default async function TeamPage({ params }: Props) {
  const { slug } = await params;
  const teamId = extractId(slug);

  if (!teamId) notFound();

  const team = await getTeam(teamId).catch(() => null);
  if (!team) notFound();

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* ─── Team Header ─────────────────────────────────────── */}
      <header className="mb-8 flex items-center gap-6">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={team.crest_url} alt="" className="h-20 w-20" />
        <div>
          <h1 className="text-3xl font-bold">{team.name}</h1>
          <p className="text-zinc-500">
            {team.league.name} · {team.venue} · Est. {team.founded}
          </p>
          <p className="text-sm text-zinc-400">Manager: {team.coach}</p>
        </div>
      </header>

      {/* ─── Squad Roster ────────────────────────────────────── */}
      <section className="mb-8">
        <h2 className="mb-4 text-xl font-bold">Squad</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {team.squad.map((player) => (
            <a
              key={player.id}
              href={`/players/${player.slug}`}
              className="flex items-center gap-3 rounded-lg border border-zinc-200 p-3 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-zinc-800 dark:hover:border-blue-700 dark:hover:bg-blue-950/30"
            >
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-zinc-100 font-mono text-xs font-bold dark:bg-zinc-800">
                {player.number ?? "—"}
              </span>
              <div>
                <div className="font-medium">{player.name}</div>
                <div className="text-xs text-zinc-400">
                  {player.position} · {player.nationality}
                </div>
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* ─── Quick Stats placeholder ─────────────────────────── */}
      <section>
        <h2 className="mb-4 text-xl font-bold">Season Overview</h2>
        <p className="text-zinc-400">
          Fixtures, results, and performance charts coming soon.
        </p>
      </section>
    </div>
  );
}
