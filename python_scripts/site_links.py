"""Génère _data/race_urls.json : lien exact du post de chaque résultat de team.json.

Le gabarit des pages coureur ne peut pas deviner l'URL d'un post (Jekyll fusionne les tirets, retire les tirets de
fin, et certains anciens posts n'ont pas le même nom que dans team.json). On associe donc chaque résultat à son post :
1. même date + même discipline + nom identique une fois « slugifié » comme Jekyll ;
2. sinon, l'unique post de cette discipline à cette date.
"""
import glob
import json
import os
import re
import urllib.parse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# discipline de team.json -> (préfixe du nom de fichier, dossier d'URL)
# (le préfixe « Clm » = contre-la-montre, classé en route)
DISCIPLINES = {"road": ("Route", "route"), "cx": ("CycloCross", "cyclo cross"), "vtt": ("VTT", "vtt")}
PREFIXES = {"road": ("Route", "Clm"), "cx": ("CycloCross",), "vtt": ("VTT",)}


def jekyll_slug(text):
    """Même règle que Jekyll (slugify « pretty », casse conservée) : le reste devient « - », sans tirets en bord."""
    return re.sub(r"[^\w.~!$&'()+,;=@]+", "-", text).strip("-")


def front_matter(path):
    with open(path, "r", encoding="utf8") as post:
        text = post.read(4000)
    head = text.split("---")[1] if text.startswith("---") else ""
    data = {}
    for line in head.splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def load_posts():
    """{(discipline, date du nom de fichier AAAA/MM/JJ): [(slug du nom, url)]} d'après _posts.

    L'URL réelle vient du front matter (Jekyll : catégorie + date du front matter + nom du fichier).
    """
    posts = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "_posts", "*.md"))):
        m = re.match(r"(\d{4})-(\d\d)-(\d\d)-(.*)\.md$", os.path.basename(path))
        if not m:
            continue
        year, month, day, rest = m.groups()
        meta = front_matter(path)
        date = re.match(r"(\d{4})-(\d\d)-(\d\d)", meta.get("date", ""))
        url_date = "/".join(date.groups()) if date else "%s/%s/%s" % (year, month, day)
        category = (meta.get("category") or "").strip().lower()
        for key, prefixes in PREFIXES.items():
            prefix = next((x for x in prefixes if rest.startswith(x)), None)
            if prefix:
                name_slug = jekyll_slug(rest[len(prefix):])
                url = "/%s/%s/%s%s" % (category or DISCIPLINES[key][1], url_date, prefix, name_slug)
                posts.setdefault((key, "%s/%s/%s" % (year, month, day)), []).append((name_slug, url))
                break
    return posts


def post_url(file_name):
    """URL (sans domaine) d'un post d'après son nom de fichier `AAAA-MM-JJ-<Type><NOM>.md` et son front matter."""
    base = os.path.basename(file_name)
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)-(.*?)(\.md)?$", base)
    if not m:
        return None
    year, month, day, rest = m.group(1), m.group(2), m.group(3), m.group(4)
    path = os.path.join(ROOT, "_posts", base if base.endswith(".md") else base + ".md")
    meta = front_matter(path) if os.path.exists(path) else {}
    date = re.match(r"(\d{4})-(\d\d)-(\d\d)", meta.get("date", ""))
    url_date = "/".join(date.groups()) if date else "%s/%s/%s" % (year, month, day)
    category = (meta.get("category") or rest).strip().lower()
    return urllib.parse.quote("/%s/%s/%s" % (category, url_date, jekyll_slug(rest)), safe="/")


def build_race_urls(team_members, posts=None):
    posts = posts if posts is not None else load_posts()
    urls = {}
    for member in team_members:
        for key in DISCIPLINES:
            for results in member.get(key, {}).values():
                for result in results:
                    date, name = result["date"].replace("-", "/"), result["raceName"]
                    candidates = posts.get((key, date), [])
                    wanted = jekyll_slug(name)
                    match = [u for slug, u in candidates if slug == wanted]
                    if not match and len(candidates) == 1:
                        match = [candidates[0][1]]
                    if not match:  # résultat classé dans une autre discipline que son post (ex. CX / VTT le même jour)
                        match = [u for other in DISCIPLINES for slug, u in posts.get((other, date), [])
                                 if slug == wanted]
                    if match:
                        urls["%s|%s|%s" % (key, date, name)] = urllib.parse.quote(match[0], safe="/")
    return dict(sorted(urls.items()))


def update_race_urls(team_path=None):
    team_path = team_path or os.path.join(ROOT, "_data", "team.json")
    with open(team_path, "r", encoding="utf8") as team_file:
        members = json.load(team_file)["team_members"]
    urls = build_race_urls(members)
    out = os.path.join(ROOT, "_data", "race_urls.json")
    new = json.dumps(urls, ensure_ascii=False, indent=4) + "\n"
    if not os.path.exists(out) or open(out, encoding="utf8").read() != new:
        with open(out, "w", encoding="utf8") as outfile:
            outfile.write(new)
    return urls


if __name__ == "__main__":
    print(len(update_race_urls()), "liens")
