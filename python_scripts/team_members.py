import json
import os
import datetime
import operator

team_path_file = '../_data/team.json'
challenge_path_file = "../_data/challenge.json"

class ChallengePoints:
    def __init__(self, point_win, point_top5, point_top10, point_top15, point_participation):
        self.point_win = point_win
        self.point_top5 = point_top5
        self.point_top10 = point_top10
        self.point_top15 = point_top15
        self.point_participation = point_participation

    def points_for_place(self, rank, status=None):
        """Points d'une course : barème de la place + participation (0 si abandon ou sans place)."""
        if status or not isinstance(rank, int) or isinstance(rank, bool):
            return 0
        if rank == 1:
            points = self.point_win
        elif rank <= 5:
            points = self.point_top5
        elif rank <= 10:
            points = self.point_top10
        elif rank <= 15:
            points = self.point_top15
        else:
            points = 0
        return points + self.point_participation

    def points_for_results(self, results):
        """Total des points d'une liste de résultats (objets make_result)."""
        return sum(self.points_for_place(r.get("rank"), r.get("status")) for r in (results or []))


DISCIPLINES = ("cx", "vtt", "road")


def make_result(date, race_name, category, rank=None, status=None, participants=None):
    """Un résultat d'équipier. date AAAA-MM-JJ ; rank entier (None si abandon) ; status None ou "AB" ;
    participants = nombre de partants de la catégorie (None si inconnu)."""
    return {"date": date, "raceName": race_name, "category": category, "rank": rank, "status": status,
            "participants": participants}


def result_identity(result):
    """Un résultat est identifié par sa date, sa course et sa catégorie."""
    return result["date"], result["raceName"], result["category"]


class TeamMember:
    def __init__(self, name):
        self.name = name
        self.cx = {}    # saison -> [résultat]
        self.vtt = {}
        self.road = {}

    def upsert_result(self, discipline, season, result):
        """Ajoute un résultat, ou remplace celui de même date + course + catégorie (idempotent)."""
        results = getattr(self, discipline).setdefault(season, [])
        for index, existing in enumerate(results):
            if result_identity(existing) == result_identity(result):
                results[index] = result
                return
        results.append(result)

    def remove_race_results(self, discipline, season, date, race_name):
        """Retire tous les résultats d'une course (toutes catégories). Retourne le nombre retiré."""
        results = getattr(self, discipline).get(season, [])
        kept = [r for r in results if not (r["date"] == date and r["raceName"] == race_name)]
        getattr(self, discipline)[season] = kept
        return len(results) - len(kept)

    def to_dict(self):
        def seasons(by_season):
            return {year: sorted(sorted(results, key=lambda r: (r["raceName"], r["category"])),
                                 key=lambda r: r["date"])  # ordre chronologique (comme l'affichage historique)
                    for year, results in sorted(by_season.items(), reverse=True) if results}
        return {"name": self.name, "cx": seasons(self.cx), "vtt": seasons(self.vtt), "road": seasons(self.road)}

    def challenge_calcul_point(self, year, points_challenge):
        """Challenge route : points des courses sur route de la saison."""
        return points_challenge.points_for_results(self.road.get(year))

    def challenge_calcul_point_boue(self, year, points_challenge):
        """Challenge boue : points des cyclo-cross et VTT de la saison."""
        return (points_challenge.points_for_results(self.cx.get(year))
                + points_challenge.points_for_results(self.vtt.get(year)))


def get_points_challenge(file_challenge):
    with open(file_challenge, 'r') as challenge_file:
        data_challenge = json.load(challenge_file)
        return ChallengePoints(data_challenge["point_win"], data_challenge["point_top5"], data_challenge["point_top10"], data_challenge[
            "point_top15"], data_challenge["point_participation"])


def update_challenge(team: dict[str, TeamMember], challenge_year, challenge):
    file_name = "../_data/" + challenge + challenge_year + ".json"
    # nouvelle saison : reprend le barème de la saison précédente si le fichier n'existe pas encore
    points_source = file_name
    if not os.path.exists(file_name):
        points_source = "../_data/" + challenge + str(int(challenge_year) - 1) + ".json"
    points_challenge = get_points_challenge(points_source)
    data = {}
    challenge_res = {}
    if challenge == "boue":
        for m in team.values():
            challenge_res[m.name] = m.challenge_calcul_point_boue(challenge_year, points_challenge)
    elif challenge == "challenge":
        for m in team.values():
            challenge_res[m.name] = m.challenge_calcul_point(challenge_year, points_challenge)
    data["point_win"] = points_challenge.point_win
    data["point_top5"] = points_challenge.point_top5
    data["point_top10"] = points_challenge.point_top10
    data["point_top15"] = points_challenge.point_top15
    data["point_participation"] = points_challenge.point_participation
    data["update_date"] = datetime.datetime.now().strftime("%d %B %Y")
    data["challenge_year"] = challenge_year
    data["challenge"] = dict(sorted(challenge_res.items(), key=operator.itemgetter(1), reverse=True))
    # la date de mise à jour ne change que si le classement change (évite un commit CI quotidien inutile)
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf8") as previous_file:
            previous = json.load(previous_file)
        if {k: v for k, v in previous.items() if k != "update_date"} == {k: v for k, v in data.items() if k != "update_date"}:
            data["update_date"] = previous.get("update_date", data["update_date"])
    json_object = json.dumps(data, ensure_ascii=False, indent=4)
    with open(file_name, "w", encoding='utf8') as outfile:
        outfile.write(json_object)


