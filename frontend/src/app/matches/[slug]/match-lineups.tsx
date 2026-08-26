import type { LineupPlayer, TeamSummary } from "@/lib/types";

// Position row mapping for vertical pitch layout
// Row 0 = GK (top for home), Row 5 = ST (bottom for home)
const POSITION_ROWS: Record<string, number> = {
  GK: 0,
  CB: 1, LB: 1, RB: 1, SW: 1,
  CDM: 2, LDM: 2, RDM: 2,
  CM: 3, LCM: 3, RCM: 3, CAM: 3, LM: 3, RM: 3,
  LW: 4, RW: 4, LF: 4, RF: 4,
  ST: 5, CF: 5, SS: 5,
};

function groupByRow(lineup: LineupPlayer[]) {
  const rows = new Map<number, LineupPlayer[]>();
  for (const p of lineup) {
    const row = POSITION_ROWS[p.position.toUpperCase()] ?? 3;
    const list = rows.get(row) ?? [];
    list.push(p);
    rows.set(row, list);
  }
  return rows;
}

function getFormation(lineup: LineupPlayer[]): string {
  const rows = groupByRow(lineup);
  const counts = Array.from(rows.entries())
    .filter(([k]) => k > 0)
    .sort(([a], [b]) => a - b)
    .map(([, v]) => v.length);
  return counts.join("-") || "?";
}

function ratingColor(rating: number): string {
  if (rating >= 7.0) return "bg-green-500";
  if (rating >= 6.0) return "bg-yellow-500";
  if (rating >= 5.0) return "bg-orange-500";
  return "bg-red-500";
}

function PlayerNode({ player }: { player: LineupPlayer }) {
  const nameParts = player.player.name.split(" ");
  const initials = nameParts.length > 1
    ? `${nameParts[0][0]} ${nameParts[nameParts.length - 1][0]}`
    : nameParts[0][0];

  return (
    <div className="flex flex-col items-center gap-0.5">
      {/* Player avatar placeholder with initials */}
      <div className="relative">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-300 text-[10px] font-bold text-zinc-700 ring-2 ring-white/50">
          {initials}
        </div>
        {/* Rating badge */}
        {player.rating !== null && (
          <div className={`absolute -bottom-1 left-1/2 -translate-x-1/2 rounded px-1.5 py-px text-[9px] font-bold text-white shadow ${ratingColor(player.rating)}`}>
            {player.rating.toFixed(1)}
          </div>
        )}
      </div>
      {/* Name + number */}
      <span className="text-center text-[10px] leading-tight text-zinc-800">
        {player.shirt_number ?? ""} {player.player.name.split(" ").pop()}
      </span>
    </div>
  );
}

export function MatchLineups({
  homeLineup,
  awayLineup,
  homeTeam,
  awayTeam,
}: {
  homeLineup: LineupPlayer[];
  awayLineup: LineupPlayer[];
  homeTeam: TeamSummary;
  awayTeam: TeamSummary;
}) {
  if (homeLineup.length === 0 && awayLineup.length === 0) {
    return (
      <section className="mb-8">
        <div className="rounded-xl border border-zinc-200 p-6">
          <p className="text-sm text-zinc-400">Lineup not yet announced</p>
        </div>
      </section>
    );
  }

  const homeRows = groupByRow(homeLineup);
  const awayRows = groupByRow(awayLineup);
  // Home: GK at top (row 0) → ST at bottom (row 5)
  const homeRowKeys = Array.from(homeRows.keys()).sort((a, b) => a - b);
  // Away: ST at top (row 5) → GK at bottom (row 0) — flipped
  const awayRowKeys = Array.from(awayRows.keys()).sort((a, b) => b - a);

  return (
    <section className="mb-8">
      {/* Single vertical pitch */}
      <div className="relative overflow-hidden rounded-2xl bg-[#3d8b3d]">
        {/* Pitch markings */}
        <div className="absolute inset-4 rounded border border-white/15" />
        <div className="absolute left-1/2 top-4 bottom-4 w-px bg-white/15" />
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-16 w-16 rounded-full border border-white/15" />
        {/* Penalty areas */}
        <div className="absolute left-1/2 -translate-x-1/2 top-4 h-16 w-28 border border-white/15" />
        <div className="absolute left-1/2 -translate-x-1/2 bottom-4 h-16 w-28 border border-white/15" />

        <div className="relative px-4 py-6">
          {/* ── Home team (top half) ── */}
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {homeTeam.crest_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={homeTeam.crest_url} alt="" className="h-6 w-6" />
              ) : (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white/20 text-[8px] font-bold text-white">
                  {homeTeam.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()}
                </div>
              )}
              <span className="text-sm font-bold text-white drop-shadow">{homeTeam.name}</span>
            </div>
            <span className="rounded bg-white/20 px-2 py-0.5 text-[10px] font-bold text-white">
              {getFormation(homeLineup)}
            </span>
          </div>

          <div className="flex flex-col gap-5 pb-6">
            {homeRowKeys.map((rowKey) => {
              const players = homeRows.get(rowKey)!;
              return (
                <div key={rowKey} className="flex items-end justify-center gap-5">
                  {players.map((p) => (
                    <PlayerNode key={p.player.id} player={p} />
                  ))}
                </div>
              );
            })}
          </div>

          {/* ── Halfway line divider ── */}
          <div className="h-px bg-white/20" />

          {/* ── Away team (bottom half) ── */}
          <div className="mt-2 mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {awayTeam.crest_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={awayTeam.crest_url} alt="" className="h-6 w-6" />
              ) : (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white/20 text-[8px] font-bold text-white">
                  {awayTeam.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()}
                </div>
              )}
              <span className="text-sm font-bold text-white drop-shadow">{awayTeam.name}</span>
            </div>
            <span className="rounded bg-white/20 px-2 py-0.5 text-[10px] font-bold text-white">
              {getFormation(awayLineup)}
            </span>
          </div>

          <div className="flex flex-col gap-5">
            {awayRowKeys.map((rowKey) => {
              const players = awayRows.get(rowKey)!;
              return (
                <div key={rowKey} className="flex items-start justify-center gap-5">
                  {players.map((p) => (
                    <PlayerNode key={p.player.id} player={p} />
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
