import datetime
import os

import team_members
import parse_results
import site_links

team = {}
results = {}
today = datetime.date.today()
# saison CX/VTT : année+1 dès août (ex. novembre 2026 -> 2027) ; surchargeable via SEASON
year = os.getenv("SEASON") or str(today.year + 1 if today.month >= 8 else today.year)
road_year = os.getenv("ROAD_SEASON") or str(int(year) - 1)

team = team_members.load_team_from_file(team)
parser = parse_results.ParseResults(team, results)
team = parser.generate_results(year)
team_members.update_team_file(team)
team_members.update_challenge(team, year, "challenge")
team_members.update_challenge(team, year, "boue")
team_members.update_road_statistics(team, road_year)
site_links.update_race_urls()  # liens des pages coureur -> posts
print("Update race done")
