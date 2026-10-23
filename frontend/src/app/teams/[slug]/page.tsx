import { redirect } from "next/navigation";

export default async function TeamRedirect({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  redirect(`/clubs/${slug}`);
}
