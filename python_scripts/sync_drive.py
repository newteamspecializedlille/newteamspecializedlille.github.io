import os
import io
import re
import json
import glob as _glob
import mimetypes
from PIL import Image
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account

# --- CHEMINS ABSOLUS relatifs au repo (fonctionne quel que soit le cwd) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(SCRIPT_DIR)

# --- CONFIGURATION ---
FOLDER_ID  = '17wRr15dS_PN6bHIb0S87mSKYPFuP5iSX'
DEST_DIR   = os.path.join(REPO_ROOT, 'assets', 'resultats')
POSTS_DIR  = os.path.join(REPO_ROOT, '_posts')
LOCAL_JSON = os.path.join(REPO_ROOT, 'credentials.json')

MAX_WIDTH  = 800  # pixels


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_drive_service(readonly=True):
    scopes = ['https://www.googleapis.com/auth/drive.readonly'] if readonly else ['https://www.googleapis.com/auth/drive']

    if os.path.exists(LOCAL_JSON):
        print("Authentification via fichier local...")
        with open(LOCAL_JSON, 'r') as f:
            info = json.load(f)
        creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
    elif 'GDRIVE_SERVICE_ACCOUNT' in os.environ:
        print("Authentification via variable d'environnement...")
        info = json.loads(os.environ['GDRIVE_SERVICE_ACCOUNT'])
        creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
    else:
        raise Exception("Erreur : Aucun identifiant trouvé (credentials.json ou variable d'env)")

    return build('drive', 'v3', credentials=creds)


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def _get_or_create_subfolder(service, parent_id, name):
    """Retourne l'ID d'un sous-dossier existant ou le crée (supporte les drives partagés)."""
    query = (
        f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' "
        f"and name = '{name}' and trashed = false"
    )
    results = service.files().list(
        q=query, fields="files(id, name)",
        supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    folder = service.files().create(body=metadata, fields='id', supportsAllDrives=True).execute()
    return folder['id']


def create_race_folder(race_year, race_type, race_name, race_date):
    """Crée la structure year/race_type/MM-DD-race_name dans le Drive partagé (tout en minuscules).

    race_date est au format YYYY/MM/DD.
    """
    parts = race_date.split("/")
    mm_dd = f"{parts[1]}-{parts[2]}"
    folder_name = f"{mm_dd}-{race_name}".lower()

    service = get_drive_service(readonly=False)
    year_id = _get_or_create_subfolder(service, FOLDER_ID, race_year.lower())
    type_id = _get_or_create_subfolder(service, year_id, race_type.lower())
    race_id = _get_or_create_subfolder(service, type_id, folder_name)
    print(f"[DRIVE] Dossier créé/existant : {race_year}/{race_type.lower()}/{folder_name} (id={race_id})")
    return race_id


def _list_folders(service, parent_id):
    query = (
        f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    results = service.files().list(
        q=query, fields="files(id, name)",
        supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    return results.get('files', [])


def _list_images(service, folder_id):
    query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
    results = service.files().list(
        q=query, fields="files(id, name)",
        supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    return results.get('files', [])


# ---------------------------------------------------------------------------
# Image resize
# ---------------------------------------------------------------------------

def _resize_image(file_path):
    """Redimensionne l'image à MAX_WIDTH px de large maximum, en conservant le ratio."""
    try:
        with Image.open(file_path) as img:
            w, h = img.size
            if w <= MAX_WIDTH:
                return
            new_h = int(h * MAX_WIDTH / w)
            img = img.resize((MAX_WIDTH, new_h), Image.LANCZOS)
            img.save(file_path)
            print(f"  Redimensionné → {MAX_WIDTH}×{new_h}px : {os.path.basename(file_path)}")
    except Exception as e:
        print(f"  ⚠ Impossible de redimensionner {file_path}: {e}")


# ---------------------------------------------------------------------------
# Post front matter update
# ---------------------------------------------------------------------------

def _update_post_images(path_context, new_image_paths):
    """Cherche le post correspondant et ajoute les chemins d'images dans le front matter.

    path_context = [year, race_type, MM-DD-racename]
    Le photographer n'est pas connu depuis drive_sync, il est omis.
    """
    year, _race_type, race_folder = path_context
    parts = race_folder.split('-', 2)
    if len(parts) < 2:
        return
    mm, dd = parts[0], parts[1]

    pattern = os.path.join(POSTS_DIR, f"{year}-{mm}-{dd}-*.md")
    matches = _glob.glob(pattern)
    if not matches:
        print(f"  ⚠ Aucun post trouvé pour {year}-{mm}-{dd}")
        return

    post_path = matches[0]
    with open(post_path, encoding='utf-8') as f:
        content = f.read()

    if not content.startswith('---'):
        return
    rest = content[3:].lstrip('\r\n')
    end = re.search(r'\n---[ \t]*(\n|$)', rest)
    if not end:
        return
    fm_text = rest[:end.start()]
    body    = rest[end.end():]

    # Chemins relatifs au repo root déjà présents dans le front matter
    existing = set(re.findall(r'^\s+path:\s*(.+)$', fm_text, re.MULTILINE))

    new_entries = []
    for abs_path in new_image_paths:
        rel = os.path.relpath(abs_path, REPO_ROOT).replace('\\', '/')
        if rel not in existing:
            new_entries.append(rel)

    if not new_entries:
        return

    addition = '\n'.join(f'  - path: {p}' for p in new_entries)
    if re.search(r'^images:', fm_text, re.MULTILINE):
        fm_text = fm_text.rstrip() + '\n' + addition
    else:
        fm_text = fm_text.rstrip() + '\nimages:\n' + addition

    with open(post_path, 'w', encoding='utf-8') as f:
        f.write(f'---\n{fm_text}\n---\n{body}')
    print(f"  [POST] {os.path.basename(post_path)} → {len(new_entries)} image(s) ajoutée(s)")


def _remove_post_images(path_context, removed_paths):
    """Retire du front matter du post les chemins d'images supprimées localement."""
    year, _race_type, race_folder = path_context
    parts = race_folder.split('-', 2)
    if len(parts) < 2:
        return
    mm, dd = parts[0], parts[1]

    pattern = os.path.join(POSTS_DIR, f"{year}-{mm}-{dd}-*.md")
    matches = _glob.glob(pattern)
    if not matches:
        return

    removed_rels = {os.path.relpath(p, REPO_ROOT).replace('\\', '/') for p in removed_paths}
    post_path = matches[0]

    with open(post_path, encoding='utf-8') as f:
        content = f.read()

    if not content.startswith('---'):
        return
    rest = content[3:].lstrip('\r\n')
    end = re.search(r'\n---[ \t]*(\n|$)', rest)
    if not end:
        return
    fm_text = rest[:end.start()]
    body    = rest[end.end():]

    # Supprimer les entrées correspondant aux fichiers supprimés
    new_lines = []
    skip_next = False
    for line in fm_text.splitlines():
        path_match = re.match(r'^\s+path:\s*(.+)$', line)
        if path_match and path_match.group(1).strip() in removed_rels:
            # Supprimer aussi la ligne photographer qui précède (si présente)
            if new_lines and re.match(r'^\s+photographer:', new_lines[-1]):
                new_lines.pop()
            elif new_lines and re.match(r'^\s+-\s+path:', new_lines[-1]):
                new_lines.pop()
            skip_next = False
            continue
        if skip_next:
            skip_next = False
            continue
        new_lines.append(line)

    with open(post_path, 'w', encoding='utf-8') as f:
        f.write(f'---\n' + '\n'.join(new_lines) + f'\n---\n{body}')
    print(f"  [POST] {os.path.basename(post_path)} → {len(removed_paths)} image(s) retirée(s)")


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def _is_image(filename):
    return os.path.splitext(filename)[1].lower() in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}


def _upload_file(service, local_path, filename, parent_id):
    """Upload un fichier local vers un dossier du Drive partagé."""
    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or 'application/octet-stream'
    metadata = {'name': filename, 'parents': [parent_id]}
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
    file = service.files().create(
        body=metadata, media_body=media, fields='id', supportsAllDrives=True
    ).execute()
    print(f"  ↑ Uploadé vers Drive : {filename} (id={file['id']})")
    return file['id']


def sync_photos():
    """Miroir bidirectionnel entre Drive et assets/resultats/.
    - Drive → Local : télécharge et redimensionne les nouvelles images, met à jour les posts.
    - Local → Drive : uploade les fichiers locaux absents du Drive.
    - Suppression locale : si une image était dans Drive (tracée dans le manifest) et n'y est plus,
      elle est supprimée en local. Drive fait référence."""
    service = get_drive_service(readonly=False)
    os.makedirs(DEST_DIR, exist_ok=True)
    manifest = _load_manifest()
    downloaded, uploaded, deleted = _sync_folder(service, FOLDER_ID, DEST_DIR, manifest=manifest)
    _save_manifest(manifest)
    print(f"\nSynchronisation terminée — {downloaded} téléchargé(s), {uploaded} uploadé(s), {deleted} supprimé(s).")


def _load_manifest():
    """Charge le manifest des fichiers précédemment synchronisés depuis Drive."""
    path = os.path.join(DEST_DIR, '.sync_manifest.json')
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def _save_manifest(manifest):
    """Sauvegarde le manifest."""
    path = os.path.join(DEST_DIR, '.sync_manifest.json')
    with open(path, 'w') as f:
        json.dump(manifest, f, indent=2)


def _sync_folder(service, drive_folder_id, local_path, path_context=None, manifest=None):
    """Sync récursif bidirectionnel. Drive fait référence pour les suppressions.
    Retourne (downloaded, uploaded, deleted)."""
    if path_context is None:
        path_context = []
    if manifest is None:
        manifest = {}

    downloaded = uploaded = deleted = 0
    new_local_paths = []
    removed_local_paths = []

    folder_key = '/'.join(path_context)

    # Indexer Drive (noms en lowercase pour cohérence locale)
    drive_folders = {f['name'].lower(): f['id'] for f in _list_folders(service, drive_folder_id)}
    drive_images  = {f['name'].lower(): f['id'] for f in _list_images(service, drive_folder_id)}

    # Indexer le local (noms en lowercase)
    local_entries = os.listdir(local_path) if os.path.exists(local_path) else []
    local_subdirs = {e.lower() for e in local_entries if os.path.isdir(os.path.join(local_path, e))}
    local_files   = {e.lower() for e in local_entries if os.path.isfile(os.path.join(local_path, e)) and _is_image(e)}

    # Récursion sur les sous-dossiers Drive uniquement (Drive = source de vérité)
    for name in drive_folders:
        sub_local = os.path.join(local_path, name)
        os.makedirs(sub_local, exist_ok=True)
        d, u, dl = _sync_folder(service, drive_folders[name], sub_local, path_context + [name], manifest)
        downloaded += d
        uploaded   += u
        deleted    += dl

    # Drive → Local : télécharger ce qui manque
    for name, file_id in drive_images.items():
        file_path = os.path.join(local_path, name)
        if not os.path.exists(file_path):
            print(f"↓ {os.path.relpath(file_path, REPO_ROOT)}")
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            fh = io.FileIO(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            _resize_image(file_path)
            new_local_paths.append(file_path)
            downloaded += 1
        # Tracker dans le manifest tout ce qui existe dans Drive
        manifest.setdefault(folder_key, set())
        if isinstance(manifest[folder_key], list):
            manifest[folder_key] = set(manifest[folder_key])
        manifest[folder_key].add(name)

    # Local → Drive : désactivé (service accounts sans quota sur Drive personnel)

    # Suppressions locales : fichiers trackés dans le manifest mais absents du Drive
    previously_synced = manifest.get(folder_key, set())
    if isinstance(previously_synced, list):
        previously_synced = set(previously_synced)
    for name in list(previously_synced):
        if name not in drive_images:
            file_path = os.path.join(local_path, name)
            if os.path.exists(file_path):
                print(f"✗ Suppression locale (supprimé du Drive) : {os.path.relpath(file_path, REPO_ROOT)}")
                os.remove(file_path)
                removed_local_paths.append(file_path)
                deleted += 1
            manifest[folder_key].discard(name)

    # Convertir les sets en listes pour la sérialisation JSON
    if folder_key in manifest and isinstance(manifest[folder_key], set):
        manifest[folder_key] = list(manifest[folder_key])

    # Mise à jour du post au niveau race (profondeur 3 = [year, race_type, MM-DD-race])
    if len(path_context) == 3:
        if new_local_paths:
            _update_post_images(path_context, new_local_paths)
        if removed_local_paths:
            _remove_post_images(path_context, removed_local_paths)

    return downloaded, uploaded, deleted


if __name__ == '__main__':
    sync_photos()