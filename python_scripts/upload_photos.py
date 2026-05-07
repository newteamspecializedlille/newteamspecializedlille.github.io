"""
upload_photos.py — Télécharge des photos depuis des URLs CDN, les sauvegarde
dans assets/results/<year>/<route>/ et met à jour le front matter du post Jekyll.

Usage (appelé par le workflow GitHub Actions) :
  Variables d'environnement attendues :
    PHOTOGRAPHER_NAME  — nom du photographe
    POST_URL           — URL du post (ex: https://…/route/2026/05/01/RoutePONT-SUR-SAMBRE/)
    IMAGES_URLS        — JSON array des URLs CDN (ex: '["https://…/a.jpg","https://…/b.jpg"]')
"""

import os
import re
import json
import base64
import unicodedata
import urllib.request


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def sanitize_path_segment(segment: str) -> str:
    normalized = unicodedata.normalize('NFD', segment)
    ascii_str = normalized.encode('ascii', 'ignore').decode('ascii')
    safe = re.sub(r'[^a-zA-Z0-9_-]', '-', ascii_str.lower())
    safe = re.sub(r'-{2,}', '-', safe).strip('-')
    return safe or 'unknown'


def extract_url_parts(post_url: str) -> dict:
    """Extrait year, month, day, route_slug (brut) et route_name (sanitisé) depuis l'URL."""
    match = re.search(r'/route/(\d{4})/(\d{2})/(\d{2})/([^/]+)/?', post_url)
    if match:
        year, month, day, slug = match.groups()
    else:
        match = re.search(r'/route/(\d+)/.*?/([^/]+)/?$', post_url)
        if match:
            year, month, day, slug = match.group(1), '00', '00', match.group(2)
        else:
            return {'year': 'unknown', 'month': '00', 'day': '00',
                    'route_slug': 'unknown', 'route_name': 'unknown'}
    return {
        'year': year, 'month': month, 'day': day,
        'route_slug': slug,
        'route_name': sanitize_path_segment(slug),
    }


# ---------------------------------------------------------------------------
# Gestion du front matter Jekyll (stdlib pure, sans PyYAML)
# ---------------------------------------------------------------------------

def split_front_matter(content: str):
    """Retourne (fm_lines, body) ou (None, content) si pas de front matter."""
    if not content.startswith('---'):
        return None, content
    rest = content[3:].lstrip('\r\n')
    end = re.search(r'\n---[ \t]*(\n|$)', rest)
    if not end:
        return None, content
    return rest[:end.start()].splitlines(), rest[end.end():]


def parse_fm(lines: list) -> dict:
    """Parse un front matter YAML simple (clés scalaires + listes de mappings)."""
    result = {}
    i = 0
    while i < len(lines):
        m = re.match(r'^(\w+):\s*(.*)', lines[i])
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val:
                result[key] = val
                i += 1
            else:
                items, i = [], i + 1
                while i < len(lines) and re.match(r'^\s+-', lines[i]):
                    item_line = lines[i].strip().lstrip('- ').strip()
                    sub = re.match(r'^(\w+):\s*(.*)', item_line)
                    if sub:
                        obj = {sub.group(1): sub.group(2).strip()}
                        i += 1
                        while i < len(lines):
                            cont = lines[i]
                            cm = re.match(r'^\s+(\w+):\s*(.*)', cont)
                            if cm and not cont.strip().startswith('-'):
                                obj[cm.group(1)] = cm.group(2).strip()
                                i += 1
                            else:
                                break
                        items.append(obj)
                    else:
                        items.append(item_line)
                        i += 1
                result[key] = items
        else:
            i += 1
    return result


def serialize_fm(data: dict) -> str:
    """Sérialise un dict en lignes YAML simples."""
    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    first = True
                    for k, v in item.items():
                        lines.append(f"  {'- ' if first else '  '}{k}: {v}")
                        first = False
                else:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    return '\n'.join(lines) + '\n'


def rebuild_post(fm_lines: list, extra: dict, body: str) -> str:
    fm = parse_fm(fm_lines)
    fm.update(extra)
    return f"---\n{serialize_fm(fm)}---\n{body}"


