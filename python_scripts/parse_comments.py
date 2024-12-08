import requests
from bs4 import BeautifulSoup
import os

import requests
from bs4 import BeautifulSoup


def fetch_threads(public_key, forum_shortname):
    """
    Récupère tous les threads (articles) d'un forum Disqus.

    :param public_key: Clé publique Disqus
    :param forum_shortname: Shortname du forum Disqus
    :return: Liste de tuples (thread_id, thread_link)
    """
    base_url = "https://disqus.com/api/3.0/threads/list.json"
    threads = []
    cursor = None

    while True:
        params = {
            "api_key": public_key,
            "forum": forum_shortname,
            "limit": 100,  # Nombre maximum de threads par requête
        }
        if cursor:
            params["cursor"] = cursor

        response = requests.get(base_url, params=params).json()

        if response.get("code") != 0:
            print("Erreur lors de la récupération des threads :", response)
            break
        # Ajouter les threads à la liste
        for thread in response["response"]:
            thread_id = thread["id"]
            thread_link = thread.get("link")  # URL de l'article
            threads.append((thread_id, thread_link))
        # Gestion de la pagination
        cursor = response["cursor"].get("next")
        if not response["cursor"].get("hasNext"):
            break

    return threads


def fetch_comments_for_thread(public_key, thread_id):
    """
    Récupère tous les commentaires d'un thread (article) et filtre ceux avec des images.

    :param public_key: Clé publique Disqus
    :param thread_id: ID du thread
    :return: Liste de tuples (author, message, image_url)
    """
    base_url = "https://disqus.com/api/3.0/posts/list.json"
    comments = []
    cursor = None

    while True:
        params = {
            "api_key": public_key,
            "thread": thread_id,
            "limit": 100,  # Nombre maximum de commentaires par requête
        }
        if cursor:
            params["cursor"] = cursor

        response = requests.get(base_url, params=params).json()

        if response.get("code") != 0:
            print("Erreur lors de la récupération des commentaires :", response)
            break

        # Parcourir les commentaires
        for comment in response["response"]:
            author = comment["author"]["name"]
            message = comment["message"]  # Contenu HTML du commentaire

            # Utiliser BeautifulSoup pour analyser le HTML et extraire les liens d'images
            soup = BeautifulSoup(message, "html.parser")
            image_url = None

            # Rechercher les balises <a> avec un href pointant vers une image
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.endswith((".jpg", ".jpeg", ".png", ".gif")):
                    image_url = href
                    break

            # Ajouter uniquement les commentaires contenant une image
            if image_url:
                comments.append((author, message, image_url))

        # Gestion de la pagination
        cursor = response["cursor"].get("next")
        if not response["cursor"].get("hasNext"):
            break

    return comments


def fetch_all_comments_with_images(public_key, forum_shortname):
    """
    Récupère tous les commentaires avec des images pour tous les articles d'un forum Disqus.

    :param public_key: Clé publique Disqus
    :param forum_shortname: Shortname du forum Disqus
    :return: Liste de tuples (author, image_url, article_url)
    """
    # Étape 1 : Récupérer tous les threads
    threads = fetch_threads(public_key, forum_shortname)

    # Étape 2 : Récupérer les commentaires avec images pour chaque thread
    results = []
    for thread_id, thread_link in threads:
        if not thread_link:
            continue  # Ignorer les threads sans lien d'article

        comments = fetch_comments_for_thread(public_key, thread_id)

        # Associer chaque commentaire à l'article
        for author, message, image_url in comments:
            results.append((author, image_url, thread_link))

    return results

def get_filename_from_url(article_url):
    file = (article_url.replace("https://teamspecializedlille.cc/cyclo%20cross/", "").replace(
        "https://teamspecializedlille.cc/cyclo%20cross/", "")
            .replace("https://teamspecializedlille.cc/route/", "").replace("/", "-"))
    if file.endswith("-"):
        file = file[:-1]
    return file

def save_image(image_url, filename):
    # Ajouter l'extension de l'image
    extension = ".jpg"
    filename += extension

    # Créer le chemin complet du fichier
    save_path = os.path.join("..", "assets", "img", "disqus_pictures", filename)

    # Télécharger l'image et la sauvegarder
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
        print(f"Image saved as {save_path}")
    else:
        print(f"Failed to download image from {image_url}")

def update_image_in_post(file_name):
    # Define the path to the posts directory
    posts_dir = "../_posts"
    file_path = os.path.join(posts_dir, file_name + ".md")

    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return

    # Read the content of the file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Define the image paths to check
    image_paths_to_check = [
        "assets/img/blog/road.jpeg",
        "assets/img/blog/cx.jpeg",
        "assets/img/blog/vtt.jpeg"
    ]

    # Modify the image field in the header if it matches one of the specified values
    in_header = False
    for i, line in enumerate(lines):
        if line.strip() == "---":
            in_header = not in_header
        if in_header and line.startswith("image:"):
            image_path = line.split(":", 1)[1].strip()
            if image_path in image_paths_to_check:
                lines[i] = f"image: assets/img/disqus_pictures/{file_name}.jpg\n"
                break

    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.writelines(lines)

    print(f"Updated image in {file_path}")


if __name__ == "__main__":
    # Remplacez ces valeurs par vos informations Disqus
    PUBLIC_KEY = os.getenv('API_KEY_DISQUS')
    FORUM_SHORTNAME = "teamspecializedlille"  # Shortname du forum Disqus

    # Récupération des commentaires pour l'article donné
    comments_with_images = fetch_all_comments_with_images(PUBLIC_KEY, FORUM_SHORTNAME)

    # Affichage des résultats
    for author, image_url, article_url in comments_with_images:
        print(f"Auteur: {author}")
        print(f"Image: {image_url}")
        print(f"Article: {article_url}")
        print("-" * 40)
        file_name = get_filename_from_url(article_url)
        update_image_in_post(file_name)
        save_image(image_url, file_name)