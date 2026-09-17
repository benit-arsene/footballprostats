# FootballProStats — Architecture Blueprint

## A. Current Architecture (What Exists Today)

### Backend (`backend/`)

| File | Purpose |
|---|---|
| `main.py` | FastAPI app; CORS middleware, 4 routers, validation error handler, `/api/health` |
| `config.py` | API keys from env, league ID mappings, `get_season_year()` helper |
| `models.py` | 23 Pydantic models mirroring frontend types (MatchSummary, MatchDetail, LeagueProfile, etc.) |
| `services/football_api.py` | API-Football client (httpx), 16 functions for fixtures/teams/players/leagues/standings/top scorers |
| `services/mapper.py` | API-Football JSON → Pydantic model mappers |
| `routes/matches.py` | 5 endpoints: `/live`, `/live/summary`, `/date/{date}`, `/{match_id}`, `/{match_id}/events` |
| `routes/players.py` | 1 endpoint: `/{player_id}` |
| `routes/teams.py` | 1 endpoint: `/{team_id}` |
| `routes/leagues.py` | 1 endpoint: `/{league_id}` |
| `requirements.txt` | fastapi, uvicorn, httpx, pydantic, python-dotenv |

### Frontend (`frontend/`)

| Route | Page | Data Source |
|---|---|---|
| `/` | Home dashboard | API-Football (via backend), MOCK fallback |
| `/matches/[slug]` | Match detail | API-Football (via backend), MOCK_MATCH_DETAILS fallback |
| `/leagues/[slug]` | League page | API-Football (via backend), MOCK fallback |
| `/players/[slug]` | Player profile | API-Football (via backend) |
| `/teams/[slug]` | Team profile | API-Football (via backend) |

### Existing Design Decisions
- Hybrid slugs: `{name}-{id}` format — SEO-friendly, O(1) DB lookup via extracted ID
- Backend proxies all API-Football calls — frontend never touches external API directly
- Pydantic models mirror TypeScript types 1:1
- Mock data used only as explicit `??` fallback on API failure
- Structured error responses: `{error: {code, message}}` with HTTP status codes
- API-Football free tier awareness: 100 req/day; 15-30s polling intervals; sessionStorage caching

---

## B. Target Architecture

```
EXTERNAL DATA SOURCES          Provider Adapters           Normalization
┌──────────────────┐          ┌────────────────┐        ┌────────────────┐
│ API-Football     │──────┐  │ api_football/  │   ┌───▶│ competitions/  │
│ Provider B       │──────┼─▶│ provider_b/    │──▶│    │ seasons/       │
│ Provider C       │──────┘  │ ...            │   │    │ teams/         │
└──────────────────┘          └────────────────┘   │    │ players/       │
                                                   │    │ matches/       │
                        ┌──────────────────────────┘    │ events/        │
                        ▼                             │    └───────┬──────┘
                ┌────────────────┐                    │              │
                │ FOOTBALLPROSTATS │◀───────────────────┘              │
                │ DB               │                                   │
                └────────┬─────────┘                                   │
                         │                                           │
                ┌────────▼─────────┐                                   │
                │ BACKEND API       │◀────────────────────────────────┘
                │ /api/v1/...       │
                └────────┬─────────┘
                         │
                ┌────────▼─────────┐
                │ FRONTEND          │
                └───────────────────┘
```

**Core principle**: External provider models never become canonical models. All provider data flows through adapters → normalization → canonical model → DB → our API → frontend.

---

## C. Entity Model

### Core Entities (must persist)

| Entity | Description | Current Representation | Persisted |
|---|---|---|---|
| **Competition** | League/tournament | `LeagueSummary`, `LeagueProfile` | Yes |
| **Season** | Competition + year | `LeagueProfile.season` | Yes |
| **Team** | Football club | `TeamSummary`, `TeamProfile` | Yes |
| **Player** | Footballer | `PlayerSummary`, `PlayerProfile` | Yes |
| **Match** | Fixture with score/status | `MatchSummary`, `MatchDetail` | Yes |
| **MatchEvent** | Goal, card, substitution | `MatchEvent` | Yes |
| **Standing** | League table row | `StandingRow` | Yes |

### Secondary Entities

| Entity | Description | Current Representation |
|---|---|---|
| **LineupPlayer** | Player in match lineup | `LineupPlayer` (in MatchDetail) |
| **MatchStatistic** | Possession, shots, corners | `MatchStats` (in MatchDetail) |
| **PlayerStatistic** | Career stats | `CareerStats` (in PlayerProfile) |
| **Venue** | Stadium | `TeamProfile.venue` (string) |
| **Coach** | Team manager | `TeamProfile.coach` (string) |
| **Referee** | Match referee | `MatchDetail.referee` (string) |
| **Transfer** | Player movement | Not yet modeled |

### Key Relationships

```text
Competition ──1:N── Season ──1:N── Match ──1:N── MatchEvent
                │              │
                │              ├── LineupPlayer (per team)
                │              └── MatchStatistic (1:1)
                │
                └──N:M── Team (via standings/season_roster)

Team ──N:M── Player (via squad)
 │              │
 │              └──N:M── Season (via player_statistics)
 │
 └──1:1── Venue
 └──1:N── Coach (historical)
```

### Historical Versioning Needs
- **Standing** — inherently temporal (per matchday)
- **Team** — squad changes per season
- **Player** — stats per season
- **Competition** — name/format changes over time
- **Match** — immutable once finished

---

## D. Frontend Information Architecture

### Proposed Navbar

```text
Matches | Competitions | Live | Seasons | Transfers | Results | Players | Teams
```

**Reasoning**:
- **Matches** — primary entry point; browse by date/competition/team/status
- **Competitions** — central hub; navigates to seasons and all competition data
- **Live** — real-time data; initially "Coming Soon" if infrastructure unavailable
- **Seasons** — major historical dimension; users navigate "Premier League → 2024/25"
- **Transfers** — enrichment data; "Coming Soon" initially
- **Results** — filtered/finished matches, separate from live fixtures
- **Players** — player profiles and statistics
- **Teams** — team profiles, squads, season history

### Proposed Route Structure

```text
/
├── matches                           ← browse by date/competition/team/status
│   └── [slug]                        ← match detail (existing)
├── competitions
│   └── [competition]
│       └── [season]                  ← season hub: standings, fixtures, scorers
├── live                              ← Coming Soon initially
├── seasons                           ← browse seasons across competitions
│   └── [seasonId]                    ← season detail: matches, standings, teams
├── transfers                         ← Coming Soon initially
├── results                           ← finished/historical matches
├── players
│   └── [player]                      ← player profile (existing)
└── teams
    └── [team]                        ← team profile (existing)
```

**Key route decisions**:
1. `/competitions/[competition]/[season]` — extends current `/leagues/[slug]` with season dimension. Same content (standings, scorers, fixtures) but now navigable by season.
2. `/seasons` — seasons are first-class entities; users want "PL → 2024/25" navigation independent of competition pages.
3. `/matches` — will support date/competition/team/status filters (currently home page date tabs, expanded).
4. `/results` — dedicated historical results view, distinct from live match browsing.

