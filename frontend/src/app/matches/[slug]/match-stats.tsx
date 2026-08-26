import type { MatchStats as MatchStatsType } from "@/lib/types";

export function MatchStats({ stats }: { stats: MatchStatsType }) {
  const bars: { label: string; home: number; away: number; suffix?: string }[] = [
    { label: "Possession", home: stats.possession[0], away: stats.possession[1], suffix: "%" },
    { label: "Shots", home: stats.shots[0], away: stats.shots[1] },
    { label: "On Target", home: stats.shots_on_target[0], away: stats.shots_on_target[1] },
    { label: "Corners", home: stats.corners[0], away: stats.corners[1] },
    { label: "Fouls", home: stats.fouls[0], away: stats.fouls[1] },
    { label: "Yellow Cards", home: stats.yellow_cards[0], away: stats.yellow_cards[1] },
    { label: "Red Cards", home: stats.red_cards[0], away: stats.red_cards[1] },
  ];

  return (
    <section className="mb-8">
      <h2 className="mb-4 text-xl font-bold">Match Statistics</h2>
      <div className="space-y-3">
        {bars.map((bar) => {
          const total = bar.home + bar.away;
          const homePct = total > 0 ? (bar.home / total) * 100 : 50;
          return (
            <div key={bar.label} className="grid grid-cols-[4rem_1fr_4rem] items-center gap-2">
              <span className="text-right font-mono text-sm font-semibold tabular-nums">
                {bar.home}{bar.suffix ?? ""}
              </span>
              <div>
                <div className="mb-0.5 text-center text-xs text-zinc-400">{bar.label}</div>
                <div className="flex h-2 overflow-hidden rounded-full bg-zinc-100">
                  <div
                    className="rounded-l-full bg-blue-500"
                    style={{ width: `${homePct}%` }}
                  />
                  <div
                    className="rounded-r-full bg-red-500"
                    style={{ width: `${100 - homePct}%` }}
                  />
                </div>
              </div>
              <span className="font-mono text-sm font-semibold tabular-nums">
                {bar.away}{bar.suffix ?? ""}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