def update_road_statistics(team: dict[str, TeamMember], year):
    with open("../_data/challenge" + year + ".json", "r", encoding="utf8") as challenge_file:
        challenge_data = json.load(challenge_file)

    challenge_points = challenge_data["challenge"]
    riders = []
    place_totals = [0] * 10

    for member in team.values():
        races = member.road.get(year, [])
        places = [sum(1 for result in races if result.get("rank") == place) for place in range(1, 11)]
        place_totals = [total + count for total, count in zip(place_totals, places)]
        riders.append({
            "name": member.name,
            "races": len(races),
            "places": places,
            "challenge_points": challenge_points.get(member.name, 0),
        })

    riders.sort(key=lambda rider: (-sum(rider["places"]), rider["name"]))
    data = {
        "year": int(year),
        "place_labels": list(range(1, 11)),
        "summary": {
            "riders": len(riders),
            "races": sum(rider["races"] for rider in riders),
            "top_10_finishes": sum(place_totals),
            "place_counts": place_totals,
            "challenge_points": sum(rider["challenge_points"] for rider in riders),
        },
        "riders": riders,
    }

    json_object = json.dumps(data, ensure_ascii=False, indent=4)
    with open("../_data/road" + year + "_stats.json", "w", encoding="utf8") as outfile:
        outfile.write(json_object)


def load_team_from_file(team: dict[str, TeamMember]) -> dict[str, TeamMember]:
    team_file = open(team_path_file, 'r')
    data = json.load(team_file)

    for member in data['team_members']:
        team[member["name"]] = TeamMember(member["name"])
        team[member["name"]].cx = member["cx"]
        team[member["name"]].vtt = member["vtt"]
        team[member["name"]].road = member["road"]

    team_file.close()
    return team


def remove_old_team(team):
    if "BOONE ERIC" in team:
        team.pop("BOONE ERIC")
    if "BRADEFER GERY" in team:
        team.pop("BRADEFER GERY")
    if "DEBUY SEBASTIEN" in team:
        team.pop("DEBUY SEBASTIEN")
    if "DARQUE JEAN FRANCOIS" in team:
        team.pop("DARQUE JEAN FRANCOIS")
    if "DUFOUR JONATHAN" in team:
        team.pop("DUFOUR JONATHAN")
    if "VERHULST ERIC" in team:
        team.pop("VERHULST ERIC")
    if "LECLERCQ FRANCK" in team:
        team.pop("LECLERCQ FRANCK")
    if "MOLKA MICHAEL" in team:
        team.pop("MOLKA MICHAEL")
    if "RAMBEAU CHRISTOPHER" in team:
        team.pop("RAMBEAU CHRISTOPHER")
    if "HULEUX LUDOVIC" in team:
        team.pop("HULEUX LUDOVIC")
    if "LECLERCQ CLEMENT" in team:
        team.pop("LECLERCQ CLEMENT")
    if "LECLERC CLEMENT" in team:
        team.pop("LECLERC CLEMENT")
    if "GINET LIONEL" in team:
        team.pop("GINET LIONEL")
    if "THEIL MICKAEL" in team:
        team.pop("THEIL MICKAEL")
    if "HOUREZ CEDRIC" in team:
        team.pop("HOUREZ CEDRIC")
    if "MATTIOLI RONALD" in team:
        team.pop("MATTIOLI RONALD")
    if "WALTER BENOIT" in team:
        team.pop("WALTER BENOIT")
    if "MEAUSOONE HENRI" in team:
        team.pop("MEAUSOONE HENRI")
    if "TRINEL EMILY" in team:
        team.pop("TRINEL EMILY")
    if "POULAIN NOAH" in team:
        team.pop("POULAIN NOAH")


def update_team_file(team):
    data = {}
    array = []
    remove_old_team(team)
    for m in team.values():
        array.append(m.to_dict())
    data["team_members"] = array
    json_object = json.dumps(data, ensure_ascii=False, indent=4)
    with open(team_path_file, "w", encoding='utf8') as outfile:
        outfile.write(json_object)
