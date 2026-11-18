# PharmaGest

Application web de gestion de pharmacie développée avec Django : catalogue, stock par lots (FEFO),
achats et réceptions, ventes avec reçu PDF, tableau de bord, rôles et permissions.

## Fonctionnalités

- **Catalogue** : médicaments (photo, prix, seuil d'alerte, archivage) et catégories.
- **Stock** : lots avec date de péremption, journal des mouvements, blocage de lots, alertes.
- **Achats** : fournisseurs, commandes (brouillon, validée, réceptions partielles), réception avec création des lots.
- **Ventes** : caisse avec recherche, sortie de stock FEFO, prix figés, mode de paiement, reçu PDF.
- **Tableau de bord** : ventes du jour, stocks faibles, lots proches de la péremption ou périmés.
- **Sécurité** : authentification Django, groupes et permissions, secrets dans `.env`, protection CSRF.

## Règles de gestion appliquées

Le stock ne se modifie que par le service `stock/services.py`, dans une transaction atomique :
une réception ou une vente ne compte qu'une fois, le stock ne devient jamais négatif, un lot périmé
ou bloqué n'est jamais vendu, chaque mouvement garde son auteur et sa date, et les ventes et achats
validés ne se suppriment pas. Les prix sont copiés sur les lignes au moment de l'opération.

## Installation

Prérequis : [uv](https://docs.astral.sh/uv/).

```powershell
git clone https://github.com/Rohann-777/pharmagest.git
cd pharmagest
uv sync
copy .env.example .env
Renseigner aussi PHARMACIE_NOM, PHARMACIE_ADRESSE et PHARMACIE_TELEPHONE, imprimés sur les documents PDF.
```

Dans `.env`, remplace `SECRET_KEY` par une clé générée :

```powershell
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Puis :

```powershell
uv run python manage.py migrate
uv run python manage.py creer_groupes
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Application : http://127.0.0.1:8000/ , gestion des données : http://127.0.0.1:8000/admin/

## Données de démonstration (développement uniquement)

Sur une base vide, en mode `DEBUG=True` :

```powershell
uv run python manage.py donnees_demo
```

Comptes créés (mot de passe `demo-pharmagest`) : `demo_admin`, `demo_pharmacien`, `demo_stock`,
`demo_caisse`, `demo_gestion`. Ne jamais utiliser ces comptes en production.

## Rôles

| Groupe | Usage |
|---|---|
| Administrateur | Toutes les permissions |
| Pharmacien responsable | Catalogue, lots, achats, ventes |
| Gestionnaire de stock | Fournisseurs, commandes, réceptions, lots |
| Caissier | Caisse et reçus |
| Responsable de gestion | Consultation |

Un utilisateur qui doit accéder à l'admin doit avoir le statut « équipe » (`is_staff`).

## Tests

```powershell
uv run python manage.py test
```

## Structure

`catalogue/` (médicaments), `stock/` (lots, mouvements, service de stock), `achats/` (fournisseurs,
commandes, réceptions), `ventes/` (caisse, ventes, reçu PDF), `rapports/` (tableau de bord),
`utilisateurs/` (utilisateur personnalisé, groupes), `templates/`, `static/`.

## Documentation

- [Guide d'utilisation](docs/guide-utilisation.md)
- [Dossier de conception : MCD, MLD, diagrammes UML](docs/conception.md)

## Limites connues

Ce projet est une première version. Ne sont pas réalisés :

- Retours et annulations de vente (le modèle `RetourVente` n'existe pas encore).
- Table `JournalAudit` dédiée : la traçabilité repose sur l'auteur et la date des mouvements, ventes et réceptions.
- Factures, bons de réception et rapport des achats en PDF (sont disponibles : reçu, bon de commande, rapport de stock, liste des péremptions, rapport des ventes).
- Tableau de bord sans sélection de période ni classement des produits les plus vendus.
- Écrans dédiés pour les fournisseurs et les commandes : via l’admin Django.
- Réinitialisation de mot de passe par e-mail ; le mot de passe se change via l'admin.
- Sélection d'un client à la caisse (le modèle `Client` existe) ; paiement mobile money saisi manuellement, sans vérification automatique.
- Sauvegarde automatisée : à faire par copie de la base ou `pg_dump` en production.
- Le tableau de bord est visible par tous les utilisateurs connectés, sans statistiques adaptées au rôle.
- Mentions légales et fiscales des documents à adapter aux règles applicables à Madagascar.
- Ce logiciel ne remplace ni les contrôles professionnels de délivrance, ni les obligations réglementaires d'une pharmacie réelle.