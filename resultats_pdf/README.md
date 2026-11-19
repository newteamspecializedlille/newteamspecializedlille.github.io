# Classements PDF

La CI (`python_scripts/main.py`) lit les classements au format PDF. Elle télécharge automatiquement le `Classements.pdf`
de chaque course listée sur les calendriers UFOLEP ; on peut aussi déposer ici un PDF à la main (prioritaire sur le site),
un dossier par discipline :

```
resultats_pdf/cx/     <NOM DE LA COURSE>.pdf     (cyclo-cross)
resultats_pdf/vtt/    <NOM DE LA COURSE>.pdf
resultats_pdf/route/  <NOM DE LA COURSE>.pdf
```

- La **date, le lien du PDF, le nom et le type** de la course (course normale, Championnat Nord / Pas-de-Calais / Département / National,
  d'après la couleur de la ligne) viennent du calendrier UFOLEP (pages VTT / Cross / Route).
  Le fichier est rattaché à la course dont le nom est celui du fichier (casse et accents ignorés), ou contenu de
  façon unique dans le nom du fichier (`TERRIL 89 - HENIN BEAUMONT.pdf` -> `HENIN BEAUMONT`).
- Il suffit de pousser le PDF sur `main` : la CI crée le post, met à jour `team.json`, les challenges et envoie la notification.
- Un PDF non rattaché est signalé dans le log de la CI (`[PDF] non rattaché ...`) : renommer le fichier.
- Si la colonne Club est vide (cas Lillers), les équipiers sont reconnus par leur nom dans `_data/team.json`.
- Le PDF doit être l'export Excel des classements (une feuille par page : `1ère Catégorie`, `2ème Catégorie`, ...).
