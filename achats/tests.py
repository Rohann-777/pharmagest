from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from catalogue.models import Categorie, Medicament

from .models import CommandeAchat, Fournisseur, LigneAchat


class MontantTotalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Les "décors" : tout ce dont une commande a besoin pour exister.
        cls.utilisateur = get_user_model().objects.create_user(
            username="gestionnaire", password="x"
        )
        cls.fournisseur = Fournisseur.objects.create(nom="Océan Pharma Distribution")
        categorie = Categorie.objects.create(nom="Antalgiques")
        cls.doliprane = Medicament.objects.create(
            nom_commercial="Doliprane", categorie=categorie, prix_achat=9999, prix_vente=1800
        )
        cls.efferalgan = Medicament.objects.create(
            nom_commercial="Efferalgan", categorie=categorie, prix_achat=2000, prix_vente=2800
        )

    def creer_commande(self):
        return CommandeAchat.objects.create(
            fournisseur=self.fournisseur, cree_par=self.utilisateur
        )

    def test_montant_total_additionne_les_lignes(self):
        commande = self.creer_commande()
        LigneAchat.objects.create(
            commande=commande, medicament=self.doliprane,
            quantite_commandee=10, prix_achat_unitaire=1200,
        )
        LigneAchat.objects.create(
            commande=commande, medicament=self.efferalgan,
            quantite_commandee=5, prix_achat_unitaire=2000,
        )
        self.assertEqual(commande.montant_total, Decimal("22000"))

    def test_commande_sans_ligne_a_un_total_nul(self):
        commande = self.creer_commande()
        self.assertEqual(commande.montant_total, Decimal("0"))

    def test_ligne_conserve_son_prix_quand_le_medicament_change_de_prix(self):
        commande = self.creer_commande()
        ligne = LigneAchat.objects.create(
            commande=commande, medicament=self.doliprane,
            quantite_commandee=10, prix_achat_unitaire=1200,
        )

        # Le prix du médicament change dans le catalogue.
        self.doliprane.prix_achat = 9999
        self.doliprane.save()

        ligne.refresh_from_db()
        # À TOI : que doit valoir ligne.sous_total ? Écris l'assertion (assertEqual).
        self.assertEqual(ligne.sous_total, Decimal("12000"))