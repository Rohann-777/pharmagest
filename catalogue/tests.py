import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import MedicamentForm
from .models import Categorie, Medicament

# Les photos des tests sont écrites dans un dossier temporaire, jamais dans media/.
MEDIA_TEST = tempfile.mkdtemp()


def image_png(nom="photo.png"):
    tampon = BytesIO()
    Image.new("RGB", (20, 20), "teal").save(tampon, format="PNG")
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA_TEST)
class MedicamentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(username="admin", password="x")
        cls.sans_droit = get_user_model().objects.create_user(username="visiteur", password="x")
        cls.categorie = Categorie.objects.create(nom="Antalgiques")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_TEST, ignore_errors=True)
        super().tearDownClass()

    def donnees(self):
        return {
            "nom_commercial": "Doliprane", "categorie": self.categorie.pk, "forme": "comprime",
            "dosage": "500 mg", "prix_achat": "1200", "prix_vente": "1800", "seuil_alerte": "10",
        }

    def test_ajout_avec_photo_puis_photo_affichee_dans_la_liste(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(
            reverse("medicament_creation"), {**self.donnees(), "photo": image_png()}
        )
        self.assertRedirects(reponse, reverse("medicament_liste"))
        medicament = Medicament.objects.get()
        self.assertTrue(medicament.photo.name.startswith("medicaments/"))
        self.assertContains(self.client.get(reverse("medicament_liste")), medicament.photo.url)

    def test_modification_met_a_jour_le_medicament(self):
        medicament = Medicament.objects.create(
            nom_commercial="Doliprane", categorie=self.categorie, prix_achat=1200, prix_vente=1800
        )
        self.client.force_login(self.admin)
        self.client.post(
            reverse("medicament_modification", args=[medicament.pk]),
            {**self.donnees(), "prix_vente": "2000"},
        )
        medicament.refresh_from_db()
        self.assertEqual(medicament.prix_vente, 2000)

    def test_photo_trop_lourde_refusee(self):
        with patch("catalogue.forms.TAILLE_MAX_PHOTO", 10):
            formulaire = MedicamentForm(data=self.donnees(), files={"photo": image_png()})
            self.assertFalse(formulaire.is_valid())
        self.assertIn("photo", formulaire.errors)

    def test_fichier_qui_n_est_pas_une_image_refuse(self):
        faux = SimpleUploadedFile("photo.png", b"ceci n'est pas une image", content_type="image/png")
        formulaire = MedicamentForm(data=self.donnees(), files={"photo": faux})
        self.assertIn("photo", formulaire.errors)

    def test_prix_negatif_refuse_cote_serveur(self):
        formulaire = MedicamentForm(data={**self.donnees(), "prix_vente": "-5"})
        self.assertIn("prix_vente", formulaire.errors)

    def test_sans_permission_acces_interdit(self):
        self.client.force_login(self.sans_droit)
        for url in (reverse("medicament_liste"), reverse("medicament_creation")):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_archivage_conserve_le_medicament_et_le_retire_de_la_liste_active(self):
        medicament = Medicament.objects.create(
            nom_commercial="Vitamine C", categorie=self.categorie, prix_achat=3500, prix_vente=5000
        )
        self.client.force_login(self.admin)
        self.client.post(reverse("medicament_archivage", args=[medicament.pk]))
        medicament.refresh_from_db()
        self.assertEqual(medicament.statut, Medicament.Statut.ARCHIVE)
        reponse = self.client.get(reverse("medicament_liste"))
        self.assertNotIn(medicament, reponse.context["medicaments"])