---

## E. Backend API Architecture

### Current Endpoints

| Endpoint | Returns | Used By |
|---|---|---|
| `GET /api/v1/matches/live` | `LiveMatchUpdate[]` | Live ticker |
| `GET /api/v1/matches/live/summary` | `MatchSummary[]` | Home page |
| `GET /api/v1/matches/date/{date}` | `MatchSummary[]` | Home page date tabs |
| `GET /api/v1/matches/{id}` | `MatchDetail` | Match detail |
| `GET /api/v1/matches/{id}/events` | `MatchDetail` | Match ticker |
| `GET /api/v1/teams/{id}` | `TeamProfile` | Team page |
| `GET /api/v1/players/{id}` | `PlayerProfile` | Player page |
| `GET /api/v1/leagues/{id}` | `LeagueProfile` | League page |
| `GET /api/health` | `{status}` | Monitoring |

### Proposed Future Endpoints (FootballProStats API)

```text
Competitions
GET   /api/v1/competitions
GET   /api/v1/competitions/:id
GET   /api/v1/competitions/:id/seasons

Seasons
GET   /api/v1/seasons/:id
GET   /api/v1/seasons/:id/matches
GET   /api/v1/seasons/:id/standings
GET   /api/v1/seasons/:id/teams

Teams
GET   /api/v1/teams/:id                    (existing)
GET   /api/v1/teams/:id/matches
GET   /api/v1/teams/:id/seasons
GET   /api/v1/teams/:id/squad

Players
GET   /api/v1/players/:id                  (existing)
GET   /api/v1/players/:id/seasons

Matches
GET   /api/v1/matches/:id                  (existing)
GET   /api/v1/matches/:id/events           (existing)

Transfers
GET   /api/v1/transfers
GET   /api/v1/transfers/:id

Data Status
GET   /api/v1/data-status                  ← what's imported/available
```

**Design principle**: Frontend depends on these internal contracts. Provider changes only affect the adapter layer, never the frontend.

---

## F. Database Architecture

### Database Direction: PostgreSQL

PostgreSQL is the chosen database technology. It satisfies all requirements:

- Relational model with strong FK enforcement
- Arrays (for `form`), JSONB (for flexible metadata)
- Full-text search (`tsvector`) for future search needs
- Excellent indexing options (B-tree, GIN, GiST)
- Mature replication, backup, and deployment options
- Wide community support and Solo-developer-friendly tooling (Alembic, SQLAlchemy, Prisma)

No secondary database is needed at this stage. PostgreSQL's JSONB handles semi-structured data; `tsvector` handles search. Elasticsearch or similar would only be considered if full-text search performance becomes a measurable bottleneck at scale.

---

### Canonical Data vs Provider-Sourced Data

**FootballProStats canonical data** is the authoritative application model. It is owned, validated, and served by FootballProStats. Examples:

- Team records (name, slug, crest, founded)
- Player records (name, position, nationality)
- Match records (teams, scores, events, stats)
- Standing rows
- Season labels and relationships

**Provider-sourced data** is raw data obtained from external APIs that populates, enriches, or verifies canonical records. Examples:

- API-Football's fixture response (used to populate our Match records)
- API-Football's standings response (used to populate our StandingRow records)
- API-Football's player response (used to populate our Player records)

**Key distinction**: Canonical entities never store provider-specific fields (no `api_football_id` columns in canonical tables). Provider identity is tracked through the `external_ids` table (see below) and through `import_jobs.provider`. Provider metadata lives in its own tables, not in canonical entities.

**How source tracking works without contaminating canonical data**:

| What | Where tracked |
|---|---|
| Which provider supplied a record | `import_jobs.provider` |
| Which external IDs map to which internal record | `external_ids` table |
| When a record was last imported | `import_jobs.completed_at` |
| What data a provider provides (capabilities) | Provider adapter configuration |

---

### Conceptual Schema (Revised)

#### Field Classification Principles

All fields are classified to ensure the schema survives incomplete provider data:

- **required** — field always has a value; record is meaningless without it
- **nullable/optional** — field may legitimately not exist; provider may not supply it
- **derived** — computed from other data, not stored directly
- **provider-dependent** — only available from certain providers; may be null when unavailable

Examples:

| Field | Classification | Reason |
|---|---|---|
| Team name | required | Core entity identity |
| Team slug | required | URL/query identifier |
| Venue name | nullable/optional | Some teams share venues; may be unknown |
| Match attendance | nullable/optional | Free-tier API may not provide; friendly matches may not have |
| Match referee | nullable/optional | Not always available from providers |
| Player height | nullable/optional | Not all providers supply |
| Player foot | nullable/optional | Not available in API-Football free tier |
| Player position | required | Core identity (even if "Unknown" as fallback) |
| Transfer fee | nullable/optional | Formats vary; may be "Free" or unknown |
| Coach name | nullable/optional | Not always available |
| Advanced statistics (xG) | provider-dependent | Only some providers offer |
| Match score | required | Core match identity |
| Standing position | required | Core identity of a standing row |

---

#### Competitions

```text
competitions
├── id (PK)                          required
├── name (text)                      required
├── slug (text, unique)              required
├── country (text, nullable)         optional — some competitions span countries
├── logo_url (text, nullable)        optional
├── created_at                       required
└── updated_at                       required
```

**No `api_football_id` column.** External IDs tracked via `external_ids` table.

---

#### Seasons

```text
seasons
├── id (PK)                          required
├── competition_id (FK)              required
├── label (text)                     required — e.g., "2024/25"
├── start_date (date, nullable)      optional
├── end_date (date, nullable)        optional
├── availability_status              required — available/partial/not_imported/coming_soon
├── import_job_id (FK → import_jobs, nullable)  optional
├── last_import_attempt (timestamp, nullable)   optional
├── created_at                       required
└── updated_at                       required

UNIQUE(competition_id, label)
```

**Historical preservation**: Every past season that has ever existed is a row in this table, regardless of whether data has been imported. Seasons are permanent records.

---

#### Teams

```text
teams
├── id (PK)                          required
├── name (text)                      required
├── slug (text, unique)              required
├── short_name (text, nullable)      optional
├── crest_url (text, nullable)       optional — may change over time
├── founded (int, nullable)          optional
├── venue_id (FK → venues, nullable) optional
├── created_at                       required
└── updated_at                       required
```

**No `api_football_id` column.** External IDs tracked via `external_ids`.

**Historical note**: Team records are permanent. When a team changes name, crest, or venue, `updated_at` tracks the change. Historical identity is preserved via `slug` which remains stable.

---

#### Venues

```text
venues
├── id (PK)                          required
├── name (text)                      required
├── city (text, nullable)            optional
├── capacity (int, nullable)         optional
├── address (text, nullable)         optional
├── created_at                       required
└── updated_at                       required
```

