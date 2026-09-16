"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import type { MatchSummary, MatchStatus, StandingRow } from "@/lib/types";
import { getLiveMatchesSummary } from "@/lib/api";
import { HOME_LEAGUE_IDS, HOMEPAGE_REFRESH_INTERVAL } from "@/lib/constants";
import { MOCK_STANDINGS, MOCK_MATCHES, MOCK_TOP_SCORERS } from "@/lib/mock-data";
import { LoadingSpinner } from "@/components/LoadingSpinner";

// ─── Flag helper (league headers only) ────────────────────────

const LEAGUE_COUNTRY: Record<string, string> = {
  England: "gb", Spain: "es", Europe: "eu",
  Germany: "de", Italy: "it", France: "fr",
};

function leagueFlag(country: string) {
  const code = LEAGUE_COUNTRY[country];
  return code ? `https://flagcdn.com/w40/${code}.png` : null;
}

// ─── Utility ──────────────────────────────────────────────────

function groupByLeague(matches: MatchSummary[]) {
  const map = new Map<number, MatchSummary[]>();
  for (const m of matches) {
    const list = map.get(m.league.id) ?? [];
    list.push(m);
    map.set(m.league.id, list);
  }
  return map;
}

function sortMatches(matches: MatchSummary[]) {
  const statusOrder: Record<MatchStatus, number> = { live: 0, scheduled: 1, finished: 2, postponed: 3, cancelled: 4 };
  return [...matches].sort((a, b) => {
    if (statusOrder[a.status] !== statusOrder[b.status]) return statusOrder[a.status] - statusOrder[b.status];
    return a.kickoff_time.localeCompare(b.kickoff_time);
  });
}

