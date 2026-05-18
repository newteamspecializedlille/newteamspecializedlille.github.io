from datetime import datetime

import json
import os
import re
import requests
import urllib3
import xlrd

import race_results
import sync_drive
import team_members

base = "https://cyclismeufolep5962.fr/"
column_result = 0
column_name = 1
column_team = 2
column_lap = 3
column_time = 4
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(REPO_ROOT, '_data')
POSTS_DIR = os.path.join(REPO_ROOT, '_posts')
RACES_PARSED_FILE = os.path.join(DATA_DIR, 'races_parsed.json')
TEMP_XLS_FILE = os.path.join(SCRIPT_DIR, 'test.xls')

# Mapping nom de sheet → clé de catégorie normalisée
CAT_MAP = {
    "1ère": "1ère",
    "2ème": "2ème",
    "3ème": "3ème",
    "Cadets": "Cadets",
    "Féminines": "Féminines",
    "Séniors A": "Séniors A",
    "Seniors A": "Séniors A",
    "Séniors B": "Séniors B",
    "Seniors B": "Séniors B",
    "Vétérans A": "Vétérans A",
    "Vétérans B": "Vétérans B",
    "Vétérans C": "Vétérans C",
}

# Mapping clé normalisée → label affiché dans le post Markdown
CAT_LABELS = {
    "1ère": "1ère Catégorie",
    "2ème": "2ème Catégorie",
    "3ème": "3ème Catégorie",
    "Cadets": "Cadets",
    "Féminines": "Féminines",
    "Séniors A": "VTT Sénior A",
    "Séniors B": "VTT Sénior B",
    "Vétérans A": "VTT Vétérans A",
    "Vétérans B": "VTT Vétérans B",
    "Vétérans C": "VTT Vétérans C",
}


def display_result_line_with_link(outfile, team_member, position):
    outfile.write("- " + get_member_with_link(team_member) + " : " + str(position) + "\n")


def get_member_with_link(team_member):
    link = "https://teamspecializedlille.cc/coureurs/"
    return "[" + team_member + "](" + link + team_member.replace(" ", "").lower() + ")"


def print_scratch_results_header(outfile):
    outfile.write("| Place | Nom | Team | Tours | Catégorie | Temps |\n")
    outfile.write("|---|---|---|---|---|---|\n")


def return_result(sheet, line):
    val = sheet.cell(line, column_result).value
    if val == "Ab" or val == "AB" or val == "":
        return val
    return int(val)


def check_if_scratch_enable(sheet):
    try:
        r = str(sheet.row(1))
        if "Tours" in r and "Temps" in r:
            return True
        return False
    except Exception:
        return False


def save_races_parsed(races_parsed):
    data = {"races_parsed": races_parsed}
    json_object = json.dumps(data, ensure_ascii=False, indent=4)
    with open(RACES_PARSED_FILE, "w", encoding='utf8') as outfile:
        outfile.write(json_object)


def load_races_parsed():
    races_parsed = []
    with open(RACES_PARSED_FILE, 'r', encoding='utf8') as races_parsed_file:
        data = json.load(races_parsed_file)
    if len(data['races_parsed']) > 0:
        for race in data['races_parsed']:
            races_parsed.append(race)
    return races_parsed


def sorted_algo(item):
    time = item[1].get("time", 0)[3] * 60 * 60 + item[1].get("time", 0)[4] * 60 + item[1].get("time", 0)[5]
    res = (item[1].get("lap", 0) * -1, time)
    return res


def print_line_table(outfile, bold, *arg):
    outfile.write("| ")
    for item in arg:
        if bold:
            outfile.write("**" + str(item) + "** | ")
        else:
            outfile.write(str(item) + " | ")
    outfile.write("\n")


