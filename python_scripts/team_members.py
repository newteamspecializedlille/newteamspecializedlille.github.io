import json
import datetime
import operator
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(REPO_ROOT, '_data')
team_path_file = os.path.join(REPO_ROOT, '_data', 'team.json')


class ChallengePoints:
    def __init__(self, point_win, point_top5, point_top10, point_top15, point_participation):
        self.point_win = point_win
        self.point_top5 = point_top5
        self.point_top10 = point_top10
        self.point_top15 = point_top15
        self.point_participation = point_participation


class TeamMember:
    def __init__(self, name):
        self.name = name
        self.active = True
        self.cx = {}
        self.vtt = {}
        self.road = {}

    def to_dict(self):
        return {
            "name": self.name,
            "active": self.active,
            "cx": dict(sorted(self.cx.items(), reverse=True)),
            "vtt": dict(sorted(self.vtt.items(), reverse=True)),
            "road": dict(sorted(self.road.items(), reverse=True)),
        }

    def _calc_points_for_season(self, season_races, points_challenge):
        points = 0
        for race in season_races:
            pos = race.get("pos")
            if isinstance(pos, int):
                if pos == 1:
                    points += points_challenge.point_win
                elif pos <= 5:
                    points += points_challenge.point_top5
                elif pos <= 10:
                    points += points_challenge.point_top10
                elif pos <= 15:
                    points += points_challenge.point_top15
                points += points_challenge.point_participation
        return points

    def challenge_calcul_point(self, year, points_challenge):
        points = 0
        if self.road.get(year):
            points += self._calc_points_for_season(self.road[year], points_challenge)
        return points

    def challenge_calcul_point_boue(self, year, points_challenge):
        points = 0
        if self.cx.get(year):
            points += self._calc_points_for_season(self.cx[year], points_challenge)
        if self.vtt.get(year):
            points += self._calc_points_for_season(self.vtt[year], points_challenge)
        return points


def _migrate_season(season_dict):
    """Convertit {'date|race|cat': pos} en liste d'objets résultats."""
    if isinstance(season_dict, list):
        return season_dict
    if not isinstance(season_dict, dict):
        return []

    result = []
    for key, pos in season_dict.items():
        parts = key.split("|")
        if len(parts) == 3:
            result.append({"date": parts[0], "race": parts[1], "cat": parts[2], "pos": pos})
        elif len(parts) == 2:
            result.append({"date": parts[0], "race": parts[1], "cat": "", "pos": pos})
        else:
            result.append({"date": "", "race": key, "cat": "", "pos": pos})
    return result


def get_points_challenge(file_challenge):
    with open(file_challenge, 'r', encoding='utf8') as challenge_file:
        data_challenge = json.load(challenge_file)
        return ChallengePoints(
            data_challenge["point_win"],
            data_challenge["point_top5"],
            data_challenge["point_top10"],
            data_challenge["point_top15"],
            data_challenge["point_participation"],
        )


def update_challenge(team: dict[str, TeamMember], challenge_year, challenge):
    file_name = os.path.join(DATA_DIR, f"{challenge}{challenge_year}.json")
    points_challenge = get_points_challenge(file_name)
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
    json_object = json.dumps(data, ensure_ascii=False, indent=4)
    with open(file_name, "w", encoding='utf8') as outfile:
        outfile.write(json_object)


def load_team_from_file(team: dict[str, TeamMember]) -> dict[str, TeamMember]:
    with open(team_path_file, 'r', encoding='utf8') as team_file:
        data = json.load(team_file)

    for member in data['team_members']:
        team_member = TeamMember(member["name"])
        team_member.active = member.get("active", True)
        team_member.cx = {year: _migrate_season(season) for year, season in member.get("cx", {}).items()}
        team_member.vtt = {year: _migrate_season(season) for year, season in member.get("vtt", {}).items()}
        team_member.road = {year: _migrate_season(season) for year, season in member.get("road", {}).items()}
        team[team_member.name] = team_member

    return team


def update_team_file(team):
    data = {}
    team_to_save = {k: v for k, v in team.items() if v.active}
    data["team_members"] = [member.to_dict() for member in team_to_save.values()]
    json_object = json.dumps(data, ensure_ascii=False, indent=4)
    with open(team_path_file, "w", encoding='utf8') as outfile:
        outfile.write(json_object)
