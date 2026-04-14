# Secufer : suivi des attestations

Mini-outil destiné aux **services RH** pour suivre les attestations
délivrées par [Secufer](https://centre-secufer.fr) (validité **3 ans**)
et anticiper la programmation des **recyclages** avant leur expiration.

Chaque attestation délivrée à l'issue d'une formation (habilitations,
SST, CACES, travail en hauteur, etc.) a une durée de validité limitée.
Passé ce délai, le salarié doit être recyclé pour rester habilité. Cet
outil permet aux RH :

- d'enregistrer les attestations au fil de leur délivrance,
- de lister en un coup d'œil les attestations **à recycler prochainement**,
- d'enregistrer les recyclages effectués (nouvelle date de référence),
- de générer un **rapport HTML** à diffuser en interne.

Pour le catalogue des formations et la prise de rendez-vous pour un
recyclage, voir le site du centre : <https://centre-secufer.fr>.

## Prérequis

- Python 3.10+
- Aucune dépendance externe (bibliothèque standard uniquement)

## Installation

```bash
git clone https://github.com/adevis/secufer.git
cd secufer
```

## Utilisation

Toutes les commandes s'exécutent via `python -m secufer_tracker`. Les
données sont stockées dans un fichier CSV (par défaut `attestations.csv`
dans le répertoire courant). Il est facile à ouvrir avec Excel ou LibreOffice
et à sauvegarder.

### Ajouter une attestation

```bash
python -m secufer_tracker add \
    --nom Durand --prenom Alice \
    --email alice.durand@entreprise.fr \
    --formation "Habilitation électrique B1V" \
    --date-delivrance 2024-04-15
```

### Lister toutes les attestations

```bash
python -m secufer_tracker list
```

Chaque ligne indique la date d'expiration calculée et le statut :

| Statut         | Signification                                   |
| -------------- | ----------------------------------------------- |
| `valide`       | Expire dans plus de 90 jours                    |
| `À PROGRAMMER` | Expire dans 30 à 90 jours : planifier le recyclage |
| `URGENT`       | Expire dans moins de 30 jours                   |
| `EXPIRÉE`      | Date dépassée : salarié non habilité            |

### Lister les attestations qui expirent bientôt

```bash
# Par défaut : horizon 90 jours
python -m secufer_tracker expiring

# Horizon personnalisé (ex. semestre)
python -m secufer_tracker expiring --days 180
```

### Enregistrer un recyclage

Quand un salarié repasse sa formation, on met à jour la date de
référence. L'expiration est alors recalculée automatiquement (date du
recyclage + 3 ans).

```bash
python -m secufer_tracker renew --id 95341829 --date-recyclage 2027-03-10
```

### Générer un rapport HTML

Un rapport coloré par statut, prêt à imprimer ou à envoyer :

```bash
python -m secufer_tracker report --output rapport_attestations.html
```

Le rapport contient un lien direct vers
[centre-secufer.fr](https://centre-secufer.fr) pour faciliter la prise
de contact en vue des recyclages.

### Supprimer une attestation

```bash
python -m secufer_tracker remove --id 95341829
```

## Format des données

Le fichier CSV utilise les colonnes suivantes :

| Colonne                  | Description                                   |
| ------------------------ | --------------------------------------------- |
| `id`                     | Identifiant unique (généré automatiquement)   |
| `nom`, `prenom`, `email` | Identité du salarié                           |
| `formation`              | Intitulé de la formation Secufer              |
| `date_delivrance`        | Date de délivrance initiale (`YYYY-MM-DD`)    |
| `date_dernier_recyclage` | Date du dernier recyclage, si applicable      |
| `notes`                  | Commentaires libres                           |

## Tests

```bash
python -m unittest discover -s tests -v
```

## Licence

Usage interne Secufer. Voir <https://centre-secufer.fr> pour toute
question relative aux formations et attestations.
