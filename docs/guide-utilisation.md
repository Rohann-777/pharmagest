# Guide d'utilisation - PharmaGest

Ce guide explique comment utiliser PharmaGest au quotidien, rôle par rôle. Pour installer
l'application, voir le fichier `README.md` à la racine du projet.

## 1. Se connecter

1. Ouvrir l'adresse de l'application dans un navigateur (en local : http://127.0.0.1:8000/).
2. Saisir son **Identifiant** et son **Mot de passe**, puis cliquer sur **Se connecter**.
3. Le **Tableau de bord** s'affiche.

Pour quitter l'application, cliquer sur **Se déconnecter** en bas du menu latéral. Sur un poste
partagé (la caisse par exemple), il faut toujours se déconnecter en fin de service : chaque
vente et chaque opération est enregistrée au nom de l'utilisateur connecté.

## 2. Le menu et les rôles

Le menu latéral n'affiche que les fonctions autorisées pour l'utilisateur connecté.

| Rôle | Ce qu'il peut faire |
|---|---|
| Caissier | Vendre à la caisse, imprimer les reçus, consulter le catalogue |
| Pharmacien responsable | Gérer le catalogue et les photos, vendre, bloquer un lot, gérer les commandes |
| Gestionnaire de stock | Gérer fournisseurs et commandes, réceptionner, bloquer un lot, rapports de stock |
| Responsable de gestion | Consulter le tableau de bord, les données et les rapports |
| Administrateur | Tout, y compris la gestion des utilisateurs |

| Entrée du menu | Contenu |
|---|---|
| Tableau de bord | Ventes du jour, alertes de stock et de péremption, rapports PDF |
| Caisse | Recherche des médicaments, ticket en cours, validation des ventes |
| Médicaments | Catalogue avec photos, ajout, modification, archivage |
| Gestion des données | Fournisseurs, commandes d'achat, lots, utilisateurs (interface d'administration) |

Une page ouverte sans le droit nécessaire affiche une erreur 403 (accès interdit).

## 3. Vendre à la caisse

1. Cliquer sur **Caisse**.
2. Dans le champ de recherche, taper le nom commercial, le principe actif (par exemple
   « paracétamol ») ou scanner le code-barres, puis cliquer sur **Chercher**.
3. Chaque résultat affiche son prix et son état de stock :
   - un badge vert indique la quantité disponible ;
   - **Stock bas** signale un stock sous le seuil d'alerte ;
   - **Rupture** signale qu'aucune unité n'est vendable : le bouton **Ajouter** est désactivé.
4. Indiquer la quantité, puis cliquer sur **Ajouter**. L'article apparaît dans le **Ticket en
   cours**, et la liste des résultats reste affichée pour enchaîner.
5. Pour enlever un article du ticket, cliquer sur **Retirer**.
6. Choisir le **Mode de paiement** (Espèces, Mobile money ou Autre), puis cliquer sur
   **Valider la vente**.
7. Le message « Vente V-000123 enregistrée » s'affiche. Cliquer sur **Ouvrir le reçu PDF**
   pour l'imprimer.

Ce que l'application fait automatiquement :

- elle délivre d'abord le lot dont la date de péremption est la plus proche (règle FEFO) ;
- elle ne vend jamais un lot périmé ou bloqué ;
- elle refuse la vente si le stock est insuffisant, et dans ce cas **rien** n'est enregistré ;
- un double clic sur **Valider la vente** n'enregistre qu'une seule vente ;
- le prix figé sur le reçu est celui du jour de la vente, même si le prix change ensuite.

Le paiement mobile money est saisi à la main : l'application ne vérifie pas la transaction
auprès de l'opérateur.

## 4. Gérer le catalogue des médicaments

### Consulter

Cliquer sur **Médicaments**. La liste affiche la photo, le nom, la catégorie, le prix de vente et
le stock vendable de chaque médicament. On peut rechercher par nom, principe actif ou
code-barres, filtrer par catégorie, puis cliquer sur **Filtrer**. La liste est découpée en pages
de 12 médicaments.

### Ajouter un médicament

1. Cliquer sur **Ajouter un médicament**.
2. Remplir les champs. Ceux marqués d'un astérisque (*) sont obligatoires.
3. Choisir éventuellement une **Photo** : JPEG, PNG ou WEBP, 2 Mo maximum.
4. Cliquer sur **Ajouter au catalogue**.

En cas d'erreur (prix négatif, code-barres déjà utilisé, image trop lourde), le message s'affiche
sous le champ concerné et la saisie est conservée.

### Modifier un médicament

Cliquer sur **Modifier** sur la ligne du médicament, changer les champs, puis cliquer sur
**Enregistrer les modifications**. Pour garder la photo actuelle, laisser le champ photo vide.

Modifier un prix ne change pas les ventes et les commandes déjà enregistrées.

### Archiver un médicament

Un médicament n'est jamais supprimé, car cela effacerait l'historique de ses ventes et de ses
achats. On l'**archive** :

1. Cliquer sur **Archiver**, puis confirmer.
2. Le médicament disparaît de la caisse et de la liste principale.
3. Pour le retrouver, cocher **Afficher les archivés** puis cliquer sur **Filtrer**. Le lien
   **Réactiver** le remet en vente.

## 5. Approvisionner la pharmacie

Toutes ces opérations se font dans **Gestion des données**.

### Ajouter un fournisseur

**Achats > Fournisseurs > Ajouter**, remplir la fiche, puis **Enregistrer**. Un fournisseur qu'on
n'utilise plus est rendu inactif (case **Actif** décochée) : on ne peut plus lui passer de commande.

