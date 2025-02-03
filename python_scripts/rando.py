import locale
from datetime import datetime
import requests
import csv
import json

# ID de la feuille Google Sheet (tiré de l'URL)
SPREADSHEET_ID = '1ZxmM4AjqzwlpqFPdoUY68f5fLKYDoTGJjzFQwMWKDRE'

# URL pour télécharger le CSV
CSV_URL = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&id={SPREADSHEET_ID}'

def parse_date(date_str):
    """Parse une date au format attendu ou retourne une erreur si invalide."""
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')  # Définit la locale en français
    formats = ['%d/%m/%Y', '%A %d %B %Y']  # Ajoute le format avec le jour de la semaine
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

    # Décoder le contenu CSV avec l'encodage UTF-8
    csv_data = response.content.decode('utf-8').splitlines()
    reader = csv.DictReader(csv_data)  # Utilise les noms de colonnes comme clés

    # Parser et afficher les données
    parsed_data = []
    for row in reader:
        try:
            parsed_row = {
                "date": parse_date(row["date"]).strftime('%Y-%m-%d'),
                "start": row.get("start", "Non définie"),
                "map": row.get("parcours", "Non définie"),
                "km": row.get("km", "Non définie"),
                "time": row.get("time", "Non définie")
            }
            parsed_data.append(parsed_row)
        except (ValueError, KeyError) as e:
            print(f"Erreur lors du parsing de la ligne : {row} -> {e}")
    parsed_data = sorted(parsed_data, key=lambda x: (x["date"], x["time"]))

    with open('../_data/cyclo_calendar.json', 'w', encoding='utf-8') as json_file:
        json.dump(parsed_data, json_file, indent=4, ensure_ascii=False)

    print("Données parsées sauvegardées dans 'cyclo_calendar.json'")

if __name__ == '__main__':
    rando()