"""Lecture des classements UFOLEP au format PDF (export Excel -> PDF).

Chaque page de classement est transformée en « feuille » exposant la même API
minimale (nrows, cell, cell_value, row, name) utilisée par
`ParseResults.parse_results_race_sheet`.
"""
import difflib
import os
import re
import unicodedata

import pdfplumber

TEAM_CLUB = "TEAM SPECIALIZED LILLE"
SAME_LINE_TOL = 2.0      # écart de "top" toléré dans un même texte
ROW_TOL = 3.0            # écart de "top" toléré dans une même ligne
CELL_GAP = 1.0           # écart (pt) entre deux caractères = nouvelle cellule

TIME_RE = re.compile(r"^\d{1,2}:\d\d:\d\d([.:]\d+)?$")
PLACE_RE = re.compile(r"^(\d{1,3}|ab\w*(\s.*)?)$", re.I)
INT_RE = re.compile(r"^\d{1,2}$")
ECART_RE = re.compile(r"\d+'")  # écart type 02' 39'' 61

# feuilles éligibles au scratch
SCRATCH_SHEETS = {"1ère", "2ème", "3ème", "Féminines", "Cadets",
                  "Seniors A", "Seniors B", "Vétérans A", "Vétérans B", "Vétérans C"}


def strip_accents(text):
    return unicodedata.normalize("NFD", str(text)).encode("ascii", "ignore").decode()


def name_key(name):
    """Clé de comparaison de noms : sans accents/casse/tirets, ordre indifférent."""
    return " ".join(sorted(strip_accents(name).upper().replace("-", " ").split()))


AGE_RE = re.compile(r"(\d\d)\s*[/-]\s*(\d\d)\s*ans?")


def normalize_category(label):
    """Libellé de catégorie unique pour les variantes d'écriture (« 30/39ans », « 30-39 ans », « Masculins 30/39 ans »
    -> « 30/39 ans » ; « Séniors B - 30/39 ans » -> « Seniors B » ; « 4ème Catégorie » -> « 4ème »)."""
    text = label.strip()
    plain = strip_accents(text).lower()
    named = re.match(r"(seniors?|veterans?)\s*-?\s*([abc])\b", plain)
    if named:  # nom de catégorie (avec ou sans tranche d'âge) : on garde le nom
        return ("Seniors " if named.group(1).startswith("senior") else "Vétérans ") + named.group(2).upper()
    if re.fullmatch(r"senior\s*([abc])", plain):
        return "Seniors " + plain[-1].upper()
    if re.search(r"\b60\s*(ans\s*)?(et\s*(plus|\+)|\+)", plain):
        return "60 ans et plus"
    age = AGE_RE.search(plain)
    if age:
        return "%s/%s ans" % age.groups()
    m = re.fullmatch(r"(\d)\s*(?:e|eme|re|ere)\s*(?:categorie)?", plain)
    if m:
        return {"1": "1ère"}.get(m.group(1), m.group(1) + "ème")
    return text


def canonical_sheet_name(title):
    t = strip_accents(title).lower()
    # VTT par tranches d'âge (UFOLEP) : 20/29 = Seniors A, 30/39 = Seniors B, 40/49, 50/59, 60+ = Vétérans A, B, C
    vtt_age = {"20/29": "Seniors A", "30/39": "Seniors B", "40/49": "Vétérans A", "50/59": "Vétérans B",
               "60": "Vétérans C"}
    m = re.match(r"vtt\s*(\d\d/\d\d|60)\b", t)
    if m and m.group(1) in vtt_age:
        return vtt_age[m.group(1)]
    ages = [("15/16", "Cadets"), ("13/14", "Minimes"), ("11/12", "Benjamins"),
            ("9/10", "Pupilles"), ("7/8", "Poussins")]
    for key, name in ages:
        if key in t:
            return name
    for key, name in (("cadet", "Cadets"), ("minime", "Minimes"), ("benjamin", "Benjamins"),
                      ("pupille", "Pupilles"), ("poussin", "Poussins"),
                      ("femin", "Féminines"), ("juniors", "Juniors"), ("tandem", "Tandem")):
        if key in t:
            return name
    m = re.search(r"seniors?\s*([abc])\b", t)
    if m:
        return "Seniors " + m.group(1).upper()
    m = re.search(r"(?:veterans?|vttrans?|vetrans?)\s*([abc])\b", t)
    if m:
        return "Vétérans " + m.group(1).upper()
    m = re.search(r"\b([123])\s*(?:re|ere|e|me|eme)\b", t)
    if m:
        return {"1": "1ère", "2": "2ème", "3": "3ème"}[m.group(1)]
    return normalize_category(title.strip())


