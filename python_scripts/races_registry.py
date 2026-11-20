"""Registre des courses déjà traitées : _data/races.json

{"races": [{"year": 2027, "cx": [{"date": "2026-11-14", "name": "COMINES", "sha": "<empreinte du PDF>"}], "vtt": [...]}]}

- une entrée présente = course déjà traitée (le PDF n'est pas relu tant qu'il ne change pas) ;
- `sha` : empreinte SHA-256 du dernier PDF lu (None = traitée, empreinte inconnue) : détecte un classement corrigé par UFOLEP ;
- seules les saisons en cours sont gardées (le script ne lit que le calendrier de la saison en cours) ; l'historique est dans git.
"""
import json
import os

DISCIPLINES = ("road", "cx", "vtt")


class RaceRegistry:
    def __init__(self):
        self.entries = {}  # (discipline, saison "2027", nom) -> {"date": "AAAA-MM-JJ" ou None, "sha": str ou None}

    @classmethod
    def load(cls, path):
        registry = cls()
        if not os.path.exists(path):
            return registry
        with open(path, "r", encoding="utf8") as source:
            data = json.load(source)
        for season in data.get("races", []):
            for discipline in DISCIPLINES:
                for race in season.get(discipline, []):
                    registry.entries[(discipline, str(season["year"]), race["name"])] = {
                        "date": race.get("date"), "sha": race.get("sha")}
        return registry

    def has(self, discipline, season, name):
        return (discipline, str(season), name) in self.entries

    def sha(self, discipline, season, name):
        entry = self.entries.get((discipline, str(season), name))
        return entry["sha"] if entry else None

    def set(self, discipline, season, name, date=None, sha=None):
        """Ajoute ou met à jour une course (date AAAA-MM-JJ ou AAAA/MM/JJ ; sha : None = inchangé pour une entrée existante)."""
        key = (discipline, str(season), name)
        entry = self.entries.setdefault(key, {"date": None, "sha": None})
        if date:
            entry["date"] = date.replace("/", "-")
        if sha:
            entry["sha"] = sha

    def touch_date(self, discipline, season, name, date):
        """Met à jour la date d'une course déjà enregistrée (la date vient du calendrier UFOLEP)."""
        if self.has(discipline, season, name):
            self.set(discipline, season, name, date)

    def prune(self, current_seasons):
        """Ne garde que les saisons en cours. current_seasons : {discipline: "2027"}."""
        self.entries = {key: value for key, value in self.entries.items()
                        if current_seasons.get(key[0]) is None or current_seasons[key[0]] == key[1]}

    def to_dict(self):
        seasons = {}
        for (discipline, season, name), entry in self.entries.items():
            seasons.setdefault(season, {}).setdefault(discipline, []).append(
                {"date": entry["date"], "name": name, "sha": entry["sha"]})
        races = []
        for season in sorted(seasons, reverse=True):
            item = {"year": int(season)}
            for discipline in DISCIPLINES:
                if discipline in seasons[season]:
                    item[discipline] = sorted(seasons[season][discipline], key=lambda r: (r["date"] or "", r["name"]))
            races.append(item)
        return {"races": races}

    def to_json(self):
        """JSON lisible : une course par ligne, saisons récentes en premier."""
        seasons = []
        for season in self.to_dict()["races"]:
            blocks = []
            for discipline in DISCIPLINES:
                if discipline in season:
                    rows = ",\n".join("        " + json.dumps(race, ensure_ascii=False) for race in season[discipline])
                    blocks.append('      "%s": [\n%s\n      ]' % (discipline, rows))
            seasons.append('    {\n      "year": %d%s\n    }' % (season["year"], "".join(",\n" + b for b in blocks)))
        return '{\n  "races": [\n%s\n  ]\n}\n' % ",\n".join(seasons)

    def save(self, path):
        """Écrit le fichier seulement s'il change (évite un commit inutile de la CI)."""
        new = self.to_json()
        if os.path.exists(path):
            with open(path, "r", encoding="utf8") as current:
                if current.read() == new:
                    return False
        with open(path, "w", encoding="utf8") as target:
            target.write(new)
        return True
