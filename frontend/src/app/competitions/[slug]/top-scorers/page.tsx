import { notFound } from "next/navigation";
import { extractId } from "@/lib/slug";
import { TOP_SCORER_COMPETITIONS, type TopScorerCompetitionKey } from "@/lib/constants";
import TopScorersView from "@/components/TopScorersView";

// The golden boot race changes with every matchweek — never bake a snapshot in.
export const dynamic = "force-dynamic";

export default async function CompetitionTopScorersPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const competitionId = extractId(slug);

  if (!competitionId) notFound();

  // Map provider competition ID to competition key (e.g. 39 → "epl", 140 → "laliga")
  let competitionKey: TopScorerCompetitionKey | null = null;
  for (const [key, entry] of Object.entries(TOP_SCORER_COMPETITIONS)) {
    if (entry.providerId === competitionId) {
      competitionKey = key as TopScorerCompetitionKey;
      break;
    }
  }

  if (!competitionKey) notFound();

  return <TopScorersView competition={competitionKey} />;
}
