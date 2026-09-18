import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

files = [
    "providers/base.py",
    "providers/registry.py",
    "providers/config.py",
    "providers/__init__.py",
    "providers/api_football/__init__.py",
    "providers/api_football/client.py",
    "providers/api_football/adapters.py",
    "providers/api_football/ids.py",
    "normalization/__init__.py",
    "normalization/matches.py",
    "normalization/teams.py",
    "normalization/players.py",
    "normalization/events.py",
    "normalization/competitions.py",
    "normalization/standings.py",
    "persistence/__init__.py",
    "persistence/repository.py",
    "services/football_api.py",
    "services/mapper.py",
    "main.py",
    "models.py",
    "config.py",
    "db/session.py",
    "db/config.py",
    "db/base.py",
    "db/models/__init__.py",
]

errors = []
for f in files:
    try:
        with open(f, "r") as fh:
            compile(fh.read(), f, "exec")
        print(f"OK: {f}")
    except SyntaxError as e:
        print(f"FAIL: {f}: {e}")
        errors.append(f)

if errors:
    print(f"\n{len(errors)} files have syntax errors")
    sys.exit(1)
else:
    print("\nAll files OK")
