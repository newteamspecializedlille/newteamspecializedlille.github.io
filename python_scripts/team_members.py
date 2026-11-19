import json
import os

team_path_file = '../_data/team.json'
# barèmes des challenges par saison (partagés avec le plugin Jekyll _plugins/challenges.rb qui calcule les classements)
rules_path_file = '../_data/challenge_rules.json'


class ChallengePoints:
    def __init__(self, point_win, point_top5, point_top10, point_top15, point_participation, abandon_counts=False):
        self.point_win = point_win
        self.point_top5 = point_top5
        self.point_top10 = point_top10
        self.point_top15 = point_top15
        self.point_participation = point_participation
        self.abandon_counts = abandon_counts

    @classmethod
    def from_rules(cls, kind, season, rules=None):
        """Barème de la saison (kind : "challenge" ou "boue") d'après _data/challenge_rules.json (défaut sinon)."""
        if rules is None:
            with open(rules_path_file, "r", encoding="utf8") as rules_file:
                rules = json.load(rules_file)
        scales = rules[kind]
        scale = scales.get(str(season), scales["default"])
        return cls(scale["point_win"], scale["point_top5"], scale["point_top10"], scale.get("point_top15", 0),
                   scale["point_participation"], rules.get("abandon_counts", False))

    def points_for_place(self, rank, status=None):
        """Points d'une course : barème de la place + participation (abandon : 0, ou la participation si la règle
        `abandon_counts` est activée)."""
        if status:
            return self.point_participation if self.abandon_counts else 0
        if not isinstance(rank, int) or isinstance(rank, bool):
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
    def __init__(self, name, active=True):
        self.name = name
        self.active = active  # False : ancien membre (gardé pour les classements des saisons passées)
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
        return {"name": self.name, "active": self.active, "cx": seasons(self.cx), "vtt": seasons(self.vtt),
                "road": seasons(self.road)}


def update_road_statistics(team: dict[str, TeamMember], year):
    points_rules = ChallengePoints.from_rules("challenge", year)
    riders = []
    place_totals = [0] * 10

    for member in (m for m in team.values() if m.active):
        races = member.road.get(year, [])
        places = [sum(1 for result in races if result.get("rank") == place) for place in range(1, 11)]
        place_totals = [total + count for total, count in zip(place_totals, places)]
        riders.append({
            "name": member.name,
            "races": len(races),
            "places": places,
            "challenge_points": points_rules.points_for_results(races),
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
        team[member["name"]] = TeamMember(member["name"], member.get("active", True))
        team[member["name"]].cx = member["cx"]
        team[member["name"]].vtt = member["vtt"]
        team[member["name"]].road = member["road"]

    team_file.close()
    return team


def update_team_file(team):
    data = {}
    array = []
    for m in team.values():
        array.append(m.to_dict())
    data["team_members"] = array
    json_object = json.dumps(data, ensure_ascii=False, indent=4)
    with open(team_path_file, "w", encoding='utf8') as outfile:
        outfile.write(json_object)