---

#### Coaches

```text
coaches
├── id (PK)                          required
├── name (text)                      required
├── nationality (text, nullable)     optional
├── created_at                       required
└── updated_at                       required
```

---

#### Team Coaches (Historical)

```text
team_coaches
├── id (PK)                          required
├── team_id (FK → teams)             required
├── coach_id (FK → coaches)          required
├── season_id (FK → seasons, nullable) optional — null if ongoing or unknown
├── start_date (date)                required
├── end_date (date, nullable)        optional — null if still coaching
└── UNIQUE(team_id, coach_id, season_id)
```

---

#### Players

```text
players
├── id (PK)                          required
├── name (text)                      required
├── slug (text, unique)              required
├── position (text)                  required — may be "Unknown" as fallback
├── number (int, nullable)           optional — varies by season/team
├── nationality (text, nullable)     optional — may change over career
├── date_of_birth (date, nullable)   optional
├── height_cm (int, nullable)        optional
├── foot (text, nullable)            optional — not all providers supply
├── created_at                       required
└── updated_at                       required
```

**No `api_football_id` column.** External IDs tracked via `external_ids`.

**Historical note**: Player records are permanent. Name spelling corrections, nationality changes, etc. update `updated_at` but history is preserved.

---

#### Team Squad (Historical Membership)

```text
team_squad
├── id (PK)                          required
├── team_id (FK → teams)             required
├── player_id (FK → players)         required
├── season_id (FK → seasons)         required
├── shirt_number (int, nullable)     optional
├── created_at                       required
└── UNIQUE(team_id, player_id, season_id)
```

A player can be in multiple teams across seasons and in the same team across different seasons (rare but possible after returns). The `UNIQUE(team_id, player_id, season_id)` constraint prevents duplicate entries for the same player in the same team in the same season.

---

#### Standing Snapshots (Historical League Tables)

**Problem with original design**: `standings(UNIQUE(season_id, team_id))` means a team can only have ONE standing per season. But we need multiple snapshots — after matchday 5, matchday 10, matchday 20, and final.

**Revised design**: Two tables — a snapshot header and snapshot rows.

```text
standing_snapshots                     ← header: one row per snapshot
├── id (PK)                            required
├── season_id (FK → seasons)           required
├── matchday (int, nullable)           optional — null for "final" or non-league
├── label (text)                       required — e.g., "After Matchday 5", "Final", "After Round 10"
├── snapshot_date (date, nullable)     optional — when this snapshot was taken
├── last_updated (timestamp)           required — when this snapshot was last modified
├── created_at                         required
└── UNIQUE(season_id, matchday)        — matchday can be null for final

standing_rows                          ← rows: positions within a snapshot
├── id (PK)                            required
├── standing_snapshot_id (FK → standing_snapshots)  required
├── team_id (FK → teams)               required
├── position (int)                     required
├── played (int)                       required
├── won (int)                          required
├── drawn (int)                        required
├── lost (int)                         required
├── goals_for (int)                    required
├── goals_against (int)                required
├── goal_difference (int)              required (derived but stored for performance)
├── points (int)                       required
├── form (text[], default [])          optional — last 5 results
├── created_at                         required
└── UNIQUE(standing_snapshot_id, team_id)  — a team appears once per snapshot
```

**Design explanation**:
- A team CAN have multiple positions in the same season (one per snapshot) — the uniqueness constraint is on `(standing_snapshot_id, team_id)`, not `(season_id, team_id)`
- `goal_difference` is derived from `goals_for - goals_against` but stored for query performance
- `form` is a compact array of last 5 results ("W","D","L")
- `matchday` is nullable: null represents the final table; non-null represents a specific matchday snapshot
- `label` is human-readable for display purposes
- Multiple snapshots per season enables historical progression viewing:
  - PL 2024/25 After Matchday 5 → PL 2024/25 After Matchday 10 → PL 2024/25 Final

---

#### Matches

```text
matches
├── id (PK)                            required
├── slug (text, unique)                required
├── competition_id (FK, nullable)      optional — null for friendlies
├── season_id (FK, nullable)           optional — null for friendly internationals
├── home_team_id (FK → teams)          required
├── away_team_id (FK → teams)          required
├── venue_id (FK → venues, nullable)   optional
├── referee_id (FK → referees, nullable) optional
├── date (date)                        required
├── kickoff_time (time, nullable)      optional
├── status (text)                      required — scheduled/live/finished/postponed/cancelled
├── minute (int, nullable)             optional
├── home_score (int)                   required — default 0
├── away_score (int)                   required — default 0
├── attendance (int, nullable)         optional
├── correction_of_id (FK → matches, nullable) optional — links to original if corrected
├── created_at                         required
└── updated_at                         required
```

**No `api_football_id` column.** External IDs tracked via `external_ids`.

**Correction strategy**:
- Match records are immutable once finalized (status = "finished")
- Corrections create a NEW match record with `correction_of_id` pointing to the original
- `correction_of_id` is nullable — most records will have it as null
- The most recent version (by `updated_at`, or by checking `correction_of_id` chains) is the current canonical version
- Correction reason/meta stored in a lightweight `match_corrections` table (see below)
- This avoids full event-sourcing while allowing legitimate corrections

```text
match_corrections
├── id (PK)                            required
├── match_id (FK → matches)            required — the corrected match
├── corrected_match_id (FK → matches)  required — the correction version
├── reason (text, nullable)            optional — why the correction was made
├── source (text, nullable)            optional — which provider/source requested it
├── created_at                         required
```

**Historical-first**: Match records are never deleted. Corrections are linked, not overwritten. Even if a match's data changes, the original record and all corrections remain queryable.

---

#### Match Events

```text
match_events
├── id (PK)                            required
├── match_id (FK → matches)            required
├── minute (int)                       required
├── added_time (int, nullable)         optional — stoppage time
├── type (text)                        required — matches EventType enum
├── team_id (FK → teams)               required
├── player_id (FK → players, nullable) optional — who performed the event
├── second_player_id (FK → players, nullable) optional — assist or subbed player
├── detail (text, nullable)            optional — description
├── created_at                         required
└── UNIQUE(match_id, id)               required — event ordering within match
```

**Historical-first**: Events are tied to a specific match version via `match_id`. If a match is corrected, the corrected match has its own event records.

---

#### Match Lineups

```text
match_lineups
├── id (PK)                            required
├── match_id (FK → matches)            required
├── team_id (FK → teams)               required
├── player_id (FK → players)           required
├── position (text)                    required — may be "Unknown"
├── shirt_number (int, nullable)       optional
├── rating (float, nullable)           optional — not all providers supply
└── UNIQUE(match_id, team_id, player_id)
```

---

#### Match Statistics

