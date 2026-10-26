import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import TeamCrest from "@/components/TeamCrest";
import { getCompetitionResults, getTeam } from "@/lib/api";
import { LEAGUE_IDS } from "@/lib/constants";
import { extractId } from "@/lib/slug";
import type { MatchSummary } from "@/lib/types";

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

function formatDate(date: string): string {
  if (!date) return "Date unavailable";
  const parsed = new Date(`${date}T00:00:00`);
  return Number.isNaN(parsed.getTime())
    ? date
    : parsed.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
}

function resultForTeam(match: MatchSummary, teamSlug: string): "W" | "D" | "L" {
  const home = match.home_team.slug === teamSlug;
  const teamScore = home ? match.home_score : match.away_score;
  const opponentScore = home ? match.away_score : match.home_score;
  if (teamScore > opponentScore) return "W";
  if (teamScore < opponentScore) return "L";
  return "D";
}

async function loadResults(): Promise<{ matches: MatchSummary[]; failed: boolean }> {
  try {
    return {
      matches: await getCompetitionResults(LEAGUE_IDS.premier_league),
      failed: false,
    };
  } catch {
    return { matches: [], failed: true };
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const teamId = extractId(slug);
  if (!teamId) return { title: "Results Not Found" };

  const team = await getTeamOrNull(teamId);
  if (!team) return { title: "Results Not Found" };

  return {
    title: `${team.name} — Results`,
    description: `Recent Premier League results for ${team.name}.`,
  };
}

export default async function ClubResultsPage({ params }: Props) {
  const { slug } = await params;
  const teamId = extractId(slug);
  if (!teamId) notFound();

  const team = await getTeamOrNull(teamId);
  if (!team) notFound();

  const resultResponse = await loadResults();
  const results = resultResponse.matches.filter(
    (match) =>
      match.home_team.slug === team.slug || match.away_team.slug === team.slug,
  );
  const record = results.reduce(
    (summary, match) => {
      const result = resultForTeam(match, team.slug);
      summary[result] += 1;
      return summary;
    },
    { W: 0, D: 0, L: 0 },
  );

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
          <Link
            href={`/clubs/${slug}`}
            className="transition-colors hover:text-zinc-950"
          >
            {team.name}
          </Link>
          <span aria-hidden="true" className="text-zinc-300">/</span>
          <span aria-current="page" className="font-semibold text-zinc-900">
            Results
          </span>
        </nav>

        <header className="relative mt-6 overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 p-5 text-white shadow-sm sm:p-7">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -right-16 -top-24 h-64 w-64 rounded-full bg-zinc-700/30 blur-3xl"
          />
          <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl border border-zinc-800 bg-white p-3 shadow-inner">
              <TeamCrest
                url={team.crest_url}
                alt={`${team.name} crest`}
                className="h-full w-full object-contain"
                fallback={
                  <span className="text-xl font-extrabold text-zinc-500">
                    {team.name.slice(0, 2).toUpperCase()}
                  </span>
                }
              />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
                Club results
              </p>
              <h1 className="mt-1 break-words text-3xl font-extrabold leading-tight tracking-tight">
                {team.name}
              </h1>
              <p className="mt-2 text-sm text-zinc-300">
                Recent Premier League results
              </p>
            </div>
          </div>
        </header>

        <nav
          aria-label="Club profile sections"
          className="mt-7 flex gap-6 overflow-x-auto border-b border-zinc-200"
        >
          <Link
            href={`/clubs/${slug}`}
            className="whitespace-nowrap border-b-2 border-transparent px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-400 transition-colors hover:border-zinc-400 hover:text-zinc-800"
          >
            Overview
          </Link>
          <Link
            href={`/clubs/${slug}/squad`}
            className="whitespace-nowrap border-b-2 border-transparent px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-400 transition-colors hover:border-zinc-400 hover:text-zinc-800"
          >
            Squad
          </Link>
          <Link
            href={`/clubs/${slug}/fixtures`}
            className="whitespace-nowrap border-b-2 border-transparent px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-400 transition-colors hover:border-zinc-400 hover:text-zinc-800"
          >
            Fixtures
          </Link>
          <span
            aria-current="page"
            className="whitespace-nowrap border-b-2 border-zinc-950 px-1 py-3 text-xs font-bold uppercase tracking-[0.14em] text-zinc-950"
          >
            Results
          </span>
        </nav>

        <section aria-label="Recent results" className="mt-7">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-400">
                Premier League
              </p>
              <h2 className="mt-1 text-xl font-bold tracking-tight text-zinc-950">
                Recent results
              </h2>
            </div>
            {results.length > 0 && (
              <div aria-label="Results record" className="flex gap-2">
                {([
                  ["W", "Wins"],
                  ["D", "Draws"],
                  ["L", "Losses"],
                ] as const).map(([key, label]) => (
                  <div
                    key={key}
                    className="min-w-14 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-center"
                    aria-label={`${record[key]} ${label}`}
                  >
                    <p className="text-sm font-bold tabular-nums text-zinc-950">
                      {record[key]}
                    </p>
                    <p className="text-[9px] font-semibold uppercase tracking-wider text-zinc-400">
                      {key}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {resultResponse.failed ? (
            <div className="rounded-xl border border-zinc-200 bg-white px-5 py-8 text-center">
              <p className="text-sm font-semibold text-zinc-800">
                Results could not be loaded
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                The results service is temporarily unavailable. Please try again later.
              </p>
            </div>
          ) : results.length === 0 ? (
            <div className="rounded-xl border border-dashed border-zinc-300 bg-white px-5 py-8 text-center">
              <span className="flex h-10 w-10 mx-auto items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-500">
                <span aria-hidden="true" className="material-symbols-outlined">
                  score
                </span>
              </span>
              <p className="mt-3 text-sm font-semibold text-zinc-800">
                No recent results available
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                There are no finished Manchester City matches in the latest available league results.
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
              <p className="border-b border-zinc-100 px-5 py-3 text-xs text-zinc-500">
                Showing {results.length} club {results.length === 1 ? "match" : "matches"} from the latest available league results.
              </p>
              <ul className="divide-y divide-zinc-100">
                {results.map((match) => {
                  const outcome = resultForTeam(match, team.slug);
                  const outcomeLabel = outcome === "W"
                    ? "Win"
                    : outcome === "D"
                      ? "Draw"
                      : "Loss";
                  const outcomeStyle = outcome === "W"
                    ? "border-zinc-900 bg-zinc-900 text-white"
                    : outcome === "D"
                      ? "border-zinc-300 bg-zinc-100 text-zinc-700"
                      : "border-zinc-300 bg-white text-zinc-500";

                  return (
                    <li key={match.id}>
                      <Link
                        href={`/matches/${match.slug}`}
                        className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-4 py-4 transition-colors hover:bg-zinc-50 sm:gap-5 sm:px-6"
                      >
                        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
                          <TeamCrest
                            url={match.home_team.crest_url}
                            alt=""
                            className="h-7 w-7 shrink-0 object-contain"
                            fallback={
                              <span aria-hidden="true" className="h-7 w-7 shrink-0 rounded-full bg-zinc-100" />
                            }
                          />
                          <span className={`truncate text-xs sm:text-sm ${match.home_team.slug === team.slug ? "font-bold text-zinc-950" : "font-medium text-zinc-700"}`}>
                            {match.home_team.name}
                          </span>
                        </div>

                        <div className="min-w-20 text-center">
                          <p className="text-lg font-extrabold tabular-nums tracking-tight text-zinc-950">
                            {match.home_score}
                            <span className="px-1.5 text-zinc-300">:</span>
                            {match.away_score}
                          </p>
                          <p className="mt-0.5 text-[10px] tabular-nums text-zinc-400">
                            {formatDate(match.date)}
                          </p>
                        </div>

                        <div className="flex min-w-0 items-center justify-end gap-2 sm:gap-3">
                          <span className={`truncate text-right text-xs sm:text-sm ${match.away_team.slug === team.slug ? "font-bold text-zinc-950" : "font-medium text-zinc-700"}`}>
                            {match.away_team.name}
                          </span>
                          <TeamCrest
                            url={match.away_team.crest_url}
                            alt=""
                            className="h-7 w-7 shrink-0 object-contain"
                            fallback={
                              <span aria-hidden="true" className="h-7 w-7 shrink-0 rounded-full bg-zinc-100" />
                            }
                          />
                        </div>

                        <span className={`col-span-3 justify-self-center rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider sm:col-span-1 sm:col-start-2 ${outcomeStyle}`}>
                          {outcomeLabel}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
