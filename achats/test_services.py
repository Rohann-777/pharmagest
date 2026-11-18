from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from catalogue.models import Categorie, Medicament
from stock.models import LotStock

from .models import CommandeAchat, Fournisseur, LigneAchat, ReceptionAchat
from .services import AchatError, receptionner, valider_commande


class ReceptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.utilisateur = get_user_model().objects.create_user(
            username="gestionnaire", password="x"
        )
        fournisseur = Fournisseur.objects.create(nom="Océan Pharma Distribution")
        categorie = Categorie.objects.create(nom="Antalgiques")
        medicament = Medicament.objects.create(
            nom_commercial="Doliprane", categorie=categorie, prix_achat=1200, prix_vente=1800
        )
        cls.commande = CommandeAchat.objects.create(
            fournisseur=fournisseur, cree_par=cls.utilisateur
        )
        cls.ligne = LigneAchat.objects.create(
            commande=cls.commande, medicament=medicament,
            quantite_commandee=20, prix_achat_unitaire=1200,
        )
        cls.peremption = timezone.localdate() + timedelta(days=365)

    def item(self, quantite, numero="LOT-A", peremption=None):
        return {
            "ligne_achat": self.ligne,
            "numero_lot": numero,
            "date_peremption": peremption or self.peremption,
            "quantite": quantite,
        }

    def test_commande_brouillon_ne_peut_pas_etre_receptionnee(self):
        with self.assertRaises(AchatError):
            receptionner(self.commande, [self.item(5)], self.utilisateur)
        self.assertEqual(LotStock.objects.count(), 0)

    def test_reception_complete_cree_le_lot_et_augmente_le_stock_une_fois(self):
        valider_commande(self.commande)
        receptionner(self.commande, [self.item(20)], self.utilisateur)

        lot = LotStock.objects.get(numero_lot="LOT-A")
        self.assertEqual(lot.quantite_disponible, 20)
        self.assertEqual(lot.quantite_recue, 20)
        self.assertEqual(lot.mouvements.count(), 1)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, CommandeAchat.Statut.RECUE)

    def test_reception_partielle_puis_complete_sur_le_meme_lot(self):
        valider_commande(self.commande)
        receptionner(self.commande, [self.item(8)], self.utilisateur)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, CommandeAchat.Statut.PARTIELLE)

        receptionner(self.commande, [self.item(12)], self.utilisateur)
        lot = LotStock.objects.get(numero_lot="LOT-A")
        self.assertEqual(lot.quantite_disponible, 20)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, CommandeAchat.Statut.RECUE)

    def test_reception_superieure_au_reste_refusee_et_rien_n_est_enregistre(self):
        valider_commande(self.commande)
        with self.assertRaises(AchatError):
            receptionner(self.commande, [self.item(25)], self.utilisateur)
        self.assertEqual(LotStock.objects.count(), 0)
        self.assertEqual(ReceptionAchat.objects.count(), 0)

    def test_lot_deja_perime_refuse_a_la_reception(self):
        valider_commande(self.commande)
        hier = timezone.localdate() - timedelta(days=1)
        with self.assertRaises(AchatError):
            receptionner(self.commande, [self.item(5, peremption=hier)], self.utilisateur)