export const API_BASE = (process.env.NEXT_PUBLIC_API_URL as string | undefined) ?? "http://localhost:8000";

export const LEAGUE_IDS = {
  premier_league: 39,
  la_liga: 140,
  champions_league: 2,
  bundesliga: 78,
  serie_a: 135,
} as const;

export const HOME_LEAGUE_IDS = new Set<number>([39, 140]);

/**
 * Internal competition ids (the primary key of the `competitions` table).
 *
 * The standings API is keyed by these ids, unlike LEAGUE_IDS above which hold
 * provider-side competition ids.
 */
export const COMPETITION_IDS = {
  premier_league: 1,
  la_liga: 2,
} as const;

/**
 * Competitions published on the player top-scorers pages.
 *
 * `dbSlug` identifies the `competitions` row that supplies the official
 * competition name, `competitionId` is the internal id the scorers endpoint
 * is keyed by, `providerId` is the provider competition id that matches carry,
 * and `label` is only the fallback used when the row cannot be read — so the
 * rendered title always names the competition being rendered.
 */
export const TOP_SCORER_COMPETITIONS = {
  epl: {
    dbSlug: "premier-league-39",
    label: "Premier League",
    competitionId: COMPETITION_IDS.premier_league,
    providerId: LEAGUE_IDS.premier_league,
  },
  laliga: {
    dbSlug: "laliga",
    label: "La Liga",
    competitionId: COMPETITION_IDS.la_liga,
    providerId: LEAGUE_IDS.la_liga,
  },
} as const;

export type TopScorerCompetitionKey = keyof typeof TOP_SCORER_COMPETITIONS;

export function isTopScorerCompetition(
  value: string,
): value is TopScorerCompetitionKey {
  return Object.prototype.hasOwnProperty.call(TOP_SCORER_COMPETITIONS, value);
}

export const POLL_INTERVALS = {
  LIVE: 15_000,
  NEAR_LIVE: 30_000,
} as const;

export const HOMEPAGE_REFRESH_INTERVAL = 150_000;

/**
 * Feature flag: disable automatic live-match polling.
 *
 * When false, `shouldPoll()` always returns false and the polling hooks
 * never start their intervals. Set to true to re-enable polling.
 */
export const POLLING_ENABLED = false;
