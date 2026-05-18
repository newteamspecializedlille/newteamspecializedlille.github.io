import requests
import json
from datetime import datetime, timedelta
import re
import os


host = "https://teamspecializedlille.cc/"


def post_notification(title, content, post_url, delay):
    API_KEY = os.getenv('API_KEY')
    APP_ID = os.getenv('APP_ID')
    url = "https://onesignal.com/api/v1/notifications"

    notification_data = {
        "app_id": APP_ID,
        "included_segments": ["Total Subscriptions"],
        "headings": {"en": title},
        "contents": {"en": content},
        "url": post_url,
        "send_after": (datetime.utcnow() + timedelta(minutes=delay)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "chrome_web_icon": f"{host}assets/images/favicons/android-chrome-192x192.png",
        "firefox_icon": f"{host}assets/images/favicons/128.png",
        "safari_icon": f"{host}assets/images/favicons/256.png"
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {API_KEY}"
    }

    response = requests.post(url, headers=headers, data=json.dumps(notification_data))

    if response.status_code == 200:
        print("Notification envoyée avec succès !")
        print("Réponse de l'API:", response.json())
    else:
        print("Erreur lors de l'envoi de la notification.")
        print("Code de statut :", response.status_code)
        print("Réponse de l'API :", response.text)


def get_new_posts():
    result = []
    with open("../output.txt", 'r') as file:
        lines = file.readlines()
        for line in lines:
            if line.startswith("[NEW POST] :"):
                cleaned_line = line.replace(" ", "").replace(".md", "").replace("[NEWPOST]:", "")
                result.append(cleaned_line.strip())
    return result


def convert_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%d %B")
    months = {
        "January": "Janvier", "February": "Février", "March": "Mars", "April": "Avril",
        "May": "Mai", "June": "Juin", "July": "Juillet", "August": "Août",
        "September": "Septembre", "October": "Octobre", "November": "Novembre", "December": "Décembre"
    }
    for eng, fr in months.items():
        formatted_date = formatted_date.replace(eng, fr)
    return formatted_date


def get_url(file_name, race_type):
    race_type = race_type.replace(" ", "%20").lower()
    return f"{host}{race_type}/{file_name}/"


def get_race_name(post):
    match = re.search(r'(Route|VTT|CycloCross)(.*)', post)
    if match:
        return match.group(2)
    return None


def create_notifications(posts):
    title = "Nouveau résultat disponible"
    for post in posts:
        if "Route" in post:
            type = "Route"
        elif "VTT" in post:
            type = "VTT"
        elif "CycloCross" in post:
            type = "Cyclo Cross"
        date_str = post[:10]
        human_date = convert_date(date_str)
        race_name = get_race_name(post)

        content = f"Résultat {type} de {race_name} le {human_date} disponible sur le site"
        url = get_url(post, type)
        post_notification(title, content, url, 0)


if __name__ == '__main__':
    new_posts = get_new_posts()
    create_notifications(new_posts)
