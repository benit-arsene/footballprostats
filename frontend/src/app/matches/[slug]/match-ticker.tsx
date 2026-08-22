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
}: {
  matchId: number;
  initialEvents: MatchEvent[];
  status: MatchStatus;
}) {
  const fetchEvents = useCallback(
    () => getMatchEvents(matchId).then((m) => m.events),
    [matchId]
  );

  const { data: liveEvents, isPolling } = useMatchPolling(
    fetchEvents as () => Promise<import("@/lib/types").MatchEvent[]>,
    status
  );

  // Use polled events when available, otherwise fall back to SSR data
  const events = liveEvents ?? initialEvents;

  return (
    <section className="mb-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold">Match Events</h2>
        {isPolling && (
          <span className="flex items-center gap-1.5 text-xs text-zinc-400">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-green-500" />
            Live - updating every 15s
          </span>
        )}
      </div>

      {events.length === 0 ? (
        <p className="rounded-lg border border-dashed border-zinc-200 p-8 text-center text-zinc-400 dark:border-zinc-700">
          No events yet
        </p>
      ) : (
        <div className="space-y-0">
          {events.map((event) => (
            <div
              key={event.id}
              className="flex items-start gap-3 border-b border-zinc-100 py-3 last:border-b-0 dark:border-zinc-800"
            >
              {/* Minute badge */}
              <div className="min-w-[3rem] text-right text-sm font-semibold tabular-nums text-zinc-500">
                {event.minute}&apos;
                {event.added_time && (
                  <span className="text-xs text-zinc-400">+{event.added_time}</span>
                )}
              </div>

              {/* Event icon */}
              <EventIcon type={event.type} />

              {/* Event description */}
              <div className="flex-1">
                <span className="font-medium">{event.player.name}</span>
                <span className="text-zinc-500"> - </span>
                <EventDescription event={event} />
                {event.detail && (
                  <span className="ml-1 text-xs text-zinc-400">({event.detail})</span>
                )}
              </div>

              {/* Team crest */}
              <div className="text-xs text-zinc-400">{event.team.name}</div>
            </div>
          ))}
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
