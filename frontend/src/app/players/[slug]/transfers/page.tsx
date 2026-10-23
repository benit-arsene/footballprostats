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
  if (!playerId) return { title: "Transfers Not Found" };

  const player = await getPlayer(playerId).catch(() => null);
  if (!player) return { title: "Transfers Not Found" };

  return {
    title: `${player.name} — Transfers`,
    description: `${player.name}'s transfer history.`,
  };
}

export default async function PlayerTransfersPage({ params }: Props) {
  const { slug } = await params;
  const playerId = extractId(slug);

  if (!playerId) notFound();

  const player = await getPlayer(playerId).catch(() => null);
  if (!player) notFound();

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <nav className="mb-4">
        <Link href={`/players/${slug}`} className="inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-900">
          <span aria-hidden="true">&larr;</span> Back to Player
        </Link>
      </nav>

      <h1 className="mb-2 text-3xl font-bold">{player.name} — Transfers</h1>
      <p className="mb-8 text-zinc-500">Transfer history.</p>

      <p className="text-zinc-400">Transfer data coming soon.</p>
    </div>
  );
}