class _Cell:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "text:%r" % (self.value,)


class _Book:
    datemode = 0


class PdfSheet:
    """Feuille de classement : lignes 0 et 1 = en-têtes (ignorées par le parseur)."""

    def __init__(self, name, header, rows, club_column_empty=False):
        self.name = name
        self.book = _Book()
        self.club_column_empty = club_column_empty
        self.scratch_eligible = name in SCRATCH_SHEETS
        self._header = header
        # place, nom, club, tours, temps, ecart
        self._rows = [["", "", "", "", "", ""], ["", "", "", "", "", ""]] + rows

    @property
    def nrows(self):
        return len(self._rows)

    def cell(self, r, c):
        return _Cell(self._rows[r][c])

    def cell_value(self, r, c):
        return self._rows[r][c]

    def row(self, r):
        if r == 1:
            return [_Cell(h) for h in self._header]
        return [_Cell(v) for v in self._rows[r]]


def _cells_from_page(page):
    """Reconstruit les cellules (runs de caractères contigus, ordre du flux PDF)."""
    cells, cur, prev = [], None, None
    for ch in page.chars:
        contiguous = (
            prev is not None
            and abs(ch["top"] - prev["top"]) <= SAME_LINE_TOL
            and -0.5 <= ch["x0"] - prev["x1"] <= CELL_GAP
        )
        if not contiguous:
            if cur:
                cells.append(cur)
            cur = {"top": ch["top"], "x0": ch["x0"], "text": ""}
        cur["text"] += ch["text"]
        prev = ch
    if cur:
        cells.append(cur)
    for c in cells:
        c["text"] = c["text"].strip()
    return [c for c in cells if c["text"]]


def _group_rows(cells):
    rows = []
    for c in sorted(cells, key=lambda c: (c["top"], c["x0"])):
        if rows and abs(c["top"] - rows[-1]["top"]) <= ROW_TOL:
            rows[-1]["cells"].append(c)
        else:
            rows.append({"top": c["top"], "cells": [c]})
    for r in rows:
        r["cells"].sort(key=lambda c: c["x0"])
    return rows


def _norm_place(text):
    return "AB" if text.lower().startswith("ab") else text


def _parse_data_row(cells, has_tours, has_time):
    texts = [c["text"] for c in cells]
    if len(texts) < 2 or not PLACE_RE.match(texts[0]):
        return None
    name = texts[1]
    if name.startswith("#") or PLACE_RE.match(name) and name.isdigit():
        return None
    rest = [t for t in texts[2:] if t != "-"]
    time = ""
    if has_time:
        for i, t in enumerate(rest):
            if TIME_RE.match(t):
                time = t
                rest = rest[:i] + rest[i + 1:]
                break
    rest = [t for t in rest if not ECART_RE.search(t) and not TIME_RE.match(t)]
    tours = ""
    if has_tours:
        for i in range(len(rest) - 1, -1, -1):
            if INT_RE.match(rest[i]):
                tours = rest[i]
                rest = rest[:i] + rest[i + 1:]
                break
    club = " ".join(t for t in rest if not t.startswith("#")).strip()
    return [_norm_place(texts[0]), name, club, tours, time, ""]


def _parse_page(page):
    rows = _group_rows(_cells_from_page(page))
    header = None
    for i, r in enumerate(rows):
        words = [c["text"].lower() for c in r["cells"]]
        if "place" in words and any(w.startswith("nom") for w in words) and "club" in words:
            header = i
            break
    if header is None:
        return None
    titles = [" ".join(c["text"] for c in r["cells"]) for r in rows[:header]]
    titles = [t for t in titles if "comit" not in strip_accents(t).lower() and "pas-de-calais" not in t.lower()]
    title = titles[-1] if titles else ""
    head = [c["text"] for c in rows[header]["cells"]]
    low = [h.lower() for h in head]
    has_tours, has_time = "tours" in low, "temps" in low
    data = []
    for r in rows[header + 1:]:
        if any(".xls" in c["text"].lower() for c in r["cells"]):  # pied de page « Classements….xls » du PDF
            continue
        parsed = _parse_data_row(r["cells"], has_tours, has_time)
        if parsed:
            data.append(parsed)
    return title, head, data


