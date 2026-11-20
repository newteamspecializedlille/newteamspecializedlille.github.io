"""Envoie une notification OneSignal pour chaque nouveau post de résultat (lignes `[NEW POST] : ...` du log de main.py)."""
import json
import os
import re
from datetime import datetime, timedelta, timezone

import requests

import site_links

HOST = "https://teamspecializedlille.cc"
OUTPUT_FILE = "../output.txt"
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre"]
TYPES = {"Route": "Route", "VTT": "VTT", "CycloCross": "Cyclo Cross"}


def get_new_posts(output_file=OUTPUT_FILE):
    """Noms de fichiers des posts créés, d'après le log de main.py."""
    posts = []
    with open(output_file, "r", encoding="utf8") as file:
        for line in file:
            if line.startswith("[NEW POST] :"):
                posts.append(line.split(":", 1)[1].strip())
    return posts


def describe_post(file_name):
    """(type, nom de la course, date en français) d'après le nom de fichier AAAA-MM-JJ-<Type><NOM>.md"""
    match = re.match(r"(\d{4})-(\d\d)-(\d\d)-(Route|VTT|CycloCross)(.*?)(\.md)?$", file_name)
    if not match:
        return None
    year, month, day, race_type, name = match.group(1, 2, 3, 4, 5)
    return TYPES[race_type], " ".join(name.replace("-", " ").split()), "%d %s" % (int(day), MONTHS[int(month) - 1])


def post_notification(title, content, post_url, delay=0):
    api_key, app_id = os.getenv("API_KEY"), os.getenv("APP_ID")
    send_after = (datetime.now(timezone.utc) + timedelta(minutes=delay)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "app_id": app_id,
        "included_segments": ["Total Subscriptions"],
        "headings": {"en": title},
        "contents": {"en": content},
        "url": post_url,
        "send_after": send_after,
        "chrome_web_icon": f"{HOST}/assets/images/favicons/android-chrome-192x192.png",
        "firefox_icon": f"{HOST}/assets/images/favicons/128.png",
        "safari_icon": f"{HOST}/assets/images/favicons/256.png",
    }
    headers = {"Content-Type": "application/json; charset=utf-8", "Authorization": f"Basic {api_key}"}
    response = requests.post("https://onesignal.com/api/v1/notifications", headers=headers,
                             data=json.dumps(payload), timeout=30)
    if response.status_code == 200:
        print("Notification envoyée :", post_url)
    else:
        print("Erreur lors de l'envoi de la notification :", response.status_code, response.text)


def create_notifications(posts):
    for file_name in posts:
        info = describe_post(file_name)
        url = site_links.post_url(file_name)
        if not info or not url:
            print("[NOTIFICATION] post ignoré (nom inattendu) : " + file_name)
            continue
        race_type, race_name, human_date = info
        post_notification("Nouveau résultat disponible",
                          f"Résultat {race_type} de {race_name} le {human_date} disponible sur le site",
                          f"{HOST}{url}")


if __name__ == "__main__":
    create_notifications(get_new_posts())
