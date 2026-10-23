import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { extractId } from "@/lib/slug";
import { getTeam } from "@/lib/api";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const teamId = extractId(slug);
  if (!teamId) return { title: "Squad Not Found" };

  const team = await getTeam(teamId).catch(() => null);
  if (!team) return { title: "Squad Not Found" };

  return {
    title: `${team.name} — Squad`,
    description: `${team.name} squad roster.`,
  };
}

export default async function ClubSquadPage({ params }: Props) {
  const { slug } = await params;
  const teamId = extractId(slug);

  if (!teamId) notFound();

  const team = await getTeam(teamId).catch(() => null);
  if (!team) notFound();

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <nav className="mb-4">
        <Link href={`/clubs/${slug}`} className="inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-900">
          <span aria-hidden="true">&larr;</span> Back to Club
        </Link>
      </nav>

      <h1 className="mb-2 text-3xl font-bold">{team.name} — Squad</h1>
      <p className="mb-8 text-zinc-500">Current season squad roster.</p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {team.squad.map((player) => (
          <a
            key={player.id}
            href={`/players/${player.slug}`}
            className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white p-3 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-zinc-800 dark:hover:border-blue-700 dark:hover:bg-blue-950/30"
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
    </div>
  );
}