```text
match_statistics
├── id (PK)                            required
├── match_id (FK → matches)            required
├── team_id (FK → teams)               required
├── possession_home (int, nullable)    provider-dependent — percentage 0-100
├── possession_away (int, nullable)    provider-dependent
├── shots (int, nullable)              provider-dependent
├── shots_on_target (int, nullable)    provider-dependent
├── corners (int, nullable)            provider-dependent
├── fouls (int, nullable)              provider-dependent
├── yellow_cards (int, nullable)       provider-dependent
├── red_cards (int, nullable)          provider-dependent
└── UNIQUE(match_id, team_id)
```

**All fields nullable** — different providers supply different statistics. A match without advanced stats is valid.

---

#### Transfers

```text
transfers
├── id (PK)                            required
├── player_id (FK → players)           required
├── from_team_id (FK → teams)          required
├── to_team_id (FK → teams)            required
├── transfer_date (date, nullable)     optional — some transfers have unknown dates
├── transfer_fee (text, nullable)      optional — format varies; "Free", "€50M", etc.
├── season_id (FK → seasons, nullable) optional — which season the transfer occurred in
└── created_at                         required
```

---

#### Player Season Statistics (Across Multiple Teams)

**Problem with original design**: `player_season_stats UNIQUE(player_id, season_id)` means a player can only have ONE team per season. But a player can transfer mid-season and play for Team A AND Team B in the same season.

**Revised design**: Add `team_id` to the uniqueness constraint.

```text
player_season_stats
├── id (PK)                            required
├── player_id (FK → players)           required
├── season_id (FK → seasons)           required
├── team_id (FK → teams)               required — which team the player was at
├── appearances (int, default 0)       required
├── goals (int, default 0)             required
├── assists (int, default 0)           required
├── yellow_cards (int, default 0)      required
├── red_cards (int, default 0)         required
├── minutes_played (int, default 0)    required
├── created_at                         required
└── UNIQUE(player_id, season_id, team_id)  ← CHANGED from (player_id, season_id)
```

**Design explanation**:
- A player can have multiple records per season — one per team
- Each record is team-specific (goals for Team A, goals for Team B are separate)
- **Overall season total** is computed by summing all records for `(player_id, season_id)` across teams
- This preserves both team-specific detail and enables aggregate queries

---

#### External IDs (Relational, No Polymorphic FKs)

**Problem with original design**: `external_ids.internal_id (int)` with a single FK target cannot enforce referential integrity — it could point to any table.

**Revised design**: Use explicit nullable FK columns for each entity type, with a `CHECK` constraint ensuring exactly one is populated per row.

```text
external_ids
├── id (PK)                            required
├── entity_type (text)                 required — competition/season/team/player/match
├── provider (text)                    required — api_football/provider_b/provider_c
├── external_id (text)                 required — provider's ID (stored as text; some use strings)
├── competition_id (FK → competitions, nullable) required when entity_type = competition
├── season_id (FK → seasons, nullable)       required when entity_type = season
├── team_id (FK → teams, nullable)             required when entity_type = team
├── player_id (FK → players, nullable)         required when entity_type = player
├── match_id (FK → matches, nullable)          required when entity_type = match
├── last_verified (timestamp, nullable)        optional
├── created_at                         required
└── UNIQUE(entity_type, provider, external_id)
```

**Referential integrity enforcement**:
- Each entity type has its own explicit FK column
- Application logic (or database CHECK constraints) ensures the correct FK column is populated based on `entity_type`
- No fake polymorphic foreign key — all relationships are real FKs to real tables
- Example: `(team, api_football, 50) → team_id 847` — the `team_id` FK enforces that 847 actually exists in the `teams` table

**Why not a polymorphic FK**: Relational databases cannot enforce FK constraints on a column that dynamically references different tables. Using separate nullable FK columns with application-level CHECK constraints provides both real FKs and flexibility.

**Deduplication**: The `UNIQUE(entity_type, provider, external_id)` constraint prevents duplicate external ID entries. On import, the system looks up `(provider, external_id)`; if found, the existing internal ID is reused.

---

#### Data Sources (Which Provider Supplied What)

```text
data_sources
├── id (PK)                            required
├── name (text)                        required — "API-Football", "Provider B"
├── base_url (text, nullable)          optional
├── is_active (bool, default true)     required
├── quota_limit (int, nullable)        optional — requests per day/hour
├── created_at                         required
└── updated_at                         required
```

This table tracks external providers as first-class records. `import_jobs.provider` FK references `data_sources.name`. Provider-specific configuration (API keys, rate limits) lives here, not in canonical tables.

---

#### Import Jobs

```text
import_jobs
├── id (PK)                            required
├── entity_type (text)                 required — competition/season/team/player/match/...
├── data_source_id (FK → data_sources) required — which provider was used
├── status (text)                      required — pending/running/completed/failed/partial
├── started_at                         required
├── completed_at (nullable)            optional
├── records_processed (int, default 0) required
├── records_failed (int, default 0)    required
├── error_message (text, nullable)     optional
├── config (JSONB, nullable)           optional — provider params, date range, etc.
└── created_at                         required
```

**How this supports the importer**:
- Import one competition/season/date range/day per job
- Resume: `records_processed` tracks progress; on restart, skip records with external IDs already in `external_ids`
- Retry: `records_failed` tracks failures; individual record retries use external_id dedup
- Source tracking: `data_source_id` records which provider supplied the data
- Partial handling: `status = "partial"` if `records_failed > 0`

---

### Key Relationship Summary

```text
Competition → Season (1:N)
Season → Match (1:N)
Season → Standing Snapshot (1:N)
Standing Snapshot → Standing Row (1:N)
Team → Player (N:M via team_squad)
Team → Player Season Stat (1:N per team)
Player → Player Season Stat (N:M via team)
Player → Transfer (N:M as from/to)
Team → Match (2:N as home/away)
Match → Match Event (1:N)
Match → Match Lineup (1:N per team)
Match → Match Statistic (1:N per team)
Team → Team Coach (1:N)
Coach → Team Coach (N:M via team_coaches)
Team → Venue (N:1)
Player → External ID (1:N)
Team → External ID (1:N)
Season → External ID (1:N)
Match → External ID (1:N)
Competition → External ID (1:N)
Import Job → Data Source (N:1)
```

---

### Indexes and Constraints (Conceptual)

#### Uniqueness Constraints (Enforced)

| Table | Constraint | Purpose |
|---|---|---|
| competitions | `UNIQUE(slug)` | Prevent duplicate competition slugs |
| seasons | `UNIQUE(competition_id, label)` | Prevent duplicate season labels per competition |
| teams | `UNIQUE(slug)` | Prevent duplicate team slugs |
| players | `UNIQUE(slug)` | Prevent duplicate player slugs |
| team_squad | `UNIQUE(team_id, player_id, season_id)` | Prevent duplicate squad entries |
| standing_snapshots | `UNIQUE(season_id, matchday)` | Prevent duplicate snapshots per season |
| standing_rows | `UNIQUE(standing_snapshot_id, team_id)` | Prevent duplicate team entries per snapshot |
| matches | `UNIQUE(slug)` | Prevent duplicate match slugs |
| match_events | `UNIQUE(match_id, id)` | Maintain event ordering within match |
| match_lineups | `UNIQUE(match_id, team_id, player_id)` | Prevent duplicate lineup entries |
| match_statistics | `UNIQUE(match_id, team_id)` | One stats record per match per team |
| player_season_stats | `UNIQUE(player_id, season_id, team_id)` | Allow multiple teams per season |
| external_ids | `UNIQUE(entity_type, provider, external_id)` | Prevent duplicate external ID mappings |
| team_coaches | `UNIQUE(team_id, coach_id, season_id)` | Prevent duplicate coaching entries |

