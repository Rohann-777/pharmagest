import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from catalogue.models import Categorie, Medicament
from stock.models import LotStock

from .models import LigneVente, Vente
from .services import VenteError, valider_vente


class VenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.caissier = get_user_model().objects.create_user(username="caissier", password="x")
        categorie = Categorie.objects.create(nom="Antalgiques")
        cls.medicament = Medicament.objects.create(
            nom_commercial="Doliprane", categorie=categorie, prix_achat=1200, prix_vente=1800
        )
        cls.proche = cls.creer_lot("LOT-PROCHE", 30, 5)
        cls.lointain = cls.creer_lot("LOT-LOINTAIN", 300, 10)
        cls.perime = cls.creer_lot("LOT-PERIME", -1, 50)

    @classmethod
    def creer_lot(cls, numero, jours, quantite):
        return LotStock.objects.create(
            medicament=cls.medicament,
            numero_lot=numero,
            date_peremption=timezone.localdate() + timedelta(days=jours),
            quantite_recue=quantite,
            quantite_disponible=quantite,
        )

    def vendre(self, quantite, jeton=None):
        return valider_vente(
            caissier=self.caissier,
            panier=[{"medicament": self.medicament, "quantite": quantite}],
            mode_paiement=Vente.ModePaiement.ESPECES,
            jeton=jeton or uuid.uuid4(),
        )

    def test_fefo_le_lot_le_plus_proche_sort_en_premier(self):
        self.vendre(3)
        self.proche.refresh_from_db()
        self.lointain.refresh_from_db()
        self.assertEqual(self.proche.quantite_disponible, 2)
        self.assertEqual(self.lointain.quantite_disponible, 10)

    def test_vente_repartie_sur_deux_lots(self):
        vente = self.vendre(8)
        self.proche.refresh_from_db()
        self.lointain.refresh_from_db()
        self.assertEqual(self.proche.quantite_disponible, 0)
        self.assertEqual(self.lointain.quantite_disponible, 7)
        self.assertEqual(vente.lignes.count(), 2)

    def test_lot_perime_exclu_et_rien_n_est_enregistre_en_cas_d_echec(self):
        # 15 unités valides (5 + 10) : demander 20 doit échouer malgré les 50 périmées.
        with self.assertRaises(VenteError):
            self.vendre(20)
        self.proche.refresh_from_db()
        self.assertEqual(self.proche.quantite_disponible, 5)
        self.assertEqual(Vente.objects.count(), 0)

    def test_double_validation_avec_le_meme_jeton_refusee(self):
        jeton = uuid.uuid4()
        self.vendre(2, jeton=jeton)
        with self.assertRaises(VenteError):
            self.vendre(2, jeton=jeton)
        self.proche.refresh_from_db()
        self.assertEqual(self.proche.quantite_disponible, 3)  # sorti une seule fois

    def test_le_prix_de_la_vente_est_fige(self):
        vente = self.vendre(3)
        self.medicament.prix_vente = 2500
        self.medicament.save()
        vente.refresh_from_db()
        self.assertEqual(vente.total, Decimal("5400"))

    def test_panier_vide_refuse(self):
        with self.assertRaises(VenteError):
            valider_vente(
                caissier=self.caissier, panier=[],
                mode_paiement=Vente.ModePaiement.ESPECES, jeton=uuid.uuid4(),
            )