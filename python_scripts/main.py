import team_members
import parse_results

team = {}
results = {}
year = "2025"

team = team_members.load_team_from_file(team)

parser = parse_results.ParseResults(team, results)
team = parser.generate_results(year)
team_members.update_team_file(team)
team_members.update_challenge(team, year)
team_members.update_challenge_boue(team, year)
print("Update done")
