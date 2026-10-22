import type { Metadata } from "next";
import TopScorersView, { topScorersMetadata } from "@/components/TopScorersView";

// The golden boot race changes with every matchweek — never bake a snapshot in.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return topScorersMetadata("epl");
}

export default function TopScorersPage() {
  return <TopScorersView competition="epl" />;
}
