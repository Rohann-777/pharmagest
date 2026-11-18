from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from achats.models import CommandeAchat, Fournisseur, LigneAchat
from catalogue.models import Categorie, Medicament
from stock.models import LotStock


class RapportsPdfTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(username="admin", password="x")
        cls.sans_droit = get_user_model().objects.create_user(username="caissier", password="x")
        categorie = Categorie.objects.create(nom="Antalgiques")
        medicament = Medicament.objects.create(
            nom_commercial="Doliprane", categorie=categorie, prix_achat=1200, prix_vente=1800
        )
        aujourdhui = timezone.localdate()
        LotStock.objects.create(
            medicament=medicament, numero_lot="LOT-OK", date_peremption=aujourdhui + timedelta(days=300),
            quantite_recue=50, quantite_disponible=50,
        )
        LotStock.objects.create(
            medicament=medicament, numero_lot="LOT-PERIME", date_peremption=aujourdhui - timedelta(days=2),
            quantite_recue=5, quantite_disponible=5,
        )
        cls.commande = CommandeAchat.objects.create(
            fournisseur=Fournisseur.objects.create(nom="Océan Pharma & Fils"), cree_par=cls.admin
        )
        LigneAchat.objects.create(
            commande=cls.commande, medicament=medicament, quantite_commandee=20, prix_achat_unitaire=1200
        )

    def urls(self):
        return [
            reverse("rapport_stock_pdf"),
            reverse("peremptions_pdf"),
            reverse("bon_commande_pdf", args=[self.commande.pk]),
        ]

    def test_chaque_rapport_est_un_pdf_valide(self):
        self.client.force_login(self.admin)
        for url in self.urls():
            reponse = self.client.get(url)
            self.assertEqual(reponse["Content-Type"], "application/pdf", url)
            self.assertTrue(reponse.content.startswith(b"%PDF"), url)

    def test_rapports_interdits_sans_permission(self):
        self.client.force_login(self.sans_droit)
        for url in self.urls():
            self.assertEqual(self.client.get(url).status_code, 403, url)