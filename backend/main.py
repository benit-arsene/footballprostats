from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import matches, teams, players, leagues

app = FastAPI(title="Football Pro Stats API", version="0.1.0")

# Allow Next.js frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register versioned API routers ───────────────────────────────────
# All endpoints live under /api/v1/ for clean versioning.
# Each router defines its own sub-path:
#   /api/v1/matches/...
#   /api/v1/teams/...
#   /api/v1/players/...
#   /api/v1/leagues/...

app.include_router(matches.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(leagues.router)


@app.get("/")
def root():
    return {"message": "Football Pro Stats API"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
