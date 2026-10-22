import type { Metadata } from "next";
import TopScorersTable, { type ScorerInput } from "@/components/TopScorersTable";
import { getCompetitionBySlug, getLiveMatchesSummary, getLiveTopScorers } from "@/lib/api";
import { TOP_SCORER_COMPETITIONS, type TopScorerCompetitionKey } from "@/lib/constants";
import type { MatchSummary } from "@/lib/types";

/**
 * Shared implementation of the player top-scorers pages.
 *
 * `/players/epl/topscorers/currentseason` and
 * `/players/<competition>/topscorers/currentseason` both render this view, so
 * the heading always names the competition that was actually loaded instead of
 * a fixed league.
 */

async function resolveCompetition(key: TopScorerCompetitionKey) {
  const entry = TOP_SCORER_COMPETITIONS[key];
  const info = await getCompetitionBySlug(entry.dbSlug).catch(() => null);
  return {
    name: info?.name ?? entry.label,
    id: info?.id ?? entry.competitionId,
  };
}

export async function topScorersMetadata(key: TopScorerCompetitionKey): Promise<Metadata> {
  const competition = await resolveCompetition(key);
  return {
    title: `${competition.name} Top Scorers — Current Season`,
    description: `Official ${competition.name} scoring records — goals, appearances, assists and penalties published by the official football-data.org feed for every recorded goalscorer.`,
  };
}

export default async function TopScorersView({
  competition,
}: {
  competition: TopScorerCompetitionKey;
}) {
  const entry = TOP_SCORER_COMPETITIONS[competition];
  const info = await getCompetitionBySlug(entry.dbSlug).catch(() => null);
  const competitionId = info?.id ?? entry.competitionId;

  const [scorersResult, matchesResult] = await Promise.allSettled([
    getLiveTopScorers(competitionId),
    getLiveMatchesSummary(),
  ]);

  let scorers: ScorerInput[] = [];
  let season: string | null = null;
  let currentMatchday: number | null = null;
  let scorersCount: number | null = null;
  let goalsTotal: number | null = null;
  let feed: "live" | "snapshot" = "live";

  if (scorersResult.status === "fulfilled" && scorersResult.value.scorers?.length > 0) {
    scorers = scorersResult.value.scorers;
    season = scorersResult.value.season ?? null;
    currentMatchday = scorersResult.value.current_matchday ?? null;
    scorersCount = scorersResult.value.scorers_count ?? null;
    goalsTotal = scorersResult.value.goals_total ?? null;
  } else {
    scorers = [];
    feed = "snapshot";
  }

  // The competition row carries the label the rest of the site uses; the
  // provider name (which can differ, e.g. "Primera Division") is the fallback
  // for when that row cannot be read.
  const providerName =
    scorersResult.status === "fulfilled" ? scorersResult.value.competition_name : null;
  const competitionName = info?.name ?? providerName ?? entry.label;

  const highlights: MatchSummary[] =
    matchesResult.status === "fulfilled" ? matchesResult.value : [];

  return (
    <main className="scorers-canvas min-h-screen w-full bg-surface font-body-md text-on-surface">
      <TopScorersTable
        competitionName={competitionName}
        competitionProviderId={entry.providerId}
        scorers={scorers}
        season={season}
        currentMatchday={currentMatchday}
        scorersCount={scorersCount}
        goalsTotal={goalsTotal}
        highlights={highlights}
        feed={feed}
      />
    </main>
  );
}
