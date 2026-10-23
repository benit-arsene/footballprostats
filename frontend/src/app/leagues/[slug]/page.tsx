import { redirect } from "next/navigation";

export default async function LeagueRedirect({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  redirect(`/competitions/${slug}`);
}
