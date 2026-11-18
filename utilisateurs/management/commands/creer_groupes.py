from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

CRUD = ["add", "change", "view"]

# {groupe: {application: {modèle: [actions]}}}
ROLES = {
    "Pharmacien responsable": {
        "catalogue": {"categorie": CRUD, "medicament": CRUD},
        "stock": {"lotstock": ["change", "view"], "mouvementstock": ["view"]},
        "achats": {
            "fournisseur": ["view"], "commandeachat": CRUD, "ligneachat": CRUD,
            "receptionachat": ["add", "view"], "lignereception": ["view"],
        },
        "ventes": {"vente": ["add", "view"], "lignevente": ["view"], "client": ["view"]},
    },
    "Gestionnaire de stock": {
        "catalogue": {"categorie": ["view"], "medicament": ["view"]},
        "stock": {"lotstock": ["change", "view"], "mouvementstock": ["view"]},
        "achats": {
            "fournisseur": CRUD, "commandeachat": CRUD, "ligneachat": CRUD,
            "receptionachat": ["add", "view"], "lignereception": ["view"],
        },
    },
    "Caissier": {
        "catalogue": {"medicament": ["view"]},
        "ventes": {"vente": ["add", "view"], "lignevente": ["view"], "client": ["add", "view"]},
    },
    "Responsable de gestion": {
        "catalogue": {"categorie": ["view"], "medicament": ["view"]},
        "stock": {"lotstock": ["view"], "mouvementstock": ["view"]},
        "achats": {
            "fournisseur": ["view"], "commandeachat": ["view"], "ligneachat": ["view"],
            "receptionachat": ["view"], "lignereception": ["view"],
        },
        "ventes": {"vente": ["view"], "lignevente": ["view"], "client": ["view"]},
    },
}
# Permissions personnalisées, déclarées dans Meta.permissions des modèles.
SPECIALES = {
    "Pharmacien responsable": [("ventes", "voir_statistiques")],
    "Responsable de gestion": [("ventes", "voir_statistiques")],
}

class Command(BaseCommand):
    help = "Crée ou met à jour les groupes d'utilisateurs et leurs permissions."

    def handle(self, *args, **options):
        administrateur, _ = Group.objects.get_or_create(name="Administrateur")
        administrateur.permissions.set(Permission.objects.all())
        self.stdout.write(self.style.SUCCESS("Administrateur : toutes les permissions"))

        for nom_groupe, droits in ROLES.items():
            groupe, _ = Group.objects.get_or_create(name=nom_groupe)
            permissions = [
                Permission.objects.get(
                    content_type__app_label=application, codename=f"{action}_{modele}"
                )
                for application, modeles in droits.items()
                for modele, actions in modeles.items()
                for action in actions
            ]
            permissions += [
                Permission.objects.get(content_type__app_label=application, codename=code)
                for application, code in SPECIALES.get(nom_groupe, [])
            ]
            groupe.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f"{nom_groupe} : {len(permissions)} permission(s)"))