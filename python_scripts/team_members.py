import json
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

class TeamMember:
    def __init__(self, name):
        self.name = name
        self.course = 0
        self.cx = {}
        self.vtt = {}
        self.road = {}

    def to_dict(self):
        res = {"name": self.name, "course": self.course,
               "cx": dict(sorted(self.cx.items(), reverse=True)),
               "vtt": dict(sorted(self.vtt.items(), reverse=True)),
               "road": dict(sorted(self.road.items(), reverse=True))}
        return res

    def challenge_calcul_point(self, year, points_challenge):
        points = 0
        if self.road.get(year):
            for race in self.road[year].items():
                if isinstance(race[1], int):
                    if race[1] == 1:
                        points += points_challenge.point_win
                    elif race[1] <= 5:
                        points += points_challenge.point_top5
                    elif race[1] <= 10:
                        points += points_challenge.point_top10
                    elif race[1] <= 15:
                        points += points_challenge.point_top15
                    points += points_challenge.point_participation
        return points

    def challenge_calcul_point_boue(self, year, points_challenge):
        points = 0
        if self.cx.get(year):
            for race in self.cx[year].items():
                if isinstance(race[1], int):
                    if race[1] == 1:
                        points += points_challenge.point_win
                    elif race[1] <= 5:
                        points += points_challenge.point_top5
                    elif race[1] <= 10:
                        points += points_challenge.point_top10
                    elif race[1] <= 15:
                        points += points_challenge.point_top15
                    points += points_challenge.point_participation
        if self.vtt.get(year):
            for race in self.vtt[year].items():
                if isinstance(race[1], int):
                    if race[1] == 1:
                        points += points_challenge.point_win
                    elif race[1] <= 5:
                        points += points_challenge.point_top5
                    elif race[1] <= 10:
                        points += points_challenge.point_top10
                    elif race[1] <= 15:
                        points += points_challenge.point_top15
                    points += points_challenge.point_participation
        return points


def get_points_challenge(file_challenge):
    with open(file_challenge, 'r') as challenge_file:
        data_challenge = json.load(challenge_file)
        return ChallengePoints(data_challenge["point_win"], data_challenge["point_top5"], data_challenge["point_top10"], data_challenge[
            "point_top15"], data_challenge["point_participation"])


def update_challenge(team: dict[str, TeamMember], challenge_year, challenge):
    file_name = "../_data/" + challenge + challenge_year + ".json"
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
    team_file = open(team_path_file, 'r')
    data = json.load(team_file)

    for member in data['team_members']:
        team[member["name"]] = TeamMember(member["name"])
        team[member["name"]].course = member["course"]
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
