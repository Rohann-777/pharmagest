from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class PagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(username="admin", password="x")

    def test_pages_protegees_redirigent_vers_la_connexion(self):
        for nom in ("tableau_de_bord", "caisse"):
            reponse = self.client.get(reverse(nom))
            self.assertRedirects(reponse, f"{reverse('login')}?next={reverse(nom)}")

    def test_tableau_de_bord_et_caisse_s_affichent(self):
        self.client.force_login(self.admin)
        for nom in ("tableau_de_bord", "caisse"):
            self.assertEqual(self.client.get(reverse(nom)).status_code, 200)