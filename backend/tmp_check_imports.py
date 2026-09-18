"""Import verification — check all modules can be imported."""
import sys
import os
import importlib

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

modules = [
    ("providers", None),
    ("providers.base", None),
    ("providers.registry", None),
    ("providers.config", None),
    ("providers.api_football", None),
    ("providers.api_football.client", None),
    ("providers.api_football.adapters", None),
    ("providers.api_football.ids", None),
    ("normalization", None),
    ("normalization.matches", None),
    ("normalization.teams", None),
    ("normalization.players", None),
    ("normalization.events", None),
    ("normalization.competitions", None),
    ("normalization.standings", None),
    ("persistence", None),
    ("persistence.repository", None),
    ("services", None),
    ("services.football_api", None),
    ("services.mapper", None),
]

errors = []
for mod_name, _ in modules:
    try:
        importlib.import_module(mod_name)
        print(f"OK: {mod_name}")
    except Exception as e:
        print(f"FAIL: {mod_name}: {e}")
        errors.append(f"{mod_name}: {e}")

if errors:
    print(f"\n{len(errors)} import errors")
    sys.exit(1)
else:
    print("\nAll imports OK")