#### Important Indexes (For Query Performance)

**Matches by season**: `(season_id, date)` — browse matches chronologically within a season
**Matches by team**: `(home_team_id, date), (away_team_id, date)` — find all matches for a team
**Matches by competition**: `(competition_id, date)` — browse matches within a competition
**Matches by date**: `(date, competition_id)` — date-based filtering (home page date tabs)
**Matches by status**: `(status, date)` — find live/scheduled/finished matches
**Player history**: `(player_id, season_id)` — query player's seasonal records
**Player season stats**: `(player_id, season_id, team_id)` — query player's team-specific stats
**Standing retrieval**: `(season_id, matchday, position)` — get full standings for a snapshot
**Standing by team**: `(standing_snapshot_id, team_id)` — find a team's position in a snapshot
**External ID lookup**: `(provider, external_id)` — fast lookup during import dedup
**Team squad**: `(team_id, season_id)` — get squad for a team in a season
**Match events**: `(match_id, minute)` — events in chronological order
**Transfers by player**: `(player_id, transfer_date)` — player transfer history
**Team coaches**: `(team_id, start_date)` — coaching history chronological
**Import jobs**: `(status, started_at)` — find running/stuck jobs
**Season availability**: `(competition_id, availability_status)` — filter by competition status

#### Duplicate Prevention

- **Matches**: `slug` unique constraint; slug derived from `{home}-vs-{away}-{id}` ensures natural uniqueness
- **External ID imports**: `UNIQUE(entity_type, provider, external_id)` prevents re-importing same entity
- **Team squad**: `UNIQUE(team_id, player_id, season_id)` prevents duplicate squad entries
- **Standing rows**: `UNIQUE(standing_snapshot_id, team_id)` prevents duplicate rows per snapshot

#### Foreign Key Enforcement

All relationships use real foreign keys to real tables. No polymorphic FKs. Each entity type references its specific parent table directly. The `external_ids` table uses per-entity FK columns (see Section F for details).

---

### Historical-First Design Review

Every entity in this schema is designed to be permanent:

- **No `deleted_at` columns** — records are never soft-deleted
- **No `is_current` flags** — recency is determined by timestamps and relationships
- **`updated_at` on all tables** — tracks when records change
- **Correction chains on matches** — corrections link to originals, originals preserved
- **Standing snapshots** — historical tables preserved; final table is just another snapshot
- **Team squad per season** — historical rosters preserved via `team_squad`
- **Player season stats per team** — historical stats preserved per season/team combination
- **Seasons are permanent** — even if data isn't imported yet, the season exists as a record

The schema does NOT assume current-season-only data anywhere. A query for "all standings in Premier League history" works by joining `standing_snapshots → seasons → competitions` with no date filter.

---

### Field Classification Summary

| Field | Classification | Notes |
|---|---|---|
| Competition name, slug | required | Core identity |
| Competition country | nullable | Some competitions span countries |
| Season label | required | Human-readable |
| Season dates | nullable | May not be precisely known |
| Season availability_status | required | Application-level state |
| Team name, slug | required | Core identity |
| Team crest_url | nullable | Changes over time; may be missing |
| Team founded | nullable | Not always known |
| Player name, slug, position | required | Core identity; position defaults to "Unknown" |
| Player number | nullable | Varies by season/team |
| Player nationality | nullable | May change over career |
| Player DOB, height, foot | nullable | Not all providers supply |
| Player stance | required | Core identity |
| Match date | required | Core identity |
| Match scores | required | Default 0 |
| Match status | required | Core identity |
| Match attendance | nullable | Provider-dependent |
| Match referee | nullable | Provider-dependent |
| Match venue | nullable | Some matches at neutral venues |
| Match correction_of_id | nullable | Only for corrections |
| Standing position, played, won, drawn, lost, goals, points | required | Core standing identity |
| Standing form | optional | Last 5 results; empty if unavailable |
| Standing matchday | nullable | Null for final table |
| Transfer date, fee | nullable | May be unknown |
| All match statistics | nullable | Provider-dependent |
| Match lineup rating | nullable | Not all providers supply |
| Import job config | optional | JSONB for flexible parameters |

---

## G. Multi-Provider Architecture

### Directory Structure

```text
backend/
├── providers/
│   ├── api_football/
│   │   ├── client.py          ← httpx calls to API-Football
│   │   ├── adapters.py        ← raw JSON → canonical format
│   │   └── ids.py             ← external ID extraction
│   ├── provider_b/
│   │   ├── client.py
│   │   ├── adapters.py
│   │   └── ids.py
│   └── provider_c/
│       ├── client.py
│       ├── adapters.py
│       └── ids.py
├── normalization/
│   ├── competitions.py        ← canonical Competition from any provider
│   ├── seasons.py
│   ├── teams.py
│   ├── players.py
│   ├── matches.py
│   ├── events.py
│   └── standings.py
├── services/                   ← existing (now thin wrappers)
│   ├── football_api.py       ← moves to providers/api_football/client.py
│   └── mapper.py             ← moves to normalization/
├── routes/                     ← unchanged (depend on canonical API)
└── models.py                   ← canonical Pydantic models (unchanged)
```

### Adapter Pattern

```text
Provider B raw JSON
       ↓
provider_b/adapters.py
       ↓
canonical model (matches models.py)
       ↓
normalization layer validates/deduplicates
       ↓
DB write
```

Each provider adapter:
1. Fetches raw data from the provider API
2. Maps provider-specific fields to canonical model fields
3. Extracts external IDs for mapping (see Section H)
4. Returns canonical model instances

**Important**: `models.py` stays as our canonical models. Provider-specific response structures are never exposed outside their adapter. The existing `services/mapper.py` becomes `normalization/` — the key difference is that instead of mapping a single provider's format, normalization validates that multiple providers' outputs converge to the same canonical shape.

### Provider Selection Strategy

Each entity type can have a primary and fallback provider:
- Matches/events: API-Football primary, Provider B fallback
- Standings: API-Football primary
- Players: API-Football primary
- Transfers: Provider C primary (if specialized)

Selection is configurable in `config.py` per entity type.

---

## H. External ID Strategy

**Detailed schema is in Section F** (External IDs table with per-entity FK columns). This section covers the conceptual strategy only.

### Architecture

