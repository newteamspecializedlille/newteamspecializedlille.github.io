from datetime import datetime, timedelta

import os
import copy
import hashlib
import tempfile
import requests
import re
from bs4 import BeautifulSoup
import team_members
import race_results
import pdf_results
import urllib3
import json
import urllib.parse
import sync_drive
import site_links

base = "https://www.cyclismeufolep5962.fr/"
HTTP_TIMEOUT = 30
# dossier des PDF de classement (resultats_pdf/{cx,vtt,route}/<NOM DE LA COURSE>.pdf)
PDF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resultats_pdf")
CALENDAR_PAGES = {"calResVTT.php": "VTT", "calResCross.php": "Cyclo Cross", "calResRoute.php": "Route"}
# classe CSS de la ligne du calendrier UFOLEP -> type de course (lignes « Course » = course normale)
CHAMPIONSHIPS = {
    "Departemental Nord": "Championnat Nord",                  # bleu
    "Departemental Pas de Calais": "Championnat Pas-de-Calais",  # vert
    "Regional": "Championnat Département",                     # jaune
    "National": "Championnat National",                        # blanc
}
# nom du calendrier -> nom historique de la course (garde les liens des posts et de team.json)
ALIASES_FILE = "../_data/race_aliases.json"
# "AAAA/MM/JJ|NOM" -> type de course (affiché dans les pages du site)
# empreinte SHA-256 du dernier PDF lu pour chaque course : détecte un classement corrigé par UFOLEP
PDF_HASHES_FILE = "../_data/pdf_hashes.json"
# une course est revérifiée (PDF re-téléchargé) pendant ce nombre de jours après sa date
RECHECK_DAYS = int(os.getenv("RECHECK_DAYS", "21"))
# clés du front matter gérées par le script (les autres, ex. `images:` ajoutées par upload_photos, sont conservées)
POST_FRONT_MATTER_KEYS = {"layout", "title", "date", "category", "permalink", "championship", "tags", "image"}
column_result = 0
column_name = 1
column_team = 2
column_lap = 3
column_time = 4
YOUNG_CATEGORIES = ["Minimes", "Benjamins", "Pupilles", "Poussins"]
# sections d'un post, dans l'ordre d'affichage : (catégorie du PDF, titre de la section, mot après le nombre de partants)
POST_SECTIONS = [
    ("1ère", "1ère Catégorie", "participants"),
    ("2ème", "2ème Catégorie", "participants"),
    ("3ème", "3ème Catégorie", "participants"),
    ("Féminines", "Féminines", "participantes"),
    ("Cadets", "Cadets", "participants"),
    ("Seniors A", "VTT Sénior A", "participants"),
    ("Seniors B", "VTT Sénior B", "participants"),
    ("Vétérans A", "VTT Vétérans A", "participants"),
    ("Vétérans B", "VTT Vétérans B", "participants"),
    ("Vétérans C", "VTT Vétérans C", "participants"),
] + [(category, category, "participants") for category in YOUNG_CATEGORIES]
POST_CATEGORIES = {section[0] for section in POST_SECTIONS}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def display_result_line_with_link(outfile, team_member, position):
    outfile.write("- " + get_member_with_link(team_member) + " : " + str(position) + "\n")


def get_member_with_link(team_member):
    link = "/coureurs/"
    return "[" + team_member + "](" + link + team_member.replace(" ", "").lower() + ")"


def print_scratch_results_header(outfile):
    outfile.write("| Place | Nom | Team | Tours | Catégorie | Temps |\n")
    outfile.write("|---|---|---|---|---|---|\n")


def return_result(sheet, line):
    val = sheet.cell(line, column_result).value
    if val == "Ab" or val == "AB" or val == "":
        return val
    return int(val)


DISCIPLINE_BY_TYPE = {"Cyclo Cross": "cx", "VTT": "vtt", "Route": "road"}


