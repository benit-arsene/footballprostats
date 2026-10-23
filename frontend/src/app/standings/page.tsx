import { redirect } from "next/navigation";

export default function StandingsIndexRedirect() {
  redirect("/competitions/epl-39/standings/current-season");
}
