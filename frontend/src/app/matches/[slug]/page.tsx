import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { extractId, extractSlugPart, isCanonicalSlug } from "@/lib/slug";
import { getMatch } from "@/lib/api";
import { MatchTicker } from "./match-ticker";
import { MatchLineups } from "./match-lineups";
import { MatchStats } from "./match-stats";

type Props = {
  params: Promise<{ slug: string }>;
};

/**
 * Match Center — /matches/[slug]-[id]
 *
 * Hybrid slug example: /matches/real-madrid-vs-man-city-984512
 *
 * SEO strategy:
 * - Server-rendered with full event data for finished matches (crawlers)
 * - Live matches poll every 15s via client-side MatchTicker
 * - Canonical redirect if slug is stale but ID is correct
 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const matchId = extractId(slug);
  if (!matchId) return { title: "Match Not Found" };

  const match = await getMatch(matchId).catch(() => null);
  if (!match) return { title: "Match Not Found" };

  return {
    title: `${match.home_team.name} vs ${match.away_team.name} — Live Score & Events`,
    description: `Full match coverage: live score, events, lineups, and stats for ${match.home_team.name} vs ${match.away_team.name}.`,
    openGraph: {
      title: `${match.home_team.name} ${match.home_score} - ${match.away_score} ${match.away_team.name}`,
      description: `Live score and event feed for ${match.home_team.name} vs ${match.away_team.name}`,
    },
  };
}

export default async function MatchPage({ params }: Props) {
  const { slug } = await params;
  const matchId = extractId(slug);

  if (!matchId) notFound();

  const match = await getMatch(matchId).catch(() => null);
  if (!match) notFound();

  // Canonical slug check — if the slug part is stale, we still serve the page
  // (Google indexes the canonical URL, so this prevents duplicate content)
  const canonicalName = `${match.home_team.name} vs ${match.away_team.name}`;
  const isCanonical = isCanonicalSlug(slug, canonicalName, match.id);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Canonical redirect hint for crawlers */}
      {!isCanonical && (
        <link
          rel="canonical"
          href={`/matches/${match.slug}`}
        />
      )}

      {/* ─── Score Header ────────────────────────────────────── */}
      <header className="mb-8 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={match.home_team.crest_url} alt="" className="h-12 w-12" />
            <span className="text-lg font-semibold">{match.home_team.name}</span>
          </div>

          <div className="text-center">
            <div className="text-4xl font-bold tabular-nums">
              {match.home_score} — {match.away_score}
            </div>
            <div className="mt-1 text-sm text-zinc-500">
              {match.status === "live" && (
                <span className="rounded bg-red-500 px-2 py-0.5 text-xs font-bold text-white animate-pulse">
                  {match.minute}&apos;
                </span>
              )}
              {match.status === "finished" && (
                <span className="text-zinc-400">Full Time</span>
              )}
              {match.status === "scheduled" && (
                <span>{match.kickoff_time}</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-lg font-semibold">{match.away_team.name}</span>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={match.away_team.crest_url} alt="" className="h-12 w-12" />
          </div>
        </div>

        <div className="mt-4 flex items-center justify-center gap-4 text-sm text-zinc-500">
          <span>{match.league.name}</span>
          <span>•</span>
          <span>{match.venue}</span>
          {match.referee && (
            <>
              <span>•</span>
              <span>Ref: {match.referee}</span>
            </>
          )}
        </div>
      </header>

      {/* ─── PCS-Style Event Ticker ──────────────────────────── */}
      <MatchTicker matchId={match.id} initialEvents={match.events} status={match.status} />

      {/* ─── Lineups ─────────────────────────────────────────── */}
      <MatchLineups
        homeLineup={match.home_lineup}
        awayLineup={match.away_lineup}
        homeTeam={match.home_team}
        awayTeam={match.away_team}
      />

      {/* ─── Match Stats ─────────────────────────────────────── */}
      {match.stats && <MatchStats stats={match.stats} />}
    </div>
  );
}
