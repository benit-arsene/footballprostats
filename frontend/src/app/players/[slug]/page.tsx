import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import TeamCrest from "@/components/TeamCrest";
import { getPlayer } from "@/lib/api";

type Props = {
  params: Promise<{ slug: string }>;
};

function formatDate(date: string): string {
  if (!date) return "";

  const parsed = new Date(`${date}T00:00:00`);
  return Number.isNaN(parsed.getTime())
    ? date
    : parsed.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
}

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

async function getPlayerOrNull(slug: string) {
  try {
    return await getPlayer(slug);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("API 404:")) return null;
    throw error;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const player = await getPlayerOrNull(slug);
  if (!player) return { title: "Player Not Found" };

  return {
    title: `${player.name} — Player Profile`,
    description: `${player.name}'s player profile and current-season statistics.`,
  };
}

export default async function PlayerPage({ params }: Props) {
  const { slug } = await params;
  const player = await getPlayerOrNull(slug);
  if (!player) notFound();

  const statDefinitions = [
    { key: "appearances", label: "Appearances", icon: "calendar_month" },
    { key: "goals", label: "Goals", icon: "sports_soccer" },
    { key: "assists", label: "Assists", icon: "assistant_navigation" },
    { key: "yellow_cards", label: "Yellow cards", icon: "style" },
    { key: "red_cards", label: "Red cards", icon: "style" },
    { key: "minutes_played", label: "Minutes played", icon: "timer" },
  ] as const;
  const details = [
    { label: "Position", value: player.position },
    { label: "Jersey number", value: player.number?.toString() },
    { label: "Nationality", value: player.nationality },
    { label: "Date of birth", value: formatDate(player.date_of_birth) },
    {
      label: "Height",
      value: player.height_cm ? `${player.height_cm} cm` : "",
    },
    { label: "Preferred foot", value: player.foot },
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
          {player.team.id > 0 && (
            <>
              <Link
                href={`/clubs/${player.team.slug}`}
                className="transition-colors hover:text-zinc-950"
              >
                {player.team.name}
              </Link>
              <span aria-hidden="true" className="text-zinc-300">/</span>
            </>
          )}
          <span aria-current="page" className="font-semibold text-zinc-900">
            {player.name}
          </span>
        </nav>

        <section className="relative mt-6 overflow-hidden rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-8">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -right-20 -top-28 h-72 w-72 rounded-full bg-zinc-100 blur-3xl"
          />
          <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:gap-8">
            <div className="relative flex h-28 w-28 shrink-0 items-center justify-center rounded-2xl border border-zinc-700 bg-zinc-950 text-3xl font-extrabold tracking-tight text-white shadow-inner sm:h-32 sm:w-32">
              {initials(player.name)}
              {player.number !== null && (
                <span className="absolute -bottom-2 -right-2 rounded-lg border-2 border-white bg-zinc-900 px-2 py-1 text-xs font-bold text-white shadow-sm">
                  #{player.number}
                </span>
              )}
              {player.team.crest_url && (
                <span className="absolute -bottom-2 -left-2 flex h-10 w-10 items-center justify-center rounded-full border border-zinc-200 bg-white p-1.5 shadow-sm">
                  <TeamCrest
                    url={player.team.crest_url}
                    alt={`${player.team.name} crest`}
                    className="h-full w-full object-contain"
                  />
                </span>
              )}
            </div>

            <div className="min-w-0 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                {player.team.name && (
                  <span className="rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-zinc-700">
                    {player.team.name}
                  </span>
                )}
                {player.nationality && (
                  <span className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wider text-zinc-600">
                    {player.nationality}
                  </span>
                )}
              </div>
              <h1 className="break-words text-3xl font-extrabold leading-tight tracking-tight text-zinc-950 sm:text-4xl">
                {player.name}
              </h1>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-zinc-500">
                {player.position && (
                  <span>
                    <strong className="font-semibold text-zinc-900">Position:</strong>{" "}
                    {player.position}
                  </span>
                )}
                {player.position && player.date_of_birth && (
                  <span aria-hidden="true" className="text-zinc-300">/</span>
                )}
                {player.date_of_birth && (
                  <span>
                    <strong className="font-semibold text-zinc-900">Born:</strong>{" "}
                    {formatDate(player.date_of_birth)}
                  </span>
                )}
                {player.height_cm && (
                  <>
                    <span aria-hidden="true" className="text-zinc-300">/</span>
                    <span>
                      <strong className="font-semibold text-zinc-900">Height:</strong>{" "}
                      {player.height_cm} cm
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
        </section>

        <section id="season-stats" aria-label="Season statistics" className="mt-8">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-zinc-400">
                Performance
              </p>
              <h2 className="mt-1 text-xl font-bold tracking-tight text-zinc-950">
                Season statistics
              </h2>
            </div>
          </div>

          {player.season_stats.length === 0 ? (
            <p className="rounded-2xl border border-zinc-200 bg-white p-5 text-sm text-zinc-500">
              No verified season statistics are available.
            </p>
          ) : (
            <div className="space-y-5">
              {player.season_stats.map((season) => {
                const statsCards = statDefinitions.flatMap(({ key, label, icon }) => {
                  const value = season[key];
                  return value === undefined
                    ? []
                    : [{
                        label,
                        value: key === "minutes_played" ? value.toLocaleString() : value,
                        icon,
                      }];
                });
                return (
                  <section
                    key={`${season.season}-${season.competition_name ?? ""}`}
                    className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-6"
                  >
                    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                      <h3 className="text-base font-bold tracking-tight text-zinc-950">
                        {season.season}
                      </h3>
                      {season.competition_name && (
                        <span className="rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs font-semibold text-zinc-600">
                          {season.competition_name}
                        </span>
                      )}
                    </div>
                    {statsCards.length === 0 ? (
                      <p className="text-sm text-zinc-500">
                        No verified statistics are available for this season.
                      </p>
                    ) : (
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                        {statsCards.map((stat) => (
                          <article
                            key={stat.label}
                            className="flex min-h-36 flex-col justify-between rounded-xl border border-zinc-200 bg-white p-5 transition-colors hover:bg-zinc-50"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <span className="text-xs font-bold uppercase tracking-[0.14em] text-zinc-500">
                                {stat.label}
                              </span>
                              <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-600">
                                <span aria-hidden="true" className="material-symbols-outlined text-lg">
                                  {stat.icon}
                                </span>
                              </span>
                            </div>
                            <p className="mt-6 text-3xl font-bold leading-none tracking-tight tabular-nums text-zinc-950">
                              {stat.value}
                            </p>
                          </article>
                        ))}
                      </div>
                    )}
                  </section>
                );
              })}
            </div>
          )}
        </section>

        <nav
          aria-label="Player profile sections"
          className="mt-8 flex gap-6 overflow-x-auto border-b border-zinc-200"
        >
          <a
            href="#overview"
            className="whitespace-nowrap border-b-2 border-zinc-950 px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-950 transition-colors"
          >
            Overview
          </a>
          <a
            href="#season-stats"
            className="whitespace-nowrap border-b-2 border-transparent px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-400 transition-colors hover:border-zinc-400 hover:text-zinc-800"
          >
            Season stats
          </a>
          <a
            href="#match-log"
            className="whitespace-nowrap border-b-2 border-transparent px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-400 transition-colors hover:border-zinc-400 hover:text-zinc-800"
          >
            Match log
          </a>
        </nav>

        <div
          id="overview"
          className="mt-6 grid grid-cols-1 items-stretch gap-4 lg:grid-cols-5"
        >
          <section
            id="match-log"
            className="overflow-hidden rounded-2xl border border-zinc-200 bg-white lg:col-span-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-100 px-5 py-4 sm:px-6">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-400">
                  On the pitch
                </p>
                <h2 className="mt-1 text-base font-bold tracking-tight text-zinc-950">
                  Match log
                </h2>
              </div>
              {player.team.name && (
                <span className="text-xs font-medium text-zinc-500">
                  {player.team.name}
                </span>
              )}
            </div>
            {player.match_logs.length === 0 ? (
              <div className="flex min-h-56 flex-col items-center justify-center px-6 py-8 text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-full border border-zinc-200 bg-zinc-50 text-zinc-500">
                  <span aria-hidden="true" className="material-symbols-outlined text-xl">
                    event_busy
                  </span>
                </span>
                <p className="mt-4 text-sm font-semibold text-zinc-800">
                  No match log available
                </p>
                <p className="mt-1 max-w-sm text-xs leading-5 text-zinc-500">
                  Individual match appearances and performance details are not available for this player.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-zinc-100 bg-zinc-50 text-[10px] uppercase tracking-wider text-zinc-500">
                      <th className="px-5 py-3 font-bold sm:px-6">Date</th>
                      <th className="px-4 py-3 font-bold">Opponent</th>
                      <th className="px-5 py-3 text-right font-bold sm:px-6">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {player.match_logs.map((match) => (
                      <tr
                        key={match.match_id}
                        className="border-b border-zinc-100 last:border-b-0"
                      >
                        <td className="whitespace-nowrap px-5 py-3 text-xs tabular-nums text-zinc-500 sm:px-6">
                          {match.date || "—"}
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-zinc-900">
                          {match.opponent}
                        </td>
                        <td className="whitespace-nowrap px-5 py-3 text-right text-xs font-semibold tabular-nums text-zinc-700 sm:px-6">
                          {match.result}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <aside className="rounded-2xl border border-zinc-200 bg-white p-5 sm:p-6 lg:col-span-2">
            <div className="flex items-center gap-3 border-b border-zinc-100 pb-4">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-600">
                <span aria-hidden="true" className="material-symbols-outlined text-lg">
                  badge
                </span>
              </span>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-400">
                  At a glance
                </p>
                <h2 className="mt-0.5 text-base font-bold tracking-tight text-zinc-950">
                  Player details
                </h2>
              </div>
            </div>
            {details.length > 0 ? (
              <dl className="divide-y divide-zinc-100">
                {details.map((detail) => (
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
                No verified player details are available.
              </p>
            )}
          </aside>
        </div>
      </div>
    </main>
  );
}
