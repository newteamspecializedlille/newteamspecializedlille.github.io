"""URL des articles de course : /resultats/<discipline>/<AAAA-MM-JJ>-<course>/

L'adresse est écrite dans le front matter de chaque post (`permalink:`) et se déduit de la date, de la discipline et du nom
de la course : la page d'un coureur la recalcule en Liquid (`_includes/rider-result-rows.html`) sans fichier intermédiaire.
Le slug doit rester identique au filtre Liquid `slugify: "latin"` (sans accents, minuscules, tirets).
"""
import os
import re
import unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# type de course (UFOLEP / nom des posts) -> dossier d'URL
URL_DIRS = {"Route": "route", "Clm": "route", "Cyclo Cross": "cyclo-cross", "CycloCross": "cyclo-cross", "VTT": "vtt"}


def slugify(text):
    """Comme le filtre Liquid `slugify: "latin"` : sans accents, minuscules, tout le reste devient « - »."""
    ascii_text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def post_permalink(race_type, date, race_name):
    """Adresse d'un article. date : AAAA-MM-JJ (ou AAAA/MM/JJ)."""
    return "/resultats/%s/%s-%s/" % (URL_DIRS[race_type], date.replace("/", "-"), slugify(race_name))


def front_matter_value(path, key):
    """Valeur d'une clé simple du front matter d'un post (None si absente)."""
    with open(path, "r", encoding="utf8") as post:
        text = post.read(4000)
    head = text.split("---")[1] if text.startswith("---") else ""
    for line in head.splitlines():
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip()
    return None


def post_url(file_name):
    """URL (sans domaine) d'un post d'après le `permalink` de son front matter (None si le post ou le permalink manque)."""
    base = os.path.basename(file_name)
    path = os.path.join(ROOT, "_posts", base if base.endswith(".md") else base + ".md")
    return front_matter_value(path, "permalink") if os.path.exists(path) else None
