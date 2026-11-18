from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings

from stock.models import MouvementStock
from ventes.models import Vente


class DonneesDemoTests(TestCase):
    @override_settings(DEBUG=True)
    def test_donnees_demo_s_executent_et_ecrivent_le_journal(self):
        call_command("donnees_demo", verbosity=0)
        self.assertEqual(Vente.objects.count(), 3)
        self.assertTrue(MouvementStock.objects.exists())

    @override_settings(DEBUG=True)
    def test_le_caissier_peut_vendre_mais_pas_receptionner(self):
        call_command("donnees_demo", verbosity=0)
        permissions = Group.objects.get(name="Caissier").permissions
        self.assertTrue(permissions.filter(codename="add_vente").exists())
        self.assertFalse(permissions.filter(codename="add_receptionachat").exists())

    def test_refuse_de_tourner_hors_mode_debug(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("donnees_demo", verbosity=0)