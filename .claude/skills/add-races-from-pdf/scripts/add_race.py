#!/usr/bin/env python3
"""Ajoute UNE course à partir d'un PDF de classement, avec le même code que la CI (python_scripts/parse_results.py).

Usage :
  python3 add_race.py --pdf CHEMIN.pdf --type "Cyclo Cross"|VTT|Route --name NOM --date AAAA-MM-JJ \
                      [--year AAAA] [--championship "Championnat Nord"]
"""
import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SCRIPTS = os.path.join(ROOT, "python_scripts")
START_DIR = os.getcwd()  # pour résoudre un chemin de PDF relatif
sys.path.insert(0, SCRIPTS)
os.chdir(SCRIPTS)  # les modules de la CI utilisent des chemins relatifs (../_data, ../_posts)

import parse_results  # noqa: E402
import team_members  # noqa: E402


def default_year(race_type, date):
    year, month = int(date[:4]), int(date[5:7])
    if race_type == "Route":
        return str(year)
    return str(year + 1 if month >= 8 else year)  # cyclo-cross / VTT : saison année+1 dès août


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--type", required=True, choices=["Cyclo Cross", "VTT", "Route"])
    ap.add_argument("--name", required=True, help="nom de la course tel qu'il apparaît sur le calendrier UFOLEP")
    ap.add_argument("--date", required=True, help="AAAA-MM-JJ")
    ap.add_argument("--year", help="année de la saison dans la clé (défaut : calculée)")
    ap.add_argument("--championship", default="", help="ex. « Championnat Nord » (vide = course normale)")
    args = ap.parse_args()

    year = args.year or default_year(args.type, args.date)
    team = team_members.load_team_from_file({})
    parser = parse_results.ParseResults(team, {})
    team = parser.add_race_from_pdf(os.path.abspath(os.path.join(START_DIR, args.pdf)), args.type, args.name, args.date.replace("-", "/"),
                                    year, args.championship)
    team_members.update_team_file(team)
    print("course ajoutée : vérifier `git diff --stat`, le post dans _posts/ et les alertes [ALERTE] ci-dessus")


if __name__ == "__main__":
    main()
