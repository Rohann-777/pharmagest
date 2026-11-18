import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogue.models import Categorie, Medicament
from stock.models import LotStock
from ventes.models import LigneVente, Vente

from .statistiques import Periode, lire_periode, statistiques_ventes


class RapportVentesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(username="admin", password="x")
        # Un caissier peut voir ses ventes, mais pas les statistiques (RG11).
        cls.caissier = get_user_model().objects.create_user(username="caissier", password="x")
        cls.caissier.user_permissions.add(Permission.objects.get(codename="view_vente"))

        categorie = Categorie.objects.create(nom="Antalgiques")
        cls.doliprane = Medicament.objects.create(
            nom_commercial="Doliprane", dosage="500 mg", categorie=categorie, prix_achat=1200, prix_vente=1800
        )
        cls.vitamine = Medicament.objects.create(
            nom_commercial="Vitamine C", categorie=categorie, prix_achat=3500, prix_vente=5000
        )
        cls.lot = LotStock.objects.create(
            medicament=cls.doliprane, numero_lot="L1",
            date_peremption=timezone.localdate() + timedelta(days=300),
            quantite_recue=100, quantite_disponible=100,
        )
        cls.aujourdhui = timezone.localdate()

        # Dans la période : 2 ventes aujourd'hui, 1 il y a 3 jours.
        cls.vendre(cls.doliprane, 3, Vente.ModePaiement.ESPECES, il_y_a=0)          # 5 400
        cls.vendre(cls.vitamine, 2, Vente.ModePaiement.MOBILE_MONEY, il_y_a=0)      # 10 000
        cls.vendre(cls.doliprane, 1, Vente.ModePaiement.ESPECES, il_y_a=3)          # 1 800
        # Hors période ou annulée : ne doivent jamais être comptées.
        cls.vendre(cls.doliprane, 50, Vente.ModePaiement.ESPECES, il_y_a=40)
        cls.vendre(cls.doliprane, 20, Vente.ModePaiement.ESPECES, il_y_a=1, statut=Vente.Statut.ANNULEE)

    @classmethod
    def vendre(cls, medicament, quantite, mode, il_y_a, statut=Vente.Statut.VALIDEE):
        vente = Vente.objects.create(
            jeton=uuid.uuid4(), caissier=cls.admin, mode_paiement=mode, statut=statut
        )
        # `date` est remplie automatiquement à la création : on la recule ensuite pour le test.
        Vente.objects.filter(pk=vente.pk).update(date=timezone.now() - timedelta(days=il_y_a))
        LigneVente.objects.create(
            vente=vente, medicament=medicament, lot=cls.lot,
            quantite=quantite, prix_unitaire=medicament.prix_vente,
        )

    def periode_7_jours(self):
        return Periode(self.aujourdhui - timedelta(days=6), self.aujourdhui, "7")

    def test_totaux_ne_comptent_que_les_ventes_validees_de_la_periode(self):
        stats = statistiques_ventes(self.periode_7_jours())
        self.assertEqual(stats["ca"], Decimal("17200"))
        self.assertEqual(stats["nb_ventes"], 3)
        self.assertEqual(stats["unites"], 6)

    def test_un_point_par_jour_meme_sans_vente(self):
        stats = statistiques_ventes(self.periode_7_jours())
        self.assertEqual(len(stats["jours"]), 7)
        self.assertEqual(stats["jours"][-1]["ca"], Decimal("15400"))  # aujourd'hui
        self.assertEqual(stats["jours"][-2]["ca"], 0)                   # hier : vente annulée

    def test_produits_classes_par_chiffre_d_affaires(self):
        stats = statistiques_ventes(self.periode_7_jours())
        noms = [p["nom"] for p in stats["top_produits"]]
        self.assertEqual(noms, ["Vitamine C", "Doliprane 500 mg"])

    def test_periode_personnalisee_invalide_revient_aux_30_jours(self):
        periode = lire_periode({"periode": "perso", "du": "2026-05-10", "au": "2026-05-01"})
        self.assertEqual(periode.cle, "30")
        self.assertTrue(periode.erreur)

    def test_periode_trop_longue_refusee(self):
        periode = lire_periode({"periode": "perso", "du": "2026-01-01", "au": "2026-06-30"})
        self.assertTrue(periode.erreur)

    def test_page_et_pdf_accessibles_avec_la_permission(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse("rapport_ventes"), {"periode": "7"})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "17 200 Ar")
        pdf = self.client.get(reverse("rapport_ventes_pdf"), {"periode": "7"})
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_statistiques_interdites_sans_la_permission_dediee(self):
        self.client.force_login(self.caissier)
        self.assertEqual(self.client.get(reverse("rapport_ventes")).status_code, 403)
        self.assertEqual(self.client.get(reverse("rapport_ventes_pdf")).status_code, 403)
