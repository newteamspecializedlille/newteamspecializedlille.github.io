import datetime
import os

import team_members
import parse_results
import site_links

team = {}
results = {}
today = datetime.date.today()
# saison CX/VTT : année+1 dès août (SEASON pour forcer) ; saison route : année civile (ROAD_SEASON pour forcer)
seasons = parse_results.default_seasons(today, os.getenv("SEASON"), os.getenv("ROAD_SEASON"))
road_year = seasons["calResRoute.php"]

team = team_members.load_team_from_file(team)
parser = parse_results.ParseResults(team, results)
team = parser.generate_results(seasons)
team_members.update_team_file(team)
# les classements challenge route / boue sont calculés au build par _plugins/challenges.rb (barèmes : _data/challenge_rules.json)
team_members.update_road_statistics(team, road_year)
site_links.update_race_urls()  # liens des pages coureur -> posts
print("Update race done")