function formatKickoff(time: string) {
  const [h, m] = time.split(":");
  const hour = parseInt(h);
  const ampm = hour >= 12 ? "PM" : "AM";
  const h12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${h12}:${m} ${ampm}`;
}

function formatKickoff24(time: string) {
  return time; // already "20:45" format
}

// ─── Components ───────────────────────────────────────────────────────

function LiveTicker({ matches }: { matches: MatchSummary[] }) {
  const live = matches.filter((m) => m.status === "live");
  if (live.length === 0) return null;

  return (
    <div className="border-b border-zinc-200 bg-zinc-50 px-6 py-1.5">
      <div className="mx-auto flex max-w-7xl items-center gap-3">
        <span className="flex items-center gap-1.5 pr-2 font-bold uppercase tracking-wide text-red-600 border-r border-zinc-300">
          <span className="h-2 w-2 animate-pulse rounded-full bg-red-600" />
          <span className="text-[11px]">LIVE</span>
        </span>
        <div className="flex items-center gap-2 overflow-x-auto">
          {live.map((m) => (
            <a
              key={m.id}
              href={`/matches/${m.slug}`}
              className="flex items-center gap-2 whitespace-nowrap rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs hover:border-zinc-400 transition-colors"
            >
              <span className="font-bold text-red-600 tabular-nums">{m.minute}&apos;</span>
              <span className="font-semibold text-zinc-800">{m.home_team.name} {m.home_score} - {m.away_score} {m.away_team.name}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200 bg-white/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <a href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-black text-white text-xs font-bold">
            FP
          </div>
          <span className="text-lg font-bold tracking-tight">Football Pro Stats</span>
        </a>
        <nav className="hidden items-center gap-1 md:flex">
          {["Live", "Fixtures", "Results", "Standings", "Players"].map((item) => (
            <a
              key={item}
              href="#"
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 hover:text-black"
            >
              {item}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5">
            <svg className="h-4 w-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span className="text-sm text-zinc-400">Search...</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function MatchCard({ match }: { match: MatchSummary }) {
  const isLive = match.status === "live";
  const isFinished = match.status === "finished";
  const isScheduled = match.status === "scheduled";

  return (
    <a
      href={`/matches/${match.slug}`}
      className={`group grid grid-cols-[40px_1fr_70px_1fr_32px] items-center rounded-lg border bg-white px-3 py-2.5 transition-all hover:shadow-sm ${
        isLive
          ? "border-l-4 border-l-red-500 border-t-zinc-200 border-r-zinc-200 border-b-zinc-200"
          : "border-zinc-200 hover:border-zinc-300"
      }`}
    >
      {/* Status */}
      <div className="pr-3">
        {isLive && (
          <span className="inline-flex items-center gap-0.5 rounded-full bg-red-500 px-1.5 py-px">
            <span className="text-[9px] font-bold text-white">LIVE</span>
            <span className="text-[9px] font-bold tabular-nums text-white">{match.minute}&apos;</span>
          </span>
        )}
        {isFinished && (
          <span className="inline-flex rounded-full bg-zinc-200 px-1.5 py-px text-[9px] font-bold text-zinc-500">FT</span>
        )}
        {isScheduled && (
          <span className="inline-flex rounded-full bg-zinc-100 px-1.5 py-px text-[9px] font-bold uppercase tracking-wider text-zinc-400">
            Upcoming
          </span>
        )}
      </div>

      {/* Home Team (right-aligned) */}
      <div className="flex items-center justify-end gap-2 overflow-hidden">
        <span className={`truncate text-xs font-semibold ${isFinished && match.home_score > match.away_score ? "text-black" : "text-zinc-600"}`}>
          {match.home_team.name}
        </span>
        {match.home_team.crest_url && (
          <img src={match.home_team.crest_url} alt="" className="h-5 w-5 flex-shrink-0 object-contain" />
        )}
      </div>

      {/* Score */}
      <div className="flex items-center justify-center">
        {isScheduled ? (
          <span className="rounded bg-zinc-100 px-2.5 py-1 text-xs font-bold tabular-nums text-zinc-500">
            {formatKickoff24(match.kickoff_time)}
          </span>
        ) : (
          <span className={`rounded px-2.5 py-1 text-sm font-black tabular-nums ${
            isLive ? "bg-red-50 text-red-600" : "bg-zinc-100 text-black"
          }`}>
            {match.home_score} - {match.away_score}
          </span>
        )}
      </div>

      {/* Away Team (left-aligned) */}
      <div className="flex items-center gap-2 overflow-hidden">
        {match.away_team.crest_url && (
          <img src={match.away_team.crest_url} alt="" className="h-5 w-5 flex-shrink-0 object-contain" />
        )}
        <span className={`truncate text-xs font-semibold ${isFinished && match.away_score > match.home_score ? "text-black" : "text-zinc-600"}`}>
          {match.away_team.name}
        </span>
      </div>

      {/* Arrow */}
      <div className="text-right text-zinc-300 group-hover:text-zinc-500 transition-colors">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </a>
  );
}

function LeagueSection({ matches }: { matches: MatchSummary[] }) {
  const league = matches[0]?.league;
  if (!league) return null;

  return (
    <div className="mb-8">
      <div className="mb-3 flex items-center gap-3">
        {leagueFlag(league.country) && (
          <img src={leagueFlag(league.country)!} alt="" className="h-4 w-6 rounded-sm object-cover" />
        )}
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-black">{league.name}</h3>
          <span className="text-xs text-zinc-400">{league.country}</span>
        </div>
        <div className="ml-auto">
          <a href={`/leagues/${league.slug}`} className="text-xs font-medium text-zinc-400 hover:text-black">
            View all
          </a>
        </div>
      </div>
      <div className="grid gap-1.5">
        {sortMatches(matches).map((m) => (
          <MatchCard key={m.id} match={m} />
        ))}
      </div>
    </div>
  );
}

function StandingsWidget({ standings }: { standings: StandingRow[] }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white">
      <div className="border-b border-zinc-100 px-4 py-3">
        <h3 className="text-sm font-bold text-black">Premier League</h3>
        <p className="text-[11px] text-zinc-400">Standings</p>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-zinc-100 text-zinc-400">
            <th className="px-3 py-2 text-left font-medium">#</th>
            <th className="px-3 py-2 text-left font-medium">Team</th>
            <th className="px-3 py-2 text-center font-medium">P</th>
            <th className="px-3 py-2 text-center font-medium">GD</th>
            <th className="px-3 py-2 text-right font-medium">Pts</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((row) => (
            <tr key={row.team.id} className="border-b border-zinc-50 last:border-b-0 hover:bg-zinc-50 transition-colors">
              <td className="px-3 py-2 tabular-nums text-zinc-400">{row.position}</td>
              <td className="px-3 py-2 font-medium text-black">{row.team.name}</td>
              <td className="px-3 py-2 text-center tabular-nums text-zinc-500">{row.played}</td>
              <td className="px-3 py-2 text-center tabular-nums">
                <span className={row.gd > 0 ? "text-green-600" : row.gd < 0 ? "text-red-500" : "text-zinc-400"}>
                  {row.gd > 0 ? `+${row.gd}` : row.gd}
                </span>
              </td>
              <td className="px-3 py-2 text-right font-bold tabular-nums text-black">{row.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="border-t border-zinc-100 px-4 py-2.5">
        <a href="/leagues/premier-league-1" className="text-[11px] font-medium text-zinc-400 hover:text-black">
          Full standings
        </a>
      </div>
    </div>
  );
}

function TopScorersWidget({ scorers }: { scorers: { player: { name: string }; team: { name: string }; goals: number }[] }) {
  return (
    <div className="mt-4 rounded-xl border border-zinc-200 bg-white">
      <div className="border-b border-zinc-100 px-4 py-3">
        <h3 className="text-sm font-bold text-black">Top Scorers</h3>
        <p className="text-[11px] text-zinc-400">Premier League 25/26</p>
      </div>
      <div className="divide-y divide-zinc-50">
        {scorers.map((s, i) => (
          <div key={s.player.name} className="flex items-center gap-3 px-4 py-2.5 hover:bg-zinc-50 transition-colors">
            <span className="w-4 text-center text-[11px] font-bold text-zinc-300 tabular-nums">{i + 1}</span>
            <div className="flex-1 overflow-hidden">
              <div className="text-xs font-semibold text-black truncate">{s.player.name}</div>
              <div className="text-[10px] text-zinc-400">{s.team.name}</div>
            </div>
            <span className="text-xs font-bold tabular-nums text-black">{s.goals}</span>
          </div>
        ))}
      </div>
      <div className="border-t border-zinc-100 px-4 py-2.5">
        <a href="/players/top-scorers" className="text-[11px] font-medium text-zinc-400 hover:text-black">
          Full scorers
        </a>
      </div>
    </div>
  );
}

function DateTabs({ active, onActiveChange }: { active: number; onActiveChange: (i: number) => void }) {
  const today = new Date();
  const dates = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() + i - 3);
    return d;
  });

  return (
    <div className="flex items-center gap-1 rounded-xl bg-zinc-100 p-1 w-max">
      {dates.map((d, i) => {
        const isToday = d.toDateString() === today.toDateString();
        const dayLabel = isToday ? "TODAY" : d.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase();
        const dateLabel = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
        return (
          <button
            key={i}
            onClick={() => onActiveChange(i)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
              active === i
                ? "bg-black text-white shadow-sm"
                : "text-zinc-600 hover:text-black"
            }`}
          >
            {dayLabel} <span className={`ml-1 font-normal ${active === i ? "text-zinc-400" : "text-zinc-400"}`}>{dateLabel}</span>
          </button>
        );
      })}
    </div>
  );
}

