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
- [ ] Export des données synthétiques préparées pour la compétition
- [ ] Conversion dans le format de la compétition

## Doc
- [ ] Finaliser le README
- [ ] Faire un dépôt des données géographiques prétraitées et utilisées pour la compétition
- [ ] Définir la licence
- [ ] Citation
- [ ] Infos sur la compétition ICDAR