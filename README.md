# Assistant de backlinks

Outil d'aide à la création de **backlinks légitimes** : le système trouve les
annuaires et plateformes pertinents pour la thématique d'un site, prépare des
fiches prêtes à soumettre, et suit l'avancement des soumissions.

## Philosophie : pas de spam

L'outil **ne soumet jamais un formulaire à votre place sur un site tiers**, et
ce quel que soit le rythme. La frontière n'est pas le volume mais le
consentement : poster des liens sur des sites qui ne vous appartiennent pas,
sans qu'ils l'autorisent, est du spam et finit pénalisé par les moteurs de
recherche.

Le partage des rôles est donc :

- 🤖 **Le robot** : détecte la thématique, trouve et classe les annuaires,
  prépare le contenu de chaque fiche, suit les statuts.
- 🔌 **Envoi automatique** : uniquement via les **API officielles** des
  plateformes qui l'autorisent explicitement (Google Business Profile, Bing
  Places, agrégateurs type Yext, plateformes de contenu type dev.to…).
- 🖐️ **Vous** : pour les annuaires à simple formulaire web, l'outil prépare
  tout (champs prêts à coller, lien direct) et **vous validez l'envoi** —
  quelques secondes par soumission.

## Prérequis

- Python 3.10+
- Aucune dépendance externe (bibliothèque standard uniquement)

## Lancement

```bash
python -m backlink_assistant
```

Puis ouvrez http://127.0.0.1:8000 dans votre navigateur.

Options :

```bash
python -m backlink_assistant --port 8080 --db mon_projet.db
```

Les données sont stockées en local dans un fichier SQLite (`backlinks.db` par
défaut). Rien n'est envoyé ailleurs.

## Utilisation

1. **Mes sites** — ajoutez un site. Le bouton « Analyser l'URL » télécharge la
   page et propose une thématique (titre, description, mots-clés). Si l'accès
   internet n'est pas disponible, saisissez les mots-clés à la main.
2. **Opportunités** — le système classe les annuaires par pertinence pour le
   site sélectionné, avec des badges (API officielle / soumission manuelle,
   gratuit / payant, type de lien). « Préparer la fiche » ouvre les champs
   prêts à coller.
3. **Aujourd'hui** — propose la meilleure soumission encore à traiter, pour
   avancer d'un backlink par jour.
4. **Suivi** — l'état de chaque soumission : à faire → soumis → validé.

## Catalogue d'annuaires

Le catalogue (`backlink_assistant/catalog.py`) liste des plateformes
légitimes avec leurs métadonnées : périmètre (généraliste / local / niche),
coût, présence d'une API officielle, type de lien. Les types de lien marqués
« inconnu » sont à vérifier au moment de la soumission (ils changent souvent).

## Tests

```bash
python -m unittest discover -s tests -v
```

## Architecture

| Module | Rôle |
| --- | --- |
| `catalog.py`  | Catalogue d'annuaires + classement par thématique |
| `analyze.py`  | Détection de thématique à partir d'une URL |
| `listing.py`  | Génération des champs de fiche prêts à coller |
| `db.py`       | Stockage local (SQLite) des sites et soumissions |
| `server.py`   | Serveur web local (API JSON + fichiers statiques) |
| `web/`        | Interface (HTML / CSS / JavaScript) |