def _parse_continuation(page, head):
    """Page sans en-tête qui prolonge la catégorie précédente (suite du tableau)."""
    rows = _group_rows(_cells_from_page(page))
    if not rows:
        return None
    flat = " ".join(c["text"] for r in rows[:3] for c in r["cells"]).lower()
    if "tour" in flat or "etat" in flat or "comit" in strip_accents(flat):
        return None
    low = [h.lower() for h in head]
    has_tours, has_time = "tours" in low, "temps" in low
    data = []
    for r in rows:
        parsed = _parse_data_row(r["cells"], has_tours, has_time)
        if parsed is None:
            return None  # une ligne qui n'est pas un résultat : ce n'est pas une suite de tableau
        data.append(parsed)
    return data


def extract_sheets(pdf_path, roster=None):
    """Retourne la liste des PdfSheet d'un PDF, dans l'ordre des feuilles.

    roster : noms des membres de team.json. Toute ligne dont le nom est dans le
    roster reçoit le club TEAM SPECIALIZED LILLE, quel que soit le club du PDF.
    """
    merged = {}
    order = []
    last = None
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            parsed = _parse_page(page)
            if parsed is None:
                if last is not None:
                    more = _parse_continuation(page, merged[last]["header"])
                    if more:
                        merged[last]["rows"].extend(more)
                continue
            title, head, rows = parsed
            name = canonical_sheet_name(title)
            last = name
            if name not in merged:
                merged[name] = {"header": head, "rows": []}
                order.append(name)
            merged[name]["rows"].extend(rows)
    keys = {name_key(n): n for n in (roster or [])}
    sheets = []
    for name in order:
        rows = merged[name]["rows"]
        club_empty = bool(rows) and all(r[2] == "" for r in rows)
        # tout coureur présent dans team.json est un équipier, quel que soit le club écrit dans le PDF
        # (club vide, « Transpondeur ne fonctionne pas », ancien club...)
        for r in rows:
            if name_key(r[1]) in keys:
                r[2] = TEAM_CLUB
        sheets.append(PdfSheet(name, merged[name]["header"], rows, club_empty))
    return sheets


def _norm_file(text):
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(text).lower()).strip()


TYPE_DIRS = {"Cyclo Cross": "cx", "VTT": "vtt", "Route": "route"}


def find_pdf(pdf_root, race_type, race_name):
    """Cherche resultats_pdf/<cx|vtt|route>/ le PDF d'une course du calendrier.

    Nom du fichier = nom de la course (égalité), sinon contenant ce nom de façon unique.
    """
    folder = os.path.join(pdf_root, TYPE_DIRS.get(race_type, race_type))
    if not os.path.isdir(folder):
        return None
    wanted = _norm_file(race_name)
    files = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(".pdf")]
    exact = [f for f in files if _norm_file(f[:-4]) == wanted]
    if exact:
        return os.path.join(folder, exact[0])
    partial = [f for f in files if wanted and wanted in _norm_file(f[:-4])]
    if len(partial) == 1:
        return os.path.join(folder, partial[0])
    return None


def list_pdfs(pdf_root):
    out = []
    for sub in TYPE_DIRS.values():
        folder = os.path.join(pdf_root, sub)
        if os.path.isdir(folder):
            out += [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(".pdf")]
    return out


def suspect_names(sheets, roster, cutoff=0.86):
    """Noms du PDF qui ressemblent à un membre de `roster` sans être reconnus (faute de frappe, nom coupé...).

    Les accents, la casse, les tirets et l'ordre des mots sont déjà ignorés par `name_key` : ne reste ici que
    de la vraie différence d'orthographe. Retourne [(feuille, nom du PDF, club du PDF, membre proche)].
    """
    keys = {name_key(n): n for n in roster}
    found = []
    for sheet in sheets:
        for row in sheet._rows[2:]:
            name, club = row[1], row[2]
            if not name or club == TEAM_CLUB or name_key(name) in keys:
                continue
            close = difflib.get_close_matches(name_key(name), list(keys), n=1, cutoff=cutoff)
            if close:
                found.append((sheet.name, name, club, keys[close[0]]))
    return found
