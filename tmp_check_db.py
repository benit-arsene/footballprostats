import os, sys
sys.path.insert(0, 'backend')
from dotenv import load_dotenv
load_dotenv('backend/.env')

from sqlalchemy import create_engine, inspect, text
from db.config import DATABASE_URL_SYNC

engine = create_engine(DATABASE_URL_SYNC)
inspector = inspect(engine)
tables = sorted(inspector.get_table_names())
print('All tables in DB:')
for t in tables:
    print(f"  {t}")
print(f"\nTotal: {len(tables)}")

# Check alembic version
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version_num FROM alembic_version'))
        for row in result:
            print(f"\nAlembic version: {row[0]}")
except Exception as e:
    print(f"\nAlembic version check failed: {e}")

engine.dispose()
