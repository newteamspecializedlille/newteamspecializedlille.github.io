import fitz
import team_members

race_date = "2024/03/17"
pdf_path = "test.pdf"
race_name = "PRIX DE PROUZEL"
race_type = "Route"


class Line:
    def __init__(self, place, dossard, name, team, points):
        self.place = place
        self.dossard = dossard
        self.name = name
        self.team = team
        self.points = points

    def display(self):
        print(str(self.place) + " | " + str(self.dossard) + " | " + self.name + " | " + self.team + " | " + str(
            self.points))


exception_name = ["PERRONNET JEREMY", "DESMOULINS PATRICK", "BRIAND CHRISTIAN", "LUYCX ADRIEN", "BOULANGER BAILLEUX",
                  "LEFEVRE PIERRE", "MASKIEWICZ ALEXANDRE", "DECROMBECQUE  LAETITIA"]
tmp_line = None
SPECIALIZED = "TEAM SPECIALIZED LILLE"


def get_member_with_link(team_member):
    link = "https://teamspecializedlille.github.io/coureurs/"
    return "[" + team_member + "](" + link + team_member.replace(" ", "").lower() + ")"


def display_result_line_with_link(outfile, line):
    if line.team == SPECIALIZED:
        if line.points and int(line.points) > 0:
            outfile.write("- " + get_member_with_link(line.name) + " : " + str(line.place) + "\n")
        else:
            outfile.write("- " + get_member_with_link(line.name) + " : Ab\n")


def display_for_category(outfile, results, title):
    if results:
        if len(results) > 0:
            outfile.write("\n### " + title + "\n")
            outfile.write(str(len(results)) + " participants\n")
        for line in results:
            display_result_line_with_link(outfile, line)
        print_table_results(outfile, results)


def print_table_results(outfile, results):
    outfile.write("\n| Place | Nom | Team |\n")
    outfile.write("|---|---|---|\n")
    for line in results:
        if line.team == SPECIALIZED:
            outfile.write(
                "|**" + line.place + "**|**" + get_member_with_link(line.name) + "**|**" + line.team + "**|\n")
        else:
            outfile.write("|" + line.place + "|" + line.name + "|" + line.team + "|\n")


def create_post_race(cate_1, cate_2, cate_3, cate_4):
    file_name = race_date.replace("/", "-") + "-" + race_type + race_name + ".md"
    race_year = race_date.split("/")[0]

    with open("../_posts/" + file_name, "w", encoding='utf8') as outfile:
        outfile.write("---\n")
        outfile.write("layout: post\n")
        outfile.write("title: " + race_type + " - " + race_name + " - " + race_year + "\n")
        outfile.write("date: " + race_date.replace("/", "-") + "\n")
        outfile.write("category: " + race_type + "\n")
        tag = race_type
        outfile.write("tags: " + tag + "\n")
        if race_type == "Route":
            outfile.write("image: assets/img/blog/road.jpeg\n")
        outfile.write("---\n")

        display_for_category(outfile, cate_1, "1ère Catégorie")
        display_for_category(outfile, cate_2, "2ème Catégorie")
        display_for_category(outfile, cate_3, "3ème Catégorie")
        display_for_category(outfile, cate_4, "4ème Catégorie")


def parse_int(s):
    if s.isdigit():
        return True
    else:
        return False


def find_prefix(dans_chaine, tableau_prefixes):
    for prefixe in tableau_prefixes:
        if dans_chaine.startswith(prefixe):
            return prefixe
    return None


def split_name_and_team(values):
    if values[len(values) - 1].isdigit():
        name_and_team = ' '.join(values[2:len(values) - 1])
    else:
        name_and_team = ' '.join(values[2:len(values)])
    name = find_prefix(name_and_team, exception_name)
    if name:
        index_div = name_and_team.find(name) + len(name)
        name = name_and_team[:index_div]
        team = name_and_team[index_div:]
        return name, team.strip()
    else:
        print("New exception need to be added :" + name_and_team)
        return name_and_team, "ERROR"


