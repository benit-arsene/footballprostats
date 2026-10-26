import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import TeamCrest from "@/components/TeamCrest";
import { getTeam } from "@/lib/api";
import { extractId } from "@/lib/slug";

type Props = {
  params: Promise<{ slug: string }>;
};

async function getTeamOrNull(teamId: number) {
  try {
    return await getTeam(teamId);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("API 404:")) return null;
    throw error;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const teamId = extractId(slug);
  if (!teamId) return { title: "Club Not Found" };

  const team = await getTeamOrNull(teamId);
  if (!team) return { title: "Club Not Found" };

  return {
    title: `${team.name} — Club Profile`,
    description: [
      team.name,
      team.founded ? `Founded ${team.founded}` : "",
      team.venue ? `Home ground: ${team.venue}` : "",
    ]
      .filter(Boolean)
      .join(". "),
  };
}

export default async function ClubPage({ params }: Props) {
  const { slug } = await params;
  const teamId = extractId(slug);
  if (!teamId) notFound();

  const team = await getTeamOrNull(teamId);
  if (!team) notFound();

  const leagueName = team.league.name && team.league.name !== "Unknown"
    ? team.league.name
    : "";
  const clubDetails = [
    { label: "Founded", value: team.founded > 0 ? team.founded.toString() : "" },
    { label: "Home ground", value: team.venue },
    { label: "Head coach / manager", value: team.coach },
    { label: "Current league", value: leagueName },
  ].filter((detail) => detail.value);

  return (
    <main className="min-h-screen bg-zinc-50 px-4 py-8 font-sans text-zinc-950 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-6xl">
        <nav
          aria-label="Breadcrumb"
          className="flex flex-wrap items-center gap-2 border-b border-zinc-200 pb-4 text-sm text-zinc-500"
        >
          <Link href="/" className="transition-colors hover:text-zinc-950">
            Home
          </Link>
          <span aria-hidden="true" className="text-zinc-300">/</span>
          <span aria-current="page" className="font-semibold text-zinc-900">
            {team.name}
          </span>
        </nav>

        <header className="relative mt-6 overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950 p-6 text-white shadow-sm sm:p-9">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -right-16 -top-28 h-80 w-80 rounded-full bg-zinc-700/30 blur-3xl"
          />
          <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:gap-8">
            <div className="flex h-28 w-28 shrink-0 items-center justify-center rounded-xl border border-zinc-800 bg-white p-4 shadow-inner sm:h-32 sm:w-32">
              <TeamCrest
                url={team.crest_url}
                alt={`${team.name} crest`}
                className="h-full w-full object-contain"
                fallback={
                  <span className="text-2xl font-extrabold tracking-tight text-zinc-500">
                    {team.name.slice(0, 2).toUpperCase()}
                  </span>
                }
              />
            </div>

            <div className="min-w-0 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
                  Club profile
                </span>
              </div>
              <h1 className="break-words text-3xl font-extrabold leading-tight tracking-tight text-white">
                {team.name}
              </h1>
              {team.venue && (
                <p className="flex items-center gap-2 text-sm text-zinc-300">
                  {team.venue}
                </p>
              )}
            </div>
          </div>
        </header>

        <nav
          aria-label="Club profile sections"
          className="mt-7 flex gap-6 overflow-x-auto border-b border-zinc-200"
        >
          <a
            href="#overview"
            className="whitespace-nowrap border-b-2 border-zinc-950 px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-950"
          >
            Overview
          </a>
          <a
            href="#squad"
            className="whitespace-nowrap border-b-2 border-transparent px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-400 transition-colors hover:border-zinc-400 hover:text-zinc-800"
          >
            Squad
          </a>
          <Link
            href={`/clubs/${slug}/fixtures`}
            className="whitespace-nowrap border-b-2 border-transparent px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-400 transition-colors hover:border-zinc-400 hover:text-zinc-800"
          >
            Fixtures
          </Link>
          <Link
            href={`/clubs/${slug}/results`}
            className="whitespace-nowrap border-b-2 border-transparent px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-400 transition-colors hover:border-zinc-400 hover:text-zinc-800"
          >
            Results
          </Link>
        </nav>

        <div
          id="overview"
          className="mt-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-5"
        >
          <section
            id="squad"
            className="overflow-hidden rounded-xl border border-zinc-200 bg-white lg:col-span-3"
          >
            <div className="flex flex-wrap items-end justify-between gap-3 border-b border-zinc-100 px-5 py-5 sm:px-6">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-400">
                  First team
                </p>
                <h2 className="mt-1 text-xl font-bold tracking-tight text-zinc-950">
                  Squad
                </h2>
              </div>
              <span className="text-xs font-medium text-zinc-500">
                {team.squad.length} {team.squad.length === 1 ? "player" : "players"}
              </span>
            </div>
            {team.squad.length === 0 ? (
              <div className="flex items-center gap-4 border-t border-dashed border-zinc-200 px-5 py-6 sm:px-6">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-dashed border-zinc-300 bg-zinc-50 text-zinc-500">
                  <span aria-hidden="true" className="material-symbols-outlined text-xl">
                    groups
                  </span>
                </span>
                <div>
                  <p className="text-sm font-semibold text-zinc-800">
                    Squad details unavailable
                  </p>
                  <p className="mt-1 text-xs leading-5 text-zinc-500">
                    A verified squad roster is not available right now.
                  </p>
                </div>
              </div>
            ) : (
              <ul className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 sm:p-5">
                {team.squad.map((player) => (
                  <li key={player.id}>
                    <Link
                      href={`/players/${player.slug}`}
                      className="group flex h-full items-center gap-3 rounded-xl border border-zinc-200 bg-white p-4 transition-colors hover:border-zinc-400 hover:bg-zinc-50"
                    >
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 text-xs font-bold tabular-nums text-zinc-600 transition-colors group-hover:border-zinc-300 group-hover:text-zinc-950">
                        {player.number ?? "—"}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold text-zinc-900">
                          {player.name}
                        </span>
                        <span className="mt-1 block truncate text-xs text-zinc-500">
                          {[player.position, player.nationality].filter(Boolean).join(" · ") || "Player"}
                        </span>
                      </span>
                      <span aria-hidden="true" className="material-symbols-outlined text-base text-zinc-300 transition-colors group-hover:text-zinc-700">
                        arrow_forward
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <aside className="rounded-xl border border-zinc-200 bg-white p-5 sm:p-6 lg:col-span-2">
            <div className="flex items-center gap-3 border-b border-zinc-100 pb-4">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-600">
                <span aria-hidden="true" className="material-symbols-outlined text-lg">
                  info
                </span>
              </span>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-400">
                  At a glance
                </p>
                <h2 className="mt-0.5 text-base font-bold tracking-tight text-zinc-950">
                  Club details
                </h2>
              </div>
            </div>
            {clubDetails.length > 0 ? (
              <dl className="divide-y divide-zinc-100">
                {clubDetails.map((detail) => (
                  <div
                    key={detail.label}
                    className="flex items-center justify-between gap-4 py-4"
                  >
                    <dt className="text-[10px] font-bold uppercase tracking-[0.14em] text-zinc-400">
                      {detail.label}
                    </dt>
                    <dd className="text-right text-sm font-semibold text-zinc-900">
                      {detail.value}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="py-6 text-sm leading-6 text-zinc-500">
                No verified club details are available.
              </p>
            )}
          </aside>
        </div>
      </div>
    </main>
  );
}