```text
External Provider ID
       ↓
external_ids table     (maps provider + external_id → internal entity)
       ↓
Internal ID
       ↓
Canonical entity query
```

### Design Principles (see Section F for schema)

- **No `api_football_id` columns in canonical tables** — provider identity lives exclusively in `external_ids`
- **No polymorphic foreign keys** — each entity type (competition/season/team/player/match) has its own explicit nullable FK column in `external_ids`
- **`UNIQUE(entity_type, provider, external_id)`** prevents duplicate external ID mappings
- **Referential integrity** — every `external_ids` row has a real FK to the actual entity table it references

### Deduplication Process

1. **On import**: Extract external IDs from provider response
2. **Lookup**: Query `external_ids` for `(provider, external_id)` match
3. **If found**: Return existing internal ID — no duplicate created
4. **If not found**: Create new entity, create `external_ids` record
5. **Conflict resolution**: If different providers claim the same entity name, use external ID mapping to determine if they reference the same entity

### Per-Entity Mapping Example

```text
API-Football: Manchester City = team_id 50
Provider B:   Manchester City = team_id 1234
FootballProStats: Manchester City = team_id 847 (internal)

external_ids:
  (team, api_football, 50)   → 847
  (team, provider_b, 1234)   → 847
```

### Slug as Alternative Identifier

Currently slugs serve as human-readable identifiers. In the future, slugs should be unique and stable:
- `slug` derived from name + ID (hybrid format)
- When DB has internal ID, slug becomes `{name}-{internal_id}`
- External provider slugs are stored in `external_ids` for lookup

---

## I. Historical Import Architecture

### Data Flow

```text
External API
     ↓
Importer (scheduled, incremental)
     ↓
Validate (schema, required fields)
     ↓
Normalize (to canonical model)
     ↓
Deduplicate (check external_ids)
     ↓
Store in DB
     ↓
Record import metadata
```

### Import Job Tracking

Table definitions for `import_jobs` and `data_sources` are in **Section F** (Data Sources and Import Jobs tables). Section I describes the process only.

The key difference from earlier versions: `import_jobs` references `data_sources.id` (FK) rather than storing provider name as text. This ensures referential integrity — every import is linked to a real, named data provider.

### Import Process Requirements

1. **Resume support**: Track `records_processed` — on restart, skip already-imported records (via external_ids check)
2. **Progress tracking**: `import_jobs` records start/end times, records processed, failures
3. **Duplicate avoidance**: Every import checks `external_ids` before creating records
4. **Quota respect**: Configurable delay between requests; provider-specific rate limits in `config.py`
5. **Retry safe failures**: Network timeouts and 5xx errors are retried; validation errors are logged but not retried
6. **Source tracking**: Every record is associated with a `data_sources` entry via `import_jobs.data_source_id`
7. **Partial import detection**: `import_jobs.status = "partial"` if failures occurred; downstream can handle accordingly

### Incremental Import Example

```text
Day 1: Import Premier League 2024/25 (matches + standings + scorers)
Day 2: Import Premier League 2023/24
Day 3: Import La Liga 2024/25
Day 4: Import La Liga 2023/24
...
```

Each day's import creates `import_jobs` records. If interrupted, the next run resumes from `records_processed`.

### Import Order (recommended)

1. Competitions → establish canonical competition records
2. Seasons → link to competitions
3. Teams → establish canonical team records
4. Players → establish canonical player records
5. Team rosters (team_squad) → link players to teams per season
6. Matches → link to competitions, seasons, teams
7. Match events/lineups/stats → linked to matches
8. Standings → linked to seasons
9. Transfers → linked to players and teams

---

## J. Current/Live Data Architecture

### Historical/Static Data (DB-first)

```text
Finished matches, old standings, historical stats, old squads,
transfers, season archives, player career trajectories.

Source: FootballProStats DB
Update: Via import jobs (batch, incremental)
Frontend: Server-rendered from DB when possible
```

### Live/Current Data (external provider + controlled polling)

```text
Live scores, current match events, today's fixtures, current standings.

Source: External provider (API-Football) via backend polling
Update: Backend-controlled polling (15-30s for live, 2-5 min for fixtures)
Frontend: Client-side polling via useMatchPolling (live matches only)
```

### Transition Boundary

When a match finishes:
1. **During match**: Live data from external provider (real-time events, scores)
2. **At full-time**: Final score captured; match status = "finished"
3. **Post-finish**: Data transitions to DB-backed (match detail, stats, events permanently stored)
4. **Frontend**: Live tab stops polling; match detail page serves from DB

The backend should track this transition:
- `Match.status` changes from `live` → `finished`
- Backend stops polling that match
- Final data is imported into DB via normal import pipeline or immediate capture

---

## K. Data Availability Model

### Season/Competition Status

Each season should display an availability status:

```text
Premier League
├── 2024/25   → Available (fully imported, DB-backed)
├── 2023/24   → Available (fully imported, DB-backed)
├── 2022/23   → Partial (import in progress or incomplete data)
├── 2021/22   → Not imported (planned for future import)
└── 2020/21   → Coming Soon (not yet scheduled for import)
```

### Status Definitions

| Status | Meaning | Frontend Display |
|---|---|---|
| **Available** | Fully imported, DB-backed, all features work | Normal page with full data |
| **Partial** | Some data imported; some features may show mock or incomplete data | Page with "Some data unavailable" notice |
| **Not imported** | Planned but not yet imported | "Coming soon" placeholder in season list |
| **Coming Soon** | Not planned yet | "Coming soon" in season list |

### Error Translation

External API errors should be translated into application states:

```text
API-Football 502 (provider limitation)
  → Season status: Partial or Not imported
  → Frontend shows mock data if available
  → User sees: "Some data unavailable — importing in progress"
  → NOT user-facing provider error

API-Football 429 (rate limit)
  → Backend: retry with backoff
  → Frontend: show cached/last-known data with stale indicator
  → User sees: "Data may be outdated — refreshing soon"
```

### Implementation

Season availability can be tracked in the DB:

```text
seasons
├── ...
├── availability_status (available/partial/not_imported/coming_soon)
├── import_job_id (FK → import_jobs, nullable)
└── last_import_attempt (timestamp, nullable)
```

---

## L. Migration Roadmap

### Phase A — Architecture + Contracts (current)

- [x] Define canonical data model (models.py already serves this)
- [x] Define FootballProStats API contracts (Section E)
- [x] Define route architecture (Section D)
- [x] Define availability model (Section K)
- [x] **OUTPUT: This blueprint document**

### Phase B — Database Foundation

- [x] **Decided**: PostgreSQL as database technology
- [x] **Decided**: All entity tables designed with field classifications
- [x] **Decided**: Historical standings model (snapshots + rows)
- [x] **Decided**: Player-season-team stats model
- [x] **Decided**: External ID architecture (per-entity FK columns)
- [x] **Decided**: Canonical vs provider data separation
- [x] **Decided**: Match correction strategy
- [x] **Decided**: Index and constraint plan
- [ ] Design final DB schema from Section F into concrete SQLAlchemy models
- [ ] Create migration tooling (Alembic)
- [ ] Set up database infrastructure (PostgreSQL hosting, credentials, backups)
- [ ] Create canonical models in DB layer matching Section F

