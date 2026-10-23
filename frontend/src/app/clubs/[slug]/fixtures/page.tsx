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
  if (!teamId) return { title: "Fixtures Not Found" };

  const team = await getTeam(teamId).catch(() => null);
  if (!team) return { title: "Fixtures Not Found" };

  return {
    title: `${team.name} — Fixtures`,
    description: `${team.name} upcoming fixtures.`,
  };
}

export default async function ClubFixturesPage({ params }: Props) {
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

      <h1 className="mb-2 text-3xl font-bold">{team.name} — Fixtures</h1>
      <p className="mb-8 text-zinc-500">Upcoming matches.</p>

      <p className="text-zinc-400">Fixture data coming soon.</p>
    </div>
  );
}
