// ─── Core Domain Types ────────────────────────────────────────────────

export type MatchStatus = "scheduled" | "live" | "finished" | "postponed" | "cancelled";

export type EventType =
  | "goal"
  | "own_goal"
  | "penalty_scored"
  | "penalty_missed"
  | "yellow_card"
  | "red_card"
  | "second_yellow_card"
  | "substitution"
  | "var_decision"
  | "kickoff"
  | "halftime"
  | "fulltime"
  | "extra_time_start"
  | "penalty_shootout";

export type TeamRole = "home" | "away";

// ─── Team ─────────────────────────────────────────────────────────────

export interface Team {
  id: number;
  name: string;
  slug: string;
  short_name: string;
  crest_url: string;
  league: LeagueSummary;
}

export interface TeamSummary {
  id: number;
  name: string;
  slug: string;
  crest_url: string;
}

export interface TeamProfile extends Team {
  founded: number;
  venue: string;
  coach: string;
  squad: PlayerSummary[];
}

// ─── Player ───────────────────────────────────────────────────────────

export interface PlayerSummary {
  id: number;
  name: string;
  slug: string;
  position: string;
  number: number | null;
  nationality: string;
}

export interface PlayerProfile extends PlayerSummary {
  date_of_birth: string;
  height_cm: number | null;
  foot: string;
  team: TeamSummary;
  career_stats: CareerStats;
  match_logs: MatchLogEntry[];
}

export interface CareerStats {
  appearances: number;
  goals: number;
  assists: number;
  yellow_cards: number;
  red_cards: number;
  minutes_played: number;
}

export interface MatchLogEntry {
  match_id: number;
  match_slug: string;
  date: string;
  opponent: string;
  result: string;
  goals: number;
  assists: number;
  rating: number | null;
}

// ─── League / Competition ─────────────────────────────────────────────

export interface LeagueSummary {
  id: number;
  name: string;
  slug: string;
  country: string;
  logo_url: string;
}

export interface LeagueProfile extends LeagueSummary {
  season: string;
  standings: StandingRow[];
  top_scorers: TopScorer[];
  fixtures: MatchSummary[];
}

export interface StandingRow {
  position: number;
  team: TeamSummary;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
  form: string[]; // last 5: ["W", "D", "L", "W", "W"]
}

export interface TopScorer {
  player: PlayerSummary;
  team: TeamSummary;
  goals: number;
  assists: number;
}

// ─── Match ────────────────────────────────────────────────────────────

export interface MatchSummary {
  id: number;
  slug: string;
  status: MatchStatus;
  minute: number | null;
  date: string;
  kickoff_time: string;
  venue: string;
  league: LeagueSummary;
  home_team: TeamSummary;
  away_team: TeamSummary;
  home_score: number;
  away_score: number;
}

export interface MatchDetail extends MatchSummary {
  attendance: number | null;
  referee: string;
  home_lineup: LineupPlayer[];
  away_lineup: LineupPlayer[];
  events: MatchEvent[];
  stats: MatchStats;
}

export interface LineupPlayer {
  player: PlayerSummary;
  position: string;
  shirt_number: number | null;
  rating: number | null;
}

export interface MatchEvent {
  id: number;
  minute: number;
  added_time: number | null;
  type: EventType;
  team: TeamSummary;
  player: PlayerSummary;
  second_player: PlayerSummary | null; // assist provider or subbed-in/out player
  detail: string | null; // e.g. "VAR: Goal overturned", "Left-footed shot"
}

export interface MatchStats {
  possession: [number, number]; // [home, away]
  shots: [number, number];
  shots_on_target: [number, number];
  corners: [number, number];
  fouls: [number, number];
  yellow_cards: [number, number];
  red_cards: [number, number];
}

// ─── Live ─────────────────────────────────────────────────────────────

export interface LiveMatchUpdate {
  match_id: number;
  slug: string;
  status: MatchStatus;
  minute: number;
  home_score: number;
  away_score: number;
  events: MatchEvent[];
  last_event_id: number;
}
