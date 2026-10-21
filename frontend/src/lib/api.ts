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
  LiveTopScorer,
} from "./types";
import { API_BASE, POLL_INTERVALS, POLLING_ENABLED } from "./constants";

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

// ─── Standings endpoints (database-backed) ─────────────────────────────
export function getStandingsBySeason(seasonId: number): Promise<{
  season: string;
  rows: Array<{
    position: number;
    team: { id: number; name: string; slug: string; crest_url: string };
    played: number;
    won: number;
    drawn: number;
    lost: number;
    goals_for: number;
    goals_against: number;
    goal_difference: number;
    points: number;
    form: string;
  }>;
}> {
  return apiFetch(`/api/v1/standings/${seasonId}`);
}

export function getLiveStandings(): Promise<{ season: string; last_updated: string; rows: any[]; }> {
  return apiFetch(`/api/v1/standings/live`);
}

export type LiveTopScorersResponse = {
  season: string;
  last_updated: string;
  scorers: LiveTopScorer[];
};

export function getLiveTopScorers(): Promise<LiveTopScorersResponse> {
  return apiFetch(`/api/v1/standings/top-scorers-live`);
}

export async function getLiveTopScorersWithLatency(): Promise<{
  data: LiveTopScorersResponse;
  latencyMs: number;
}> {
  const started = performance.now();
  const data = await getLiveTopScorers();
  return { data, latencyMs: performance.now() - started };
}

export function getSeasons(competitionId: number = 1): Promise<{ id: number; label: string }[]> {
  return apiFetch(`/api/v1/standings/seasons?competition_id=${competitionId}`);
}

export type PollingOptions = {
  intervalMs?: number;
  enabled?: boolean;
};

/**
 * Returns true if the match is in a state that should be polled.
 *
 * Polling is gated behind the POLLING_ENABLED feature flag so it can be
 * disabled globally without touching the polling hooks or components.
 */
export function shouldPoll(status: string): boolean {
  if (!POLLING_ENABLED) return false;
  return status === "live";
}
