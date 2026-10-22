import type { Metadata } from "next";
import TopScorersTable, { type ScorerInput } from "@/components/TopScorersTable";
import { getCompetitionBySlug, getLiveMatchesSummary, getLiveTopScorers } from "@/lib/api";
import type { MatchSummary } from "@/lib/types";

const SLUG_TO_DB_SLUG: Record<string, string> = {
  epl: "premier-league-39",
  laliga: "laliga",
};

export const dynamic = "force-dynamic";

export default async function CompetitionTopScorersPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug: competition } = await params;
  const dbSlug = SLUG_TO_DB_SLUG[competition];
  if (!dbSlug) {
    return <main className="p-8">Unsupported competition.</main>;
  }

  let competitionInfo;
  try {
    competitionInfo = await getCompetitionBySlug(dbSlug);
  } catch {
    return <main className="p-8">Competition not registered.</main>;
  }

  const [scorersResult, matchesResult] = await Promise.allSettled([
    getLiveTopScorers(competitionInfo.id),
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

  const highlights: MatchSummary[] =
    matchesResult.status === "fulfilled" ? matchesResult.value : [];

  return (
    <main className="scorers-canvas min-h-screen w-full bg-surface font-body-md text-on-surface">
      <TopScorersTable
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