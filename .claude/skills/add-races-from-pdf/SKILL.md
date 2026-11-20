---
name: add-races-from-pdf
description: Ajoute des courses de cyclo-cross (ou VTT/route) au site à partir de PDF de classements UFOLEP (Classements exportés d'Excel en PDF) - crée le post dans _posts, met à jour _data/team.json et races.json (les classements challenge/boue se calculent au build). Utiliser quand l'utilisateur donne un ou plusieurs PDF de résultats à ajouter aux résultats.
---

# Ajouter des courses depuis un PDF

**Voie normale (recommandée)** : la CI télécharge et lit les `Classements.pdf` du site UFOLEP. Pour un PDF fourni à la main, le déposer dans
`resultats_pdf/{cx,vtt,route}/<NOM DE LA COURSE>.pdf` et pousser : la CI (`python_scripts/main.py` + `pdf_results.py`)
retrouve la course dans le calendrier UFOLEP (date/type/nom), crée le post, met à jour `team.json`/`races.json`
et notifie (voir `resultats_pdf/README.md` ; tests : `cd python_scripts && python -m unittest discover tests`).

**Voie manuelle** : seulement si la CI ne peut pas rattacher le PDF au calendrier. Le script `add_race.py` appelle exactement
le même code que la CI (`ParseResults.add_race_from_pdf`) : il lit le PDF, crée le post, met à jour `team.json`,
`races.json` (le type de championnat est porté par `raceType` dans `team.json`). Plus de saisie manuelle des résultats.

## 1. Repérer la course
Nom exact et date sur le calendrier UFOLEP (calResVTT.php / calResCross.php / calResRoute.php). Une ligne colorée = championnat
(bleu : Championnat Nord, vert : Championnat Pas-de-Calais, jaune : Championnat Département, blanc : Championnat National).

## 2. Lancer (une seule fois par course)
```bash
python3 .claude/skills/add-races-from-pdf/scripts/add_race.py --pdf "CHEMIN.pdf" --type "Cyclo Cross" \
    --name "COMINES" --date 2026-11-14 [--championship "Championnat Nord"]
```
- `--year` est calculé (route : année civile ; cyclo-cross/VTT : année+1 dès août) ; le préciser sinon.
- Une course déjà dans `races.json` (même saison, discipline et nom) est refusée.
- Lire les lignes `[ALERTE]` : un équipier au nom proche d'un membre existant mais non reconnu (faute d'orthographe), ou un
  nouveau membre créé. Accents, casse, tirets et ordre des mots sont ignorés pour reconnaître un membre.

## 3. Vérifier
`git diff --stat`, relire le post, puis démarrer le site (skill `serve-site-local`). Ne pas commiter sans demande.
Les dossiers Drive ne sont créés que si les identifiants Drive sont disponibles (sinon un message `[DRIVE]` est affiché).
L'adresse du post (`permalink:` du front matter, `/resultats/<discipline>/<AAAA-MM-JJ>-<course>/`) est écrite par le script ; la page d'un coureur la recalcule
depuis `team.json`, il n'y a pas de fichier de liens à mettre à jour.
