import type { EventType } from "@/lib/types";

const iconMap: Record<EventType, string> = {
  goal: "G",
  own_goal: "OG",
  penalty_scored: "PK",
  penalty_missed: "PK!",
  yellow_card: "YC",
  red_card: "RC",
  second_yellow_card: "2Y",
  substitution: "SUB",
  var_decision: "VAR",
  kickoff: "KO",
  halftime: "HT",
  fulltime: "FT",
  extra_time_start: "ET",
  penalty_shootout: "PS",
};

const colorMap: Record<EventType, string> = {
  goal: "bg-green-600 text-white",
  own_goal: "bg-orange-500 text-white",
  penalty_scored: "bg-green-600 text-white",
  penalty_missed: "bg-red-500 text-white",
  yellow_card: "bg-yellow-400 text-black",
  red_card: "bg-red-600 text-white",
  second_yellow_card: "bg-red-600 text-white",
  substitution: "bg-blue-500 text-white",
  var_decision: "bg-purple-500 text-white",
  kickoff: "bg-zinc-600 text-white",
  halftime: "bg-zinc-500 text-white",
  fulltime: "bg-zinc-500 text-white",
  extra_time_start: "bg-zinc-500 text-white",
  penalty_shootout: "bg-indigo-500 text-white",
};

export function EventIcon({ type }: { type: EventType }) {
  return (
    <span
      className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${colorMap[type] ?? "bg-zinc-700 text-white"}`}
      aria-label={type.replace(/_/g, " ")}
    >
      {iconMap[type] ?? "•"}
    </span>
  );
}