def parse_line(line):
    values = line.split(',')
    if "Place" in line:
        return None
    if len(values) == 5 and values[len(values) - 1].isdigit():
        return Line(values[0], values[1], values[2], values[3], values[4])
    elif len(values) > 5 or (len(values) == 5 and values[len(values) - 1].isdigit() == False):
        name_and_team = split_name_and_team(values)
        if values[len(values) - 1].isdigit():
            return Line(values[0], values[1], name_and_team[0], name_and_team[1], values[len(values) - 1])
        else:
            return Line(values[0], values[1], name_and_team[0], name_and_team[1], 0)
    elif "3EME" in line:
        return 3
    elif "2EME" in line:
        return 2
    elif "4EME" in line:
        return 4
    elif "1ERE" in line:
        return 1
    elif len(values) == 4:
        if values[len(values) - 1].isdigit():
            name_and_team = split_name_and_team(values)
            return Line(values[0], values[1], name_and_team[0], name_and_team[1], values[len(values) - 1])
        else:
            # abandon
            return Line(values[0], values[1], values[2], values[3], 0)
    elif len(values) < 5:
        global tmp_line
        if tmp_line is None:
            tmp_line = line
        elif tmp_line:
            line = tmp_line + ' ' + line
            tmp_line = None
            return parse_line(line)
    else:
        print("Error during the parsing of line : " + line)
    return None


def validate_results_for_spe(results):
    count = 0
    for line in results:
        if line.team == SPECIALIZED:
            count += 1
    if count == 0:
        return None
    return results


def get_hash_individual_race(race_cat):
    # year / race / cate /  => pos
    return race_date + "|" + race_name + "|" + race_cat


def update_team_for_category(team, cate, season, race_cat):
    for line in cate:
        if line.team == SPECIALIZED:
            member = line.name
            if member not in team:
                team[member] = team_members.TeamMember(member)
            team[member].course += 1
            if race_type == "Route":
                if team[member].road.get(season) is None:
                    team[member].road[season] = {}
                hash_individual = get_hash_individual_race(race_cat)
                team[member].road[season][hash_individual] = int(line.place)
    return team


# noinspection PyShadowingNames
def update_team_results(team, cate_1, cate_2, cate_3, cate_4, season):
    team = update_team_for_category(team, cate_1, season, "1ère")
    team = update_team_for_category(team, cate_2, season, "2ème")
    team = update_team_for_category(team, cate_3, season, "3ème")
    team = update_team_for_category(team, cate_4, season, "4ème")
    return team


# noinspection PyShadowingNames
def extract_table_from_pdf(pdf_path):
    cate_1 = None
    cate_2 = None
    cate_3 = None
    cate_4 = None

    with fitz.open(pdf_path) as doc:
        for page_number, page in enumerate(doc):
            blocks = page.get_text("blocks")
            results = []
            for block in blocks:
                x0, y0, x1, y1, text, block_num, line_num = block
                tmp = text.strip().replace('\n', ',')
                # print(f"Text block {block_num} (Page {page_number + 1}): {tmp}")
                line = parse_line(tmp)
                if line:
                    results.append(line)
            for res in results:
                if isinstance(res, int):
                    results.remove(res)
                    match res:
                        case 1:
                            cate_1 = results
                        case 2:
                            cate_2 = results
                        case 3:
                            cate_3 = results
                        case 4:
                            cate_4 = results
    return cate_1, cate_2, cate_3, cate_4


team = {}
cate_1, cate_2, cate_3, cate_4 = extract_table_from_pdf(pdf_path)
create_post_race(validate_results_for_spe(cate_1), validate_results_for_spe(cate_2),
                 validate_results_for_spe(cate_3), validate_results_for_spe(cate_4))
team = team_members.load_team_from_file(team)
team = update_team_results(team, cate_1, cate_2, cate_3, cate_4, "2024")
team_members.update_team_file(team)
team_members.update_challenge(team, "2024")
print("Update done")
