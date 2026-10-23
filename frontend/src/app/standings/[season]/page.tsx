import { redirect } from "next/navigation";

export default function StandingsSeasonRedirect() {
  redirect("/competitions/epl-39/standings/current-season");
}
