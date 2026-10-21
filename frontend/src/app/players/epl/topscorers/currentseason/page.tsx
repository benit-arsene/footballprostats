import type { Metadata } from "next";
import TopScorersTable, { type ScorerInput } from "@/components/TopScorersTable";
import { getLiveMatchesSummary, getLiveTopScorers } from "@/lib/api";
import type { MatchSummary } from "@/lib/types";

// The golden boot race changes with every matchweek — never bake a snapshot in.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Premier League Top Scorers — Current Season",
  description:
    "Official Premier League scoring records — goals, appearances, assists and penalties published by the official football-data.org feed for every recorded goalscorer.",
};

export default async function TopScorersPage() {
  const [scorersResult, matchesResult] = await Promise.allSettled([
    getLiveTopScorers(),
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