function QuickLinks() {
  const links = [
    { href: "/leagues/premier-league-1", label: "Premier League", abbr: "PL" },
    { href: "/leagues/la-liga-2", label: "La Liga", abbr: "LL" },
    { href: "/leagues/champions-league-3", label: "Champions League", abbr: "CL" },
    { href: "/players/top-scorers", label: "Top Scorers", abbr: "TS" },
  ];

  return (
    <div className="flex gap-2">
      {links.map((link) => (
        <a
          key={link.label}
          href={link.href}
          className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs font-medium text-zinc-700 transition-colors hover:border-zinc-300 hover:text-black"
        >
          <span className="flex h-5 w-5 items-center justify-center rounded bg-zinc-100 text-[9px] font-bold text-zinc-500">
            {link.abbr}
          </span>
          <span className="hidden sm:inline">{link.label}</span>
        </a>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState(3);
  const [liveMatches, setLiveMatches] = useState<MatchSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const fetchLive = useCallback(async () => {
    try {
      const apiMatches = await getLiveMatchesSummary();
      if (apiMatches.length > 0) {
        setLiveMatches([...apiMatches]);
        // Save to sessionStorage as backup
        if (typeof window !== "undefined") {
          sessionStorage.setItem("liveMatches", JSON.stringify(apiMatches));
        }
      }
    } catch {
      // API error / rate limit — restore from cache if available
      if (typeof window !== "undefined") {
        const cached = sessionStorage.getItem("liveMatches");
        if (cached) {
          setLiveMatches(JSON.parse(cached));
        }
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Restore from cache immediately
    if (typeof window !== "undefined") {
      const cached = sessionStorage.getItem("liveMatches");
      if (cached) {
        setLiveMatches(JSON.parse(cached));
      }
    }
    fetchLive();
    // Poll at configured interval (respects API-Football free-tier limit)
    const interval = setInterval(fetchLive, HOMEPAGE_REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchLive]);

  // Merge: real API matches first, then mock for leagues not in API
  const mockOnly = MOCK_MATCHES.filter((m) => !HOME_LEAGUE_IDS.has(m.league.id));
  const matches = [...liveMatches, ...mockOnly];

  const grouped = useMemo(() => groupByLeague(matches), [matches]);
  const liveCount = matches.filter((m) => m.status === "live").length;
  const finishedCount = matches.filter((m) => m.status === "finished").length;

  const today = new Date();
  const headingDate = new Date(today);
  headingDate.setDate(headingDate.getDate() + activeTab - 3);
  const isToday = headingDate.toDateString() === today.toDateString();
  const headingText = isToday
    ? "Today's Matches"
    : headingDate.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });

  return (
    <div className="min-h-screen bg-white">
      <Header />
      <LiveTicker matches={matches} />

      {loading && matches.length === 0 && (
        <LoadingSpinner message="Loading matches..." />
      )}

      <main className="mx-auto max-w-7xl px-4 py-6">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-black">{headingText}</h1>
            <div className="mt-1 flex items-center gap-3 text-xs text-zinc-400">
              {liveCount > 0 && (
                <span className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                  {liveCount} live
                </span>
              )}
              {finishedCount > 0 && <span>{finishedCount} finished</span>}
              <span>{matches.length} total</span>
            </div>
          </div>
          <DateTabs active={activeTab} onActiveChange={setActiveTab} />
        </div>

        <div className="mb-6">
          <QuickLinks />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_300px]">
          <div>
            {Array.from(grouped.entries()).map(([leagueId, leagueMatches]) => (
              <LeagueSection key={leagueId} matches={leagueMatches} />
            ))}
          </div>

      <aside className="hidden lg:block">
        <div className="sticky top-20">
          <StandingsWidget standings={MOCK_STANDINGS} />
          <TopScorersWidget scorers={MOCK_TOP_SCORERS} />
        </div>
      </aside>
        </div>
      </main>
    </div>
  );
}
