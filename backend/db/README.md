# FootballProStats Database

PostgreSQL database for FootballProStats — an independent football historical database.

## Requirements

- PostgreSQL 14+
- Python 3.11+
- See `../../requirements.txt` for Python dependencies (includes SQLAlchemy 2.x, Alembic, psycopg2-binary)

## Environment Variables

Copy `../../.env.example` to `../../.env` and set:

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/footballprostats
```

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `DB_POOL_SIZE` | 5 | Connection pool size |
| `DB_MAX_OVERFLOW` | 10 | Max overflow connections |
| `DB_POOL_RECYCLE` | 3600 | Recycle connections after N seconds |

## Database Setup

### 1. Create the database

```bash
createdb footballprostats
# or via psql:
psql -c "CREATE DATABASE footballprostats;"
```

### 2. Run migrations

The initial migration creates all 21 tables:

```bash
cd backend
alembic -c db/alembic.ini upgrade head
```

Or use the inline migration (for development without Alembic CLI setup):

```bash
cd backend
python -c "from db.models import Base; from db.session import engine; Base.metadata.create_all(engine)"
```

### 3. Reset development database

```bash
dropdb footballprostats
createdb footballprostats
cd backend
python -c "from db.models import Base; from db.session import engine; Base.metadata.create_all(engine)"
```

## Tables

| Table | Description |
|---|---|
| `competitions` | Football competitions (leagues, cups) |
| `seasons` | Competition seasons (2024/25, 2023/24, etc.) |
| `teams` | Football clubs |
| `venues` | Stadiums |
| `coaches` | Individual coaches |
| `team_coaches` | Historical coaching assignments |
| `players` | Footballers |
| `team_squad` | Historical squad membership per season |
| `referees` | Match referees |
| `matches` | Fixtures with scores and status |
| `match_events` | Goals, cards, substitutions |
| `match_lineups` | Players in match lineups |
| `match_statistics` | Possession, shots, corners, etc. |
| `standing_snapshots` | League table snapshots (per matchday, final) |
| `standing_rows` | Team positions within a snapshot |
| `transfers` | Player movements between teams |
| `player_season_stats` | Per-player, per-season, per-team stats |
| `data_sources` | External providers (API-Football, etc.) |
| `external_ids` | Provider ID → internal entity mappings |
| `import_jobs` | Import job tracking |
| `match_corrections` | Historical match corrections |

## Schema Design Principles

- **No provider-specific fields** in canonical tables (no `api_football_id` etc.)
- **Historical-first**: all records are permanent; corrections use immutable chains
- **External IDs** use per-entity FK columns (not polymorphic FKs)
- **All provider-dependent fields are nullable** (attendance, referee, height, foot, advanced stats, etc.)
- **Standings**: `standing_snapshots` (header) → `standing_rows` (data), supports multiple positions per team per season

## Configuration

Database configuration is in `db/config.py`, which reads from environment variables.

Connection settings:
- `DATABASE_URL` — connection string (required)
- `DB_POOL_SIZE` — default 5
- `DB_MAX_OVERFLOW` — default 10
- `DB_POOL_RECYCLE` — default 3600 seconds
