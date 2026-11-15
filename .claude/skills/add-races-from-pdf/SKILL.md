---
name: add-races-from-pdf
description: Ajoute des courses de cyclo-cross (ou VTT/route) au site à partir de PDF de classements UFOLEP (Classements.xls exportés en PDF) - crée le post dans _posts, met à jour _data/team.json, le challenge boue/challenge et races_parsed.json. Utiliser quand l'utilisateur donne un ou plusieurs PDF de résultats à ajouter aux résultats.
---

# Ajouter des courses depuis un PDF

Normalement la CI (`python_scripts/main.py`) parse les xls du site UFOLEP. Ce skill sert quand on n'a que le PDF : il reproduit le même résultat à la main.

## 1. Lire le PDF
Utiliser `Read` sur le PDF (pas de pdftotext installé). Le texte est une suite de lignes (place, nom, club, tours, temps).
- Les **libellés de feuille sont placés APRÈS la liste** ("1re Cgorie" clôt la liste 1ère, etc.). Ordre des feuilles : 1ère, 2ème, 3ème, Féminines, Cadets, puis jeunes (Minimes, Benjamins...).
- Seules les **5 premières feuilles** (1ère, 2ème, 3ème, Féminines, Cadets) alimentent le scratch. Les jeunes sont ignorés.
- Les `AB` (abandons) sont à inclure : avec tours+temps s'ils sont indiqués, sinon 0 tour et temps `0:38:53` (le script gère).
- Les pages "ETAT TOUR PAR TOUR" à la fin sont inutiles. La date de la course s'y trouve (JJ/MM/AAAA).
- Le PDF perd les accents : les restaurer (Sébastien, Clément, Frédéric, Théo, Cédric, `TEAM BIKE CAMBRÉSIS - CATTENIÈRES`...) comme dans les posts existants (`_posts/*Verlinghem*`).
- Équipe : club `TEAM SPECIALIZED LILLE`. Relever la catégorie, la place (ou `Ab`) de chaque membre.

## 2. Écrire la spec JSON (dans le scratchpad)
```json
{"type": "Cyclo Cross", "year": "2027", "date": "2026-11-14", "name": "COMINES",
 "cats": {"1ère": [["NOM", "CLUB", 8, "0:48:21"], ["ABANDON SANS TEMPS", "CLUB"]], "2ème": [], "3ème": [], "Féminines": [], "Cadets": []},
 "team": {"3ème": [["MOULIN FELIX", 4], ["SCHULZ YANNICK", "Ab"]]}}
```
- `cats` : lignes dans l'ordre du PDF. Temps `h:mm:ss`.
- `team` : places réelles (le rang PDF), `"Ab"` pour abandon.
- `year` = année de la saison (ex. saison 2026-27 → `2027`, cf. `main.py`), `date` = date réelle.

## 3. Lancer
```bash
python3 .claude/skills/add-races-from-pdf/scripts/add_race.py spec.json
```
Le script : écrit `_posts/AAAA-MM-JJ-<Type><NOM>.md` (scratch trié tours puis temps), ajoute les résultats dans `_data/team.json` (+1 `course`), recalcule `_data/boue<year>.json` (cx/vtt) ou `challenge<year>.json` (route), et ajoute l'entrée dans `_data/races_parsed.json` pour éviter un doublon via la CI.
Ne lancer qu'UNE fois par course (le compteur `course` est incrémenté).

## 4. Vérifier
`git diff --stat`, relire le post, puis démarrer le site (skill `serve-site-local`). Ne pas commiter sans demande. Les dossiers Drive (`sync_drive`) ne sont pas créés.
