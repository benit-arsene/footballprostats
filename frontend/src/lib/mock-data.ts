import type { LeagueSummary, StandingRow, MatchSummary, TopScorer } from "@/lib/types";

// ─── Shared references (used by both mock-matches and homepage) ───

export const MOCK_LEAGUE_PL = { id: 1, name: "Premier League", slug: "premier-league-1", country: "England", logo_url: "" };
export const MOCK_LEAGUE_LL = { id: 2, name: "La Liga", slug: "la-liga-2", country: "Spain", logo_url: "" };
export const MOCK_LEAGUE_CL = { id: 3, name: "Champions League", slug: "champions-league-3", country: "Europe", logo_url: "" };

// ─── Homepage mock data ───────────────────────────────────────────

export const MOCK_LEAGUES: LeagueSummary[] = [MOCK_LEAGUE_PL, MOCK_LEAGUE_LL, MOCK_LEAGUE_CL];

export const MOCK_STANDINGS: StandingRow[] = [
  { position: 1, team: { id: 10, name: "Arsenal", slug: "arsenal-10", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/uyhbfe1612467038.png" }, played: 28, won: 22, drawn: 4, lost: 2, gf: 68, ga: 24, gd: 44, points: 70, form: ["W","W","D","W","W"] },
  { position: 2, team: { id: 11, name: "Liverpool", slug: "liverpool-11", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/kfaher1737969724.png" }, played: 28, won: 21, drawn: 5, lost: 2, gf: 65, ga: 26, gd: 39, points: 68, form: ["W","D","W","W","L"] },
  { position: 3, team: { id: 12, name: "Man City", slug: "man-city-12", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/vwpvry1467462651.png" }, played: 28, won: 20, drawn: 4, lost: 4, gf: 62, ga: 30, gd: 32, points: 64, form: ["L","W","W","D","W"] },
  { position: 4, team: { id: 13, name: "Chelsea", slug: "chelsea-13", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/pbf4ul1782638263.png" }, played: 28, won: 15, drawn: 7, lost: 6, gf: 48, ga: 35, gd: 13, points: 52, form: ["D","W","L","W","W"] },
  { position: 5, team: { id: 14, name: "Aston Villa", slug: "aston-villa-14", crest_url: "" }, played: 28, won: 14, drawn: 6, lost: 8, gf: 45, ga: 38, gd: 7, points: 48, form: ["W","L","D","W","L"] },
];

export const MOCK_TOP_SCORERS: TopScorer[] = [
  { player: { id: 341, name: "E. Haaland", slug: "erling-haaland-341", position: "Forward", number: 9, nationality: "Norway" }, team: { id: 12, name: "Man City", slug: "man-city-12", crest_url: "" }, goals: 24, assists: 0 },
  { player: { id: 309, name: "M. Salah", slug: "mohamed-salah-309", position: "Forward", number: 11, nationality: "Egypt" }, team: { id: 11, name: "Liverpool", slug: "liverpool-11", crest_url: "" }, goals: 21, assists: 0 },
  { player: { id: 14, name: "O. Watkins", slug: "ollie-watkins-14", position: "Forward", number: 14, nationality: "England" }, team: { id: 14, name: "Aston Villa", slug: "aston-villa-14", crest_url: "" }, goals: 18, assists: 0 },
  { player: { id: 138, name: "K. Palmer", slug: "cole-palmer-138", position: "Midfielder", number: 20, nationality: "England" }, team: { id: 13, name: "Chelsea", slug: "chelsea-13", crest_url: "" }, goals: 17, assists: 0 },
  { player: { id: 109, name: "B. Saka", slug: "bukayo-saka-109", position: "Forward", number: 7, nationality: "England" }, team: { id: 10, name: "Arsenal", slug: "arsenal-10", crest_url: "" }, goals: 16, assists: 0 },
];

export const MOCK_MATCHES: MatchSummary[] = [
  { id: 101, slug: "arsenal-vs-chelsea-101", status: "live", minute: 67, date: "2026-08-22", kickoff_time: "15:00", venue: "Emirates Stadium", league: MOCK_LEAGUE_PL, home_team: { id: 10, name: "Arsenal", slug: "arsenal-10", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/uyhbfe1612467038.png" }, away_team: { id: 13, name: "Chelsea", slug: "chelsea-13", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/pbf4ul1782638263.png" }, home_score: 2, away_score: 1 },
  { id: 102, slug: "real-madrid-vs-barcelona-102", status: "live", minute: 34, date: "2026-08-22", kickoff_time: "21:00", venue: "Santiago Bernabeu", league: MOCK_LEAGUE_LL, home_team: { id: 20, name: "Real Madrid", slug: "real-madrid-20", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/vwvwrw1473502969.png" }, away_team: { id: 21, name: "Barcelona", slug: "barcelona-21", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/wq9sir1639406443.png" }, home_score: 1, away_score: 1 },
  { id: 103, slug: "liverpool-vs-man-city-103", status: "finished", minute: null, date: "2026-08-22", kickoff_time: "12:30", venue: "Anfield", league: MOCK_LEAGUE_PL, home_team: { id: 11, name: "Liverpool", slug: "liverpool-11", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/kfaher1737969724.png" }, away_team: { id: 12, name: "Man City", slug: "man-city-12", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/vwpvry1467462651.png" }, home_score: 3, away_score: 2 },
  { id: 104, slug: "bayern-vs-dortmund-104", status: "finished", minute: null, date: "2026-08-22", kickoff_time: "18:30", venue: "Allianz Arena", league: MOCK_LEAGUE_CL, home_team: { id: 30, name: "Bayern Munich", slug: "bayern-munich-30", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/01ogkh1716960412.png" }, away_team: { id: 31, name: "Dortmund", slug: "dortmund-31", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/tqo8ge1716960353.png" }, home_score: 4, away_score: 0 },
  { id: 105, slug: "inter-vs-ac-milan-105", status: "scheduled", minute: null, date: "2026-08-22", kickoff_time: "20:45", venue: "San Siro", league: MOCK_LEAGUE_CL, home_team: { id: 40, name: "Inter Milan", slug: "inter-milan-40", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/ryhu6d1617113103.png" }, away_team: { id: 41, name: "AC Milan", slug: "ac-milan-41", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/wvspur1448806617.png" }, home_score: 0, away_score: 0 },
  { id: 106, slug: "juventus-vs-napoli-106", status: "scheduled", minute: null, date: "2026-08-22", kickoff_time: "20:45", venue: "Allianz Stadium", league: MOCK_LEAGUE_CL, home_team: { id: 42, name: "Juventus", slug: "juventus-42", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/uxf0gr1742983727.png" }, away_team: { id: 43, name: "Napoli", slug: "napoli-43", crest_url: "https://r2.thesportsdb.com/images/media/team/badge/l8qyxv1742982541.png" }, home_score: 0, away_score: 0 },
];