def to_rank_status(value):
    """Place lue dans le PDF -> (rank, status) : (7, None) ; abandon ou place absente -> (None, "AB")."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value, None
    return None, "AB"


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


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf8") as json_file:
        return json.load(json_file)


def save_json(path, data):
    with open(path, "w", encoding="utf8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
        json_file.write("\n")


def championship_label(css_classes):
    """Type de course d'après les classes CSS de la ligne (None pour une course normale)."""
    css = " ".join(css_classes).replace("tdCal", "").strip()
    if css.startswith("National"):
        css = "National"
    return CHAMPIONSHIPS.get(css)


def parse_calendar(html):
    """Lit la page calendrier UFOLEP : [{date AAAA/MM/JJ, pdf (lien relatif), championship}]."""
    rows = []
    for tr in BeautifulSoup(html, "html.parser").find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue
        date = re.search(r"(\d\d)/(\d\d)/(\d{4})", cells[0].get_text())
        if not date:
            continue
        link = next((a["href"] for a in cells[-1].find_all("a", href=True)
                     if a["href"].lower().endswith("classements.pdf")), None)
        rows.append({"date": date.group(3) + "/" + date.group(2) + "/" + date.group(1), "pdf": link,
                     "championship": championship_label(cells[0].get("class", []))})
    return rows


