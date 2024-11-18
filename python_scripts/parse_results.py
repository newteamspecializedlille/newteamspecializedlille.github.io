from datetime import datetime

import requests
import re
import xlrd
import team_members
import race_results
import urllib3
import json

base = "https://cyclismeufolep5962.fr/"
column_result = 0
column_name = 1
column_team = 2
column_lap = 3
column_time = 4
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def display_result_line_with_link(outfile, team_member, position):
    outfile.write("- " + get_member_with_link(team_member) + " : " + str(position) + "\n")


def get_member_with_link(team_member):
    link = "https://teamspecializedlille.github.io/coureurs/"
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
    with open("../_data/races_parsed.json", "w", encoding='utf8') as outfile:
        outfile.write(json_object)


def load_races_parsed():
    races_parsed = []
    races_parsed_file = open("../_data/races_parsed.json", 'r')
    data = json.load(races_parsed_file)
    if len(data['races_parsed']) > 0:
        for race in data['races_parsed']:
            races_parsed.append(race)
    races_parsed_file.close()
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
    race_date = ""
    race_name = ""
    race_type = ""
    race_year = ""
    race_cat = ""
    races_parsed = []
    team = {}

    def __init__(self, team, results):
        self.team = team
        self.results = results
        self.race_date = ""
        self.race_name = ""
        self.race_type = ""
        self.race_year = ""
        self.races_parsed = []

    def display_race_infos(self):
        print("__________________________________________________________________________")
        print(
            "Type: " + self.race_type + ", name: " + self.race_name + ", date: " + self.race_date + "(" + self.race_year + ")")
        print("__________________________________________________________________________")

    def get_hash_race(self):
        return self.race_type + "/" + self.race_year + "/" + self.race_name

    def get_hash_individual_race(self):
        # year / race / cate /  => pos
        return self.race_date + "|" + self.race_name + "|" + self.race_cat

    def is_team_member(self, sheet, line):
        if line <= 1:
            return False
        if "TEAM SPECIALIZED LILLE" in str(sheet.cell(line, column_team).value):
            return True

        elif str(sheet.cell(line, column_team).value) == "":

            if sheet.cell(line, column_result).value == "Ab" or sheet.cell(line, column_result).value == "AB":
                member = sheet.cell(line, column_name).value
                if member in self.team:
                    return True
        return False

    def parse_results_race_sheet(self, coureurbook, sheet, season):
        sheet = coureurbook.sheet_by_index(sheet)
        self.race_cat = sheet.name
        hash_race = self.get_hash_race()
        scratch_enable = check_if_scratch_enable(sheet)
        if hash_race not in self.results:
            self.results[hash_race] = race_results.RaceResults(hash_race)
        for line in range(sheet.nrows):
            if str(sheet.cell(line, column_team).value) != "":
                if self.race_cat == "1ère":
                    self.results[hash_race].one_riders += 1
                elif self.race_cat == "2ème":
                    self.results[hash_race].two_riders += 1
                elif self.race_cat == "3ème":
                    self.results[hash_race].three_riders += 1
                elif self.race_cat == "Cadets":
                    self.results[hash_race].cadet_riders += 1
                elif self.race_cat == "Féminines":
                    self.results[hash_race].fem_riders += 1
                elif self.race_cat == "Séniors A":
                    self.results[hash_race].VTTSeniorsA_riders += 1
                elif self.race_cat == "Seniors B":
                    self.results[hash_race].VTTSeniorsB_riders += 1
                elif self.race_cat == "Vétérans A":
                    self.results[hash_race].VTTVeteransA_riders += 1
                elif self.race_cat == "Vétérans B":
                    self.results[hash_race].VTTVeteransB_riders += 1
                elif self.race_cat == "Vétérans C":
                    self.results[hash_race].VTTVeteransC_riders += 1
            if self.is_team_member(sheet, line):
                member = sheet.cell(line, column_name).value
                if member not in self.team:
                    self.team[member] = team_members.TeamMember(member)
                self.team[member].course += 1
                hash_individual = self.get_hash_individual_race()
                if self.race_type == "Cyclo Cross":
                    if self.team[member].cx.get(season) is None:
                        self.team[member].cx[season] = {}
                    self.team[member].cx[season][hash_individual] = return_result(sheet, line)
                elif self.race_type == "VTT":
                    if self.team[member].vtt.get(season) is None:
                        self.team[member].vtt[season] = {}
                    self.team[member].vtt[season][hash_individual] = return_result(sheet, line)
                elif self.race_type == "Route":
                    if self.team[member].road.get(season) is None:
                        self.team[member].road[season] = {}
                    self.team[member].road[season][hash_individual] = return_result(sheet, line)
                if self.race_cat == "1ère":
                    self.results[hash_race].one[member] = return_result(sheet, line)
                elif self.race_cat == "2ème":
                    self.results[hash_race].two[member] = return_result(sheet, line)
                elif self.race_cat == "3ème":
                    self.results[hash_race].three[member] = return_result(sheet, line)
                elif self.race_cat == "Cadets":
                    self.results[hash_race].cadet[member] = return_result(sheet, line)
                elif self.race_cat == "Féminines":
                    self.results[hash_race].fem[member] = return_result(sheet, line)
                elif self.race_cat == "Seniors A":
                    self.results[hash_race].VTTSeniorsA[member] = return_result(sheet, line)
                elif self.race_cat == "Seniors B":
                    self.results[hash_race].VTTSeniorsB[member] = return_result(sheet, line)
                elif self.race_cat == "Vétérans A":
                    self.results[hash_race].VTTVeteransA[member] = return_result(sheet, line)
                elif self.race_cat == "Vétérans B":
                    self.results[hash_race].VTTVeteransB[member] = return_result(sheet, line)
                elif self.race_cat == "Vétérans C":
                    self.results[hash_race].VTTVeteransC[member] = return_result(sheet, line)
            member = sheet.cell(line, column_name).value
            if member != "" and line > 1 and scratch_enable and str(type(member)) == "<class 'str'>":
                if sheet.cell(line, column_time).value == "":
                    test = (40, 0, 0, 0, 38, 53)
                else:

                    raw_time = sheet.cell(line, column_time).value
                    if isinstance(raw_time, str):
                        raw_time = raw_time.split('.')[0]  # Remove characters after the point
                        split_time = raw_time.split(":")
                        test = (0, 0, 0, int(split_time[0]), int(split_time[1]), int(split_time[2]))
                    else:
                        try:
                            test = xlrd.xldate.xldate_as_tuple(raw_time, sheet.book.datemode)
                        except Exception:
                            test = (40, 0, 0, 0, 38, 53)

                try:
                    lap = int(sheet.cell_value(line, column_lap))
                except Exception:
                    lap = 0
                self.results[hash_race].scratch[member] = {"team": str(sheet.cell_value(line, column_team)),
                                                           "lap": int(lap), "time": test, "cat": self.race_cat}

    def parse_results_race(self, file_url, season):
        try:
            r = requests.get(file_url, verify=False)
            if r.status_code == 200:
                output = open('test.xls', 'wb')
                output.write(r.content)

                coureurbook = xlrd.open_coureurbook('test.xls')
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
            else:
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
        if (len(self.results[hash_race].one.keys()) == 0 and len(self.results[hash_race].two.keys()) == 0 and len(
                self.results[hash_race].three.keys()) == 0 and len(self.results[hash_race].fem.keys()) == 0
                and len(self.results[hash_race].cadet.keys()) == 0 and len(
                    self.results[hash_race].VTTSeniorsA.keys()) == 0 and len(
                    self.results[hash_race].VTTSeniorsB.keys()) == 0 and len(
                    self.results[hash_race].VTTVeteransA.keys()) == 0
                and len(self.results[hash_race].VTTVeteransB.keys()) == 0 and len(
                    self.results[hash_race].VTTVeteransC.keys()) == 0):
            return
        file_name = self.race_date.replace("/", "-") + "-" + self.race_type.replace(" ", "") + self.race_name.replace(
            " ", "-") + ".md"
        print("[NEW POST] : " + file_name)
        with open("../_posts/" + file_name, "w", encoding='utf8') as outfile:
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
                outfile.write("image: assets/img/blog/cx.jpeg\n")
            elif self.race_type == "VTT":
                outfile.write("image: assets/img/blog/vtt.jpeg\n")
            elif self.race_type == "Route":
                outfile.write("image: assets/img/blog/road.jpeg\n")
            outfile.write("---\n")

            result_to_display = self.results[hash_race].one
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### 1ère Catégorie\n")
                outfile.write(str(self.results[hash_race].one_riders) + " participants\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])
            result_to_display = self.results[hash_race].two
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### 2ème Catégorie\n")
                outfile.write(str(self.results[hash_race].two_riders) + " participants\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])
            result_to_display = self.results[hash_race].three
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### 3ème Catégorie\n")
                outfile.write(str(self.results[hash_race].three_riders) + " participants\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])

            result_to_display = self.results[hash_race].fem
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### Féminines\n")
                outfile.write(str(self.results[hash_race].fem_riders) + " participantes\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])

            result_to_display = self.results[hash_race].cadet
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### Cadets\n")
                outfile.write(str(self.results[hash_race].cadet_riders) + " participants\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])

            result_to_display = self.results[hash_race].VTTSeniorsA
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### VTT Sénior A\n")
                outfile.write(str(self.results[hash_race].VTTSeniorsA_riders) + " participants\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])

            result_to_display = self.results[hash_race].VTTSeniorsB
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### VTT Sénior B\n")
                outfile.write(str(self.results[hash_race].VTTSeniorsB_riders) + " participants\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])

            result_to_display = self.results[hash_race].VTTVeteransA
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### VTT Vétérans A\n")
                outfile.write(str(self.results[hash_race].VTTVeteransA_riders) + " participants\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])

            result_to_display = self.results[hash_race].VTTVeteransB
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### VTT Vétérans B\n")
                outfile.write(str(self.results[hash_race].VTTVeteransB_riders) + " participants\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])

            result_to_display = self.results[hash_race].VTTVeteransC
            if len(result_to_display.keys()) > 0:
                outfile.write("\n### VTT Vétérans C\n")
                outfile.write(str(self.results[hash_race].VTTVeteransC_riders) + " participants\n")
            for line in result_to_display.keys():
                display_result_line_with_link(outfile, line, result_to_display[line])

            self.print_scratch_results(outfile, hash_race)
            self.results = {}

    def print_scratch_results(self, outfile, hash_race):
        nb_line = 1
        if (len(self.results[hash_race].VTTVeteransC.keys()) > 0 or len(
                self.results[hash_race].VTTVeteransB.keys()) > 0 or len(
            self.results[hash_race].VTTVeteransA.keys()) > 0 or len(
            self.results[hash_race].VTTSeniorsB.keys()) > 0 or
                len(self.results[hash_race].VTTSeniorsA.keys()) > 0 or len(
                    self.results[hash_race].one.keys()) > 0 or len(
                    self.results[hash_race].two.keys()) > 0 or len(self.results[hash_race].three.keys()) > 0 or len(
                    self.results[hash_race].cadet.keys()) > 0 or
                len(self.results[hash_race].fem.keys()) > 0 and self.results[hash_race].scratch.keys() > 0):
            outfile.write("\n### Scratch\n")
            outfile.write(str(len(self.results[hash_race].scratch)) + " participants\n\n")
            print_scratch_results_header(outfile)

            for line in self.results[hash_race].scratch:
                if line[1]["team"] == "TEAM SPECIALIZED LILLE":
                    print_line_table(outfile, True, str(nb_line), get_member_with_link(line[0]), line[1]["team"],
                                     line[1]["lap"],
                                     line[1]["cat"], line[1]["time"])
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

        # vtt
        r = requests.post('https://cyclismeufolep5962.fr/calResVTT.php', verify=False, data=myobj).text.splitlines()
        self.parse_race_payload(r, year)
        # cross
        r = requests.post('https://cyclismeufolep5962.fr/calResCross.php', verify=False, data=myobj).text.splitlines()
        self.parse_race_payload(r, year)
        # road
        r = requests.post('https://cyclismeufolep5962.fr/calResRoute.php', verify=False, data=myobj).text.splitlines()

        self.parse_race_payload(r, year)
        save_races_parsed(self.races_parsed)

        return self.team
