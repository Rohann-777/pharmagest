from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogue.models import Categorie, Medicament
from stock.models import LotStock

from .models import Vente


class CaisseVueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.utilisateur = get_user_model().objects.create_superuser(username="admin", password="x")
        categorie = Categorie.objects.create(nom="Antalgiques")
        cls.medicament = Medicament.objects.create(
            nom_commercial="Doliprane", categorie=categorie, prix_achat=1200, prix_vente=1800
        )
        cls.lot = LotStock.objects.create(
            medicament=cls.medicament, numero_lot="LOT-1",
            date_peremption=timezone.localdate() + timedelta(days=200),
            quantite_recue=10, quantite_disponible=10,
        )

    def test_flux_complet_ajout_validation_et_recu_pdf(self):
        self.client.force_login(self.utilisateur)
        self.client.post(reverse("caisse_ajouter"), {"medicament": self.medicament.pk, "quantite": 3})
        jeton = self.client.get(reverse("caisse")).context["jeton"]
        self.client.post(reverse("caisse_valider"), {"jeton": jeton, "mode_paiement": "especes"})

        self.assertEqual(Vente.objects.count(), 1)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite_disponible, 7)

        reponse = self.client.get(reverse("recu_pdf", args=[Vente.objects.get().pk]))
        self.assertEqual(reponse["Content-Type"], "application/pdf")
        self.assertTrue(reponse.content.startswith(b"%PDF"))