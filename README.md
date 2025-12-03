# R510-repartition-charge

##### Groupe
Théo Tornatore
Pierrick Marquillies

# Comment lancer le projet ? 
Tout d'abord, quelques dépendences :
mongosh https://www.mongodb.com/try/download/shell
mongo tools https://www.mongodb.com/try/download/database-tools
pymongo (pip install pymongo)
Il faut pensez à ajouter le chemin de mongo tools dans les variables environnements du système utilisateur

Aller dans le dossier docker (cd ./docker)
Exécuter docker compose -up
Patienter un peu pour que tous les containeurs se lancent correctement (énormément de logs vont s'afficher, dont possiblement des erreurs)

Exécuter le script de setup (./setup-cluster.ps1)
Attendre qu'il se termine

Le projet est lancé ! 

Il est maintenant possible de le tester via un script python
Aller dans le dossier scripts (cd ../scripts)
Exécuter le script python (py test.py)
Le script affiche (normalement) des informations confirmant le bon fonctionnement du projet !