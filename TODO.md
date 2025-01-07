# TODO

## Code
- [ ] Script de pré-traitement des données issues de la BDTOPO :
    - Pour chaque département : 
        - [X] Dans la couche département, sélectionner l'entité avec le code insee correspondant
        - [X] Pour l'ensemble des couches associées (surface hydro, cours d'eau, lieu dit non nommé, tronçon de route), sélectionner les objets situées dans la géométrie du département et les exporter dans une nouvelle couche
        - [X] Fusionner les couches de même type des différents départements une seule
        - [ ] Ajouter les couches dans la base de données automatiquement
- [ ] Joseph : parfois pour les éléments linéaires (cours d'eau ou routes), il arrive qu'il y ait 2 fois le texte, est-ce évitable ? Supprimer en post-traitement ?
- [X] Intégrer un peu de rotation dans les numéros de parcelles pour permettre au réseau d'apprendre ces variations
- [X] Export des données synthétiques préparées pour la compétition
- [X] Conversion dans le format de la compétition

## Bugs identifiés
- Avec QGIS, pour les objets linéaires, l'étiquette d'un même objet peut être est répétée plusieurs fois (dépend des paramètres de styles). La distance entre deux répétitions doit être fixée par l'utilisateur.
    - Il semble que QGIS ne génère les boites (annotations) que pour une vsualisation du label (pas pour toutes). Il faut paramétrer la distance minimale entre deux répétitions au delà de la longueur du plus long objet dans une même zone : 
        - 1900m pour les cours d'eau => 2000m
        - Désactiver la répétition pour les autres couches linéaires.
- Avec un petit écran (style PC) (???), les images générées ont une dimension 3000x3000 pixels (pourquoi ???), alors qu'avec QGIS ouvert sur un écran les images ont bien une dimension de 2000*2000 pixels comme fixé dans le code.

## Amélioration des données
- Problème des rues à doubles voies qui créent des mots dupliqués...
    - Faire une zone tampon (r=12) autour des tronçons de rues (largeur uniquement).
    - Supprimer les objets avec un label vide
    - Si les buffers se touches (intérieur) et même label.

## Doc
- [ ] Finaliser le README
- [ ] Faire un dépôt des données géographiques prétraitées et utilisées pour la compétition
- [ ] Définir la licence
- [ ] Citation
- [ ] Infos sur la compétition ICDAR