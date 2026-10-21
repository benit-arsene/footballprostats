"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import type { MatchSummary } from "@/lib/types";

// ─── Incoming row shape ───────────────────────────────────────────────
// Accepts both the live football-data rows and the cached snapshot shape.

export type ScorerInput = {
  player?: {
    id?: number | null;
    name?: string | null;
    position?: string | null;
    section?: string | null;
    nationality?: string | null;
    shirt_number?: number | null;
    number?: number | null;
  } | null;
  team?: {
    name?: string | null;
    short_name?: string | null;
    tla?: string | null;
    crest_url?: string | null;
  } | null;
  goals?: number | null;
  assists?: number | null;
  penalties?: number | null;
  played_matches?: number | null;
};

type Props = {
  scorers: ScorerInput[];
  season?: string | null;
  currentMatchday?: number | null;
  scorersCount?: number | null;
  goalsTotal?: number | null;
  highlights?: MatchSummary[];
  feed?: "live" | "snapshot";
};

// ─── View model ──────────────────────────────────────────────────────

type PositionGroup = "offence" | "midfield" | "defence";

type ScorerRow = {
  id: string;
  rank: number;
  name: string;
  initials: string;
  club: string;
  clubCode: string;
  nation: string;
  nationCode: string;
  position: string;
  positionCode: string;
  positionGroup: PositionGroup | null;
  shirtNumber: number | null;
  goals: number;
  assists: number;
  ga: number;
  apps: number | null;
  penalties: number;
  goalsPerApp: number | null;
};

const DASH = "—";
const EN_DASH = "–";
const PAGE_SIZES = [10, 25, 50, 100];

// ─── Identity helpers ────────────────────────────────────────────────

const NATION_CODES: Record<string, string> = {
  england: "ENG",
  scotland: "SCO",
  wales: "WAL",
  "northern ireland": "NIR",
  ireland: "IRL",
  "republic of ireland": "IRL",
  norway: "NOR",
  sweden: "SWE",
  denmark: "DEN",
  finland: "FIN",
  iceland: "ISL",
  netherlands: "NED",
  holland: "NED",
  belgium: "BEL",
  germany: "GER",
  france: "FRA",
  spain: "ESP",
  portugal: "POR",
  italy: "ITA",
  switzerland: "SUI",
  austria: "AUT",
  poland: "POL",
  czechia: "CZE",
  "czech republic": "CZE",
  croatia: "CRO",
  serbia: "SRB",
  slovenia: "SVN",
  slovakia: "SVK",
  hungary: "HUN",
  romania: "ROU",
  bulgaria: "BUL",
  greece: "GRE",
  turkey: "TUR",
  ukraine: "UKR",
  russia: "RUS",
  georgia: "GEO",
  albania: "ALB",
  "north macedonia": "MKD",
  "bosnia and herzegovina": "BIH",
  montenegro: "MNE",
  kosovo: "KVX",
  armenia: "ARM",
  azerbaijan: "AZE",
  kazakhstan: "KAZ",
  uzbekistan: "UZB",
  israel: "ISR",
  brazil: "BRA",
  argentina: "ARG",
  uruguay: "URU",
  colombia: "COL",
  chile: "CHI",
  peru: "PER",
  ecuador: "ECU",
  paraguay: "PAR",
  venezuela: "VEN",
  bolivia: "BOL",
  mexico: "MEX",
  "united states": "USA",
  usa: "USA",
  canada: "CAN",
  jamaica: "JAM",
  "trinidad and tobago": "TRI",
  nigeria: "NGA",
  ghana: "GHA",
  senegal: "SEN",
  "ivory coast": "CIV",
  "cote divoire": "CIV",
  cameroon: "CMR",
  morocco: "MAR",
  algeria: "ALG",
  tunisia: "TUN",
  egypt: "EGY",
  mali: "MLI",
  "burkina faso": "BFA",
  guinea: "GUI",
  "dr congo": "COD",
  "south africa": "RSA",
  kenya: "KEN",
  japan: "JPN",
  "south korea": "KOR",
  australia: "AUS",
  "new zealand": "NZL",
  iran: "IRN",
  iraq: "IRQ",
  "saudi arabia": "KSA",
  qatar: "QAT",
  china: "CHN",
};