class ParseResults:
    def __init__(self, team, results):
        self.team = team
        self.results = results
        self.race_date = ""
        self.race_name = ""
        self.race_type = ""
        self.race_year = ""
        self.race_cat = ""
        self.races_parsed = []

    def display_race_infos(self):
        print("__________________________________________________________________________")
        print(
            "Type: " + self.race_type + ", name: " + self.race_name + ", date: " + self.race_date + "(" + self.race_year + ")")
        print("__________________________________________________________________________")

    def get_hash_race(self):
        return self.race_type + "/" + self.race_year + "/" + self.race_name

    def is_team_member(self, sheet, line):
        if line <= 1:
            return False
        if "TEAM SPECIALIZED LILLE" in str(sheet.cell(line, column_team).value):
            return True

        if str(sheet.cell(line, column_team).value) == "":
            if sheet.cell(line, column_result).value == "Ab" or sheet.cell(line, column_result).value == "AB":
                member = sheet.cell(line, column_name).value
                if member in self.team:
                    return True
        return False

    def _get_discipline_results(self, member, season):
        if self.race_type == "Cyclo Cross":
            discipline = self.team[member].cx
        elif self.race_type == "VTT":
            discipline = self.team[member].vtt
        else:
            discipline = self.team[member].road

        if discipline.get(season) is None:
            discipline[season] = []
        return discipline[season]

    def _upsert_race_entry(self, season_results, race_entry):
        existing_key = (race_entry["date"], race_entry["race"], race_entry["cat"])
        for index, existing in enumerate(season_results):
            if (existing.get("date"), existing.get("race"), existing.get("cat")) == existing_key:
                season_results[index] = race_entry
                return
        season_results.append(race_entry)

    def parse_results_race_sheet(self, coureurbook, sheet, season):
        sheet = coureurbook.sheet_by_index(sheet)
        self.race_cat = sheet.name
        cat_key = CAT_MAP.get(self.race_cat)
        hash_race = self.get_hash_race()
        scratch_enable = check_if_scratch_enable(sheet)
        if hash_race not in self.results:
            self.results[hash_race] = race_results.RaceResults(hash_race)
        for line in range(sheet.nrows):
            if str(sheet.cell(line, column_team).value) != "" and cat_key:
                self.results[hash_race].riders_count[cat_key] = self.results[hash_race].riders_count.get(cat_key, 0) + 1
            if self.is_team_member(sheet, line):
                member = sheet.cell(line, column_name).value
                if member not in self.team:
                    self.team[member] = team_members.TeamMember(member)
                race_entry = {
                    "date": self.race_date,
                    "race": self.race_name,
                    "cat": self.race_cat,
                    "pos": return_result(sheet, line),
                }
                season_results = self._get_discipline_results(member, season)
                self._upsert_race_entry(season_results, race_entry)
                if cat_key:
                    if cat_key not in self.results[hash_race].categories:
                        self.results[hash_race].categories[cat_key] = {}
                    self.results[hash_race].categories[cat_key][member] = return_result(sheet, line)
            member = sheet.cell(line, column_name).value
            if member != "" and line > 1 and scratch_enable and str(type(member)) == "<class 'str'>":
                if sheet.cell(line, column_time).value == "":
                    test = (40, 0, 0, 0, 38, 53)
                else:
                    raw_time = sheet.cell(line, column_time).value
                    if isinstance(raw_time, str):
                        raw_time = raw_time.split('.')[0]
                        split_time = raw_time.split(":")
                        try:
                            test = (0, 0, 0, int(split_time[0]), int(split_time[1]), int(split_time[2]))
                        except Exception:
                            test = (40, 0, 0, 0, 38, 53)
                    else:
                        try:
                            test = xlrd.xldate.xldate_as_tuple(raw_time, sheet.book.datemode)
                        except Exception:
                            test = (40, 0, 0, 0, 38, 53)

                try:
                    lap = int(sheet.cell_value(line, column_lap))
                except Exception:
                    lap = 0
                self.results[hash_race].scratch[member] = {
                    "team": str(sheet.cell_value(line, column_team)),
                    "lap": int(lap),
                    "time": test,
                    "cat": self.race_cat,
                }

    def parse_results_race(self, file_url, season):
        try:
            r = requests.get(file_url, verify=False)
            if r.status_code == 200:
                with open(TEMP_XLS_FILE, 'wb') as output:
                    output.write(r.content)

                coureurbook = xlrd.open_workbook(TEMP_XLS_FILE)
                self.parse_results_race_sheet(coureurbook, 0, season)
                self.parse_results_race_sheet(coureurbook, 1, season)
                self.parse_results_race_sheet(coureurbook, 2, season)
                self.parse_results_race_sheet(coureurbook, 3, season)
                self.parse_results_race_sheet(coureurbook, 4, season)
                hash_race = self.get_hash_race()

                if len(self.results[hash_race].scratch) > 0:
                    self.results[hash_race].scratch = sorted(self.results[hash_race].scratch.items(), key=sorted_algo,
                                                             reverse=False)
                    for res in self.results[hash_race].scratch:
                        res[1]["time"] = (
                            str(res[1]["time"][3]) + ":" + str(res[1]["time"][4]) + ":" + str(res[1]["time"][5]))

                return True
            return False
        except requests.exceptions.ConnectionError:
            print("Connection problem with " + file_url)
            return False

    def set_race_date(self, line):
        date = re.search(r"(.*)(\d\d\/\d\d\/\d\d\d\d)(.*)", line)
        if date:
            date = re.search(r"(\d\d)\/(\d\d)\/(\d\d\d\d)", date.group(2))
            self.race_date = date.group(3) + "/" + date.group(2) + "/" + date.group(1)

    def set_race_infos(self, line):
        reg = re.search(r"(.*)\/(\d\d\d\d)\/(.*)\/(.*)", line)
        if reg:
            self.race_name = reg.group(3)
            self.race_type = reg.group(1)
            self.race_year = reg.group(2)

    def create_post_race(self):
        hash_race = self.get_hash_race()
        if len(self.results) == 0:
            return
        if not any(self.results[hash_race].categories.get(cat_key) for cat_key in CAT_LABELS):
            return
        file_name = self.race_date.replace("/", "-") + "-" + self.race_type.replace(" ", "") + self.race_name.replace(
            " ", "-") + ".md"
        print("[NEW POST] : " + file_name)
        try:
            sync_drive.create_race_folder(self.race_year, self.race_type, self.race_name, self.race_date)
        except Exception as e:
            print(f"[DRIVE] Erreur création dossier : {e}")
        with open(os.path.join(POSTS_DIR, file_name), "w", encoding='utf8') as outfile:
            outfile.write("---\n")
            outfile.write("layout: post\n")
            outfile.write("title: " + self.race_type + " - " + self.race_name + " - " + self.race_year + "\n")
            outfile.write("date: " + self.race_date.replace("/", "-") + "\n")
            outfile.write("category: " + self.race_type + "\n")
            tag = self.race_type
            if self.race_type == "Cyclo Cross":
                tag = "cyclo-cross"
            outfile.write("tags: " + tag + "\n")
            if self.race_type == "Cyclo Cross":
                outfile.write("image: assets/img/blog/cx.png\n")
            elif self.race_type == "VTT":
                outfile.write("image: assets/img/blog/vtt.png\n")
            elif self.race_type == "Route":
                outfile.write("image: assets/img/blog/road.png\n")
            outfile.write("---\n")

            for cat_key, label in CAT_LABELS.items():
                result_to_display = self.results[hash_race].categories.get(cat_key, {})
                count = self.results[hash_race].riders_count.get(cat_key, 0)
                if result_to_display:
                    participants_label = "participantes" if cat_key == "Féminines" else "participants"
                    outfile.write(f"\n### {label}\n")
                    outfile.write(f"{count} {participants_label}\n")
                    for member, position in result_to_display.items():
                        display_result_line_with_link(outfile, member, position)

            self.print_scratch_results(outfile, hash_race)
            self.results = {}

    def print_scratch_results(self, outfile, hash_race):
        nb_line = 1
        has_categories = any(self.results[hash_race].categories.get(cat_key) for cat_key in CAT_LABELS)
        if has_categories and self.results[hash_race].scratch:
            outfile.write("\n### Scratch\n")
            outfile.write(str(len(self.results[hash_race].scratch)) + " participants\n\n")
            print_scratch_results_header(outfile)

            for line in self.results[hash_race].scratch:
                if line[1]["team"] == "TEAM SPECIALIZED LILLE":
                    print_line_table(outfile, True, str(nb_line), get_member_with_link(line[0]), line[1]["team"],
                                     line[1]["lap"], line[1]["cat"], line[1]["time"])
                else:
                    print_line_table(outfile, False, str(nb_line), line[0], line[1]["team"], line[1]["lap"],
                                     line[1]["cat"], line[1]["time"])

                nb_line += 1

    def parse_race_payload(self, res, season):
        current_date = datetime.now().strftime("%Y/%m/%d")
        for line in res:
            if "/" in line:
                self.set_race_date(line)
            if "Classements.xls" in line:
                file = re.search(r"(.*)='(.*)'(.*)", line).group(2)
                self.set_race_infos(file)
                if file not in self.races_parsed and self.race_date <= current_date:
                    url = base + file
                    print(url)
                    if self.parse_results_race(url, season):
                        self.races_parsed.append(file)
                        self.display_race_infos()
                        self.create_post_race()

    def generate_results(self, year):
        self.races_parsed = load_races_parsed()
        myobj = {'saison': year}

        r = requests.post('https://cyclismeufolep5962.fr/calResVTT.php', verify=False, data=myobj).text.splitlines()
        self.parse_race_payload(r, year)
        r = requests.post('https://cyclismeufolep5962.fr/calResCross.php', verify=False, data=myobj).text.splitlines()
        self.parse_race_payload(r, year)
        r = requests.post('https://cyclismeufolep5962.fr/calResRoute.php', verify=False, data=myobj).text.splitlines()
        self.parse_race_payload(r, year)
        save_races_parsed(self.races_parsed)

        return self.team