def default_seasons(today, cx_override=None, road_override=None):
    """Saison de chaque calendrier UFOLEP.

    Cyclo-cross / VTT : année+1 dès août (novembre 2026 -> 2027). Route : année civile (août-septembre 2026 -> 2026).
    """
    cx_year = cx_override or str(today.year + 1 if today.month >= 8 else today.year)
    road_year = road_override or str(today.year)
    return {"calResVTT.php": cx_year, "calResCross.php": cx_year, "calResRoute.php": road_year}


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as pdf:
        for chunk in iter(lambda: pdf.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preserved_front_matter(path):
    """Lignes du front matter d'un post existant à conserver (clés inconnues du script, ex. `images:` + sa liste)."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf8") as post:
        lines = post.read().split("\n")
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return []
    kept, keeping = [], False
    for line in lines[1:lines.index("---", 1)]:
        key = re.match(r"^([A-Za-z_][\w-]*):", line)
        if key:
            keeping = key.group(1) not in POST_FRONT_MATTER_KEYS
        if keeping:
            kept.append(line)
    return kept


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


class _PdfBook:
    """Classeur construit à partir des feuilles d'un PDF."""

    def __init__(self, sheets):
        self._sheets = sheets
        self.nsheets = len(sheets)

    def sheet_by_index(self, index):
        return self._sheets[index]


class ParseResults:
    race_date = ""
    race_name = ""
    race_type = ""
    race_year = ""
    race_championship = ""
    aliases = {}
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
        self.used_pdfs = set()

    def display_race_infos(self):
        print("__________________________________________________________________________")
        print(
            "Type: " + self.race_type + ", name: " + self.race_name + ", date: " + self.race_date + "(" + self.race_year + ")")
        print("__________________________________________________________________________")

    def get_hash_race(self):
        return self.race_type + "/" + self.race_year + "/" + self.race_name

    def is_participant_row(self, sheet, line):
        """Une ligne compte comme participant dès que le nom est renseigné (le club peut être absent du PDF)."""
        return line > 1 and str(sheet.cell(line, column_name).value) != ""

    def is_team_member(self, sheet, line):
        if line <= 1:
            return False
        if "TEAM SPECIALIZED LILLE" in str(sheet.cell(line, column_team).value):
            return True

        elif str(sheet.cell(line, column_team).value) == "":

            if sheet.cell(line, column_result).value == "Ab" or sheet.cell(line, column_result).value == "AB":
                member = sheet.cell(line, column_name).value
                if self.find_team_key(str(member).upper()) in self.team:
                    return True
        return False

    def parse_results_race_sheet(self, coureurbook, sheet, season):
        sheet_index = sheet
        sheet = coureurbook.sheet_by_index(sheet)
        self.race_cat = sheet.name
        hash_race = self.get_hash_race()
        scratch_enable = check_if_scratch_enable(sheet) and sheet.scratch_eligible
        if hash_race not in self.results:
            self.results[hash_race] = race_results.RaceResults(hash_race)
        participants = sum(1 for line in range(sheet.nrows) if self.is_participant_row(sheet, line))
        for line in range(sheet.nrows):
            if self.is_participant_row(sheet, line) and self.race_cat in POST_CATEGORIES:
                self.results[hash_race].add_rider(self.race_cat)
            if self.is_team_member(sheet, line):
                # les noms des licenciés du club sont stockés en majuscules (ex: "FONTAINE Hector" -> "FONTAINE HECTOR")
                member = self.find_team_key(str(sheet.cell(line, column_name).value).upper())
                if member not in self.team:
                    print("[ALERTE] " + self.race_name + " / " + self.race_cat + " : nouveau membre créé « " + member
                          + " » (club « TEAM SPECIALIZED LILLE » dans le PDF) : vérifier qu'il ne s'agit pas d'un "
                          + "membre existant mal orthographié")
                    self.team[member] = team_members.TeamMember(member)
                discipline = DISCIPLINE_BY_TYPE.get(self.race_type)
                # un ancien membre (active: false) apparaît dans le post mais ses résultats ne sont plus enregistrés
                if discipline and self.team[member].active:
                    rank, status = to_rank_status(return_result(sheet, line))
                    self.team[member].upsert_result(discipline, season, team_members.make_result(
                        self.race_date.replace("/", "-"), self.race_name, self.race_cat, rank, status, participants,
                        self.race_championship))
                if self.race_cat in POST_CATEGORIES:
                    self.results[hash_race].add_team_result(self.race_cat, member, return_result(sheet, line))
            member = sheet.cell(line, column_name).value
            if member != "" and line > 1 and scratch_enable and str(type(member)) == "<class 'str'>":
                if sheet.cell(line, column_time).value == "":
                    test = (40, 0, 0, 0, 38, 53)
                else:

                    raw_time = str(sheet.cell(line, column_time).value).split('.')[0]  # sans les centièmes
                    split_time = raw_time.split(":")
                    try:
                        test = (0, 0, 0, int(split_time[0]), int(split_time[1]), int(split_time[2]))
                    except Exception:
                        test = (40, 0, 0, 0, 38, 53)

                try:
                    lap = int(sheet.cell_value(line, column_lap))
                except Exception:
                    lap = 0
                self.results[hash_race].scratch[member] = {"team": str(sheet.cell_value(line, column_team)),
                                                           "lap": int(lap), "time": test, "cat": self.race_cat}

    def finalize_scratch(self, hash_race):
        """Trie le scratch (tours décroissants puis temps) et formate les temps."""
        if len(self.results[hash_race].scratch) > 0:
            self.results[hash_race].scratch = sorted(self.results[hash_race].scratch.items(), key=sorted_algo,
                                                     reverse=False)
            for res in self.results[hash_race].scratch:
                res[1]["time"] = "%d:%02d:%02d" % (res[1]["time"][3], res[1]["time"][4], res[1]["time"][5])

    def parse_results_race_pdf(self, pdf_path, season):
        """Analyse un PDF de classement (une feuille par catégorie)."""
        sheets = pdf_results.extract_sheets(pdf_path, roster=self.active_names())
        if not sheets:
            print("[PDF] aucune feuille exploitable dans " + pdf_path)
            return False
        for sheet_name, name, club, close in pdf_results.suspect_names(sheets, self.active_names()):
            print("[ALERTE] " + self.race_name + " / " + sheet_name + " : « " + name + " » (club : " + (club or "?")
                  + ") ressemble au membre « " + close + " » mais n'est pas reconnu : orthographe à vérifier")
        book = _PdfBook(sheets)
        for index in range(book.nsheets):
            self.parse_results_race_sheet(book, index, season)
        self.finalize_scratch(self.get_hash_race())
        return True

    def active_names(self):
        """Noms des membres actuels (les anciens membres ne sont pas reconnus dans les PDF)."""
        return [name for name, member in self.team.items() if member.active]

    def find_team_key(self, member):
        """Retrouve la clé existante d'un membre malgré accents/ordre des mots."""
        if member in self.team:
            return member
        wanted = pdf_results.name_key(member)
        for key in self.team:
            if pdf_results.name_key(key) == wanted:
                return key
        return member

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
        if not any(self.results[hash_race].team.values()):
            return
        file_name = self.post_file_name()
        post_path = "../_posts/" + file_name
        extra_front_matter = preserved_front_matter(post_path)
        if os.path.exists(post_path):
            # post déjà publié : mis à jour sans notification (les photos et autres clés du front matter sont gardées)
            print("[MAJ] post mis à jour : " + file_name)
        else:
            print("[NEW POST] : " + file_name)
            try:
                sync_drive.create_race_folder(self.race_year, self.race_type, self.race_name, self.race_date)
            except Exception as e:
                print(f"[DRIVE] Erreur création dossier : {e}")
        with open(post_path, "w", encoding='utf8') as outfile:
            outfile.write("---\n")
            outfile.write("layout: post\n")
            outfile.write("title: " + self.race_type + " - " + self.race_name + " - " + self.race_year + "\n")
            outfile.write("date: " + self.race_date.replace("/", "-") + "\n")
            outfile.write("category: " + self.race_type + "\n")
            outfile.write("permalink: " + site_links.post_permalink(self.race_type, self.race_date, self.race_name) + "\n")
            if self.race_championship:
                outfile.write("championship: " + self.race_championship + "\n")
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
            for line in extra_front_matter:
                outfile.write(line + "\n")
            outfile.write("---\n")

            for category, heading, word in POST_SECTIONS:
                team_results = self.results[hash_race].team.get(category, {})
                if not team_results:
                    continue
                outfile.write("\n### " + heading + "\n")
                outfile.write(str(self.results[hash_race].riders.get(category, 0)) + " " + word + "\n")
                for member, result in team_results.items():
                    display_result_line_with_link(outfile, member, result)

            self.print_scratch_results(outfile, hash_race)
            self.results = {}

    def print_scratch_results(self, outfile, hash_race):
        nb_line = 1
        res = self.results[hash_race]
        # le scratch n'est publié que si l'équipe a un résultat dans une catégorie « adultes » (pas seulement les jeunes)
        has_team_results = any(res.team.get(category) for category in POST_CATEGORIES
                               if category not in YOUNG_CATEGORIES)
        if has_team_results and len(res.scratch) > 0:
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

    def post_file_name(self):
        return self.race_date.replace("/", "-") + "-" + self.race_type.replace(" ", "") + self.race_name.replace(
            " ", "-") + ".md"

    def download_pdf(self, pdf_href):
        """Télécharge le Classements.pdf publié sur le site UFOLEP (None si absent)."""
        url = urllib.parse.quote(base + pdf_href, safe=':/', encoding=None, errors=None)
        try:
            r = requests.get(url, verify=False, timeout=HTTP_TIMEOUT)
        except requests.exceptions.RequestException:
            print("[PDF] connexion impossible : " + url)
            return None
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            return None
        fd, path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, "wb") as output:
            output.write(r.content)
        return path

    def fetch_race_pdf(self, pdf_href, calendar_name):
        """PDF d'une course : fichier déposé dans resultats_pdf/ (prioritaire), sinon téléchargé depuis UFOLEP.
        Retourne (chemin, fichier_temporaire) ou (None, False)."""
        pdf = pdf_results.find_pdf(PDF_DIR, self.race_type, calendar_name)
        if pdf:
            self.used_pdfs.add(os.path.abspath(pdf))
            return pdf, False
        downloaded = self.download_pdf(pdf_href)
        return downloaded, downloaded is not None

    def load_race(self, pdf_href, calendar_name, season, key=None):
        """Lit une nouvelle course (et mémorise l'empreinte de son PDF)."""
        path, temporary = self.fetch_race_pdf(pdf_href, calendar_name)
        if not path:
            return False
        print("[PDF] " + (pdf_href if temporary else path))
        try:
            loaded = self.parse_results_race_pdf(path, season)
            if loaded and key:
                self.pdf_hashes[key] = file_sha256(path)
            return loaded
        finally:
            if temporary:
                os.remove(path)

    def purge_race_results(self, season):
        """Retire des membres les résultats de la course courante (avant de la relire)."""
        discipline = DISCIPLINE_BY_TYPE[self.race_type]
        date = self.race_date.replace("/", "-")
        for member in self.team.values():
            member.remove_race_results(discipline, season, date, self.race_name)

    def refresh_race(self, pdf_href, calendar_name, key, season):
        """Course récente déjà traitée : relit son PDF s'il a changé (classement corrigé par UFOLEP)."""
        path, temporary = self.fetch_race_pdf(pdf_href, calendar_name)
        if not path:
            return
        backup = copy.deepcopy(self.team)
        try:
            digest = file_sha256(path)
            if self.pdf_hashes.get(key) == digest:
                return
            print("[MAJ] PDF nouveau ou modifié, course relue : " + key)
            self.purge_race_results(season)
            self.results = {}
            if self.parse_results_race_pdf(path, season):
                self.pdf_hashes[key] = digest
                self.display_race_infos()
                self.create_post_race()
            else:
                raise ValueError("PDF illisible")
        except Exception as e:  # on garde les résultats précédents
            print("[ERROR] relecture de " + key + " impossible, résultats conservés : " + repr(e))
            self.team.clear()
            self.team.update(backup)
            self.results = {}
        finally:
            if temporary:
                os.remove(path)

    def is_recent(self):
        limit = (datetime.now() - timedelta(days=RECHECK_DAYS)).strftime("%Y/%m/%d")
        return self.race_date >= limit

    def set_race_type_on_results(self):
        """Reporte le type de championnat du calendrier sur les résultats déjà enregistrés de la course (idempotent)."""
        discipline = DISCIPLINE_BY_TYPE.get(self.race_type)
        if not self.race_championship or not discipline:
            return
        date = self.race_date.replace("/", "-")
        for member in self.team.values():
            member.set_race_type(discipline, date, self.race_name, self.race_championship)

    def set_championship_on_post(self):
        """Ajoute/met à jour `championship:` dans le front matter d'un post existant (idempotent)."""
        path = "../_posts/" + self.post_file_name()
        if not self.race_championship or not os.path.exists(path):
            return
        with open(path, "r", encoding="utf8") as post:
            lines = post.read().split("\n")
        if lines[0] != "---" or "---" not in lines[1:]:
            return
        end = lines.index("---", 1)
        wanted = "championship: " + self.race_championship
        front = [line for line in lines[1:end] if not line.startswith("championship:")]
        front.insert(next((i + 1 for i, line in enumerate(front) if line.startswith("category:")), len(front)), wanted)
        new = "\n".join(["---"] + front + lines[end:])
        if new != "\n".join(lines):
            with open(path, "w", encoding="utf8") as post:
                post.write(new)

    def process_calendar(self, html, season):
        """Parcourt un calendrier UFOLEP : date, type de course et lien du PDF de chaque course."""
        current_date = datetime.now().strftime("%Y/%m/%d")
        for row in parse_calendar(html):
            if not row["pdf"]:
                continue  # pas encore de résultats publiés
            self.race_date = row["date"]
            self.set_race_infos(row["pdf"])
            calendar_name = self.race_name
            alias_key = self.race_type + "/" + self.race_year + "/" + calendar_name
            self.race_name = self.aliases.get(alias_key, calendar_name)
            self.race_championship = row["championship"]
            self.set_race_type_on_results()
            self.set_championship_on_post()
            key = row["pdf"]
            # déjà traitée sous son nom historique (alias) ?
            legacy_key = self.race_type + "/" + self.race_year + "/" + self.race_name + "/Classements.pdf"
            if legacy_key in self.races_parsed:
                key = legacy_key
            if key in self.races_parsed:
                if self.is_recent():
                    self.refresh_race(row["pdf"], calendar_name, key, season)
                else:
                    local_pdf = pdf_results.find_pdf(PDF_DIR, self.race_type, calendar_name)
                    if local_pdf:  # PDF déposé à la main pour une course ancienne : rattaché, pas d'avertissement
                        self.used_pdfs.add(os.path.abspath(local_pdf))
                continue
            if self.race_date > current_date:
                continue
            try:
                loaded = self.load_race(row["pdf"], calendar_name, season, key)
            except Exception as e:  # une course en erreur ne doit pas bloquer les autres
                print("[ERROR] " + key + " : " + repr(e))
                self.results = {}
                continue
            if loaded:
                self.races_parsed.append(key)
                self.display_race_infos()
                self.create_post_race()

    def add_race_from_pdf(self, pdf_path, race_type, race_name, race_date, year, championship=""):
        """Ajoute une course à partir d'un PDF local, avec exactement le traitement de la CI
        (utilisé par le skill add-races-from-pdf quand la CI ne peut pas rattacher le PDF au calendrier).

        race_date : AAAA/MM/JJ ; year : année de la saison dans la clé (ex. cyclo-cross 2026-27 -> 2027).
        """
        self.races_parsed = load_races_parsed()
        self.aliases = load_json(ALIASES_FILE)
        self.pdf_hashes = load_json(PDF_HASHES_FILE)
        self.race_type, self.race_name, self.race_year = race_type, race_name, str(year)
        self.race_date, self.race_championship = race_date, championship
        key = race_type + "/" + str(year) + "/" + race_name + "/Classements.pdf"
        if key in self.races_parsed:
            raise ValueError("course déjà traitée : " + key)
        self.results = {}
        if not self.parse_results_race_pdf(pdf_path, str(year)):
            raise ValueError("PDF illisible : " + pdf_path)
        self.races_parsed.append(key)
        save_races_parsed(self.races_parsed)
        self.pdf_hashes[key] = file_sha256(pdf_path)
        save_json(PDF_HASHES_FILE, dict(sorted(self.pdf_hashes.items())))
        self.display_race_infos()
        self.create_post_race()
        return self.team

    def fetch_calendar(self, page, year):
        try:
            r = requests.post('https://cyclismeufolep5962.fr/' + page, verify=False, data={'saison': year},
                              timeout=HTTP_TIMEOUT)
            return r.content.decode('utf-8')
        except requests.exceptions.RequestException as e:
            print("[CALENDRIER] " + page + " indisponible : " + repr(e))
            return ""

    def generate_results(self, seasons):
        """seasons : {page calendrier: année de la saison} (route = année civile, CX/VTT = année+1 dès août)."""
        self.races_parsed = load_races_parsed()
        self.used_pdfs = set()
        self.aliases = load_json(ALIASES_FILE)
        self.pdf_hashes = load_json(PDF_HASHES_FILE)
        hashes_before = dict(self.pdf_hashes)

        # calendriers UFOLEP : date / type / lien du PDF de chaque course
        pages = os.getenv("CALENDARS", ",".join(CALENDAR_PAGES)).split(",")
        for page in pages:
            season = str(seasons[page])
            self.process_calendar(self.fetch_calendar(page, season), season)
        save_races_parsed(self.races_parsed)
        if self.pdf_hashes != hashes_before:
            save_json(PDF_HASHES_FILE, dict(sorted(self.pdf_hashes.items())))

        for pdf in pdf_results.list_pdfs(PDF_DIR):
            if os.path.abspath(pdf) not in self.used_pdfs:
                print("[PDF] non rattaché à une course du calendrier (nom du fichier à vérifier) : " + pdf)

        return self.team
