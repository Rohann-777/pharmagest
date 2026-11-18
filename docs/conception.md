# Dossier de conception - PharmaGest

Ce dossier décrit la structure des données (MCD, MLD) et le fonctionnement de l'application
(diagrammes UML) tels qu'ils sont **réellement implémentés** dans le code. Les éléments prévus
par le cahier des charges mais non réalisés sont listés à la fin, dans « Écarts ».

Les diagrammes sont écrits en Mermaid : GitHub les affiche directement. Pour les exporter en
image (PNG ou SVG), coller le bloc de code sur https://mermaid.live.

## 1. Organisation du projet

| Application Django | Responsabilité | Modèles |
|---|---|---|
| `utilisateurs/` | Comptes, groupes, permissions | `Utilisateur` |
| `catalogue/` | Référentiel des produits | `Categorie`, `Medicament` |
| `stock/` | Lots, journal et service de stock | `LotStock`, `MouvementStock` |
| `achats/` | Fournisseurs, commandes, réceptions | `Fournisseur`, `CommandeAchat`, `LigneAchat`, `ReceptionAchat`, `LigneReception` |
| `ventes/` | Caisse, ventes, reçu PDF | `Client`, `Vente`, `LigneVente` |
| `rapports/` | Tableau de bord, données de démonstration | aucun |

Les dépendances vont dans un seul sens, ce qui évite les imports circulaires :

```mermaid
flowchart LR
    catalogue --> stock
    stock --> achats
    stock --> ventes
    achats --> rapports
    ventes --> rapports
    utilisateurs -. auteur des opérations .-> stock
    utilisateurs -. auteur des opérations .-> achats
    utilisateurs -. auteur des opérations .-> ventes
```

Seul le service `stock/services.py` (`enregistrer_mouvement`) modifie la quantité d'un lot.
Les achats et les ventes l'appellent, ce qui place les règles de stock à un seul endroit.

## 2. Modèle conceptuel de données (MCD)

### 2.1 Entités

| Entité | Identifiant | Propriétés |
|---|---|---|
| CATEGORIE | id | nom (unique), description |
| MEDICAMENT | id | nom_commercial, denomination_generique, forme, dosage, laboratoire, code_barres (unique si renseigné), photo, prix_achat, prix_vente, seuil_alerte, statut, date_creation |
| LOT_STOCK | id | numero_lot, date_peremption, quantite_recue, quantite_disponible, bloque, date_creation |
| MOUVEMENT_STOCK | id | type_mouvement, quantite (signée), motif, date |
| FOURNISSEUR | id | nom, adresse, telephone, email, numero_fiscal, contact_principal, actif |
| COMMANDE_ACHAT | id | statut, date_creation, date_commande, notes |
| LIGNE_ACHAT | id | quantite_commandee, prix_achat_unitaire |
| RECEPTION_ACHAT | id | date, notes |
| LIGNE_RECEPTION | id | quantite_recue |
| CLIENT | id | nom, telephone, actif |
| VENTE | id | jeton (unique), mode_paiement, statut, date |
| LIGNE_VENTE | id | quantite, prix_unitaire |
| UTILISATEUR | id | identifiant, mot de passe (haché), nom, prénom, email, statuts |
| GROUPE | id | nom |

### 2.2 Associations et cardinalités (notation Merise)

