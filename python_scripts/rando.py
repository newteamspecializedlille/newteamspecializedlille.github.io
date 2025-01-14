import requests
import csv
import json
from datetime import datetime

# ID de la feuille Google Sheet (tiré de l'URL)
SPREADSHEET_ID = '1ZxmM4AjqzwlpqFPdoUY68f5fLKYDoTGJjzFQwMWKDRE'

# URL pour télécharger le CSV
CSV_URL = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&id={SPREADSHEET_ID}'

def parse_date(date_str):
    """Parse une date au format attendu ou retourne une erreur si invalide."""
    formats = ['%d/%m/%Y']  # Gère les formats abrégés et longs
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date invalide : {date_str}")

def parse_time(time_str):
    """Parse une heure au format attendu ou retourne une erreur si invalide."""
    try:
        return datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        raise ValueError(f"Heure invalide : {time_str}")

def rando():
    # Télécharger le contenu du CSV
    response = requests.get(CSV_URL)
    response.raise_for_status()  # Vérifie les erreurs HTTP

    # Décoder le contenu CSV
    csv_data = response.text.splitlines()
    reader = csv.DictReader(csv_data)  # Utilise les noms de colonnes comme clés

    # Parser et afficher les données
    parsed_data = []
    for row in reader:
        try:
            parsed_row = {
                "date": parse_date(row["Date"]).strftime('%Y-%m-%d'),
                "start": row["Lieu de depart"],
                "map": row["Parcours"],
                "km": row["Km"],
                "time": parse_time(row["Heure"]).strftime('%H:%M'),
            }
            parsed_data.append(parsed_row)
        except (ValueError, KeyError) as e:
            print(f"Erreur lors du parsing de la ligne : {row} -> {e}")
    parsed_data = sorted(parsed_data, key=lambda x: (x["date"], x["time"]))


    with open('../_data/cyclo_calendar.json', 'w') as json_file:
        json.dump(parsed_data, json_file, indent=4)

    print("Données parsées sauvegardées dans 'cyclo_calendar.json'")

if __name__ == '__main__':
    rando()