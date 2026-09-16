export const API_BASE = (process.env.NEXT_PUBLIC_API_URL as string | undefined) ?? "http://localhost:8000";

export const LEAGUE_IDS = {
  premier_league: 39,
  la_liga: 140,
  champions_league: 2,
  bundesliga: 78,
  serie_a: 135,
} as const;

export const HOME_LEAGUE_IDS = new Set<number>([39, 140]);

export const POLL_INTERVALS = {
  LIVE: 15_000,
  NEAR_LIVE: 30_000,
} as const;

export const HOMEPAGE_REFRESH_INTERVAL = 150_000;
