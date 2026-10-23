import { redirect } from "next/navigation";
import { TOP_SCORER_COMPETITIONS, type TopScorerCompetitionKey } from "@/lib/constants";

export default async function TopScorersRedirect({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const key = slug as TopScorerCompetitionKey;
  const entry = TOP_SCORER_COMPETITIONS[key];
  if (!entry) redirect("/competitions/epl-39/top-scorers/current-season");
  redirect(`/competitions/${key}-${entry.providerId}/top-scorers/current-season`);
}
