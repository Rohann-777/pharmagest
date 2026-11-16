from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from catalogue.models import Categorie, Medicament

from .models import LotStock, MouvementStock
from .services import StockError, enregistrer_mouvement

Type = MouvementStock.Type


class EnregistrerMouvementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.auteur = get_user_model().objects.create_user(username="caissier", password="x")
        categorie = Categorie.objects.create(nom="Antalgiques")
        cls.medicament = Medicament.objects.create(
            nom_commercial="Doliprane", categorie=categorie, prix_achat=1200, prix_vente=1800
        )

    def creer_lot(self, numero="LOT-1", jours=365, quantite=20, bloque=False):
        return LotStock.objects.create(
            medicament=self.medicament,
            numero_lot=numero,
            date_peremption=timezone.localdate() + timedelta(days=jours),
            quantite_recue=quantite,
            quantite_disponible=quantite,
            bloque=bloque,
        )

    def test_reception_augmente_le_stock_une_seule_fois(self):
        lot = self.creer_lot(quantite=10)
        enregistrer_mouvement(lot=lot, type_mouvement=Type.RECEPTION, quantite=20, auteur=self.auteur)
        lot.refresh_from_db()
        self.assertEqual(lot.quantite_disponible, 30)
        self.assertEqual(lot.mouvements.count(), 1)

    def test_vente_diminue_le_stock(self):
        lot = self.creer_lot(quantite=20)
        mouvement = enregistrer_mouvement(lot=lot, type_mouvement=Type.VENTE, quantite=-3, auteur=self.auteur)
        lot.refresh_from_db()
        self.assertEqual(lot.quantite_disponible, 17)
        self.assertEqual(mouvement.quantite, -3)

    def test_vente_superieure_au_stock_refusee(self):
        lot = self.creer_lot(quantite=20)
        with self.assertRaises(StockError):
            enregistrer_mouvement(lot=lot, type_mouvement=Type.VENTE, quantite=-25, auteur=self.auteur)
        lot.refresh_from_db()
        self.assertEqual(lot.quantite_disponible, 20)
        self.assertEqual(lot.mouvements.count(), 0)

    def test_vente_lot_perime_refusee(self):
        lot = self.creer_lot(jours=-1)
        with self.assertRaises(StockError):
            enregistrer_mouvement(lot=lot, type_mouvement=Type.VENTE, quantite=-1, auteur=self.auteur)

    def test_vente_lot_bloque_refusee(self):
        lot = self.creer_lot(bloque=True)
        with self.assertRaises(StockError):
            enregistrer_mouvement(lot=lot, type_mouvement=Type.VENTE, quantite=-1, auteur=self.auteur)

    def test_quantite_nulle_refusee(self):
        lot = self.creer_lot()
        with self.assertRaises(StockError):
            enregistrer_mouvement(lot=lot, type_mouvement=Type.CORRECTION, quantite=0, auteur=self.auteur)