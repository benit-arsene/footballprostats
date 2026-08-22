import type { LineupPlayer, TeamSummary } from "@/lib/types";

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
  return (
    <section className="mb-8">
      <h2 className="mb-4 text-xl font-bold">Lineups</h2>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <LineupColumn team={homeTeam} lineup={homeLineup} />
        <LineupColumn team={awayTeam} lineup={awayLineup} />
      </div>
    </section>
  );
}

function LineupColumn({
  team,
  lineup,
}: {
  team: TeamSummary;
  lineup: LineupPlayer[];
}) {
  return (
    <div className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="mb-3 flex items-center gap-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={team.crest_url} alt="" className="h-6 w-6" />
        <h3 className="font-semibold">{team.name}</h3>
      </div>
      {lineup.length === 0 ? (
        <p className="text-sm text-zinc-400">Lineup not yet announced</p>
      ) : (
        <ul className="space-y-1">
          {lineup.map((p) => (
            <li
              key={p.player.id}
              className="flex items-center justify-between text-sm"
            >
              <span>
                <span className="mr-1.5 font-mono text-xs text-zinc-400">
                  {p.shirt_number ?? "—"}
                </span>
                {p.player.name}
              </span>
              {p.rating !== null && (
                <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs font-semibold dark:bg-zinc-800">
                  {p.rating.toFixed(1)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
