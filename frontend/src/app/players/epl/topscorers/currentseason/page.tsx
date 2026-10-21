import type { Metadata } from "next";
import TopScorersTable, { type ScorerInput } from "@/components/TopScorersTable";
import { getLiveMatchesSummary, getLiveTopScorersWithLatency } from "@/lib/api";
import { MOCK_MATCHES, MOCK_TOP_SCORERS } from "@/lib/mock-data";
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
    getLiveTopScorersWithLatency(),
    getLiveMatchesSummary(),
  ]);

  let scorers: ScorerInput[] = [];
  let season: string | null = null;
  let updatedAt: string | null = null;
  let latencyMs: number | null = null;
  let feed: "live" | "snapshot" = "live";

  if (scorersResult.status === "fulfilled" && scorersResult.value.data.scorers?.length > 0) {
    scorers = scorersResult.value.data.scorers;
    season = scorersResult.value.data.season ?? null;
    updatedAt = scorersResult.value.data.last_updated ?? null;
    latencyMs = scorersResult.value.latencyMs;
  } else {
    // The stadium feed is unreachable — keep the page useful with the cached snapshot.
    scorers = MOCK_TOP_SCORERS;
    feed = "snapshot";
  }

  const highlights: MatchSummary[] =
    matchesResult.status === "fulfilled" ? matchesResult.value : MOCK_MATCHES;

  return (
    <main className="scorers-canvas min-h-screen w-full bg-surface font-body-md text-on-surface">
      <TopScorersTable
        scorers={scorers}
        season={season}
        updatedAt={updatedAt}
        latencyMs={latencyMs}
        highlights={highlights}
        feed={feed}
      />
    </main>
  );
}