### Phase C — Provider Abstraction

- [ ] Create provider interface/abstract class
- [ ] Move `services/football_api.py` → `providers/api_football/`
- [ ] Move `services/mapper.py` → `normalization/`
- [ ] Create `external_ids` table and lookup service
- [ ] Build provider selection config
- [ ] Test: existing endpoints still work via provider abstraction

### Phase D — Historical Importer

- [ ] Build import job framework (`import_jobs` table)
- [ ] Build single-entity importer (competitions → players)
- [ ] Build import orchestration (ordered import from Section I)
- [ ] Add resume/replay capability
- [ ] Add quota management (rate limiting per provider)
- [ ] Test: import a single competition season end-to-end

### Phase E — Migrate Frontend to Database-Backed Data

- [ ] Add backend routes for new API (Section E future endpoints)
- [ ] Update frontend to use new routes instead of provider-mirrored routes
- [ ] Implement availability status UI (Section K)
- [ ] Migrate league page → `/competitions/[id]/[season]`
- [ ] Create seasons browse page
- [ ] All existing functionality remains working during migration

### Phase F — Second Provider Integration

- [ ] Implement provider B adapter
- [ ] Test fallback behavior
- [ ] Test provider conflict resolution (Section H)
- [ ] Migrate some entity types to provider B for load distribution

### Phase G — Live Infrastructure

- [ ] Build backend polling service (replaces `useMatchPolling`)
- [ ] Implement match finish detection and DB transition
- [ ] Add CTV/cron for periodic data freshness checks
- [ ] Implement stale data indicators

### Phase H — Advanced Statistics

- [ ] Heatmaps, xG, pass maps
- [ ] Player comparison tools
- [ ] Historical trend charts
- [ ] Requires Phase B-E completion first

**Order rationale**: Backend contracts (A) must exist before DB (B). DB and providers (B+C) must exist before importer (D). DB data must exist before frontend migrates (E). Frontend migration should precede additional providers (F) so users aren't confused by dual-provider behavior. Live (G) and stats (H) are dependent on all foundational work.

---

## M. Risks and Unresolved Questions

### Unresolved Decisions

1. **Import concurrency**: Should imports run sequentially or parallel? API-Football quota limits favor sequential; provider B/C might allow parallel.

2. **Standing snapshot granularity**: Store per-matchday or per-round? API-Football provides per-matchday; some competitions use rounds.

3. **Player identity across seasons**: Same player may have different name spellings, nationalities, or positions in different providers. Deduplication strategy needed beyond external ID matching.

4. **Transfer data sourcing**: No current provider for transfers. Need to identify Provider C or web scraping strategy.

5. **Frontend state management**: Current approach uses React state + sessionStorage. Future: consider React Query / TanStack Query for server state. Not yet needed.

6. **Search implementation**: Blueprint identifies search as future need. PostgreSQL `tsvector` is the default approach; Elasticsearch only if measurable search performance bottleneck.

7. **Multi-provider primary/fallback at entity level**: Which provider is primary for which entity? Requires operational testing with real API limits.

8. **Match correction UI**: How should corrections be presented to users? Show both versions? Show only the current version with correction history accessible via admin? Decision deferred until Phase E.

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| API-Football free tier season restriction | Standings/scorers unavailable for current season | Mock fallback + availability model (Section K) |
| Provider schema changes break normalization | Backend errors, frontend shows empty data | Version provider adapters; schema validation at import |
| Import jobs run slowly (large historical data) | Incomplete data for users | Incremental import with progress indicators |
| External ID conflicts between providers | Duplicate entities in DB | `external_ids` table + deduplication (Section G) |
| Frontend coupled to provider-specific data | Provider change forces frontend update | Strict backend API contracts (Section E) |
| Quota exhaustion during peak times | API failures for live data | Backend polling + caching + graceful degradation |
| Match corrections overwrite history | Historical data lost | Immutable records + correction chains (Section F) |

---

## Summary

### 1. What I Inspected
- All 9 backend Python files (main, models, config, services, routes)
- All frontend app routes (home, matches, leagues, players, teams)
- All frontend lib files (types, api, constants, slug, mock-data, mock-matches, use-polling)
- All frontend components (LoadingSpinner, ErrorDisplay, EmptyState)
- All match detail sub-components (content, stats, lineups, ticker, event-icon)
- Current git state (only `frontend/src/app/page.tsx` modified this session)

### 2. Proposed Architecture
- External providers → Adapters → Normalization → DB → Backend API → Frontend
- External provider models never become canonical models
- FootballProStats has its own data model independent of any provider
- Historical data from DB; live data from controlled provider polling
- Season availability model (available/partial/not_imported/coming_soon)

### 3. What Should Be Built First
- **Phase A** (architecture contracts) — documented in this blueprint ✅
- **Phase B** (database schema) — next logical step after architecture is defined
- **Phase C** (provider abstraction) — refactor existing `football_api.py`/`mapper.py` into provider/normalization layers

### 4. What Should NOT Be Built Yet
- Database implementation (Phase B — architecture first)
- Second provider (Phase F — need single-provider foundation)
- Live polling backend (Phase G — need DB first)
- Search (Phase H area — needs DB)
- Transfers (no data source identified)
- New navbar redesign (deferred per scope rules)
- Importer (Phase D — needs DB + provider abstraction)

### 5. Decisions Requiring Human Confirmation

1. Import concurrency model (sequential vs parallel?)
2. Standing snapshot granularity (per-matchday vs per-round?)
3. Transfer data source identification
4. Search engine choice (PostgreSQL full-text vs Elasticsearch?)
5. Whether to proceed to Phase B immediately or refine blueprint further
6. Match correction presentation UI design

---

## N. Architecture Review Decisions

The following 10 issues were identified and resolved during the technical review:

### N.1 Historical Standings

**Decision**: Two-table design — `standing_snapshots` (header) + `standing_rows` (data rows).

**Why**: A team needs multiple positions in the same season (after different matchdays, plus final). `standings(UNIQUE(season_id, team_id))` prevented this. The new design has `standing_snapshots.UNIQUE(season_id, matchday)` where matchday is nullable (null = final table). Each snapshot has its own `standing_rows` with `UNIQUE(standing_snapshot_id, team_id)`.

### N.2 Player Statistics Across Multiple Teams

**Decision**: `player_season_stats UNIQUE(player_id, season_id, team_id)` instead of `UNIQUE(player_id, season_id)`.

**Why**: A player can play for Team A and Team B in the same season (mid-season transfer). Each team-specific record preserves individual stats; overall season totals are computed via `SUM()` grouped by `(player_id, season_id)`.

### N.3 External ID Architecture