| Association | Entité A (card.) | Entité B (card.) | Lecture |
|---|---|---|---|
| CLASSER | MEDICAMENT (1,1) | CATEGORIE (0,n) | Un médicament appartient à une seule catégorie ; une catégorie regroupe zéro ou plusieurs médicaments. |
| CONDITIONNER | LOT_STOCK (1,1) | MEDICAMENT (0,n) | Un lot concerne un seul médicament ; un médicament a zéro ou plusieurs lots. |
| TRACER | MOUVEMENT_STOCK (1,1) | LOT_STOCK (0,n) | Un mouvement porte sur un seul lot. |
| EFFECTUER | MOUVEMENT_STOCK (1,1) | UTILISATEUR (0,n) | Chaque mouvement a un auteur. |
| PASSER | COMMANDE_ACHAT (1,1) | FOURNISSEUR (0,n) | Une commande est adressée à un seul fournisseur. |
| CREER | COMMANDE_ACHAT (1,1) | UTILISATEUR (0,n) | Chaque commande a un auteur. |
| COMPOSER_ACHAT | LIGNE_ACHAT (1,1) | COMMANDE_ACHAT (0,n) | Une commande en brouillon peut être vide. |
| COMMANDER | LIGNE_ACHAT (1,1) | MEDICAMENT (0,n) | Une ligne commande un seul médicament. |
| RECEVOIR | RECEPTION_ACHAT (1,1) | COMMANDE_ACHAT (0,n) | Une commande peut être reçue en plusieurs fois. |
| CONTROLER | RECEPTION_ACHAT (1,1) | UTILISATEUR (0,n) | Chaque réception a un auteur. |
| COMPOSER_RECEPTION | LIGNE_RECEPTION (1,1) | RECEPTION_ACHAT (1,n) | Une réception contient au moins une ligne. |
| SOLDER | LIGNE_RECEPTION (1,1) | LIGNE_ACHAT (0,n) | Une ligne commandée peut être livrée en plusieurs fois. |
| ALIMENTER | LIGNE_RECEPTION (1,1) | LOT_STOCK (0,n) | Une ligne reçue alimente un seul lot. |
| ACHETER | VENTE (0,1) | CLIENT (0,n) | Le client est facultatif (vente au comptoir). |
| ENCAISSER | VENTE (1,1) | UTILISATEUR (0,n) | Chaque vente a un caissier. |
| COMPOSER_VENTE | LIGNE_VENTE (1,1) | VENTE (1,n) | Une vente contient au moins une ligne. |
| VENDRE | LIGNE_VENTE (1,1) | MEDICAMENT (0,n) | Une ligne vend un seul médicament. |
| DELIVRER | LIGNE_VENTE (1,1) | LOT_STOCK (0,n) | Une ligne indique le lot réellement délivré. |
| APPARTENIR | UTILISATEUR (0,n) | GROUPE (0,n) | Un utilisateur peut avoir plusieurs rôles. |

Les lignes (achat, réception, vente) sont des entités et non des associations porteuses :
`LIGNE_RECEPTION` doit pouvoir référencer une `LIGNE_ACHAT` précise, ce qui impose un identifiant.

### 2.3 Schéma entité-association

```mermaid
erDiagram
    CATEGORIE ||--o{ MEDICAMENT : classe
    MEDICAMENT ||--o{ LOT_STOCK : conditionne
    LOT_STOCK ||--o{ MOUVEMENT_STOCK : trace
    UTILISATEUR ||--o{ MOUVEMENT_STOCK : effectue
    FOURNISSEUR ||--o{ COMMANDE_ACHAT : recoit
    UTILISATEUR ||--o{ COMMANDE_ACHAT : cree
    COMMANDE_ACHAT ||--o{ LIGNE_ACHAT : contient
    MEDICAMENT ||--o{ LIGNE_ACHAT : commande
    COMMANDE_ACHAT ||--o{ RECEPTION_ACHAT : est_recue_par
    UTILISATEUR ||--o{ RECEPTION_ACHAT : controle
    RECEPTION_ACHAT ||--|{ LIGNE_RECEPTION : contient
    LIGNE_ACHAT ||--o{ LIGNE_RECEPTION : est_soldee_par
    LOT_STOCK ||--o{ LIGNE_RECEPTION : est_alimente_par
    CLIENT |o--o{ VENTE : achete
    UTILISATEUR ||--o{ VENTE : encaisse
    VENTE ||--|{ LIGNE_VENTE : contient
    MEDICAMENT ||--o{ LIGNE_VENTE : vendu_dans
    LOT_STOCK ||--o{ LIGNE_VENTE : delivre_dans
    UTILISATEUR }o--o{ GROUPE : appartient

    MEDICAMENT {
        int id PK
        string nom_commercial
        string code_barres UK "facultatif"
        decimal prix_achat
        decimal prix_vente
        int seuil_alerte
        string statut "actif ou archive"
    }
    LOT_STOCK {
        int id PK
        string numero_lot "unique par medicament"
        date date_peremption
        int quantite_disponible "jamais negative"
        bool bloque
    }
    MOUVEMENT_STOCK {
        int id PK
        string type_mouvement
        int quantite "positive entree, negative sortie"
        datetime date
    }
    VENTE {
        int id PK
        uuid jeton UK "anti double validation"
        string mode_paiement
        string statut
    }
    LIGNE_VENTE {
        int id PK
        int quantite
        decimal prix_unitaire "fige au moment de la vente"
    }
```

## 3. Modèle logique de données (MLD)

Notation : clé primaire soulignée en texte par `id`, clé étrangère précédée de `#`.
Les tables Django réelles sont préfixées par le nom de l'application (`catalogue_medicament`, etc.).