/** Diacritic-insensitive lookup key. */
function key(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function nationCode(nationality?: string | null): string {
  if (!nationality) return DASH;
  const cleaned = nationality.trim();
  return NATION_CODES[key(cleaned)] ?? (cleaned.replace(/[^a-zA-Z]/g, "").slice(0, 3).toUpperCase() || DASH);
}

function initials(name: string): string {
  const parts = name.replace(/\./g, " ").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "??";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

const CLUB_CODES: Array<[RegExp, string]> = [
  [/man(?:chester)?\s*(?:city|cty)/i, "MCI"],
  [/man(?:chester)?\s*(?:united|utd)/i, "MUN"],
  [/newcastle/i, "NEW"],
  [/nottingham|forest/i, "NFO"],
  [/tottenham|spurs/i, "TOT"],
  [/west ham/i, "WHU"],
  [/crystal palace/i, "CRY"],
  [/brighton/i, "BHA"],
  [/bournemouth/i, "BOU"],
  [/brentford/i, "BRE"],
  [/aston villa/i, "AVL"],
  [/wolverhampton|wolves/i, "WOL"],
  [/arsenal/i, "ARS"],
  [/chelsea/i, "CHE"],
  [/everton/i, "EVE"],
  [/fulham/i, "FUL"],
  [/ipswich/i, "IPS"],
  [/leicester/i, "LEI"],
  [/liverpool/i, "LIV"],
  [/southampton/i, "SOU"],
  [/real madrid/i, "RMA"],
  [/barcelona/i, "BAR"],
  [/bayern/i, "FCB"],
  [/dortmund/i, "BVB"],
  [/juventus/i, "JUV"],
  [/napoli/i, "NAP"],
  [/ac milan/i, "MIL"],
  [/inter/i, "INT"],
  [/paris saint|psg/i, "PSG"],
];

function clubCode(team?: ScorerInput["team"]): string {
  const tla = team?.tla?.trim();
  if (tla) return tla.toUpperCase();

  const name = team?.name?.trim() ?? "";
  for (const [pattern, code] of CLUB_CODES) {
    if (pattern.test(name)) return code;
  }

  const shortName = team?.short_name?.trim();
  if (shortName) return shortName.replace(/[^a-zA-Z]/g, "").slice(0, 3).toUpperCase();

  const letters = name
    .replace(/\b(fc|afc|cf|sc|club|the)\b/gi, "")
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word[0])
    .join("");
  return letters.slice(0, 3).toUpperCase() || DASH;
}

const POSITION_CODES: Array<[RegExp, string]> = [
  [/goalkeeper|\bkeeper\b|\bgk\b/i, "GK"],
  [/right[- ]wing/i, "RW"],
  [/left[- ]wing/i, "LW"],
  [/wing/i, "W"],
  [/second striker/i, "SS"],
  [/attacking mid/i, "CAM"],
  [/defensive mid/i, "DM"],
  [/central mid|centre mid|midfield/i, "CM"],
  [/right[- ]back/i, "RB"],
  [/left[- ]back/i, "LB"],
  [/centre[- ]back|center[- ]back|defender/i, "CB"],
  [/striker|forward/i, "CF"],
];

function groupFromText(text: string): PositionGroup | null {
  const value = text.toLowerCase();
  if (/wing|forward|striker|offen|attack/.test(value)) return "offence";
  if (/midfield|mid\b/.test(value)) return "midfield";
  if (/defen|back|keeper/.test(value)) return "defence";
  return null;
}

/** Coarse group taken straight from the provider's `section` value. */
function groupFromSection(section: string): PositionGroup | null {
  const value = section.toLowerCase();
  if (value.startsWith("off")) return "offence";
  if (value.startsWith("mid")) return "midfield";
  if (value.startsWith("def")) return "defence";
  return null;
}

function positionOf(player?: ScorerInput["player"]): {
  label: string;
  code: string;
  group: PositionGroup | null;
} {
  // The provider publishes a coarse section (Offence / Midfield / Defence) and a
  // fine-grained position that is currently null. A section never implies a
  // specific role, so it is shown as the section itself — never as FW/MF/DF.
  const position = player?.position?.trim();
  const section = player?.section?.trim();

  if (position) {
    const code =
      POSITION_CODES.find(([pattern]) => pattern.test(position))?.[1] ??
      position
        .split(/\s+/)
        .map((word) => word[0])
        .join("")
        .slice(0, 3)
        .toUpperCase();
    return {
      label: position,
      code,
      group: groupFromText(position) ?? (section ? groupFromSection(section) : null),
    };
  }

  if (section) {
    return { label: section, code: section, group: groupFromSection(section) };
  }

  return { label: DASH, code: DASH, group: null };
}

// ─── Formatting helpers ──────────────────────────────────────────────

function formatSeason(value?: string | null): string {
  if (!value) return "Current Season";
  const match = value.match(/^(\d{4})\s*\/\s*(\d{2,4})$/);
  if (!match) return value;
  return `${match[1]}/${match[2].slice(-2)}`;
}

function Dash() {
  return <span className="text-secondary">{DASH}</span>;
}

// ─── Normalisation ───────────────────────────────────────────────────

function buildRows(scorers: ScorerInput[]): ScorerRow[] {
  const rows: ScorerRow[] = [];

  scorers.forEach((scorer, index) => {
    const name = scorer.player?.name?.trim();
    if (!name) return;

    const position = positionOf(scorer.player);
    // football-data.org only publishes assists and penalties for players who
    // have them, so a missing value means none — it is read as zero here.
    const assists = typeof scorer.assists === "number" ? scorer.assists : 0;
    const penalties = typeof scorer.penalties === "number" ? scorer.penalties : 0;
    const goals = scorer.goals ?? 0;
    const apps = typeof scorer.played_matches === "number" ? scorer.played_matches : null;

    rows.push({
      id: `${scorer.player?.id ?? name}-${index}`,
      rank: 0,
      name,
      initials: initials(name),
      club: scorer.team?.name?.trim() || "Unknown club",
      clubCode: clubCode(scorer.team),
      nation: scorer.player?.nationality?.trim() || "Unknown",
      nationCode: nationCode(scorer.player?.nationality),
      position: position.label,
      positionCode: position.code,
      positionGroup: position.group,
      shirtNumber: scorer.player?.shirt_number ?? scorer.player?.number ?? null,
      goals,
      assists,
      ga: goals + assists,
      apps,
      penalties,
      goalsPerApp: apps !== null && apps > 0 ? goals / apps : null,
    });
  });

  rows.sort((a, b) => {
    if (b.goals !== a.goals) return b.goals - a.goals;
    if (b.assists !== a.assists) return b.assists - a.assists;
    return a.name.localeCompare(b.name);
  });

  return rows.map((row, index) => ({ ...row, rank: index + 1 }));
}

// ─── Table model ─────────────────────────────────────────────────────

type ColumnKey =
  | "apps"
  | "goals"
  | "assists"
  | "ga"
  | "penalties"
  | "goalsPerApp";

type SortKey = "player" | "club" | ColumnKey;

type SortDir = "asc" | "desc";

const COLUMNS: Array<{
  key: ColumnKey;
  label: string;
  minWidth: string;
  padding: string;
  headExtra?: string;
}> = [
  { key: "apps", label: "Apps", minWidth: "min-w-[70px]", padding: "px-space-sm" },
  {
    key: "goals",
    label: "Goals",
    minWidth: "min-w-[85px]",
    padding: "px-space-md",
    headExtra: "bg-surface-container font-extrabold text-primary",
  },
  { key: "assists", label: "Ast", minWidth: "min-w-[60px]", padding: "px-space-sm" },
  { key: "ga", label: "G+A", minWidth: "min-w-[60px]", padding: "px-space-sm" },
  { key: "penalties", label: "Pen", minWidth: "min-w-[60px]", padding: "px-space-sm" },
  { key: "goalsPerApp", label: "Goals / App", minWidth: "min-w-[105px]", padding: "px-space-md" },
];

const ALL_COLUMNS_VISIBLE: Record<ColumnKey, boolean> = {
  apps: true,
  goals: true,
  assists: true,
  ga: true,
  penalties: true,
  goalsPerApp: true,
};

/** Opening view keeps the table scannable: only the scoring columns. */
const DEFAULT_COLUMNS_VISIBLE: Record<ColumnKey, boolean> = {
  apps: false,
  goals: true,
  assists: true,
  ga: true,
  penalties: false,
  goalsPerApp: false,
};

function sortValue(row: ScorerRow, sortKey: SortKey): number | string | null {
  switch (sortKey) {
    case "player":
      return row.name;
    case "club":
      return row.club;
    case "apps":
      return row.apps;
    case "goals":
      return row.goals;
    case "assists":
      return row.assists;
    case "ga":
      return row.ga;
    case "penalties":
      return row.penalties;
    case "goalsPerApp":
      return row.goalsPerApp;
  }
}

function pageWindow(current: number, total: number): Array<number | "ellipsis"> {
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, "ellipsis", total];
  if (current >= total - 3) return [1, "ellipsis", total - 4, total - 3, total - 2, total - 1, total];
  return [1, "ellipsis", current - 1, current, current + 1, "ellipsis", total];
}

