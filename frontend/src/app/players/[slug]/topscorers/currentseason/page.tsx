import type { Metadata } from "next";
import TopScorersView, { topScorersMetadata } from "@/components/TopScorersView";
import { isTopScorerCompetition } from "@/lib/constants";

// The golden boot race changes with every matchweek — never bake a snapshot in.
export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  if (!isTopScorerCompetition(slug)) return { title: "Top Scorers" };
  return topScorersMetadata(slug);
}

export default async function CompetitionTopScorersPage({ params }: Props) {
  const { slug } = await params;
  if (!isTopScorerCompetition(slug)) {
    return <main className="p-8">Unsupported competition.</main>;
  }
  return <TopScorersView competition={slug} />;
}