- **CATEGORIE** (id, nom, description)
- **MEDICAMENT** (id, nom_commercial, denomination_generique, forme, dosage, laboratoire, code_barres, photo, prix_achat, prix_vente, seuil_alerte, statut, date_creation, #categorie_id)
- **LOT_STOCK** (id, numero_lot, date_peremption, quantite_recue, quantite_disponible, bloque, date_creation, #medicament_id)
- **MOUVEMENT_STOCK** (id, type_mouvement, quantite, motif, date, #lot_id, #auteur_id)
- **FOURNISSEUR** (id, nom, adresse, telephone, email, numero_fiscal, contact_principal, actif)
- **COMMANDE_ACHAT** (id, statut, date_creation, date_commande, notes, #fournisseur_id, #cree_par_id)
- **LIGNE_ACHAT** (id, quantite_commandee, prix_achat_unitaire, #commande_id, #medicament_id)
- **RECEPTION_ACHAT** (id, date, notes, #commande_id, #recu_par_id)
- **LIGNE_RECEPTION** (id, quantite_recue, #reception_id, #ligne_achat_id, #lot_id)
- **CLIENT** (id, nom, telephone, actif)
- **VENTE** (id, jeton, mode_paiement, statut, date, #client_id, #caissier_id)
- **LIGNE_VENTE** (id, quantite, prix_unitaire, #vente_id, #medicament_id, #lot_id)
- **UTILISATEUR** (id, username, password, first_name, last_name, email, is_staff, is_superuser, is_active, last_login, date_joined)
- **GROUPE** (id, name)
- **UTILISATEUR_GROUPES** (#utilisateur_id, #groupe_id)

### Contraintes d'intégrité

| Contrainte | Où | Rôle |
|---|---|---|
| `UNIQUE (code_barres)`, valeur `NULL` autorisée | MEDICAMENT | RG02 : pas de doublon, mais plusieurs médicaments sans code |
| `UNIQUE (medicament_id, numero_lot)` | LOT_STOCK | Un numéro de lot n'existe qu'une fois par médicament |
| `CHECK (quantite_disponible >= 0)` | LOT_STOCK | RG07, filet de sécurité au niveau de la base |
| `UNIQUE (commande_id, medicament_id)` | LIGNE_ACHAT | Un médicament par commande |
| `UNIQUE (jeton)` | VENTE | RG06 : une validation répétée est refusée |
| `ON DELETE PROTECT` | toutes les clés étrangères sauf les lignes | RG10 : rien ne disparaît en cascade |
| `ON DELETE CASCADE` | lignes vers leur document | Une ligne n'existe que dans son document (brouillon supprimable) |

## 4. Diagrammes UML

### 4.1 Cas d'utilisation

Mermaid n'a pas de diagramme de cas d'utilisation natif : la figure ci-dessous en est une
représentation équivalente (acteurs à gauche, cas d'utilisation au centre). L'administrateur
hérite de tous les cas d'utilisation des autres acteurs.

```mermaid
flowchart LR
    caissier["Acteur : Caissier"]
    stock["Acteur : Gestionnaire de stock"]
    pharmacien["Acteur : Pharmacien responsable"]
    gestion["Acteur : Responsable de gestion"]
    admin["Acteur : Administrateur"]

    subgraph systeme["Système PharmaGest"]
        uc_auth(["S'authentifier"])
        uc_vente(["Vendre des médicaments"])
        uc_recu(["Imprimer le reçu PDF"])
        uc_catalogue(["Gérer le catalogue et les photos"])
        uc_cmd(["Gérer les commandes fournisseurs"])
        uc_recep(["Réceptionner une commande"])
        uc_lot(["Bloquer un lot"])
        uc_tdb(["Consulter le tableau de bord"])
        uc_users(["Gérer les utilisateurs et les rôles"])
    end

    caissier --> uc_vente
    caissier --> uc_recu
    stock --> uc_cmd
    stock --> uc_recep
    stock --> uc_lot
    pharmacien --> uc_catalogue
    pharmacien --> uc_vente
    pharmacien --> uc_lot
    gestion --> uc_tdb
    admin --> uc_users
    uc_vente -. "include" .-> uc_auth
    uc_recep -. "include" .-> uc_auth
    uc_catalogue -. "include" .-> uc_auth
    uc_recu -. "extend" .-> uc_vente
```

### 4.2 Diagramme de classes

```mermaid
classDiagram
    direction LR

    class Utilisateur {
        +username
        +groups
    }
    class Categorie {
        +nom
        +description
    }
    class Medicament {
        +nom_commercial
        +denomination_generique
        +forme
        +dosage
        +code_barres
        +photo
        +prix_achat
        +prix_vente
        +seuil_alerte
        +statut
    }
    class LotStock {
        +numero_lot
        +date_peremption
        +quantite_recue
        +quantite_disponible
        +bloque
        +est_perime() bool
        +est_delivrable() bool
    }
    class MouvementStock {
        +type_mouvement
        +quantite
        +motif
        +date
    }
    class Fournisseur {
        +nom
        +telephone
        +actif
    }
    class CommandeAchat {
        +statut
        +date_commande
        +numero() str
        +montant_total() Decimal
    }
    class LigneAchat {
        +quantite_commandee
        +prix_achat_unitaire
        +sous_total() Decimal
        +quantite_recue() int
        +quantite_restante() int
    }
    class ReceptionAchat {
        +date
        +numero() str
    }
    class LigneReception {
        +quantite_recue
    }
    class Client {
        +nom
        +telephone
    }
    class Vente {
        +jeton
        +mode_paiement
        +statut
        +numero() str
        +total() Decimal
    }
    class LigneVente {
        +quantite
        +prix_unitaire
        +sous_total() Decimal
    }
    class ServiceStock {
        <<service>>
        +enregistrer_mouvement(lot, type, quantite, auteur) MouvementStock
    }
    class ServiceAchats {
        <<service>>
        +valider_commande(commande)
        +annuler_commande(commande)
        +receptionner(commande, lignes, utilisateur) ReceptionAchat
    }
    class ServiceVentes {
        <<service>>
        +valider_vente(caissier, panier, mode_paiement, jeton) Vente
    }

    Categorie "1" --> "0..*" Medicament
    Medicament "1" --> "0..*" LotStock
    LotStock "1" --> "0..*" MouvementStock
    Utilisateur "1" --> "0..*" MouvementStock : auteur
    Fournisseur "1" --> "0..*" CommandeAchat
    CommandeAchat "1" *-- "0..*" LigneAchat
    LigneAchat "0..*" --> "1" Medicament
    CommandeAchat "1" --> "0..*" ReceptionAchat
    ReceptionAchat "1" *-- "1..*" LigneReception
    LigneReception "0..*" --> "1" LigneAchat
    LigneReception "0..*" --> "1" LotStock
    Client "0..1" --> "0..*" Vente
    Utilisateur "1" --> "0..*" Vente : caissier
    Vente "1" *-- "1..*" LigneVente
    LigneVente "0..*" --> "1" Medicament
    LigneVente "0..*" --> "1" LotStock
    ServiceAchats ..> ServiceStock : utilise
    ServiceVentes ..> ServiceStock : utilise
    ServiceStock ..> MouvementStock : crée
```

### 4.3 Diagramme de séquence : valider une vente

Ce scénario couvre RG06 (pas de double sortie), RG07 (pas de stock négatif), RG08 (lots
périmés ou bloqués exclus), RG12 (prix figé) et la règle FEFO.

```mermaid
sequenceDiagram
    actor C as Caissier
    participant V as Vue caisse
    participant SV as Service ventes
    participant SS as Service stock
    participant BD as Base de données

    C->>V: Valider la vente (panier, jeton, mode de paiement)
    V->>SV: valider_vente(...)
    activate SV
    Note over SV,BD: transaction.atomic, tout ou rien
    SV->>BD: Le jeton existe-t-il déjà ?
    alt jeton déjà utilisé
        SV-->>V: VenteError, vente déjà enregistrée
    else nouveau jeton
        SV->>BD: Créer la vente
        loop pour chaque article du panier
            SV->>BD: Lots valides et non bloqués, verrouillés, triés par péremption (FEFO)
            loop tant qu'il reste une quantité à servir
                SV->>SS: enregistrer_mouvement(lot, VENTE, -quantité prise)
                SS->>BD: Contrôle RG07 et RG08, mise à jour du lot, écriture du mouvement
                SV->>BD: Créer la ligne de vente (lot délivré, prix figé)
            end
            opt stock insuffisant
                SV-->>V: VenteError, annulation complète (rollback)
            end
        end
        SV-->>V: Vente validée
    end
    deactivate SV
    V-->>C: Message de confirmation et lien vers le reçu PDF
```

### 4.4 Diagramme de séquence : réceptionner une commande

```mermaid
sequenceDiagram
    actor G as Gestionnaire de stock
    participant V as Vue réception
    participant SA as Service achats
    participant SS as Service stock
    participant BD as Base de données

    G->>V: Saisir lots, péremptions et quantités reçues
    V->>SA: receptionner(commande, lignes, utilisateur)
    activate SA
    Note over SA,BD: transaction.atomic, tout ou rien
    SA->>BD: Verrouiller la commande, vérifier son statut (RG04)
    SA->>BD: Créer la réception
    loop pour chaque ligne reçue
        SA->>SA: Contrôles (quantité restante, lot non périmé)
        SA->>BD: Retrouver ou créer le lot
        SA->>SS: enregistrer_mouvement(lot, RECEPTION, +quantité)
        SS->>BD: Mise à jour du lot et écriture du mouvement (RG05)
        SA->>BD: Créer la ligne de réception
    end
    SA->>BD: Statut de la commande : partielle ou reçue
    SA-->>V: Réception enregistrée
    deactivate SA
    V-->>G: Message de confirmation
```

### 4.5 Diagramme d'états : commande d'achat

```mermaid
stateDiagram-v2
    state "Brouillon" as Brouillon
    state "Commandée" as Commandee
    state "Partiellement réceptionnée" as Partielle
    state "Entièrement réceptionnée" as Recue
    state "Annulée" as Annulee

    [*] --> Brouillon : création
    Brouillon --> Commandee : valider_commande()
    Brouillon --> Annulee : annuler_commande()
    Commandee --> Annulee : annuler_commande()
    Commandee --> Partielle : réception partielle
    Commandee --> Recue : réception complète
    Partielle --> Partielle : nouvelle réception partielle
    Partielle --> Recue : réception du reste
    Brouillon --> [*] : suppression (seul état supprimable)
    Recue --> [*]
    Annulee --> [*]
```

Seul un brouillon peut être modifié ou supprimé. Une commande validée est figée, ce qui
garantit que le stock reçu correspond toujours à ce qui a été commandé.

## 5. Traçabilité des règles de gestion

| Règle | Implémentation | Vérifiée par |
|---|---|---|
| RG01 Identifiant unique | Clé primaire automatique de chaque modèle | Structure de la base |
| RG02 Code-barres non dupliqué | `unique=True, null=True` sur `Medicament.code_barres` | Contrainte de base de données |
| RG03 Validation serveur | Valideurs des modèles, formulaires Django, contrôles des services | `catalogue/tests.py`, `stock/tests.py` |
| RG04 Commande sans effet sur le stock | Seul `receptionner()` appelle le service de stock | `achats/test_services.py` |
| RG05 Réception comptée une fois | Transaction atomique, contrôle du reste à recevoir | `achats/test_services.py` |
| RG06 Vente comptée une fois | Jeton unique, transaction atomique | `ventes/tests.py` |
| RG07 Stock jamais négatif | Contrôle dans `enregistrer_mouvement`, `CHECK` en base | `stock/tests.py`, `ventes/tests.py` |
| RG08 Lots périmés ou bloqués exclus | `LotStock.est_delivrable`, filtre FEFO de la vente | `stock/tests.py`, `ventes/tests.py` |
| RG09 Auteur, date, historique | Champs `auteur`, `cree_par`, `recu_par`, `caissier` ; journal en lecture seule | Admin verrouillé |
| RG10 Pas de suppression sans traçabilité | `on_delete=PROTECT`, archivage des médicaments, suppression limitée aux brouillons | Admin verrouillé, `catalogue/tests.py` |
| RG11 Accès aux seules fonctions autorisées | Groupes Django, `permission_required` sur chaque vue | `catalogue/tests.py`, `rapports/test_donnees_demo.py` |
| RG12 Prix historiques conservés | Prix copiés sur `LigneAchat` et `LigneVente` | `achats/tests.py`, `ventes/tests.py` |

## 6. Écarts avec le cahier des charges

| Prévu | Décision dans cette version |
|---|---|
| Table `Paiement` | Le mode de paiement est un champ de `Vente` (paiement unique, saisi à la main) |
| Table `RetourVente` | Non réalisée : les retours et remboursements ne sont pas gérés |
| Table `JournalAudit` | Non réalisée : la traçabilité repose sur les auteurs et dates des opérations et sur le journal des mouvements de stock |
| Apps `medicaments`, `fournisseurs`, `clients` séparées | Regroupées dans `catalogue`, `achats` et `ventes` pour limiter les dépendances croisées |
