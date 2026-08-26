"use client";

import { useState } from "react";
import type { MatchDetail, MatchStatus } from "@/lib/types";
import { MatchTicker } from "./match-ticker";
import { MatchLineups } from "./match-lineups";
import { MatchStats } from "./match-stats";

type Tab = "results" | "lineups" | "stats";

const TABS: { key: Tab; label: string }[] = [
  { key: "lineups", label: "Lineups" },
  { key: "stats", label: "Live Stats" },
  { key: "results", label: "Results" },
];

export function MatchContent({
  match,
}: {
  match: MatchDetail;
}) {
  const [activeTab, setActiveTab] = useState<Tab>("results");

  return (
    <div>
      {/* ─── Tab Buttons ──────────────────────────────────────── */}
      <div className="mb-6 flex items-center gap-1 rounded-xl border border-zinc-200 bg-white p-1 w-max">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === tab.key
                ? "bg-zinc-900 text-white shadow-sm"
                : "text-zinc-500 hover:text-zinc-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ─── Tab Content ──────────────────────────────────────── */}
      <div>
        {activeTab === "lineups" && (
          <MatchLineups
            homeLineup={match.home_lineup}
            awayLineup={match.away_lineup}
            homeTeam={match.home_team}
            awayTeam={match.away_team}
          />
        )}

        {activeTab === "stats" && (
          <>
            {match.stats && <MatchStats stats={match.stats} />}
            <MatchTicker
              matchId={match.id}
              initialEvents={match.events}
              status={match.status}
              homeTeamId={match.home_team.id}
              awayTeamId={match.away_team.id}
              homeTeamName={match.home_team.name}
              awayTeamName={match.away_team.name}
              homeCrest={match.home_team.crest_url}
              awayCrest={match.away_team.crest_url}
            />
          </>
        )}

        {activeTab === "results" && (
          <p className="text-zinc-400">Results coming soon.</p>
        )}
      </div>
    </div>
  );
}
