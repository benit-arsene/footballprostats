"use client";

import { useCallback } from "react";
import type { MatchEvent, MatchStatus } from "@/lib/types";
import { getMatchEvents } from "@/lib/api";
import { useMatchPolling } from "@/lib/use-polling";
import { EventIcon } from "./event-icon";

/**
 * PCS-Style Match Event Ticker
 *
 * Displays a chronological incident feed similar to ProCyclingStats:
 * events listed top-to-bottom by minute, with icons for each event type.
 *
 * For live matches, polls every 15 seconds for new events.
 * For finished matches, renders the cached server data (no polling).
 */
export function MatchTicker({
  matchId,
  initialEvents,
  status,
  homeTeamId,
  awayTeamId,
  homeTeamName,
  awayTeamName,
  homeCrest,
  awayCrest,
}: {
  matchId: number;
  initialEvents: MatchEvent[];
  status: MatchStatus;
  homeTeamId?: number;
  awayTeamId?: number;
  homeTeamName?: string;
  awayTeamName?: string;
  homeCrest?: string;
  awayCrest?: string;
}) {
  const fetchEvents = useCallback(
    (): Promise<MatchEvent[]> => getMatchEvents(matchId).then((m) => m.events),
    [matchId]
  );

  const { data: liveEvents, isPolling } = useMatchPolling(fetchEvents, status);

  // Use polled events when available, otherwise fall back to SSR data
  const events = (liveEvents ?? initialEvents).slice().reverse();

  return (
    <section className="mb-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold">Timeline</h2>
        <div className="flex items-center gap-4">
          {isPolling && (
            <span className="flex items-center gap-1.5 text-xs text-zinc-400">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-green-500" />
              Live
            </span>
          )}
        </div>
      </div>

      {/* Team legend */}
      {homeTeamName && awayTeamName && (
        <div className="mb-3 flex items-center justify-between rounded-lg bg-zinc-50 px-4 py-2">
          <div className="flex items-center gap-2">
            {homeCrest ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={homeCrest} alt="" className="h-5 w-5" />
            ) : (
              <div className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-200 text-[7px] font-bold text-zinc-500">H</div>
            )}
            <span className="text-xs font-semibold text-zinc-700">{homeTeamName}</span>
          </div>
          <span className="text-[10px] text-zinc-400">vs</span>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-zinc-700">{awayTeamName}</span>
            {awayCrest ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={awayCrest} alt="" className="h-5 w-5" />
            ) : (
              <div className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-200 text-[7px] font-bold text-zinc-500">A</div>
            )}
          </div>
        </div>
      )}

      {events.length === 0 ? (
        <p className="rounded-lg border border-dashed border-zinc-200 p-8 text-center text-zinc-400">
          No events yet
        </p>
      ) : (
        <div>
          <div className="space-y-0">
            {events.map((event, i) => {
              const isGoal = ["goal", "own_goal", "penalty_scored", "penalty_missed"].includes(event.type);
              const isCard = ["yellow_card", "red_card", "second_yellow_card"].includes(event.type);
              const isSub = event.type === "substitution";
              const isSpecial = event.type === "kickoff" || event.type === "halftime" || event.type === "fulltime";

              const isHome = homeTeamId ? event.team.id === homeTeamId : true;
              const isAway = awayTeamId ? event.team.id === awayTeamId : false;

              // Special events (kickoff, halftime, fulltime) are centered
              if (isSpecial) {
                return (
                  <div key={event.id} className="flex items-center gap-3 border-b border-zinc-300 py-2 last:border-b-0">
                    <div className="flex-1 border-t border-zinc-200" />
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-zinc-400 text-[9px] font-bold text-white">
                      {event.minute}
                    </div>
                    <EventDescription event={event} />
                    <div className="flex-1 border-t border-zinc-200" />
                  </div>
                );
              }

              // Team badge for this event
              const crest = isHome ? homeCrest : awayCrest;
              const teamName = isHome ? homeTeamName : awayTeamName;

              return (
                <div
                  key={event.id}
                  className={`relative flex items-start gap-3 border-b border-zinc-300 py-2.5 last:border-b-0 ${
                    isHome ? "flex-row" : "flex-row-reverse"
                  }`}
                >
                  {/* Event content */}
                  <div className={`flex-1 min-w-0 pt-0.5 ${isHome ? "text-left" : "text-right"}`}>
                    <div className={`flex items-center gap-2 ${isHome ? "" : "justify-end"}`}>
                      {event.added_time && (
                        <span className="text-[10px] text-zinc-600">+{event.added_time}</span>
                      )}
                      <EventDescription event={event} />
                    </div>
                    <div className={`mt-0.5 flex items-center gap-1.5 ${isHome ? "" : "justify-end"}`}>
                      {event.detail && (
                        <span className="text-[10px] text-zinc-600">({event.detail})</span>
                      )}
                      <span className="text-xs font-medium text-zinc-900">{event.player.name}</span>
                    </div>
                    {event.second_player && (
                      <div className={`mt-0.5 text-[10px] text-zinc-600 ${isHome ? "" : "text-right"}`}>
                        {event.type === "substitution"
                          ? `↔ ${event.second_player.name}`
                          : `assist: ${event.second_player.name}`}
                      </div>
                    )}
                  </div>

                  {/* Timeline circle with minute + team badge */}
                  <div className="relative z-10 flex flex-col items-center gap-1 flex-shrink-0">
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-full text-[10px] font-bold tabular-nums text-white shadow-sm ${
                        isGoal
                          ? "bg-green-600"
                          : isCard
                            ? event.type === "yellow_card"
                              ? "bg-yellow-400 text-zinc-900"
                              : "bg-red-600"
                            : isSub
                              ? "bg-blue-500"
                              : "bg-zinc-600"
                      }`}
                    >
                      {event.minute}
                    </div>
                    {/* Mini team badge */}
                    {crest ? (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img src={crest} alt="" className="h-4 w-4" />
                    ) : (
                      <span className="text-[8px] font-bold text-zinc-400">{isHome ? "H" : "A"}</span>
                    )}
                  </div>

                  {/* Empty spacer for the other side */}
                  <div className="flex-1 min-w-0" />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

function EventDescription({ event }: { event: MatchEvent }) {
  switch (event.type) {
    case "goal":
      return <span className="text-green-600 font-semibold">Goal!</span>;
    case "own_goal":
      return <span className="text-orange-500 font-semibold">Own Goal</span>;
    case "penalty_scored":
      return <span className="text-green-600 font-semibold">Penalty Scored</span>;
    case "penalty_missed":
      return <span className="text-red-500 font-semibold">Penalty Missed</span>;
    case "yellow_card":
      return <span className="text-yellow-500 font-semibold">Yellow Card</span>;
    case "red_card":
      return <span className="text-red-600 font-semibold">Red Card</span>;
    case "second_yellow_card":
      return <span className="text-red-600 font-semibold">Second Yellow - Red</span>;
    case "substitution":
      return (
        <span className="text-blue-500 font-semibold">
          Substitution
          {event.second_player && (
            <span className="text-zinc-400 font-normal"> ({event.second_player.name})</span>
          )}
        </span>
      );
    case "var_decision":
      return <span className="text-purple-500 font-semibold">VAR Decision</span>;
    case "kickoff":
      return <span className="text-zinc-400">Kick Off</span>;
    case "halftime":
      return <span className="font-semibold text-zinc-500">Half Time</span>;
    case "fulltime":
      return <span className="font-semibold text-zinc-500">Full Time</span>;
    default:
      return <span className="text-zinc-500">{event.type.replace(/_/g, " ")}</span>;
  }
}
