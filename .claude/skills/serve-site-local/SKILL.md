---
name: serve-site-local
description: Démarre le site Jekyll en local (http://127.0.0.1:4000) pour vérifier des changements (posts, _data). Utiliser quand l'utilisateur demande de lancer/démarrer le site en local ou de vérifier le rendu.
---

# Démarrer le site en local

Piège : `.bundle/config` du repo pointe vers un chemin du runner GitHub (`/home/runner/...`), donc `bundle install` / `bundle exec` échouent en local. Ne pas modifier ce fichier : le contourner par variables d'environnement avec un dossier de gems et de config hors repo.

```bash
S=<scratchpad>            # dossier temporaire de la session
mkdir -p $S/bcfg
export BUNDLE_APP_CONFIG=$S/bcfg BUNDLE_PATH=$S/gems
bundle install            # une seule fois (sinon gems déjà là)
nohup bundle exec jekyll serve --port 4000 --destination $S/site > $S/jekyll.log 2>&1 &
```
- Lancer le serveur en arrière-plan (la commande est longue), attendre `Server running` dans `$S/jekyll.log` (~10-20 s).
- `--destination` hors repo évite de polluer `_site`.
- Vérifier : `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:4000/` ainsi que `/challenge/`, `/boue/`, et les posts (URL `/cyclo%20cross/AAAA/MM/JJ/CycloCross<NOM>/`).
- Régénération auto activée : relancer inutile après modification d'un post ou d'un `_data`.
- Donner l'URL à l'utilisateur et proposer d'arrêter le serveur ensuite (`pkill -f "jekyll serve"`).
