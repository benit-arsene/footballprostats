import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { extractId, extractSlugPart, isCanonicalSlug } from "@/lib/slug";
import { getMatch } from "@/lib/api";
import { MOCK_MATCH_DETAILS } from "@/lib/mock-matches";
import { MatchContent } from "./match-content";

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

  const match = await getMatch(matchId).catch(() => null) ?? MOCK_MATCH_DETAILS[matchId] ?? null;
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

  const match = await getMatch(matchId).catch(() => null) ?? MOCK_MATCH_DETAILS[matchId] ?? null;
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
      <header className="mb-8 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        {/* Main score line */}
        <div className="flex items-center justify-center gap-4">
          {/* Home */}
          <div className="flex items-center gap-3">
            {match.home_team.crest_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={match.home_team.crest_url} alt="" className="h-10 w-10" />
            ) : (
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-100 text-xs font-bold text-zinc-500">
                {match.home_team.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()}
              </div>
            )}
            <span className="text-xl font-bold text-zinc-800">{match.home_team.name}</span>
          </div>

          {/* Score */}
          <div className="text-4xl font-black tabular-nums text-zinc-800">
            {match.home_score} — {match.away_score}
          </div>

          {/* Away */}
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold text-zinc-800">{match.away_team.name}</span>
            {match.away_team.crest_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={match.away_team.crest_url} alt="" className="h-10 w-10" />
            ) : (
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-100 text-xs font-bold text-zinc-500">
                {match.away_team.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()}
              </div>
            )}
          </div>
        </div>

        {/* Status badge */}
        <div className="mt-2 flex justify-center">
          {match.status === "live" && (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-500 px-3 py-0.5 text-xs font-bold text-white animate-pulse">
              <span className="h-1.5 w-1.5 rounded-full bg-white" />
              {match.minute}&apos;
            </span>
          )}
          {match.status === "finished" && (
            <span className="inline-flex rounded-full bg-zinc-100 px-3 py-0.5 text-xs font-bold text-zinc-500">FT</span>
          )}
          {match.status === "scheduled" && (
            <span className="inline-flex rounded-full bg-blue-50 px-3 py-0.5 text-xs font-bold text-blue-600">{match.kickoff_time}</span>
          )}
        </div>

        {/* Meta line */}
        <div className="mt-3 flex items-center justify-center gap-3 text-xs text-zinc-400">
          <span className="rounded bg-zinc-50 px-2 py-0.5 font-medium">{match.league.name}</span>
          <span>|</span>
          <span>{match.venue}</span>
          {match.referee && match.referee !== "TBD" && (
            <>
              <span>|</span>
              <span>Ref: {match.referee}</span>
            </>
          )}
        </div>
      </header>

      {/* ─── Tabbed Content: Results / Lineups / Live Stats ─── */}
      <MatchContent match={match} />
    </div>
  );
}
