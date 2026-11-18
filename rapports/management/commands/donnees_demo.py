import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from achats.models import CommandeAchat, Fournisseur, LigneAchat
from achats.services import receptionner, valider_commande
from catalogue.models import Categorie, Medicament
from stock.models import LotStock
from ventes.models import Vente
from ventes.services import valider_vente

MOT_DE_PASSE = "demo-pharmagest"


class Command(BaseCommand):
    help = "Charge un jeu de données fictives (base vide, mode DEBUG uniquement)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Cette commande crée des comptes de démonstration : mode DEBUG requis.")
        if Medicament.objects.exists():
            raise CommandError("La base contient déjà des médicaments : utilisez une base vide.")

        call_command("creer_groupes", verbosity=0)
        aujourdhui = timezone.localdate()

        def dans(jours):
            return aujourdhui + timedelta(days=jours)

        # Utilisateurs
        comptes = [
            ("demo_admin", "Administrateur", True),
            ("demo_pharmacien", "Pharmacien responsable", True),
            ("demo_stock", "Gestionnaire de stock", True),
            ("demo_caisse", "Caissier", False),
            ("demo_gestion", "Responsable de gestion", True),
        ]
        utilisateurs = {}
        for identifiant, groupe, equipe in comptes:
            utilisateur = get_user_model().objects.create_user(
                identifiant, password=MOT_DE_PASSE, is_staff=equipe
            )
            utilisateur.groups.add(Group.objects.get(name=groupe))
            utilisateurs[groupe] = utilisateur

        # Catalogue
        categories = {
            nom: Categorie.objects.create(nom=nom)
            for nom in ["Antalgiques", "Vitamines", "Antiseptiques", "Antipaludiques", "Antibiotiques"]
        }
        forme = Medicament.Forme
        catalogue = [
            ("Doliprane", "Paracétamol", "Antalgiques", forme.COMPRIME, "500 mg", "3400000000011", 1200, 1800, 20),
            ("Efferalgan", "Paracétamol", "Antalgiques", forme.COMPRIME, "1 g", "3400000000028", 2000, 2800, 15),
            ("Vitamine C", "Acide ascorbique", "Vitamines", forme.COMPRIME, "500 mg", None, 3500, 5000, 10),
            ("Bétadine", "Povidone iodée", "Antiseptiques", forme.AUTRE, "10 %", None, 4000, 5500, 8),
            ("Coartem", "Artéméther / luméfantrine", "Antipaludiques", forme.COMPRIME, "20/120 mg", "3400000000035", 12000, 16000, 10),
            ("Amoxicilline", "Amoxicilline", "Antibiotiques", forme.GELULE, "500 mg", "3400000000042", 3000, 4500, 15),
        ]
        medicaments = {}
        for nom, generique, categorie, f, dosage, code, achat, vente, seuil in catalogue:
            medicaments[nom] = Medicament.objects.create(
                nom_commercial=nom, denomination_generique=generique, categorie=categories[categorie],
                forme=f, dosage=dosage, code_barres=code, prix_achat=achat, prix_vente=vente,
                seuil_alerte=seuil,
            )

        # Fournisseurs
        ocean = Fournisseur.objects.create(
            nom="Océan Pharma Distribution", adresse="Zone Ankorondrano, Antananarivo",
            telephone="020 22 000 01", email="contact@oceanpharma.example", contact_principal="Mme Rasoa",
        )
        madamed = Fournisseur.objects.create(
            nom="MadaMed Grossiste", adresse="Rue de l'Indépendance, Toamasina",
            telephone="020 53 000 02", email="commandes@madamed.example", contact_principal="M. Andry",
        )
        Fournisseur.objects.create(
            nom="Pharmalog Indian Ocean", adresse="Zone Ivato, Antananarivo",
            telephone="020 22 000 03", email="info@pharmalog.example", contact_principal="M. Hery",
            actif=False,
        )

        # Achats : passés par les services, donc avec lots et mouvements de stock réels.
        gestionnaire = utilisateurs["Gestionnaire de stock"]

        def commander(fournisseur, articles):
            commande = CommandeAchat.objects.create(fournisseur=fournisseur, cree_par=gestionnaire)
            lignes = {
                nom: LigneAchat.objects.create(
                    commande=commande, medicament=medicaments[nom], quantite_commandee=quantite,
                    prix_achat_unitaire=medicaments[nom].prix_achat,
                )
                for nom, quantite in articles
            }
            return commande, lignes

        commande, lignes = commander(ocean, [
            ("Doliprane", 100), ("Efferalgan", 60), ("Vitamine C", 40), ("Bétadine", 30), ("Amoxicilline", 50),
        ])
        valider_commande(commande)

        def element(nom, numero, jours, quantite):
            return {"ligne_achat": lignes[nom], "numero_lot": numero,
                    "date_peremption": dans(jours), "quantite": quantite}

        receptionner(commande, [
            element("Doliprane", "LOT-DOL-A", 400, 60),
            element("Doliprane", "LOT-DOL-B", 20, 40),
            element("Efferalgan", "LOT-EFF-A", 500, 60),
            element("Vitamine C", "LOT-VIT-A", 250, 40),
            element("Bétadine", "LOT-BET-A", 300, 25),
            element("Bétadine", "LOT-BET-OLD", 10, 5),
            element("Amoxicilline", "LOT-AMX-A", 90, 50),
        ], gestionnaire)

        commande, lignes = commander(madamed, [("Coartem", 30)])
        valider_commande(commande)
        receptionner(commande, [element("Coartem", "LOT-COA-A", 365, 30)], gestionnaire)

        # Une commande validée, à réceptionner depuis l'interface pour s'exercer.
        commande, _ = commander(ocean, [("Efferalgan", 40), ("Amoxicilline", 30)])
        valider_commande(commande)

        # Situations d'alerte (démonstration uniquement) : un lot périmé et un lot bloqué.
        LotStock.objects.filter(numero_lot="LOT-BET-OLD").update(date_peremption=dans(-5))
        LotStock.objects.filter(numero_lot="LOT-COA-A").update(bloque=True)

        # Ventes du jour
        caissier = utilisateurs["Caissier"]
        ventes = [
            ({"Doliprane": 3, "Vitamine C": 1}, Vente.ModePaiement.ESPECES),
            ({"Efferalgan": 2}, Vente.ModePaiement.MOBILE_MONEY),
            ({"Amoxicilline": 4, "Doliprane": 5}, Vente.ModePaiement.ESPECES),
        ]
        for panier, mode in ventes:
            valider_vente(
                caissier=caissier,
                panier=[{"medicament": medicaments[nom], "quantite": q} for nom, q in panier.items()],
                mode_paiement=mode,
                jeton=uuid.uuid4(),
            )

        self.stdout.write(self.style.SUCCESS("Données de démonstration créées."))
        self.stdout.write(f"Comptes (mot de passe : {MOT_DE_PASSE}) :")
        for identifiant, groupe, _ in comptes:
            self.stdout.write(f"  {identifiant}  ({groupe})")