// ─── Small presentational pieces ─────────────────────────────────────

function SortHeader({
  label,
  icon,
  active,
  align = "end",
  onClick,
}: {
  label: string;
  icon: string | null;
  active: boolean;
  align?: "start" | "center" | "end";
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full cursor-pointer items-center gap-1 uppercase transition-colors ${
        align === "end" ? "justify-end" : align === "center" ? "justify-center" : ""
      } ${active ? "text-primary" : "hover:text-primary"}`}
    >
      <span>{label}</span>
      {icon ? (
        <span className="material-symbols-outlined text-[13px]" aria-hidden="true">
          {icon}
        </span>
      ) : null}
    </button>
  );
}

function SpotlightMetric({
  label,
  value,
  note,
}: {
  label: string;
  value: string | number;
  note: string;
}) {
  return (
    <div className="flex flex-col rounded-chip bg-surface-container-highest/20 p-space-sm">
      <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-primary-container">
        {label}
      </span>
      <div className="mt-0.5 flex items-baseline gap-1">
        <span className="font-stat-display text-headline-md text-on-primary">{value}</span>
      </div>
      <span className="font-body-sm text-body-sm text-on-primary-container">{note}</span>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between font-stat-tabular text-body-sm">
      <span className="font-label-sm text-label-sm uppercase text-secondary">{label}</span>
      <span className="font-bold text-primary">{value}</span>
    </div>
  );
}

// ─── Component ───────────────────────────────────────────────────────

export default function TopScorersTable({
  scorers,
  season,
  currentMatchday = null,
  scorersCount = null,
  goalsTotal = null,
  highlights = [],
  feed = "live",
}: Props) {
  const rows = useMemo(() => buildRows(scorers), [scorers]);

  const [query, setQuery] = useState("");
  const [club, setClub] = useState("");
  const [nation, setNation] = useState("");
  const [positionGroup, setPositionGroup] = useState<"" | PositionGroup>("");
  const [minApps, setMinApps] = useState(0);
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: "goals", dir: "desc" });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [visibleColumns, setVisibleColumns] = useState<Record<ColumnKey, boolean>>({
    ...DEFAULT_COLUMNS_VISIBLE,
  });
  const [columnsOpen, setColumnsOpen] = useState(false);
  const columnsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!columnsOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (!columnsRef.current?.contains(event.target as Node)) setColumnsOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setColumnsOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [columnsOpen]);

  const clubs = useMemo(
    () => Array.from(new Set(rows.map((row) => row.club))).sort((a, b) => a.localeCompare(b)),
    [rows],
  );

  const nations = useMemo(() => {
    const map = new Map<string, string>();
    rows.forEach((row) => {
      if (row.nationCode !== DASH) map.set(row.nationCode, row.nation);
    });
    return Array.from(map, ([code, name]) => ({ code, name })).sort((a, b) =>
      a.name.localeCompare(b.name),
    );
  }, [rows]);

  const maxApps = useMemo(
    () => rows.reduce((max, row) => Math.max(max, row.apps ?? 0), 0),
    [rows],
  );

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows.filter((row) => {
      if (club && row.club !== club) return false;
      if (nation && row.nationCode !== nation) return false;
      if (positionGroup && row.positionGroup !== positionGroup) return false;
      if (minApps > 0 && (row.apps ?? 0) < minApps) return false;
      if (needle) {
        const haystack = `${row.name} ${row.club} ${row.nation} ${row.position}`.toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      return true;
    });
  }, [rows, query, club, nation, positionGroup, minApps]);

  const sorted = useMemo(() => {
    const tiebreak = (a: ScorerRow, b: ScorerRow) => {
      if (b.goals !== a.goals) return b.goals - a.goals;
      if (b.assists !== a.assists) return b.assists - a.assists;
      return a.name.localeCompare(b.name);
    };

    return [...filtered].sort((a, b) => {
      const left = sortValue(a, sort.key);
      const right = sortValue(b, sort.key);
      if (left === null && right === null) return tiebreak(a, b);
      if (left === null) return 1;
      if (right === null) return -1;
      const comparison =
        typeof left === "string" ? left.localeCompare(right as string) : left - (right as number);
      if (comparison !== 0) return sort.dir === "asc" ? comparison : -comparison;
      return tiebreak(a, b);
    });
  }, [filtered, sort]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const pageRows = sorted.slice(startIndex, startIndex + pageSize);
  const rangeStart = sorted.length === 0 ? 0 : startIndex + 1;
  const rangeEnd = Math.min(startIndex + pageSize, sorted.length);

  const visibleColumnList = COLUMNS.filter((column) => visibleColumns[column.key]);
  const columnCount = 3 + visibleColumnList.length;
  const columnSpan = columnCount;

  const leader = rows[0] ?? null;
  const runnersUp = rows.slice(1, 3);

  const seasonValue = formatSeason(season);
  const matchdayValue = currentMatchday === null ? DASH : currentMatchday;
  const scorerCountValue = scorersCount === null ? DASH : scorersCount;

  // Factual season summary — every figure comes from the provider payload.
  const seasonNote = (() => {
    const parts: string[] = [];
    if (goalsTotal !== null) parts.push(`${goalsTotal} goals recorded`);
    if (scorersCount !== null) parts.push(`across ${scorersCount} scorers`);
    if (currentMatchday !== null) parts.push(`through matchday ${currentMatchday}`);
    if (parts.length === 0) return "Awaiting the first matchday of the season.";
    return `${parts.join(" ")}.`;
  })();

  const highlightCards = useMemo(
    () =>
      highlights
        .filter(
          (match) =>
            match.league?.name === "Premier League" &&
            (match.status === "live" || match.status === "finished"),
        )
        .slice(0, 4)
        .map((match) => ({
          id: match.id,
          score: `${clubCode({ name: match.home_team.name })} ${match.home_score ?? 0}${EN_DASH}${
            match.away_score ?? 0
          } ${clubCode({ name: match.away_team.name })}`,
          detail: match.status === "live" ? `${match.minute ?? 0}' Live` : "Full time",
        })),
    [highlights],
  );

  function toggleSort(nextKey: SortKey) {
    setSort((previous) =>
      previous.key === nextKey
        ? { key: nextKey, dir: previous.dir === "desc" ? "asc" : "desc" }
        : {
            key: nextKey,
            dir: nextKey === "player" || nextKey === "club" ? "asc" : "desc",
          },
    );
    setPage(1);
  }

  function resetFilters() {
    setQuery("");
    setClub("");
    setNation("");
    setPositionGroup("");
    setMinApps(0);
    setPage(1);
  }

  function sortIcon(sortKey: SortKey): string | null {
    if (sort.key === sortKey) return sort.dir === "desc" ? "arrow_downward" : "arrow_upward";
    if (sortKey === "player" || sortKey === "club") return "unfold_more";
    return null;
  }

  function retheme(key: SortKey): "ascending" | "descending" | "none" {
    if (sort.key !== key) return "none";
    return sort.dir === "asc" ? "ascending" : "descending";
  }

  return (
    <div className="flex w-full flex-col">
      {/* ─── Matchweek context bar ─────────────────────────────────── */}
      <section className="w-full bg-surface-container-low py-space-xs shadow-sm">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-margin-desktop md:px-margin-wide">
          <div className="flex items-center gap-space-lg overflow-x-auto py-1 text-nowrap">
            <span className="flex items-center gap-1 font-label-sm text-label-sm uppercase tracking-widest text-secondary">
              <span className="material-symbols-outlined text-[13px] text-primary" aria-hidden="true">
                schedule
              </span>
              Matchday Highlights
            </span>
            <div className="flex items-center gap-space-sm pl-space-sm">
              {highlightCards.map((card, index) => (
                <div
                  key={card.id}
                  className={`${
                    index === 3 ? "hidden xl:flex" : "flex"
                  } items-center gap-1.5 rounded-chip bg-surface-container-lowest px-2 py-0.5 shadow-sm`}
                >
                  <span className="font-label-sm text-label-sm font-bold uppercase text-primary">
                    {card.score}
                  </span>
                  <span className="font-body-sm text-body-sm text-secondary">{card.detail}</span>
                </div>
              ))}
              {highlightCards.length === 0 ? (
                <span className="font-body-sm text-body-sm text-secondary">
                  No fixtures in the live window.
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </section>

      {/* ─── Analytical canvas ─────────────────────────────────────── */}
        <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-space-lg px-margin-desktop py-space-lg md:px-margin-wide">
        {/* Breadcrumb + feed status */}
        <div className="flex flex-wrap items-center justify-between gap-space-sm">
          <nav
            aria-label="Breadcrumb"
            className="flex items-center gap-space-xs font-label-md text-label-md uppercase tracking-wider text-secondary"
          >
            <Link href="/" className="transition-colors hover:text-primary">
              Home
            </Link>
            <span className="material-symbols-outlined text-[13px] text-outline" aria-hidden="true">
              chevron_right
            </span>
            <Link href="/standings" className="transition-colors hover:text-primary">
              EPL
            </Link>
            <span className="material-symbols-outlined text-[13px] text-outline" aria-hidden="true">
              chevron_right
            </span>
            <Link
              href="/players/epl/topscorers/currentseason"
              className="transition-colors hover:text-primary"
            >
              Player Stats
            </Link>
            <span className="material-symbols-outlined text-[13px] text-outline" aria-hidden="true">
              chevron_right
            </span>
            <span className="font-bold text-primary">Current Season</span>
          </nav>
          <div className="flex items-center gap-space-xs">
            <div className="flex items-center gap-1 rounded-chip bg-surface-container-lowest px-space-sm py-1 shadow-sm">
              <span
                aria-hidden="true"
                className={`h-2 w-2 rounded-pill ${
                  feed === "live" ? "animate-ping bg-primary" : "bg-outline"
                }`}
              />
              <span className="font-label-sm text-label-sm font-bold uppercase tracking-widest text-primary">
                {feed === "live" ? "Verified Data Feed" : "Cached Snapshot"}
              </span>
            </div>
            <div className="rounded-chip bg-surface-container px-space-sm py-1 font-label-sm text-label-sm uppercase text-secondary">
              {seasonValue} • Cumulative
            </div>
          </div>
        </div>

        {/* Editorial header */}
        <header className="flex flex-col justify-between gap-space-lg py-space-sm lg:flex-row lg:items-end">
          <div className="flex max-w-[768px] flex-col gap-space-xs">
            <h1 className="font-headline-xl text-headline-xl uppercase tracking-tight text-primary">
              Premier League Top Scorers
            </h1>
            <p className="font-body-lg text-body-lg text-secondary">
              Official Premier League scoring records — goals, appearances, assists and penalties
              as published by the official football-data.org feed for every recorded goalscorer.
            </p>
          </div>

          {/* Quick export and configuration toolset */}
          <div className="flex items-center gap-space-xs self-start lg:self-auto">
            <div className="relative" ref={columnsRef}>
              <button
                type="button"
                aria-expanded={columnsOpen}
                aria-haspopup="dialog"
                onClick={() => setColumnsOpen((open) => !open)}
                className="flex h-8 items-center gap-1.5 rounded-chip bg-surface-container-lowest px-space-md font-label-md text-label-md uppercase tracking-wider text-primary shadow-sm transition-colors hover:bg-surface-container-low"
              >
                <span className="material-symbols-outlined text-[15px]" aria-hidden="true">
                  tune
                </span>
                <span>Columns ({columnCount})</span>
              </button>
              {columnsOpen ? (
                <div
                  role="dialog"
                  aria-label="Visible columns"
                  className="absolute right-0 top-full z-40 mt-2 w-[248px] rounded-card border border-outline-variant bg-surface-container-lowest p-space-md shadow-lg"
                >
                  <div className="flex items-center justify-between pb-space-sm">
                    <span className="font-label-sm text-label-sm uppercase tracking-widest text-secondary">
                      Visible Columns
                    </span>
                    <button
                      type="button"
                      onClick={() => setVisibleColumns({ ...ALL_COLUMNS_VISIBLE })}
                      className="font-label-sm text-label-sm font-bold uppercase text-primary transition-colors hover:text-secondary"
                    >
                      All
                    </button>
                  </div>
                  <div className="grid grid-cols-1 gap-0.5">
                    {COLUMNS.map((column) => (
                      <label
                        key={column.key}
                        className="flex cursor-pointer items-center gap-space-sm rounded-chip px-1 py-1 transition-colors hover:bg-surface-container-low"
                      >
                        <input
                          type="checkbox"
                          checked={visibleColumns[column.key]}
                          onChange={() =>
                            setVisibleColumns((current) => ({
                              ...current,
                              [column.key]: !current[column.key],
                            }))
                          }
                          className="h-3 w-3 accent-primary"
                        />
                        <span className="font-label-md text-label-md uppercase tracking-wider text-on-surface">
                          {column.label}
                        </span>
                      </label>
                    ))}
                  </div>
                  <p className="pt-space-sm font-body-sm text-body-sm text-secondary">
                    Rank, player and club stay pinned.
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        {/* ─── Podium / leaders spotlight ───────────────────────────── */}
        <section className="grid grid-cols-1 gap-space-md md:grid-cols-12">
          {leader ? (
            <article className="relative flex flex-col justify-between overflow-hidden rounded-card bg-primary p-space-lg text-on-primary shadow-md md:col-span-12 lg:col-span-6">
              <div className="pointer-events-none absolute -right-10 -bottom-10 select-none opacity-10">
                <span className="text-[240px] font-extrabold leading-none tracking-tighter">01</span>
              </div>

              <div className="relative z-10 flex flex-col gap-space-md">
                <div className="flex flex-wrap items-center justify-between gap-space-sm">
                  <div className="flex items-center gap-space-xs">
                    <span className="flex items-center gap-1 rounded-chip bg-surface-container-lowest px-space-sm py-1 font-label-sm text-label-sm font-extrabold uppercase tracking-widest text-primary">
                      <span
                        className="material-symbols-outlined text-[13px] text-primary"
                        aria-hidden="true"
                      >
                        military_tech
                      </span>
                      Golden Boot Leader
                    </span>
                    <span className="rounded-chip bg-surface-container-highest/20 px-space-xs py-1 font-label-sm text-label-sm uppercase text-on-primary">
                      Rank 01
                    </span>
                  </div>
                  <div className="flex items-center gap-space-xs font-label-sm text-label-sm uppercase tracking-widest text-on-primary-container">
                    <span>{leader.club}</span>
                    <span className="h-1.5 w-1.5 rounded-pill bg-surface-container-lowest" aria-hidden="true" />
                    <span>{leader.nationCode}</span>
                  </div>
                </div>

                <div className="flex flex-col items-start justify-between gap-space-md pt-space-xs sm:flex-row sm:items-center">
                  <div className="flex items-center gap-space-md">
                    <div className="flex h-16 w-16 items-center justify-center rounded-card bg-surface-container-lowest font-headline-lg text-headline-lg font-extrabold text-primary shadow-sm">
                      {leader.initials}
                    </div>
                    <div className="flex flex-col">
                      <h2 className="font-headline-lg text-headline-lg uppercase tracking-tight text-on-primary">
                        {leader.name}
                      </h2>
                      <div className="flex flex-wrap items-center gap-space-xs font-label-md text-label-md uppercase text-on-primary-container">
                        <span>
                          {leader.position}
                          {leader.shirtNumber !== null ? ` (#${leader.shirtNumber})` : ""}
                        </span>
                        <span aria-hidden="true">•</span>
                        <span>{leader.apps !== null ? `${leader.apps} Apps` : `Apps ${DASH}`}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-baseline justify-center gap-2 self-stretch rounded-card bg-surface-container-highest/25 px-space-lg py-space-xs shadow-[inset_0_2px_4px_rgba(0,0,0,0.06)] sm:self-auto">
                    <span className="font-stat-display text-[46px] font-extrabold leading-none text-on-primary">
                      {leader.goals}
                    </span>
                    <div className="flex flex-col">
                      <span className="font-label-sm text-label-sm uppercase tracking-widest text-on-primary">
                        Goals
                      </span>
                      <span className="font-label-sm text-label-sm text-on-primary-container">
                        {leader.apps && leader.apps > 0
                          ? `${(leader.goals / leader.apps).toFixed(2)} / APP`
                          : `${DASH} / APP`}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Metric cluster */}
              <div className="relative z-10 grid grid-cols-2 gap-space-sm pt-space-lg sm:grid-cols-4">
                <SpotlightMetric
                  label="Appearances"
                  value={leader.apps === null ? DASH : leader.apps}
                  note={leader.apps === null ? "Not reported" : "Matches played"}
                />
                <SpotlightMetric
                  label="Assists"
                  value={leader.assists}
                  note="Assists recorded"
                />
                <SpotlightMetric
                  label="Penalties"
                  value={leader.penalties}
                  note="Penalty goals"
                />
                <SpotlightMetric
                  label="Goals / App"
                  value={leader.goalsPerApp === null ? DASH : leader.goalsPerApp.toFixed(2)}
                  note={leader.goalsPerApp === null ? "Needs appearances" : "Goals per appearance"}
                />
              </div>
            </article>
          ) : (
            <article className="flex flex-col items-center justify-center gap-space-sm rounded-card bg-surface-container-lowest p-space-xl text-center shadow-sm md:col-span-12">
              <span className="material-symbols-outlined text-[24px] text-secondary" aria-hidden="true">
                emoji_events
              </span>
              <p className="font-headline-md text-headline-md uppercase tracking-tight text-primary">
                Leaderboard warming up
              </p>
              <p className="font-body-md text-body-md text-secondary">
                Goalscorers appear here as soon as the live feed reports them.
              </p>
            </article>
          )}

          {runnersUp.map((player, index) => (
            <article
              key={player.id}
              className="flex flex-col justify-between rounded-card bg-surface-container-lowest p-space-md shadow-sm md:col-span-6 lg:col-span-3"
            >
              <div className="flex flex-col gap-space-sm">
                <div className="flex items-center justify-between gap-space-sm">
                  <span className="rounded-chip bg-surface-container-high px-space-xs py-0.5 font-label-sm text-label-sm font-bold uppercase tracking-widest text-primary">
                    Rank {String(player.rank).padStart(2, "0")}
                  </span>
                  <div className="flex min-w-0 items-center gap-1 font-label-sm text-label-sm uppercase text-secondary">
                    <span>{player.nationCode}</span>
                    <span className="h-1 w-1 shrink-0 rounded-pill bg-outline" aria-hidden="true" />
                    <span className="truncate">{player.club}</span>
                  </div>
                </div>

                <div className="mt-space-xs flex items-center gap-space-sm">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-card bg-surface-container font-headline-md text-headline-md font-bold text-primary">
                    {player.initials}
                  </div>
                  <div className="flex min-w-0 flex-col">
                    <h3 className="truncate font-headline-md text-headline-md uppercase tracking-tight text-primary">
                      {player.name}
                    </h3>
                    <span className="truncate font-body-sm text-body-sm text-secondary">
                      {player.position} • {player.apps !== null ? `${player.apps} Apps` : `Apps ${DASH}`}
                    </span>
                  </div>
                </div>

                <div className="flex items-baseline justify-between pb-space-xs pt-space-xs">
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm uppercase tracking-wider text-secondary">
                      Primary Record
                    </span>
                    <div className="flex items-baseline gap-1.5">
                      <span className="font-stat-display text-stat-display text-primary">
                        {player.goals}
                      </span>
                      <span className="font-label-md text-label-md uppercase text-secondary">Goals</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="font-label-sm text-label-sm uppercase tracking-wider text-secondary">
                      {index === 0 ? "Playmaking" : "Goal Inv."}
                    </span>
                    <div className="flex items-baseline gap-1.5">
                      <span className="font-stat-display text-stat-display text-primary">
                        {index === 0 ? player.assists : player.ga}
                      </span>
                      <span className="font-label-md text-label-md uppercase text-secondary">
                        {index === 0 ? "Assists" : "G+A"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-space-xs rounded-chip bg-surface-container-low p-space-sm pt-space-sm">
                <MiniStat
                  label="Apps"
                  value={player.apps === null ? DASH : String(player.apps)}
                />
                <MiniStat
                  label="Penalties"
                  value={String(player.penalties)}
                />
              </div>
            </article>
          ))}
        </section>

        {/* ─── Controls, filters and sort ribbon ─────────────────────── */}
        <section className="flex flex-col gap-space-md rounded-card bg-surface-container-lowest p-space-md shadow-sm">
          <div className="grid grid-cols-1 gap-space-xs sm:grid-cols-2 lg:grid-cols-12">
            <div className="relative flex items-center lg:col-span-4">
              <span
                className="material-symbols-outlined absolute left-3 text-[16px] text-secondary"
                aria-hidden="true"
              >
                search
              </span>
              <input
                type="text"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(1);
                }}
                aria-label="Search player, nationality, or club"
                placeholder="Search player, nationality, or club..."
                className="h-8 w-full rounded-chip bg-surface-container-low pl-9 pr-3 font-label-md text-label-md text-primary outline-none transition-all placeholder:text-outline focus:bg-surface-container-lowest focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="relative lg:col-span-2">
              <select
                aria-label="Filter by club"
                value={club}
                onChange={(event) => {
                  setClub(event.target.value);
                  setPage(1);
                }}
                className="h-8 w-full cursor-pointer appearance-none rounded-chip bg-surface-container-low px-space-sm font-label-md text-label-md uppercase text-primary outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">{clubs.length > 0 ? `All ${clubs.length} Clubs` : "All Clubs"}</option>
                {clubs.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              <span
                className="material-symbols-outlined pointer-events-none absolute right-2 top-2 text-[16px] text-secondary"
                aria-hidden="true"
              >
                expand_more
              </span>
            </div>

            <div className="relative lg:col-span-2">
              <select
                aria-label="Filter by section"
                value={positionGroup}
                onChange={(event) => {
                  setPositionGroup(event.target.value as "" | PositionGroup);
                  setPage(1);
                }}
                className="h-8 w-full cursor-pointer appearance-none rounded-chip bg-surface-container-low px-space-sm font-label-md text-label-md uppercase text-primary outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">All Sections</option>
                <option value="offence">Offence</option>
                <option value="midfield">Midfield</option>
                <option value="defence">Defence</option>
              </select>
              <span
                className="material-symbols-outlined pointer-events-none absolute right-2 top-2 text-[16px] text-secondary"
                aria-hidden="true"
              >
                expand_more
              </span>
            </div>

            <div className="relative lg:col-span-2">
              <select
                aria-label="Filter by nationality"
                value={nation}
                onChange={(event) => {
                  setNation(event.target.value);
                  setPage(1);
                }}
                className="h-8 w-full cursor-pointer appearance-none rounded-chip bg-surface-container-low px-space-sm font-label-md text-label-md uppercase text-primary outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">All Nations</option>
                {nations.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.name} ({item.code})
                  </option>
                ))}
              </select>
              <span
                className="material-symbols-outlined pointer-events-none absolute right-2 top-2 text-[16px] text-secondary"
                aria-hidden="true"
              >
                expand_more
              </span>
            </div>

            <div className="flex h-8 items-center justify-between rounded-chip bg-surface-container-low px-space-sm lg:col-span-2">
              <label
                htmlFor="min-apps"
                className="font-label-sm text-label-sm uppercase text-secondary"
              >
                Min. Apps
              </label>
              <input
                id="min-apps"
                type="number"
                min={0}
                max={maxApps || undefined}
                value={minApps}
                onChange={(event) => {
                  const next = Number(event.target.value);
                  setMinApps(Number.isFinite(next) ? Math.max(0, Math.floor(next)) : 0);
                  setPage(1);
                }}
                className="w-10 bg-transparent text-right font-stat-tabular text-stat-tabular font-bold text-primary outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
              <button
                type="button"
                onClick={resetFilters}
                className="font-label-sm text-label-sm font-bold uppercase text-secondary transition-colors hover:text-primary"
              >
                Reset
              </button>
            </div>
          </div>
        </section>

        {/* ─── Master data grid ─────────────────────────────────────── */}
        <section className="flex flex-col overflow-hidden rounded-card bg-surface-container-lowest shadow-sm">
          <div className="w-full overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">
                Premier League top scorers, season {seasonValue}. Sortable by player, club and every
                performance column.
              </caption>
              <thead>
                <tr className="h-10 select-none bg-surface-container-low font-label-md text-label-md uppercase tracking-wider text-secondary">
                  <th scope="col" aria-sort="none" className="w-12 px-space-sm py-2 text-center font-bold">
                    #
                  </th>
                  <th scope="col" aria-sort={retheme("player")} className="min-w-[200px] px-space-md py-2">
                    <SortHeader
                      label="Player"
                      icon={sortIcon("player")}
                      active={sort.key === "player"}
                      align="start"
                      onClick={() => toggleSort("player")}
                    />
                  </th>
                  <th scope="col" aria-sort={retheme("club")} className="min-w-[170px] px-space-md py-2">
                    <SortHeader
                      label="Club"
                      icon={sortIcon("club")}
                      active={sort.key === "club"}
                      align="start"
                      onClick={() => toggleSort("club")}
                    />
                  </th>

                  {visibleColumnList.map((column) => {
                    const sortKey = column.key as SortKey;
                    return (
                      <th
                        key={column.key}
                        scope="col"
                        aria-sort={retheme(sortKey)}
                        className={`${column.minWidth} ${column.padding} py-2 text-center ${
                          column.headExtra ?? ""
                        }`}
                      >
                        <SortHeader
                          label={column.label}
                          icon={sortIcon(sortKey)}
                          active={sort.key === sortKey}
                          align="center"
                          onClick={() => toggleSort(sortKey)}
                        />
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y-0 font-stat-tabular text-stat-tabular text-on-surface">
                {pageRows.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => setSelectedId(row.id)}
                    className={`h-11 cursor-pointer transition-colors hover:bg-surface-container-low ${
                      selectedId === row.id
                        ? "bg-surface-container-high/40"
                        : "bg-surface-container-lowest"
                    }`}
                  >
                    <td className="px-space-sm text-center">
                      {row.rank <= 3 ? (
                        <span
                          className={`inline-flex h-5 w-5 items-center justify-center rounded-chip font-bold text-label-sm ${
                            row.rank === 1
                              ? "bg-primary text-on-primary"
                              : "bg-surface-container-high text-primary"
                          }`}
                        >
                          {row.rank}
                        </span>
                      ) : (
                        <span className="font-bold text-label-sm text-secondary">{row.rank}</span>
                      )}
                    </td>

                    <td className="px-space-md">
                      <div className="flex items-center gap-space-sm">
                        <div
                          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-chip font-bold text-label-sm ${
                            row.rank === 1
                              ? "bg-surface-container-high text-primary"
                              : "bg-surface-container text-primary"
                          }`}
                        >
                          {row.initials}
                        </div>
                        <div className="flex flex-col">
                          <span className="whitespace-nowrap font-body-lg text-body-lg font-bold tracking-tight text-primary">
                            {row.name}
                          </span>
                          <div className="flex items-center gap-1 font-label-sm text-label-sm uppercase text-secondary">
                            <span>{row.nationCode}</span>
                            <span aria-hidden="true">•</span>
                            <span className="rounded-chip bg-surface-container px-1 text-primary">
                              {row.positionCode}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-space-md">
                      <div className="flex items-center gap-1.5 font-body-sm text-body-sm text-primary">
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-pill bg-surface-container text-[9px] font-bold">
                          {row.clubCode}
                        </span>
                        <span className="truncate">{row.club}</span>
                      </div>
                    </td>

                    {visibleColumns.apps ? (
                      <td className="px-space-sm text-center text-secondary">
                        {row.apps === null ? <Dash /> : row.apps}
                      </td>
                    ) : null}

                    {visibleColumns.goals ? (
                      <td className="bg-surface-container/60 px-space-md text-center font-extrabold text-headline-sm text-primary">
                        {row.goals}
                      </td>
                    ) : null}

                    {visibleColumns.assists ? (
                      <td className="px-space-sm text-center font-medium">{row.assists}</td>
                    ) : null}

                    {visibleColumns.ga ? (
                      <td className="px-space-sm text-center font-bold text-primary">{row.ga}</td>
                    ) : null}

                    {visibleColumns.penalties ? (
                      <td className="px-space-sm text-center font-medium">{row.penalties}</td>
                    ) : null}

                    {visibleColumns.goalsPerApp ? (
                      <td className="px-space-md text-center font-bold text-primary">
                        {row.goalsPerApp === null ? <Dash /> : row.goalsPerApp.toFixed(2)}
                      </td>
                    ) : null}
                  </tr>
                ))}

                {pageRows.length === 0 ? (
                  <tr>
                    <td
                      colSpan={columnSpan}
                      className="px-space-md py-space-xl text-center font-body-md text-body-md text-secondary"
                    >
                      No goalscorers match the current filters.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          {/* Table footer and pagination */}
          <div className="flex flex-col items-center justify-between gap-space-md bg-surface-container-low p-space-md md:flex-row">
            <div className="flex flex-wrap items-center gap-space-md">
              <span className="font-body-sm text-body-sm text-secondary">
                Showing{" "}
                <strong className="font-bold text-primary">
                  {rangeStart}
                  {EN_DASH}
                  {rangeEnd}
                </strong>{" "}
                of <strong className="font-bold text-primary">{sorted.length}</strong> recorded
                goalscorers
              </span>
              <div className="flex items-center gap-1.5 font-label-sm text-label-sm uppercase text-secondary">
                <span>Per Page:</span>
                <div className="flex items-center gap-1">
                  {PAGE_SIZES.map((size) => (
                    <button
                      key={size}
                      type="button"
                      onClick={() => {
                        setPageSize(size);
                        setPage(1);
                      }}
                      aria-pressed={pageSize === size}
                      className={`rounded-chip px-1.5 py-0.5 ${
                        pageSize === size
                          ? "bg-primary font-bold text-on-primary"
                          : "bg-surface-container-lowest text-secondary transition-colors hover:text-primary"
                      }`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <nav aria-label="Pagination" className="flex items-center gap-1">
              <button
                type="button"
                disabled={currentPage === 1}
                onClick={() => setPage(currentPage - 1)}
                aria-label="Previous page"
                className={`flex h-7 w-7 items-center justify-center rounded-chip ${
                  currentPage === 1
                    ? "cursor-not-allowed bg-surface-container text-outline"
                    : "bg-surface-container-lowest text-secondary transition-colors hover:bg-surface-container"
                }`}
              >
                <span className="material-symbols-outlined text-[14px]" aria-hidden="true">
                  chevron_left
                </span>
              </button>

              {pageWindow(currentPage, totalPages).map((item, index) =>
                item === "ellipsis" ? (
                  <span
                    key={`ellipsis-${index}`}
                    className="px-1 font-label-sm text-label-sm text-secondary"
                  >
                    •••
                  </span>
                ) : (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setPage(item)}
                    aria-current={item === currentPage ? "page" : undefined}
                    className={`flex h-7 w-7 items-center justify-center rounded-chip font-label-md text-label-md ${
                      item === currentPage
                        ? "bg-primary font-bold text-on-primary"
                        : "bg-surface-container-lowest text-secondary transition-colors hover:bg-surface-container"
                    }`}
                  >
                    {item}
                  </button>
                ),
              )}

              <button
                type="button"
                disabled={currentPage === totalPages}
                onClick={() => setPage(currentPage + 1)}
                aria-label="Next page"
                className={`flex h-7 w-7 items-center justify-center rounded-chip ${
                  currentPage === totalPages
                    ? "cursor-not-allowed bg-surface-container text-outline"
                    : "bg-surface-container-lowest text-secondary transition-colors hover:bg-surface-container"
                }`}
              >
                <span className="material-symbols-outlined text-[14px]" aria-hidden="true">
                  chevron_right
                </span>
              </button>
            </nav>
          </div>
        </section>

        {/* ─── Methodology, glossary & season summary ────────────────── */}
        <section className="grid grid-cols-1 gap-space-md md:grid-cols-12">
          <div className="flex flex-col gap-space-xs rounded-card bg-surface-container-lowest p-space-md shadow-sm md:col-span-8">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-[16px] text-primary" aria-hidden="true">
                info
              </span>
              <h2 className="font-headline-sm text-headline-sm uppercase tracking-wider text-primary">
                Metrics Glossary &amp; Data Source
              </h2>
            </div>
            <div className="grid grid-cols-1 gap-space-sm pt-space-xs font-body-sm text-body-sm text-secondary sm:grid-cols-2">
              <div className="flex flex-col gap-0.5">
                <span className="font-label-sm text-label-sm font-bold uppercase text-primary">
                  Goals &amp; Appearances
                </span>
                <p>
                  Goals scored and matches played, published by the official feed for every
                  goalscorer of the current season.
                </p>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="font-label-sm text-label-sm font-bold uppercase text-primary">
                  Golden Boot Tiebreaker
                </span>
                <p>Tied on goals: 1. Most assists; 2. Player name, alphabetically.</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col justify-between rounded-card bg-surface-container-lowest p-space-md shadow-sm md:col-span-4">
            <div className="flex items-center justify-between gap-space-sm">
              <span className="font-label-sm text-label-sm font-bold uppercase tracking-widest text-secondary">
                Season Summary
              </span>
              <span className="rounded-chip bg-surface-container px-1.5 py-0.5 font-label-sm text-label-sm text-primary">
                {seasonValue}
              </span>
            </div>
            <div className="flex items-baseline justify-between py-space-xs">
              <div className="flex items-baseline gap-1">
                <span className="font-stat-display text-stat-display text-primary">
                  {matchdayValue}
                </span>
                <span className="font-label-md text-label-md uppercase text-secondary">
                  Matchday
                </span>
              </div>
              <div className="text-right">
                <span className="font-stat-tabular text-stat-tabular font-bold text-primary">
                  {scorerCountValue}
                </span>
                <div className="font-label-sm text-label-sm uppercase text-secondary">
                  Scorers
                </div>
              </div>
            </div>
            <span className="pt-1 font-label-sm text-label-sm text-secondary">{seasonNote}</span>
          </div>
        </section>
      </div>
    </div>
  );
}
