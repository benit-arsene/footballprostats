import type { Metadata } from "next";
import TopScorersTable, { type ScorerInput } from "@/components/TopScorersTable";
import { getLiveMatchesSummary, getLiveTopScorers } from "@/lib/api";
import type { MatchSummary } from "@/lib/types";

// The golden boot race changes with every matchweek — never bake a snapshot in.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Premier League Top Scorers — Current Season",
  description:
    "Official Premier League scoring records, expected goals (xG), shot conversion and tactical high-impact finishing metrics for every golden boot contender.",
};

export default async function TopScorersPage() {
  const [scorersResult, matchesResult] = await Promise.allSettled([
    getLiveTopScorers(),
    getLiveMatchesSummary(),
  ]);

  let scorers: ScorerInput[] = [];
  let season: string | null = null;
  let updatedAt: string | null = null;
  let feed: "live" | "snapshot" = "live";

  if (scorersResult.status === "fulfilled" && scorersResult.value.scorers?.length > 0) {
    scorers = scorersResult.value.scorers;
    season = scorersResult.value.season ?? null;
    updatedAt = scorersResult.value.last_updated ?? null;
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
        updatedAt={updatedAt}
        highlights={highlights}
        feed={feed}
      />
    </main>
  );
}