### Créer une commande

1. **Achats > Commandes d'achat > Ajouter**.
2. Choisir le fournisseur.
3. Dans les lignes, choisir chaque médicament, la quantité et le prix d'achat unitaire.
4. Cliquer sur **Enregistrer**. La commande est créée au statut **Brouillon**.

Un brouillon peut encore être modifié ou supprimé. **Une commande ne change pas le stock** :
seule la réception le fait.

### Valider, annuler, imprimer

Dans la liste des commandes, cocher la commande, choisir l'action **Valider les commandes
sélectionnées** (ou **Annuler les commandes sélectionnées**), puis cliquer sur **Envoyer**.
Une commande validée ne peut plus être modifiée.

Le lien **PDF** de la colonne **Bon de commande** ouvre le bon à transmettre au fournisseur.

### Réceptionner une livraison

1. Dans la liste des commandes, cliquer sur **Réceptionner** (colonne **Réception**). Le lien
   n'apparaît que pour une commande validée.
2. Pour chaque médicament livré, saisir le **N° de lot**, la date de **Péremption** et la
   **Quantité reçue**. Laisser la quantité vide pour un article non livré.
3. Cliquer sur **Enregistrer la réception**.

Le stock augmente immédiatement, une seule fois. Une livraison incomplète fait passer la
commande en **Partiellement réceptionnée** : la page de réception n'affiche alors que le reste à
recevoir. L'application refuse une quantité supérieure au reste commandé et un lot déjà périmé.

## 6. Surveiller le stock

### Tableau de bord

Le **Tableau de bord** affiche les ventes du jour (en ariary), le nombre de médicaments actifs,
les médicaments à réapprovisionner (stock sous le seuil d'alerte), les lots qui périment dans
moins de 30 jours et les lots périmés encore en stock. Tous les chiffres sont calculés à partir
des données réelles.

Le montant affiché est un chiffre d'affaires : ce n'est pas un bénéfice.

### Rapports PDF

Depuis le tableau de bord (rôles autorisés à consulter le stock) :

- **Rapport de stock (PDF)** : stock vendable de chaque médicament, état et valeur au prix d'achat ;
- **Péremptions sous 30 jours (PDF)** : lots périmés ou proches de l'échéance, à retirer de la vente.

### Rapport des ventes

Le menu **Rapport des ventes** (pharmacien responsable, responsable de gestion, administrateur)
affiche, pour la période choisie : le chiffre d'affaires, le nombre de ventes, le panier moyen,
les unités vendues, le chiffre d'affaires par jour, les produits les plus vendus et la répartition
par mode de paiement. Choisir un raccourci (7, 30 ou 90 jours, ce mois-ci) ou saisir deux dates puis
cliquer sur **Afficher** ; la période est limitée à 92 jours. **Exporter en PDF** produit le même
rapport pour la même période.

### Bloquer un lot

En cas de rappel de lot ou de doute sur un produit : **Gestion des données > Stock > Lots**,
ouvrir le lot, cocher **Bloqué**, puis **Enregistrer**. Le lot n'est plus jamais proposé à la
vente. Les quantités d'un lot ne se modifient pas à la main : elles ne changent que par les
réceptions et les ventes.

### Historique des mouvements

**Gestion des données > Stock > Mouvements de stock** liste chaque entrée et sortie avec son
type, sa quantité, son auteur et sa date. Cet historique ne peut être ni modifié ni supprimé.

## 7. Gérer les utilisateurs (administrateur)

1. **Gestion des données > Utilisateurs > Ajouter**, saisir un identifiant et un mot de passe,
   puis **Enregistrer**.
2. Sur la fiche qui s'ouvre, compléter le nom, choisir le ou les **Groupes** (le rôle).
3. Cocher **Statut équipe** si la personne doit accéder à **Gestion des données**. Ce n'est pas
   nécessaire pour un caissier.
4. **Enregistrer**.

Pour changer un mot de passe, ouvrir la fiche de l'utilisateur et suivre le lien du champ
**Mot de passe**. Pour retirer l'accès à un ancien employé, décocher **Actif** plutôt que de
supprimer son compte : son nom reste attaché à ses opérations passées.

## 8. Messages fréquents

| Message | Signification | Que faire |
|---|---|---|
| Stock insuffisant pour … | Il n'y a pas assez d'unités vendables (lots périmés et bloqués exclus) | Réduire la quantité ou réceptionner une commande |
| Cette vente a déjà été enregistrée | La validation a été envoyée deux fois | Rien : la vente n'est comptée qu'une fois |
| La photo dépasse 2 Mo | Image trop lourde | Réduire l'image ou en choisir une autre |
| Seule une commande validée peut être réceptionnée | La commande est encore en brouillon ou annulée | Valider la commande d'abord |
| … reçu(s) pour … restant(s) à recevoir | La quantité saisie dépasse ce qui reste à livrer | Corriger la quantité |
| Un lot déjà périmé ne peut pas être réceptionné | Date de péremption passée | Vérifier la date, refuser le lot au fournisseur |
| Erreur 403 | La fonction n'est pas autorisée pour ce rôle | Demander le droit à l'administrateur |

## 9. Limites de cette version

Les retours et remboursements de vente, les factures, les bons de réception et les rapports
des ventes et des achats ne sont pas encore disponibles. PharmaGest aide à gérer la
pharmacie mais ne remplace ni les contrôles professionnels de délivrance ni les obligations
réglementaires applicables.
