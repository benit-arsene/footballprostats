import sys
sys.path.insert(0, 'backend')
from dotenv import load_dotenv
load_dotenv('backend/.env')

from sqlalchemy import create_engine, text
from db.config import DATABASE_URL_SYNC

engine = create_engine(DATABASE_URL_SYNC)

# Test unique constraints
tests = [
    # (description, sql, should_fail)
    ("duplicate competition slug",
     "INSERT INTO competitions (name, slug, country) VALUES ('Test', 'premier-league', 'UK')", True),
    ("duplicate team slug",
     "INSERT INTO teams (name, slug) VALUES ('Test Team', 'test-team')", True),
    ("duplicate player slug",
     "INSERT INTO players (name, slug) VALUES ('Test Player', 'test-player')", True),
    ("duplicate match slug",
     "INSERT INTO matches (slug, date, home_team_id, away_team_id) VALUES ('test-match', '2024-01-01', 1, 2)", True),
    ("duplicate season (competition_id, label)",
     "INSERT INTO seasons (competition_id, label) VALUES (1, '2024/25')", True),
]

# Need to create test records first for FK references
# Insert a competition first
with engine.connect() as conn:
    conn.execute(text("""
        INSERT INTO competitions (name, slug, country) VALUES ('Test Comp', 'test-comp', 'UK')
    """))
    conn.execute(text("""
        INSERT INTO teams (name, slug) VALUES ('Test Team', 'test-team')
    """))
    conn.execute(text("""
        INSERT INTO players (name, slug) VALUES ('Test Player', 'test-player')
    """))
    conn.execute(text("""
        INSERT INTO seasons (competition_id, label) VALUES (1, '2024/25')
    """))
    conn.execute(text("""
        INSERT INTO referees (name) VALUES ('Test Ref')
    """))
    conn.execute(text("""
        INSERT INTO venues (name) VALUES ('Test Venue')
    """))
    conn.commit()

with engine.connect() as conn:
    for desc, sql, should_fail in tests:
        try:
            conn.execute(text(sql))
            conn.commit()
            result = "PASS (inserted)" if not should_fail else "FAIL (should have been rejected)"
        except Exception as e:
            conn.rollback()
            result = "PASS (rejected)" if should_fail else f"FAIL: {e}"
        print(f"{desc}: {result}")

engine.dispose()
