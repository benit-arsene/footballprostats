/**
 * API client for the FastAPI backend.
 *
 * Features:
 * - Type-safe fetch wrapper
 * - HTTP polling hook for live match updates (15–30 s intervals)
 * - Cache-friendly fetching for finished match event data
 */

import type {
  MatchSummary,
  MatchDetail,
  LiveMatchUpdate,
  TeamProfile,
  PlayerProfile,
  LeagueProfile,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Generic fetch helper ─────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

// ─── Match endpoints ──────────────────────────────────────────────────

export function getLiveMatches(): Promise<LiveMatchUpdate[]> {
  return apiFetch("/api/v1/matches/live");
}

export function getMatch(matchId: number): Promise<MatchDetail> {
  return apiFetch(`/api/v1/matches/${matchId}`);
}

export function getMatchEvents(matchId: number): Promise<MatchDetail> {
  return apiFetch(`/api/v1/matches/${matchId}/events`);
}

export function getLiveMatchesSummary(): Promise<MatchSummary[]> {
  return apiFetch("/api/v1/matches/live/summary");
}

export function getMatchesByDate(date: string): Promise<MatchSummary[]> {
  return apiFetch(`/api/v1/matches/date/${date}`);
}

// ─── Team endpoints ───────────────────────────────────────────────────

export function getTeam(teamId: number): Promise<TeamProfile> {
  return apiFetch(`/api/v1/teams/${teamId}`);
}

// ─── Player endpoints ─────────────────────────────────────────────────

export function getPlayer(playerId: number): Promise<PlayerProfile> {
  return apiFetch(`/api/v1/players/${playerId}`);
}

// ─── League endpoints ─────────────────────────────────────────────────

export function getLeague(leagueId: number): Promise<LeagueProfile> {
  return apiFetch(`/api/v1/leagues/${leagueId}`);
}

// ─── Polling utilities ────────────────────────────────────────────────

export type PollingOptions = {
  intervalMs?: number;
  enabled?: boolean;
};

/**
 * Returns true if the match is in a state that should be polled.
 */
export function shouldPoll(status: string): boolean {
  return status === "live";
}

/**
 * Polling interval constants (in milliseconds).
 * Live matches poll every 15 s; near-live every 30 s.
 */
export const POLL_INTERVALS = {
  LIVE: 15_000,
  NEAR_LIVE: 30_000,
} as const;
