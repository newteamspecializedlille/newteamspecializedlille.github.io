#!/usr/bin/env python3
"""Ajoute une course à partir d'une spec JSON (voir SKILL.md)."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "python_scripts"))
import team_members  # noqa: E402

TEAM = "TEAM SPECIALIZED LILLE"
SCRATCH_CATS = ["1ère", "2ème", "3ème", "Féminines", "Cadets"]
IMAGES = {"Cyclo Cross": "cx.png", "VTT": "vtt.png", "Route": "road.png"}


def secs(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s


def link(m):
    return "[%s](https://teamspecializedlille.cc/coureurs/%s)" % (m, m.replace(" ", "").lower())


def build_post(spec):
    rows = []
    for cat in SCRATCH_CATS:
        for r in spec["cats"].get(cat, []):
            rows.append((r[0], r[1], r[2] if len(r) > 2 else 0, r[3] if len(r) > 3 else "0:38:53", cat))
    rows.sort(key=lambda r: (-r[2], secs(r[3])))
    typ = spec["type"]
    tag = "cyclo-cross" if typ == "Cyclo Cross" else typ
    out = "---\nlayout: post\ntitle: %s - %s - %s\ndate: %s\ncategory: %s\ntags: %s\nimage: assets/img/blog/%s\n---\n" % (
        typ, spec["name"], spec["year"], spec["date"], typ, tag, IMAGES[typ])
    for cat in ("1ère", "2ème", "3ème"):
        if cat in spec["team"]:
            out += "\n### %s Catégorie\n%d participants\n" % (cat, len(spec["cats"][cat]))
            for m, p in spec["team"][cat]:
                out += "- %s : %s\n" % (link(m), p)
    out += "\n### Scratch\n%d participants\n\n| Place | Nom | Team | Tours | Catégorie | Temps |\n|---|---|---|---|---|---|\n" % len(rows)
    for i, (n, c, l, t, cat) in enumerate(rows, 1):
        if c == TEAM:
            out += "| **%d** | **%s** | **%s** | **%d** | **%s** | **%s** | \n" % (i, link(n), c, l, cat, t)
        else:
            out += "| %d | %s | %s | %d | %s | %s | \n" % (i, n, c, l, cat, t)
    return out


def main(path):
    spec = json.load(open(path, encoding="utf8"))
    fn = os.path.join(ROOT, "_posts", "%s-%s%s.md" % (spec["date"], spec["type"].replace(" ", ""), spec["name"].replace(" ", "-")))
    if os.path.exists(fn):
        sys.exit("Post déjà existant : " + fn)
    open(fn, "w", encoding="utf8").write(build_post(spec))
    print("post:", fn)

    os.chdir(os.path.join(ROOT, "python_scripts"))
    team = team_members.load_team_from_file({})
    key = {"Cyclo Cross": "cx", "VTT": "vtt", "Route": "road"}[spec["type"]]
    date = spec["date"].replace("-", "/")
    for cat, lst in spec["team"].items():
        for m, place in lst:
            if m not in team:
                team[m] = team_members.TeamMember(m)
            team[m].course += 1
            getattr(team[m], key).setdefault(spec["year"], {})["%s|%s|%s" % (date, spec["name"], cat)] = place
    team_members.update_team_file(team)
    team_members.update_challenge(team, spec["year"], "challenge" if spec["type"] == "Route" else "boue")

    rp_path = "../_data/races_parsed.json"
    rp = json.load(open(rp_path, encoding="utf8"))
    rp["races_parsed"].append("%s/%s/%s/Classements.xls" % (spec["type"], spec["year"], spec["name"]))
    json.dump(rp, open(rp_path, "w", encoding="utf8"), ensure_ascii=False, indent=4)
    print("data mises à jour")


if __name__ == "__main__":
    main(sys.argv[1])