# ---------------------------------------------------------------------------
# Logique principale
# ---------------------------------------------------------------------------

def parse_images_urls(raw: str) -> list:
    """Parse le format Zapier : blocs de clés/valeurs séparés par lignes vides.

    Chaque bloc peut contenir :
      cdnUrl: https://...
      mimeType: image/png
      name: photo.png
      size: 123456
      uuid: ...

    Retourne la liste des cdnUrl trouvées.
    """
    urls = []
    # Cherche toutes les lignes "cdnUrl: <url>"
    for match in re.finditer(r'cdnUrl:\s*(https?://\S+)', raw):
        urls.append(match.group(1).strip())
    return urls


def main():
    photographer_name = os.environ.get('PHOTOGRAPHER_NAME', '').strip()
    post_url          = os.environ.get('POST_URL', '').strip()
    images_urls_raw   = os.environ.get('IMAGES_URLS', '').strip()

    # Essayer JSON d'abord, sinon parser le format clé:valeur Zapier
    try:
        parsed = json.loads(images_urls_raw)
        if isinstance(parsed, list):
            images_urls = parsed
        elif isinstance(parsed, str):
            images_urls = parse_images_urls(parsed)
        else:
            images_urls = []
    except (json.JSONDecodeError, ValueError):
        images_urls = parse_images_urls(images_urls_raw)

    print(f"Photographe   : {photographer_name}")
    print(f"Post URL      : {post_url}")
    print(f"Nb images     : {len(images_urls)}")

    parts      = extract_url_parts(post_url)
    year       = parts['year']
    month      = parts['month']
    day        = parts['day']
    route_slug = parts['route_slug']
    route_name = parts['route_name']

    print(f"Post cible    : _posts/{year}-{month}-{day}-{route_slug}.md")
    print(f"Dossier assets: assets/results/{year}/{route_name}/")

    # Créer le dossier de destination
    dest_dir = os.path.join('assets', 'results', year, route_name)
    os.makedirs(dest_dir, exist_ok=True)

    uploaded_paths = []

    for counter, cdn_url in enumerate(images_urls, start=1):
        if not cdn_url:
            continue

        # Déduire l'extension depuis l'URL
        ext_match = re.search(r'\.(\w{2,4})(?:\?|$)', cdn_url)
        ext = ext_match.group(1).lower() if ext_match else 'jpg'
        filename = f"photo_{counter:02d}.{ext}"
        dest_path = os.path.join(dest_dir, filename)

        print(f"  Téléchargement {filename} depuis {cdn_url[:70]}...")
        try:
            req = urllib.request.Request(cdn_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            with open(dest_path, 'wb') as f:
                f.write(data)
            print(f"  ✓ {filename} sauvegardé ({len(data)} octets)")
            uploaded_paths.append(dest_path.replace('\\', '/'))
        except Exception as exc:
            print(f"  ✗ Erreur pour {filename}: {exc}")

    if not uploaded_paths:
        print("Aucune image téléchargée, arrêt.")
        return

    # Mettre à jour le front matter du post
    post_path = os.path.join('_posts', f"{year}-{month}-{day}-{route_slug}.md")
    if not os.path.exists(post_path):
        print(f"Post introuvable : {post_path}")
        return

    with open(post_path, encoding='utf-8') as f:
        content = f.read()

    fm_lines, body = split_front_matter(content)
    if fm_lines is None:
        print(f"Pas de front matter dans {post_path}")
        return

    fm = parse_fm(fm_lines)
    existing = fm.get('images', []) if isinstance(fm.get('images'), list) else []
    existing_paths = {e.get('path') for e in existing if isinstance(e, dict)}

    for p in uploaded_paths:
        if p not in existing_paths:
            existing.append({'photographer': photographer_name, 'path': p})

    updated = rebuild_post(fm_lines, {'images': existing}, body)
    with open(post_path, 'w', encoding='utf-8') as f:
        f.write(updated)

    print(f"✓ Front matter mis à jour : {post_path}")
    print(f"  {len(uploaded_paths)} image(s) ajoutée(s)")


if __name__ == '__main__':
    main()
