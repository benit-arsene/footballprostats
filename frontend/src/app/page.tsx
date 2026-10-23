"use client";

import Link from "next/link";
import {
  Fragment,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";
import TeamCrest from "@/components/TeamCrest";
import {
  getLiveMatchesSummary,
  getLiveStandings,
  getLiveTopScorers,
  getMatchesByDate,
} from "@/lib/api";
import { HOMEPAGE_REFRESH_INTERVAL } from "@/lib/constants";
import { MOCK_STANDINGS, MOCK_TOP_SCORERS } from "@/lib/mock-data";
import type { LeagueSummary, LiveTopScorer, MatchStatus, MatchSummary } from "@/lib/types";

/*
 * The app runs on a 66.67% root font size, while this reference layout is
 * authored against a 16px root. These custom properties restore the reference
 * spacing/type scale inside the page without touching the rest of the site.
 */
const CANVAS_STYLE: CSSProperties & Record<`--${string}`, string> = {
  "--spacing": "4px",
  "--container-7xl": "1280px",
  "--container-2xl": "672px",
  "--text-xs": "12px",
  "--text-sm": "14px",
  "--text-base": "16px",
  "--text-lg": "18px",
  "--text-xl": "20px",
  "--text-2xl": "24px",
  "--radius-sm": "4px",
  "--radius-md": "6px",
  "--radius-lg": "8px",
  "--radius-xl": "12px",
  "--radius-2xl": "16px",
};

// ─── Identity helpers ────────────────────────────────────────────────

const TEAM_CODES: Array<[RegExp, string]> = [
  [/man(?:chester)?\s*(?:city|cty)/i, "MCI"],
  [/man(?:chester)?\s*(?:united|utd)/i, "MUN"],
  [/newcastle/i, "NEW"],
  [/nottingham|forest/i, "NFO"],
  [/tottenham|spurs/i, "TOT"],
  [/west ham/i, "WHU"],
  [/crystal palace/i, "CRY"],
  [/brighton/i, "BHA"],
  [/bournemouth/i, "BOU"],
  [/brentford/i, "BRE"],
  [/aston villa/i, "AVL"],
  [/wolverhampton|wolves/i, "WOL"],
  [/arsenal/i, "ARS"],
  [/chelsea/i, "CHE"],
  [/everton/i, "EVE"],
  [/fulham/i, "FUL"],
  [/liverpool/i, "LIV"],
  [/coventry/i, "COV"],
  [/hull city/i, "HUL"],
  [/burnley/i, "BUR"],
  [/leeds/i, "LEE"],
  [/sunderland/i, "SUN"],
  [/real madrid/i, "RMA"],
  [/espanyol/i, "ESP"],
  [/barcelona|barça/i, "FCB"],
  [/deportivo alav[eé]s|alaves/i, "ALA"],
  [/m[aá]laga/i, "MAL"],
  [/rayo vallecano/i, "RAY"],
  [/elche/i, "ELC"],
  [/real racing|racing (?:club )?(?:de )?santander/i, "RAC"],
  [/valencia/i, "VAL"],
  [/villarreal/i, "VIL"],
  [/atl[eé]tico de madrid|atletico madrid/i, "ATM"],
  [/deportivo la coru/i, "DEP"],
  [/athletic club|athletic bilbao/i, "ATH"],
  [/getafe/i, "GET"],
  [/celta/i, "CEL"],
  [/real betis|betis/i, "BET"],
  [/real sociedad/i, "RSO"],
  [/levante/i, "LEV"],
  [/sevilla/i, "SEV"],
  [/osasuna/i, "OSA"],
  [/girona/i, "GIR"],
  [/mallorca/i, "MLL"],
  [/almer[ií]a/i, "ALM"],
  [/c[aá]diz/i, "CAD"],
  [/granada/i, "GRA"],
  [/las palmas/i, "LPA"],
  [/valladolid/i, "VLL"],
  [/bayern/i, "BAY"],
  [/dortmund/i, "BVB"],
  [/juventus/i, "JUV"],
  [/napoli/i, "NAP"],
  [/ac milan/i, "ACM"],
  [/inter(?:nazionale)?/i, "INT"],
  [/paris saint|psg/i, "PSG"],
];

function teamCode(name: string): string {
  for (const [pattern, code] of TEAM_CODES) {
    if (pattern.test(name)) return code;
  }
  const cleaned = name
    .replace(/\b(fc|afc|cf|sc|club|the|de|del|la)\b/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
  const words = cleaned.split(" ").filter(Boolean);
  const code =
    words.length > 1
      ? words.map((word) => word[0]).join("")
      : (words[0] ?? "").slice(0, 3);
  return code.slice(0, 3).toUpperCase() || "—";
}

const LEAGUE_DISPLAY: Array<[RegExp, string, string]> = [
  [/premier league/i, "Premier League", "England"],
  [/primera|la liga/i, "La Liga", "Spain"],
  [/champions league/i, "Champions League", "Europe"],
  [/bundesliga/i, "Bundesliga", "Germany"],
  [/serie a/i, "Serie A", "Italy"],
  [/ligue 1/i, "Ligue 1", "France"],
];

function leagueDisplay(league: LeagueSummary): { name: string; country: string } {
  for (const [pattern, name, country] of LEAGUE_DISPLAY) {
    if (pattern.test(league.name)) return { name, country: league.country || country };
  }
  return { name: league.name, country: league.country };
}

function initials(name: string): string {
  const parts = name.replace(/\./g, " ").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "??";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function leagueBadge(league: LeagueSummary): { label: string; bg: string; fg: string } {
  const name = league.name ?? "";
  if (/premier league/i.test(name)) return { label: "PL", bg: "#3d195b", fg: "#00ff85" };
  if (/la liga|primera/i.test(name)) return { label: "LL", bg: "#ee1a35", fg: "#ffffff" };
  if (/champions league/i.test(name)) return { label: "★", bg: "#0e1e5b", fg: "#ffffff" };
  return { label: teamCode(name).slice(0, 2), bg: "#18181b", fg: "#ffffff" };
}

const TEAM_TINTS: Array<[RegExp, string]> = [
  [/arsenal/i, "bg-red-50 border-red-200"],
  [/chelsea/i, "bg-blue-50 border-blue-200"],
  [/liverpool/i, "bg-red-50 border-red-200"],
  [/man(?:chester)?\s*city/i, "bg-sky-50 border-sky-200"],
  [/real madrid/i, "bg-amber-50 border-amber-200"],
  [/barcelona/i, "bg-indigo-50 border-indigo-200"],
  [/bayern/i, "bg-red-50 border-red-200"],
  [/dortmund/i, "bg-yellow-50 border-yellow-300"],
  [/inter/i, "bg-blue-50 border-blue-200"],
  [/ac milan/i, "bg-red-50 border-red-200"],
  [/juventus/i, "bg-zinc-100 border-zinc-300"],
  [/napoli/i, "bg-sky-50 border-sky-200"],
];

function teamTint(name: string): string {
  for (const [pattern, tint] of TEAM_TINTS) {
    if (pattern.test(name)) return tint;
  }
  return "bg-zinc-50 border-zinc-200";
}

const TEAM_BADGE_TINTS: Array<[RegExp, string]> = [
  [/man(?:chester)?\s*city/i, "bg-sky-100 text-sky-700"],
  [/arsenal/i, "bg-red-100 text-red-700"],
  [/chelsea/i, "bg-blue-900 text-white"],
  [/liverpool/i, "bg-red-100 text-red-800"],
  [/brighton/i, "bg-blue-100 text-blue-700"],
  [/bournemouth/i, "bg-zinc-200 text-zinc-800"],
  [/real madrid/i, "bg-amber-100 text-amber-700"],
  [/barcelona/i, "bg-indigo-100 text-indigo-700"],
  [/bayern/i, "bg-red-100 text-red-700"],
  [/dortmund/i, "bg-yellow-100 text-yellow-800"],
  [/inter/i, "bg-blue-100 text-blue-800"],
  [/ac milan/i, "bg-red-100 text-red-700"],
  [/juventus/i, "bg-zinc-100 text-zinc-800"],
  [/napoli/i, "bg-sky-100 text-sky-700"],
];

function teamBadgeTint(name: string): string {
  for (const [pattern, tint] of TEAM_BADGE_TINTS) {
    if (pattern.test(name)) return tint;
  }
  return "bg-zinc-100 text-zinc-700";
}

const TEAM_CREST_FALLBACKS: Array<[RegExp, string]> = [
  [
    /arsenal/i,
    "https://r2.thesportsdb.com/images/media/team/badge/uyhbfe1612467038.png",
  ],
  [
    /chelsea/i,
    "https://r2.thesportsdb.com/images/media/team/badge/pbf4ul1782638263.png",
  ],
  [
    /liverpool/i,
    "https://r2.thesportsdb.com/images/media/team/badge/kfaher1737969724.png",
  ],
  [
    /man(?:chester)?\s*city/i,
    "https://r2.thesportsdb.com/images/media/team/badge/vwpvry1467462651.png",
  ],
  [
    /aston villa/i,
    "https://crests.football-data.org/58.png",
  ],
  [
    /real madrid/i,
    "https://r2.thesportsdb.com/images/media/team/badge/vwvwrw1473502969.png",
  ],
  [
    /barcelona|barça/i,
    "https://r2.thesportsdb.com/images/media/team/badge/wq9sir1639406443.png",
  ],
  [
    /bayern/i,
    "https://r2.thesportsdb.com/images/media/team/badge/01ogkh1716960412.png",
  ],
  [
    /dortmund/i,
    "https://r2.thesportsdb.com/images/media/team/badge/tqo8ge1716960353.png",
  ],
  [
    /inter/i,
    "https://r2.thesportsdb.com/images/media/team/badge/ryhu6d1617113103.png",
  ],
  [
    /ac milan/i,
    "https://r2.thesportsdb.com/images/media/team/badge/wvspur1448806617.png",
  ],
  [
    /juventus/i,
    "https://r2.thesportsdb.com/images/media/team/badge/uxf0gr1742983727.png",
  ],
  [
    /napoli/i,
    "https://r2.thesportsdb.com/images/media/team/badge/l8qyxv1742982541.png",
  ],
];

function teamCrestFallback(name: string): string | null {
  for (const [pattern, url] of TEAM_CREST_FALLBACKS) {
    if (pattern.test(name)) return url;
  }
  return null;
}

function playerAvatarTint(team: string): string {
  if (/man(?:chester)?\s*city/i.test(team)) return "bg-zinc-900";
  if (/chelsea/i.test(team)) return "bg-blue-900";
  if (/liverpool/i.test(team)) return "bg-red-900";
  if (/bournemouth/i.test(team)) return "bg-zinc-800";
  return "bg-zinc-900";
}

// ─── Formatting / normalisation helpers ──────────────────────────────

function groupByLeague(matches: MatchSummary[]) {
  const map = new Map<number, MatchSummary[]>();
  for (const match of matches) {
    const list = map.get(match.league.id) ?? [];
    list.push(match);
    map.set(match.league.id, list);
  }
  return map;
}

function sortMatches(matches: MatchSummary[]) {
  const statusOrder: Record<MatchStatus, number> = {
    live: 0,
    scheduled: 1,
    finished: 2,
    postponed: 3,
    cancelled: 4,
  };
  return [...matches].sort((a, b) => {
    if (statusOrder[a.status] !== statusOrder[b.status]) {
      return statusOrder[a.status] - statusOrder[b.status];
    }
    return a.kickoff_time.localeCompare(b.kickoff_time);
  });
}

function leagueOrder(name: string): number {
  if (/premier league/i.test(name)) return 0;
  if (/la liga|primera/i.test(name)) return 1;
  if (/champions league/i.test(name)) return 2;
  return 3;
}

function normalizeForm(value: unknown): string[] {
  const letters = Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : typeof value === "string"
      ? value.split("")
      : [];
  return letters
    .map((letter) => letter.toUpperCase())
    .filter((letter) => letter === "W" || letter === "D" || letter === "L")
    .slice(-5);
}

type StandingApiRow = {
  position?: number;
  team?: { name?: string | null; crest_url?: string | null } | null;
  played?: number;
  goal_difference?: number;
  gd?: number;
  goals_for?: number;
  gf?: number;
  goals_against?: number;
  ga?: number;
  points?: number;
  form?: string | string[] | null;
};

type StandingView = {
  position: number;
  name: string;
  code: string;
  crestUrl: string | null;
  played: number;
  gd: number;
  points: number;
  form: string[];
};

function buildStandings(raw: StandingApiRow[]): StandingView[] {
  return raw.slice(0, 5).map((row, index) => {
    const name = row.team?.name ?? "Unknown";
    const crestUrl = row.team?.crest_url?.trim() || teamCrestFallback(name);
    const played = Number(row.played ?? 0);
    const gd =
      typeof row.goal_difference === "number"
        ? row.goal_difference
        : typeof row.gd === "number"
          ? row.gd
          : Number(row.goals_for ?? row.gf ?? 0) - Number(row.goals_against ?? row.ga ?? 0);
    return {
      position: Number(row.position ?? index + 1),
      name,
      code: teamCode(name),
      crestUrl,
      played,
      gd,
      points: Number(row.points ?? 0),
      form: normalizeForm(row.form),
    };
  });
}

type ScorerView = {
  key: string;
  name: string;
  playerInitials: string;
  team: string;
  code: string;
  crestUrl: string | null;
  goals: number;
  assists: number;
  npg: number;
  apps: number | null;
  position: string | null;
};

function buildScorers(raw: LiveTopScorer[]): ScorerView[] {
  return raw.slice(0, 6).map((scorer, index) => {
    const name = scorer.player?.name?.trim() || "Unknown player";
    const team = scorer.team?.name?.trim() || "Unknown club";
    const goals = scorer.goals ?? 0;
    const penalties = scorer.penalties ?? 0;
    return {
      key: `${scorer.player?.id ?? name}-${index}`,
      name,
      playerInitials: initials(name),
      team,
      code: teamCode(team),
      crestUrl: scorer.team?.crest_url?.trim() || teamCrestFallback(team),
      goals,
      assists: scorer.assists ?? 0,
      npg: Math.max(0, goals - penalties),
      apps: typeof scorer.played_matches === "number" ? scorer.played_matches : null,
      position: scorer.player?.position ?? null,
    };
  });
}

function kickoffLabel(time: string): string {
  return time.slice(0, 5);
}

function halfLabel(minute: number | null): string {
  if (minute === null) return "Live";
  if (minute > 45) return "2nd Half";
  return "1st Half";
}

// ─── Page pieces ─────────────────────────────────────────────────────

function LiveTicker({ matches, liveCount }: { matches: MatchSummary[]; liveCount: number }) {
  const statusOrder: Record<MatchStatus, number> = {
    live: 0,
    finished: 1,
    scheduled: 2,
    postponed: 3,
    cancelled: 4,
  };
  const ticker = [...matches]
    .sort((a, b) => statusOrder[a.status] - statusOrder[b.status])
    .slice(0, 4);

  return (
    <section className="bg-zinc-950 text-white border-b border-zinc-800 py-1.5 px-4 sm:px-6 lg:px-8 text-xs overflow-hidden">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-2 shrink-0 pr-4 border-r border-zinc-800">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
            Live Wire
          </span>
        </div>

        <div className="flex items-center space-x-6 overflow-x-auto scrollbar-none py-0.5 px-4 font-mono text-xs">
          {ticker.map((match, index) => {
            const isLive = match.status === "live";
            const isFinished = match.status === "finished";
            return (
              <Fragment key={match.id}>
                <Link
                  href={`/matches/${match.slug}`}
                  className="inline-flex items-center space-x-2 text-zinc-300 hover:text-white transition-colors shrink-0 group"
                >
                  {isLive ? (
                    <span className="px-1.5 py-0.5 text-[9px] font-bold rounded-[4px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 tracking-tight group-hover:bg-emerald-500/30 tabular-nums">
                      {match.minute ?? 0}&apos;
                    </span>
                  ) : isFinished ? (
                    <span className="px-1.5 py-0.5 text-[9px] font-semibold text-zinc-400 bg-zinc-900 border border-zinc-800 rounded-[4px]">
                      FT
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 text-[9px] font-medium text-zinc-400 bg-zinc-900 border border-zinc-800 rounded-[4px] tabular-nums">
                      {kickoffLabel(match.kickoff_time)}
                    </span>
                  )}
                  <span className="font-sans font-medium text-xs text-white">
                    {match.home_team.name}
                  </span>
                  {isLive || isFinished ? (
                    <>
                      <span className="font-bold text-white px-1 tracking-widest tabular-nums">
                        {match.home_score} - {match.away_score}
                      </span>
                      <span className="font-sans text-xs text-zinc-300">
                        {match.away_team.name}
                      </span>
                    </>
                  ) : (
                    <span className="font-sans text-xs text-zinc-300">
                      vs {match.away_team.name}
                    </span>
                  )}
                </Link>
                {index < ticker.length - 1 ? (
                  <span className="text-zinc-700 select-none">•</span>
                ) : null}
              </Fragment>
            );
          })}
        </div>

        <div className="hidden lg:flex items-center space-x-2 shrink-0 pl-4 border-l border-zinc-800 text-[11px] text-zinc-400">
          <span className="font-mono text-emerald-400 font-semibold">{liveCount}</span> active
          matches
        </div>
      </div>
    </section>
  );
}

function SiteHeader({ searchRef }: { searchRef: RefObject<HTMLInputElement | null> }) {
  const nav = [
    { label: "Live", href: "/", active: true },
    { label: "Fixtures", href: "/", active: false },
    { label: "Results", href: "/", active: false },
    { label: "Standings", href: "/standings", active: false },
    { label: "Players", href: "/players/epl/topscorers/currentseason", active: false },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-zinc-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center space-x-6">
            <Link href="/" className="flex items-center space-x-2.5 group">
              <div className="w-7 h-7 bg-black text-white flex items-center justify-center font-extrabold text-[11px] tracking-tighter rounded-[4px] transition-transform group-hover:scale-95 shadow-sm">
                FP
              </div>
              <span className="font-bold text-sm tracking-tight text-black flex items-center gap-1.5">
                FOOTBALL <span className="text-zinc-500 font-normal">PRO STATS</span>
              </span>
            </Link>

            <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-zinc-200">
              {nav.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  className={
                    item.active
                      ? "px-3 py-1.5 text-xs font-semibold text-black bg-zinc-100 rounded-md"
                      : "px-3 py-1.5 text-xs font-medium text-zinc-600 hover:text-black hover:bg-zinc-50 rounded-md transition-colors"
                  }
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>

          <div className="flex items-center space-x-3">
            <div className="relative w-52 sm:w-64">
              <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none">
                <svg
                  className="h-3.5 w-3.5 text-zinc-400"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" x2="16.65" y1="21" y2="16.65" />
                </svg>
              </div>
              <input
                ref={searchRef}
                type="text"
                aria-label="Search team, league, player"
                placeholder="Search team, league, player..."
                className="w-full pl-8 pr-12 py-1.5 text-xs bg-zinc-50 hover:bg-zinc-100 focus:bg-white text-zinc-900 placeholder:text-zinc-400 rounded-md border border-zinc-200 focus:border-black focus:outline-none focus:ring-1 focus:ring-black transition-all"
              />
              <div className="absolute inset-y-0 right-0 pr-2 flex items-center pointer-events-none">
                <kbd className="px-1.5 py-0.5 text-[9px] font-mono text-zinc-500 bg-zinc-200/80 rounded-[4px] border border-zinc-300">
                  ⌘K
                </kbd>
              </div>
            </div>
            <button
              type="button"
              aria-label="Account"
              className="w-8 h-8 rounded-full border border-zinc-300 flex items-center justify-center bg-zinc-100 hover:bg-zinc-200 text-xs font-bold text-zinc-800 transition-colors shadow-xs"
            >
              JD
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

function MatchRow({ match }: { match: MatchSummary }) {
  const isLive = match.status === "live";
  const isFinished = match.status === "finished";
  const isScheduled = match.status === "scheduled";

  return (
    <Link
      href={`/matches/${match.slug}`}
      className="block p-4 hover:bg-zinc-50/80 transition-colors group"
    >
      <div className="flex items-center justify-between">
        <div className="w-24 shrink-0 flex flex-col items-start gap-1">
          {isLive ? (
            <>
              <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-300 font-mono text-[10px] font-bold tracking-tight shadow-xs">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600" />
                </span>
                <span className="tabular-nums">{match.minute ?? 0}&apos;</span>
              </div>
              <span className="text-[9px] font-medium text-emerald-700 uppercase tracking-widest pl-1 font-mono">
                {halfLabel(match.minute)}
              </span>
            </>
          ) : (
            <>
              <span className="inline-block px-2.5 py-1 rounded-md bg-zinc-100 text-zinc-700 font-mono text-[10px] font-bold border border-zinc-200 tracking-tight">
                {isFinished ? "FT" : isScheduled ? "UPCOMING" : match.status.toUpperCase()}
              </span>
              {isFinished ? (
                <span className="text-[9px] font-mono text-zinc-400 pl-0.5">Full Time</span>
              ) : null}
            </>
          )}
        </div>

        <div className="flex-1 flex items-center justify-center max-w-2xl px-2">
          <div className="flex-1 flex items-center justify-end space-x-3 text-right pr-4 min-w-0">
            <div className="min-w-0">
              <div className="text-sm font-bold text-black tracking-tight group-hover:underline truncate">
                {match.home_team.name}
              </div>
              <div className="text-[10px] font-mono text-zinc-400">
                {teamCode(match.home_team.name)}
              </div>
            </div>
            <div
              className={`w-8 h-8 rounded-full border flex items-center justify-center shrink-0 shadow-xs ${teamTint(match.home_team.name)}`}
            >
              <TeamCrest
                url={match.home_team.crest_url || teamCrestFallback(match.home_team.name)}
                alt={match.home_team.name}
                className="h-5 w-5 object-contain"
                fallback={
                  <span className="text-[9px] font-extrabold text-zinc-600">
                    {initials(match.home_team.name)}
                  </span>
                }
              />
            </div>
          </div>

          <div className="shrink-0 flex flex-col items-center justify-center w-28">
            {isScheduled ? (
              <div className="flex items-center justify-center px-3.5 py-1.5 rounded-lg bg-zinc-100 text-black border border-zinc-300 font-mono text-xs font-bold tracking-tight shadow-xs tabular-nums">
                {kickoffLabel(match.kickoff_time)}
              </div>
            ) : (
              <div
                className={`flex items-center justify-center px-3.5 py-1.5 rounded-lg font-mono text-sm font-black tracking-widest tabular-nums ${
                  isLive
                    ? "bg-zinc-950 text-white shadow-sm"
                    : "bg-zinc-100 text-black border border-zinc-300 shadow-xs"
                }`}
              >
                {match.home_score} - {match.away_score}
              </div>
            )}
          </div>

          <div className="flex-1 flex items-center justify-start space-x-3 text-left pl-4 min-w-0">
            <div
              className={`w-8 h-8 rounded-full border flex items-center justify-center shrink-0 shadow-xs ${teamTint(match.away_team.name)}`}
            >
              <TeamCrest
                url={match.away_team.crest_url || teamCrestFallback(match.away_team.name)}
                alt={match.away_team.name}
                className="h-5 w-5 object-contain"
                fallback={
                  <span className="text-[9px] font-extrabold text-zinc-600">
                    {initials(match.away_team.name)}
                  </span>
                }
              />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-medium text-zinc-800 tracking-tight group-hover:underline truncate">
                {match.away_team.name}
              </div>
              <div className="text-[10px] font-mono text-zinc-400">
                {teamCode(match.away_team.name)}
              </div>
            </div>
          </div>
        </div>

        <div className="w-8 shrink-0 text-right">
          <span className="text-zinc-300 group-hover:text-black transition-colors inline-block text-sm">
            →
          </span>
        </div>
      </div>

    </Link>
  );
}

function LeagueCard({ matches }: { matches: MatchSummary[] }) {
  const league = matches[0]?.league;
  if (!league) return null;
  const badge = leagueBadge(league);
  const display = leagueDisplay(league);

  return (
    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-zinc-50/80 border-b border-zinc-200 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div
            className="w-5 h-5 rounded-[4px] text-[9px] font-extrabold flex items-center justify-center shadow-xs"
            style={{ backgroundColor: badge.bg, color: badge.fg }}
          >
            {badge.label}
          </div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xs font-bold tracking-tight text-black uppercase">
              {display.name}
            </h2>
            {display.country ? (
              <>
                <span className="text-zinc-400 text-xs">•</span>
                <span className="text-zinc-500 text-xs">{display.country}</span>
              </>
            ) : null}
          </div>
        </div>
        <Link
          href={`/leagues/${league.slug}`}
          className="text-[11px] font-medium text-zinc-500 hover:text-black flex items-center space-x-1 transition-colors"
        >
          <span>View all</span>
          <svg
            className="w-3 h-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
          </svg>
        </Link>
      </div>
      <div className="divide-y divide-zinc-200">
        {sortMatches(matches).map((match) => (
          <MatchRow key={match.id} match={match} />
        ))}
      </div>
    </div>
  );
}

function StandingsCard({
  leagueName,
  season,
  matchday,
  rows,
}: {
  leagueName: string;
  season: string;
  matchday: number | null;
  rows: StandingView[];
}) {
  return (
    <section className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-zinc-50/80 border-b border-zinc-200 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-tight text-black">{leagueName}</h3>
          <p className="text-[11px] text-zinc-500">Standings {season}</p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="flex items-center space-x-1 text-[10px] text-zinc-400">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            <span className="hidden sm:inline">UCL</span>
          </span>
          {matchday !== null ? (
            <span className="px-1.5 py-0.5 text-[9px] font-bold rounded-[4px] bg-zinc-200 text-zinc-700">
              MD {matchday}
            </span>
          ) : null}
        </div>
      </div>

      <div className="p-1 overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead>
            <tr className="border-b border-zinc-100 text-[10px] font-bold uppercase text-zinc-400 tracking-wider">
              <th className="py-2 pl-3 pr-1 w-7" scope="col">
                #
              </th>
              <th className="py-2 px-1" scope="col">
                Team
              </th>
              <th className="py-2 px-1 text-center w-6" scope="col">
                P
              </th>
              <th className="py-2 px-1 text-center w-8" scope="col">
                GD
              </th>
              <th className="py-2 px-1 text-center w-20" scope="col">
                Form
              </th>
              <th className="py-2 pr-3 pl-1 text-right w-8 font-bold text-zinc-900" scope="col">
                Pts
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 font-mono text-[11px]">
            {rows.map((row) => (
              <tr key={`${row.position}-${row.name}`} className="hover:bg-zinc-50 transition-colors">
                <td className="py-2.5 pl-3 pr-1 font-bold text-zinc-900 relative">
                  <div
                    className={`absolute left-0 top-1 bottom-1 w-0.5 rounded-r ${
                      row.position <= 4
                        ? "bg-blue-500"
                        : row.position === 5
                          ? "bg-amber-500"
                          : "bg-zinc-300"
                    }`}
                  />
                  <div className="flex items-center space-x-1">
                    <span
                      className={`inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-sans ${
                        row.position === 1
                          ? "bg-black text-white"
                          : "bg-zinc-100 text-zinc-800 border border-zinc-200"
                      }`}
                    >
                      {row.position}
                    </span>
                  </div>
                </td>
                <td className="py-2.5 px-1 font-sans font-medium text-zinc-900">
                  <div className="flex items-center space-x-1.5 min-w-0">
                    <span className="w-4 h-4 rounded-full bg-white border border-zinc-200 flex items-center justify-center shrink-0 p-[1px] overflow-hidden">
                      <TeamCrest
                        url={row.crestUrl}
                        alt={`${row.name} crest`}
                        className="h-full w-full object-contain"
                        fallback={
                          <span
                            className={`w-full h-full rounded-full flex items-center justify-center text-[7px] font-black ${teamBadgeTint(row.name)}`}
                          >
                            {row.code.slice(0, 2)}
                          </span>
                        }
                      />
                    </span>
                    <span className="truncate">{row.name}</span>
                  </div>
                </td>
                <td className="py-2.5 px-1 text-center text-zinc-600 tabular-nums">{row.played}</td>
                <td
                  className={`py-2.5 px-1 text-center font-semibold tabular-nums ${
                    row.gd > 0 ? "text-emerald-600" : row.gd < 0 ? "text-rose-500" : "text-zinc-500"
                  }`}
                >
                  {row.gd > 0 ? `+${row.gd}` : row.gd}
                </td>
                <td className="py-2.5 px-1 text-center">
                  <div className="inline-flex items-center space-x-0.5">
                    {row.form.map((result, index) => (
                      <span
                        key={`${result}-${index}`}
                        className={`w-3.5 h-3.5 rounded-full text-white text-[8px] font-sans font-bold flex items-center justify-center ${
                          result === "W"
                            ? "bg-emerald-600"
                            : result === "D"
                              ? "bg-amber-500"
                              : "bg-rose-600"
                        }`}
                      >
                        {result}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-2.5 pr-3 pl-1 text-right font-bold text-black tabular-nums">
                  {row.points}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-2 border-t border-zinc-100 bg-zinc-50/50">
        <Link
          href="/standings"
          className="w-full py-1.5 px-3 rounded-[4px] text-center block text-xs font-semibold text-zinc-800 hover:text-black hover:bg-zinc-100 border border-zinc-200 transition-colors"
        >
          Full Standings &amp; Form Table →
        </Link>
      </div>
    </section>
  );
}

function TopScorersCard({
  leagueName,
  season,
  rows,
}: {
  leagueName: string;
  season: string;
  rows: ScorerView[];
}) {
  return (
    <section className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-zinc-50/80 border-b border-zinc-200 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-tight text-black">Top Scorers</h3>
          <p className="text-[11px] text-zinc-500">
            {leagueName} {season}
          </p>
        </div>
        <div className="flex items-center space-x-3 text-[10px] font-mono text-zinc-400">
          <span>AST</span>
          <span>NPG</span>
          <span className="text-black font-bold">G</span>
        </div>
      </div>

      <div className="divide-y divide-zinc-100">
        {rows.map((row, index) => (
          <div
            key={row.key}
            className="p-3 hover:bg-zinc-50 transition-colors flex items-center justify-between"
          >
            <div className="flex items-center space-x-2.5 min-w-0">
              <span
                className={`font-mono text-xs w-3 text-center ${
                  index === 0 ? "font-black text-black" : "font-semibold text-zinc-400"
                }`}
              >
                {index + 1}
              </span>
              <div className="relative">
                <div
                  className={`w-8 h-8 rounded-full text-white font-bold text-[10px] flex items-center justify-center shadow-xs ${playerAvatarTint(row.team)}`}
                >
                  {row.playerInitials}
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-white border border-white flex items-center justify-center overflow-hidden p-[1px]">
                  <TeamCrest
                    url={row.crestUrl}
                    alt={`${row.team} crest`}
                    className="h-full w-full object-contain"
                    fallback={
                      <span
                        className={`w-full h-full rounded-full flex items-center justify-center text-[6px] font-bold ${teamBadgeTint(row.team)}`}
                      >
                        {row.code}
                      </span>
                    }
                  />
                </span>
              </div>
              <div className="min-w-0">
                <p
                  className={`text-xs truncate ${
                    index === 0 ? "font-bold text-black" : "font-semibold text-zinc-800"
                  }`}
                >
                  {row.name}
                </p>
                <p className="text-[10px] text-zinc-400 font-mono truncate">
                  {row.apps !== null ? `${row.apps} apps` : (row.position ?? row.team)}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3 text-right font-mono text-xs">
              <span className="text-zinc-500 w-6 text-center">{row.assists}</span>
              <span className="text-zinc-500 w-6 text-center">{row.npg}</span>
              <span
                className={`inline-flex items-center justify-center w-7 py-0.5 rounded-[4px] tabular-nums ${
                  index === 0
                    ? "bg-black text-white font-extrabold"
                    : "bg-zinc-100 text-zinc-900 border border-zinc-200 font-bold"
                }`}
              >
                {row.goals}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="p-2 border-t border-zinc-100 bg-zinc-50/50">
        <Link
          href="/players/epl/topscorers/currentseason"
          className="w-full py-1.5 px-3 rounded-[4px] text-center block text-xs font-semibold text-zinc-800 hover:text-black hover:bg-zinc-100 border border-zinc-200 transition-colors"
        >
          Full Golden Boot Race →
        </Link>
      </div>
    </section>
  );
}

// ─── Page ────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState(3);
  const [liveMatches, setLiveMatches] = useState<MatchSummary[]>([]);
  const [dateMatches, setDateMatches] = useState<{
    date: string;
    matches: MatchSummary[];
    error: boolean;
  }>({ date: "", matches: [], error: false });
  const [standingsRaw, setStandingsRaw] = useState<StandingApiRow[]>([]);
  const [standingsSeason, setStandingsSeason] = useState("");
  const [liveScorers, setLiveScorers] = useState<LiveTopScorer[]>([]);
  const [scorersSeason, setScorersSeason] = useState("");
  const [competitionName, setCompetitionName] = useState("Premier League");
  const [currentMatchday, setCurrentMatchday] = useState<number | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchLive = async () => {
      try {
        const apiMatches = await getLiveMatchesSummary();
        if (cancelled || apiMatches.length === 0) return;
        setLiveMatches([...apiMatches]);
        if (typeof window !== "undefined") {
          sessionStorage.setItem("liveMatches", JSON.stringify(apiMatches));
        }
      } catch {
        if (typeof window === "undefined" || cancelled) return;
        const cached = sessionStorage.getItem("liveMatches");
        if (cached) setLiveMatches(JSON.parse(cached));
      }
    };

    fetchLive();
    const interval = setInterval(fetchLive, HOMEPAGE_REFRESH_INTERVAL);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadStandings = async () => {
      try {
        const data = await getLiveStandings();
        if (cancelled) return;
        setStandingsRaw(data.rows ?? []);
        setStandingsSeason(data.season ?? "");
      } catch {
        // Mock standings remain the fallback.
      }
    };

    const loadScorers = async () => {
      try {
        const data = await getLiveTopScorers();
        if (cancelled) return;
        setLiveScorers(data.scorers ?? []);
        setScorersSeason(data.season ?? "");
        setCompetitionName(data.competition_name ?? "Premier League");
        setCurrentMatchday(data.current_matchday ?? null);
      } catch {
        // Mock top scorers remain the fallback.
      }
    };

    loadStandings();
    loadScorers();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const today = new Date();
  const selectedDay = useMemo(() => {
    const day = new Date(today);
    day.setDate(day.getDate() + activeTab - 3);
    return day;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const isToday = selectedDay.toDateString() === today.toDateString();
  const headingText = isToday
    ? "Today's Matches"
    : selectedDay.toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
      });
  const selectedDate = `${selectedDay.getFullYear()}-${String(selectedDay.getMonth() + 1).padStart(2, "0")}-${String(selectedDay.getDate()).padStart(2, "0")}`;

  // Real fixtures and results for the selected matchday, straight from the
  // provider-backed /matches/date endpoint (live + scheduled + finished).
  useEffect(() => {
    let cancelled = false;

    const loadDateMatches = async () => {
      try {
        const list = await getMatchesByDate(selectedDate);
        if (cancelled) return;
        setDateMatches({ date: selectedDate, matches: list, error: false });
      } catch {
        if (cancelled) return;
        setDateMatches({ date: selectedDate, matches: [], error: true });
      }
    };

    loadDateMatches();
    return () => {
      cancelled = true;
    };
  }, [selectedDate]);

  const matchesPending = dateMatches.date !== selectedDate;

  // Live scores refresh faster than the date snapshot, so in-progress games
  // are overlaid on today's fixtures when both feeds carry the same match.
  const matches = useMemo(() => {
    if (matchesPending) return [];
    if (!isToday) return dateMatches.matches;

    const merged = new Map<number, MatchSummary>();
    for (const match of dateMatches.matches) merged.set(match.id, match);
    for (const match of liveMatches) {
      if (match.status === "live") merged.set(match.id, match);
    }
    return Array.from(merged.values());
  }, [dateMatches, liveMatches, isToday, matchesPending]);

  const liveCount = matches.filter((match) => match.status === "live").length;
  const finishedCount = matches.filter((match) => match.status === "finished").length;
  const tickerMatches = matches.length > 0 ? matches : liveMatches;
  const tickerLiveCount = tickerMatches.filter((match) => match.status === "live").length;

  const sections = useMemo(() => {
    const grouped = groupByLeague(matches);
    return Array.from(grouped.entries()).sort(
      (a, b) => leagueOrder(a[1][0]?.league.name ?? "") - leagueOrder(b[1][0]?.league.name ?? ""),
    );
  }, [matches]);

  const standings = useMemo(
    () => buildStandings(standingsRaw.length > 0 ? standingsRaw : MOCK_STANDINGS),
    [standingsRaw],
  );

  const standingsMatchday = useMemo(() => {
    if (currentMatchday !== null) return currentMatchday;
    if (standingsRaw.length === 0) return null;
    return standingsRaw.reduce((max, row) => Math.max(max, Number(row.played ?? 0)), 0) || null;
  }, [currentMatchday, standingsRaw]);

  const scorers = useMemo(
    () =>
      buildScorers(
        liveScorers.length > 0
          ? liveScorers
          : (MOCK_TOP_SCORERS as unknown as LiveTopScorer[]),
      ),
    [liveScorers],
  );

  const leagueName = competitionName || "Premier League";
  const seasonLabel = standingsSeason || "Current Season";
  const scorerSeasonLabel = scorersSeason || standingsSeason;

  const dateTabs = Array.from({ length: 7 }, (_, index) => {
    const day = new Date(today);
    day.setDate(day.getDate() + index - 3);
    return day;
  });

  return (
    <div
      className="min-h-screen flex flex-col bg-[#f9f9fa] font-sans text-[#09090b] selection:bg-black selection:text-white"
      style={CANVAS_STYLE}
    >
      <SiteHeader searchRef={searchRef} />
      <LiveTicker matches={tickerMatches} liveCount={tickerLiveCount} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-6 border-b border-zinc-200 gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold tracking-tight text-black">{headingText}</h1>
              {standingsMatchday !== null ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-[4px] text-[10px] font-semibold uppercase tracking-wider bg-black text-white">
                  Matchday {standingsMatchday}
                </span>
              ) : null}
            </div>
            <div className="flex items-center space-x-3 text-xs text-zinc-500 font-medium">
              <span className="flex items-center space-x-1.5 text-emerald-600 font-semibold">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                <span>{liveCount} Live</span>
              </span>
              <span className="text-zinc-300">•</span>
              <span>{finishedCount} Finished</span>
              <span className="text-zinc-300">•</span>
              <span>{matches.length} Total Matches</span>
            </div>
          </div>

          <div className="flex items-center space-x-1 bg-zinc-100 p-1 rounded-lg border border-zinc-200 self-start lg:self-auto overflow-x-auto max-w-full scrollbar-none">
            {dateTabs.map((day, index) => {
              const dayIsToday = day.toDateString() === today.toDateString();
              const weekday = day.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase();
              const dateLabel = day.toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
              });
              return (
                <button
                  key={dateLabel}
                  type="button"
                  onClick={() => setActiveTab(index)}
                  className={`px-3 py-1.5 text-center rounded-md transition text-xs whitespace-nowrap ${
                    activeTab === index
                      ? "bg-black text-white shadow-sm"
                      : "text-zinc-600 hover:text-black hover:bg-zinc-200/60"
                  }`}
                >
                  <span
                    className={`block text-[10px] tracking-wider uppercase ${
                      activeTab === index
                        ? "text-zinc-400 font-bold"
                        : "text-zinc-400 font-medium"
                    }`}
                  >
                    {dayIsToday ? "TODAY" : weekday}
                  </span>
                  <span className={`text-xs ${activeTab === index ? "font-bold" : "font-semibold"}`}>
                    {dateLabel}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center space-x-2 py-4 overflow-x-auto scrollbar-none text-xs">
          <Link
            href="/"
            className="px-3 py-1.5 rounded-full bg-black text-white font-medium flex items-center space-x-1.5 shrink-0 shadow-sm"
          >
            <span>All Matches</span>
          </Link>
          <Link
            href="/leagues/premier-league-1"
            className="px-3 py-1.5 rounded-full bg-white text-zinc-700 hover:text-black hover:bg-zinc-100 border border-zinc-200 font-medium flex items-center space-x-2 shrink-0 transition"
          >
            <span
              className="w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center"
              style={{ backgroundColor: "#3d195b", color: "#00ff85" }}
            >
              PL
            </span>
            <span>Premier League</span>
          </Link>
          <Link
            href="/leagues/la-liga-2"
            className="px-3 py-1.5 rounded-full bg-white text-zinc-700 hover:text-black hover:bg-zinc-100 border border-zinc-200 font-medium flex items-center space-x-2 shrink-0 transition"
          >
            <span
              className="w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center"
              style={{ backgroundColor: "#ee1a35", color: "#ffffff" }}
            >
              LL
            </span>
            <span>La Liga</span>
          </Link>
          <Link
            href="/leagues/champions-league-3"
            className="px-3 py-1.5 rounded-full bg-white text-zinc-700 hover:text-black hover:bg-zinc-100 border border-zinc-200 font-medium flex items-center space-x-2 shrink-0 transition"
          >
            <span
              className="w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center"
              style={{ backgroundColor: "#0e1e5b", color: "#ffffff" }}
            >
              ★
            </span>
            <span>Champions League</span>
          </Link>
          <Link
            href="/players/epl/topscorers/currentseason"
            className="px-3 py-1.5 rounded-full bg-white text-zinc-700 hover:text-black hover:bg-zinc-100 border border-zinc-200 font-medium flex items-center space-x-2 shrink-0 transition"
          >
            <span className="w-4 h-4 rounded-full bg-zinc-200 text-zinc-800 text-[9px] font-bold flex items-center justify-center">
              TS
            </span>
            <span>Top Scorers</span>
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-2">
          <section className="lg:col-span-8 space-y-6">
            {sections.length === 0 ? (
              <div className="bg-white rounded-xl border border-zinc-200 shadow-sm px-6 py-12 text-center">
                <p className="text-sm font-bold text-black">
                  {matchesPending
                    ? "Loading matches…"
                    : dateMatches.error
                      ? "Unable to load matches"
                      : "No matches on this date"}
                </p>
                <p className="text-xs text-zinc-500 mt-1">
                  {matchesPending
                    ? "Fetching the latest fixtures and results."
                    : dateMatches.error
                      ? "The match feed could not be reached. Please try again."
                      : "Use the date selector above to browse another matchday."}
                </p>
              </div>
            ) : (
              sections.map(([leagueId, leagueMatches]) => (
                <LeagueCard key={leagueId} matches={leagueMatches} />
              ))
            )}
          </section>

          <aside className="lg:col-span-4 space-y-6">
            <StandingsCard
              leagueName={leagueName}
              season={seasonLabel}
              matchday={standingsMatchday}
              rows={standings}
            />
            <TopScorersCard
              leagueName={leagueName}
              season={scorerSeasonLabel || "Current Season"}
              rows={scorers}
            />
          </aside>
        </div>
      </main>

      <footer className="mt-12 bg-white border-t border-zinc-200 text-xs text-zinc-500 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="w-5 h-5 bg-black text-white flex items-center justify-center text-[9px] font-black rounded-[4px] shadow-xs">
              FP
            </span>
            <span className="font-semibold text-zinc-800">Football Pro Stats</span>
            <span className="text-zinc-400">© 2026.&nbsp;</span>
          </div>
          <div className="flex items-center space-x-4 text-xs font-medium">
            <a className="hover:text-black transition-colors" href="#">
              Privacy Policy
            </a>
            <span className="text-zinc-300">•</span>
            <a className="hover:text-black transition-colors" href="#">
              Terms of Service
            </a>
            <span className="text-zinc-300">•</span>
            <a className="hover:text-black transition-colors" href="#">
              API Docs
            </a>
            <span className="text-zinc-300">•</span>
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-[4px] bg-zinc-100 border border-zinc-200 text-zinc-600">
              v3.4.1
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
