"""
crop_faces.py — Génère des photos recadrées sur le visage pour chaque coureur.

Stratégie :
1. Détecte le visage directement dans l'image nobg/ (fond transparent → blanc pour la détection)
2. Fallback : détecte dans large/ (fond réel) et projette les coordonnées dans nobg/
   en se basant sur le centre relatif du visage (robuste aux différences d'aspect ratio)
3. Recadre carré centré sur le visage avec marge, redimensionne en OUTPUT_SIZE px

Usage :
    python3 python_scripts/crop_faces.py

Dépendances :
    pip install opencv-python-headless Pillow
"""

import cv2
import numpy as np
import os
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LARGE_DIR = os.path.join(BASE_DIR, "assets", "imgs", "team", "large")
NOBG_DIR  = os.path.join(BASE_DIR, "assets", "imgs", "team", "nobg")
HEAD_DIR  = os.path.join(BASE_DIR, "assets", "imgs", "team", "head")
OUTPUT_SIZE = 300  # px carré

os.makedirs(HEAD_DIR, exist_ok=True)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def detect_face_in_nobg(nobg_path):
    """
    Composite le PNG transparent sur fond blanc, puis détecte le visage.
    Retourne (x, y, w, h) de la plus grande boîte, ou None.
    """
    img_pil = Image.open(nobg_path).convert("RGBA")
    bg = Image.new("RGBA", img_pil.size, (255, 255, 255, 255))
    bg.paste(img_pil, mask=img_pil.split()[3])
    cv_img = cv2.cvtColor(np.array(bg.convert("RGB")), cv2.COLOR_RGB2BGR)
    return _detect(cv_img)


def detect_face_in_large(large_path):
    """Détecte le visage dans l'image large/. Retourne (x, y, w, h) ou None."""
    img = cv2.imread(large_path)
    return _detect(img) if img is not None else None


def _detect(cv_img):
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    for sf, mn in [(1.1, 4), (1.05, 3), (1.1, 2), (1.05, 2)]:
        faces = face_cascade.detectMultiScale(gray, scaleFactor=sf, minNeighbors=mn, minSize=(30, 30))
        if len(faces) > 0:
            return max(faces, key=lambda f: f[2] * f[3])
    return None


def project_large_face_to_nobg(large_box, large_w, large_h, nobg_w, nobg_h):
    """
    Projette les coordonnées de la boîte détectée dans large/ vers nobg/ en utilisant
    les positions relatives (% de l'image). Les portraits nobg/ sont généralement
    centrés horizontalement et le visage est dans la partie haute.
    """
    x, y, w, h = large_box
    # Centre du visage en % de l'image large
    cx_rel = (x + w / 2) / large_w
    cy_rel = (y + h / 2) / large_h
    # Taille du visage en % de la largeur large
    w_rel  = w / large_w

    # Projeter dans nobg en gardant les proportions relatives
    # La largeur nobg est 687, la hauteur 800 → les visages sont ~10-15% de la largeur nobg
    new_w = int(w_rel * nobg_w * 2.5)  # ajustement empirique ratio landscape→portrait
    new_h = new_w
    new_cx = int(cx_rel * nobg_w)
    new_cy = int(cy_rel * nobg_h)
    new_x  = new_cx - new_w // 2
    new_y  = new_cy - new_h // 2
    return (new_x, new_y, new_w, new_h)


def fallback_upper_crop(nobg_w, nobg_h):
    """
    Fallback ultime : le visage est probablement dans le quart supérieur, centré horizontalement.
    """
    face_h = int(nobg_h * 0.25)
    face_w = face_h
    x = (nobg_w - face_w) // 2
    y = int(nobg_h * 0.05)
    return (x, y, face_w, face_h)


def crop_and_save(nobg_path, box, output_path):
    """
    Recadre l'image nobg sur la zone visage + marges, carré centré, OUTPUT_SIZE×OUTPUT_SIZE.
    Le fond transparent est conservé.
    """
    img = Image.open(nobg_path).convert("RGBA")
    nw, nh = img.size
    x, y, w, h = box

    # Marges généreuses : 80% vers le haut (front, casque), 50% côtés, 30% bas
    pad_top    = int(h * 0.80)
    pad_side   = int(w * 0.50)
    pad_bottom = int(h * 0.30)

    left   = x - pad_side
    top    = y - pad_top
    right  = x + w + pad_side
    bottom = y + h + pad_bottom

    # Forcer carré en prenant la plus grande dimension
    cw = right - left
    ch = bottom - top
    side = max(cw, ch)
    cx   = (left + right)  // 2
    cy   = (top  + bottom) // 2
    half = side // 2

    left2   = cx - half
    top2    = cy - half
    right2  = cx + half
    bottom2 = cy + half

    # Si le crop sort de l'image, on décale (pas de crop)
    if left2 < 0:
        right2 -= left2
        left2   = 0
    if top2 < 0:
        bottom2 -= top2
        top2    = 0
    if right2 > nw:
        left2  -= (right2 - nw)
        right2  = nw
    if bottom2 > nh:
        top2   -= (bottom2 - nh)
        bottom2 = nh

    # Clamp final
    left2   = max(0, left2)
    top2    = max(0, top2)
    right2  = min(nw, right2)
    bottom2 = min(nh, bottom2)

    cropped = img.crop((left2, top2, right2, bottom2))

    # Mettre dans un carré avec fond transparent si le crop est plus petit
    result = Image.new("RGBA", (OUTPUT_SIZE, OUTPUT_SIZE), (0, 0, 0, 0))
    thumb  = cropped.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)
    result.paste(thumb, (0, 0))
    result.save(output_path, "PNG")


def main():
    images = sorted(
        f for f in os.listdir(NOBG_DIR)
        if f.endswith(".png") and f != "empty.png"
    )

    for fname in images:
        nobg_path  = os.path.join(NOBG_DIR,  fname)
        large_path = os.path.join(LARGE_DIR, fname)
        out_path   = os.path.join(HEAD_DIR,  fname)

        # Taille nobg
        img_pil = Image.open(nobg_path)
        nobg_w, nobg_h = img_pil.size

        # 1. Détecter directement dans nobg
        box = detect_face_in_nobg(nobg_path)
        source = "nobg"

        # 2. Fallback : détecter dans large et projeter
        if box is None and os.path.exists(large_path):
            large_box = detect_face_in_large(large_path)
            if large_box is not None:
                limg = cv2.imread(large_path)
                lh, lw = limg.shape[:2]
                box = project_large_face_to_nobg(large_box, lw, lh, nobg_w, nobg_h)
                source = "large→projected"

        # 3. Fallback ultime : quart supérieur
        if box is None:
            box = fallback_upper_crop(nobg_w, nobg_h)
            source = "fallback"

        crop_and_save(nobg_path, box, out_path)
        x, y, w, h = box
        print(f"  {'✓' if source == 'nobg' else '~'}  {fname:35s} [{source}] box=({x},{y},{w},{h})")

    print(f"\nImages sauvegardées dans : {HEAD_DIR}")


if __name__ == "__main__":
    main()
