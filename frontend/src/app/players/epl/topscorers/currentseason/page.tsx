import { getLiveTopScorers } from "@/lib/api";

export default async function TopScorersPage() {
  let scorers: any[] = [];
  let lastUpdated = "";
  try {
    const data = await getLiveTopScorers();
    scorers = data.scorers || [];
    lastUpdated = data.last_updated;
  } catch {
    scorers = [];
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-3xl font-bold">Premier League Top Scorers</h1>
      {scorers.length === 0 ? (
        <p className="text-zinc-400">Top scorer data not available.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-zinc-400">
                <th className="pb-2 pr-2 font-medium">#</th>
                <th className="pb-2 pr-4 font-medium">Player</th>
                <th className="pb-2 pr-4 font-medium">Team</th>
                <th className="pb-2 pr-2 font-medium text-center">Goals</th>
                <th className="pb-2 font-medium text-center">Assists</th>
              </tr>
            </thead>
            <tbody>
              {scorers.map((s, i) => (
                <tr key={i} className="border-b border-zinc-100">
                  <td className="py-2.5 pr-2 tabular-nums text-zinc-400">{i + 1}</td>
                  <td className="py-2.5 pr-4 font-medium">{s.player?.name}</td>
                  <td className="py-2.5 pr-4 text-zinc-600">{s.team?.name}</td>
                  <td className="py-2.5 pr-2 text-center font-bold tabular-nums">{s.goals ?? "-"}</td>
                  <td className="py-2.5 text-center tabular-nums">{s.assists ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