**Decision**: Remove all `api_football_id` columns from canonical tables. Use `external_ids` with explicit nullable FK columns per entity type and `UNIQUE(entity_type, provider, external_id)` constraint.

**Why**: Having `api_football_id`, `provider_b_id`, `provider_c_id` in every table doesn't scale. A single `external_ids` table with per-entity FK columns enforces referential integrity properly. No polymorphic FKs — each entity type has its own real FK column.

**Referential integrity**: When `entity_type = 'team'`, `team_id` FK is populated and all other entity FKs are NULL. Database CHECK constraints or application logic ensures exactly one entity FK is populated per row.

### N.4 Canonical vs Provider Data

**Decision**: Canonical entities store zero provider-specific fields. Provider metadata lives in `data_sources`, `external_ids`, and `import_jobs` tables.

**Why**: Canonical data is FootballProStats' own model. Providers populate/verify it but should never contaminate it. The separation ensures provider changes (API-Football changes their schema) never require canonical entity changes.

### N.5 PostgreSQL Selected

**Decision**: PostgreSQL is the confirmed database technology.

**Why**: Strong relational support, JSONB for flexible metadata, full-text search (`tsvector`), excellent indexing, mature tooling (Alembic, SQLAlchemy, Prisma), wide deployment options, solo-developer-friendly. No need for Elasticsearch at this stage — `tsvector` handles search needs for the current data volume.

### N.6 Required vs Optional Field Classification

**Decision**: Every field is classified as required, nullable/optional, derived, or provider-dependent. All statistical, attendance, referee, height, foot, transfer fee, and advanced stat fields are nullable by default.

**Why**: Different providers supply different data. Making fields required when providers may not supply them causes import failures and data loss. The schema must survive incomplete provider data gracefully.

### N.7 Historical-First Design Confirmed

**Decision**: All entities are permanent records. No soft-deletes, no `is_current` flags, no time-based assumptions. Records are only corrected via immutable chains.

**Why**: API-Football could stop providing historical seasons at any time. FootballProStats must preserve all historical data independently. The schema supports querying "all standings in competition history" without date filters.

### N.8 Match Correction Strategy

**Decision**: Immutable match records with correction chains via `correction_of_id` FK + `match_corrections` log table.

**Why**: Finished matches should not be silently modified. Corrections create new records linked to the original, preserving the full history. No event sourcing complexity. Simple enough for a solo developer.

### N.9 Indexes and Constraints

**Decision**: Conceptual index and constraint plan documented in Section F covering all major query patterns (matches by date/team/competition/season, standings retrieval, external ID lookups, player history).

**Why**: Database performance planning must precede implementation. Key queries (home page match list, standings table, player profile) must be fast from day one.

### N.10 Import Architecture Verified

**Decision**: Schema supports all importer requirements: per-competition/season/date imports, resume via `records_processed`, dedup via `external_ids`, quota respect via rate limiting, source tracking via `data_sources` + `import_jobs`, partial import detection via status field.

**Why**: The importer is critical for building the historical database. The schema must support it before Phase D implementation begins.

---

## O. Phase B Ready Checklist

### Decided (Ready for Phase B)

- [x] **Database technology**: PostgreSQL confirmed
- [x] **All 18 entity tables designed** with field classifications
- [x] **Historical standings model**: `standing_snapshots` + `standing_rows`
- [x] **Player stats model**: `player_season_stats` supports multiple teams per season
- [x] **External ID strategy**: `external_ids` with per-entity FK columns
- [x] **Canonical vs provider separation**: Zero provider fields in canonical tables
- [x] **Required/optional/derived/provider-dependent classification**: All fields classified
- [x] **Historical-first design**: All entities permanent, no time assumptions
- [x] **Match correction strategy**: Immutable records + correction chains
- [x] **Indexes and constraints**: Conceptual plan for all major query patterns
- [x] **Import architecture**: Schema verified for incremental importer requirements
- [x] **Multi-provider architecture**: Adapter + normalization layers designed (Sections G, H)
- [x] **Frontend route architecture**: Routes designed (Section D)
- [x] **Backend API contracts**: Internal API endpoints designed (Section E)
- [x] **Data availability model**: available/partial/not_imported/coming_soon (Section K)
- [x] **Migration roadmap**: Phases A through H planned (Section L)

### Still Unresolved (Decide Before or During Phase B)

- [ ] Import concurrency model (sequential vs parallel per provider?)
- [ ] Standing snapshot granularity (per-matchday vs per-round?)
- [ ] Transfer data source identification
- [ ] Match correction UI design (how are corrections shown to users?)
- [ ] Search engine approach (PostgreSQL tsvector — confirmed default — vs Elasticsearch if bottleneck)
- [ ] Player identity deduplication strategy beyond external ID matching
- [ ] Database infrastructure setup (hosting, credentials, backup strategy)
- [ ] Whether to add `deleted_at` for soft-delete support in future phases

### Phase B Entry Criteria

To begin Phase B implementation, the following must be confirmed:
1. All section N decisions approved
2. All unresolved items either decided or deferred with explicit decisions
3. Database infrastructure provisioned
4. Alembic/migration tooling configured
5. PostgreSQL connection tested

---

## Summary

### 1. What I Inspected
- All 9 backend Python files (main, models, config, services, routes)
- All frontend app routes (home, matches, leagues, players, teams)
- All frontend lib files (types, api, constants, slug, mock-data, mock-matches, use-polling)
- All frontend components (LoadingSpinner, ErrorDisplay, EmptyState)
- All match detail sub-components (content, stats, lineups, ticker, event-icon)
- Existing database schema design in the architecture blueprint

### 2. Proposed Architecture
- External providers → Adapters → Normalization → DB (PostgreSQL) → Backend API → Frontend
- External provider models never become canonical models
- FootballProStats has its own data model independent of any provider
- Historical data from DB; live data from controlled provider polling
- Season availability model (available/partial/not_imported/coming_soon)
- All records permanent (historical-first); corrections via immutable chains

### 3. What Should Be Built First
- **Phase A** (architecture contracts) — documented in this blueprint ✅
- **Phase B** (database schema) — all decisions now made, ready to implement
- **Phase C** (provider abstraction) — refactor existing `football_api.py`/`mapper.py` into provider/normalization layers

### 4. What Should NOT Be Built Yet
- New API providers (Phase F — need single-provider foundation)
- Live polling backend (Phase G — need DB first)
- Importer (Phase D — needs DB + provider abstraction)
- Search engine beyond PostgreSQL (deferred)
- Transfers (no data source identified)
- New navbar redesign (deferred per scope rules)
- Frontend redesign (deferred until DB-backed data available)

### 5. Decisions Requiring Human Confirmation
1. Import concurrency model (sequential vs parallel?)
2. Standing snapshot granularity (per-matchday vs per-round?)
3. Transfer data source identification
4. Search engine choice (PostgreSQL full-text vs Elasticsearch?)
5. Match correction UI design
6. Whether to proceed to Phase B immediately
