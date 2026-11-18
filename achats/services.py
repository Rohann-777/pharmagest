from django.db import transaction
from django.db.models import F
from django.utils import timezone

from stock.models import LotStock, MouvementStock
from stock.services import enregistrer_mouvement

from .models import CommandeAchat, LigneReception, ReceptionAchat

Statut = CommandeAchat.Statut


class AchatError(Exception):
    """Règle métier d'achat non respectée (message affichable à l'utilisateur)."""


def _verrouiller(commande):
    return CommandeAchat.objects.select_for_update().get(pk=commande.pk)


@transaction.atomic
def valider_commande(commande):
    commande = _verrouiller(commande)
    if commande.statut != Statut.BROUILLON:
        raise AchatError("Seul un brouillon peut être validé.")
    if not commande.lignes.exists():
        raise AchatError("Une commande sans ligne ne peut pas être validée.")
    if not commande.fournisseur.actif:
        raise AchatError("Ce fournisseur est inactif.")

    commande.statut = Statut.COMMANDEE
    commande.date_commande = timezone.now()
    commande.save(update_fields=["statut", "date_commande"])
    return commande


@transaction.atomic
def annuler_commande(commande):
    commande = _verrouiller(commande)
    if commande.statut not in (Statut.BROUILLON, Statut.COMMANDEE):
        raise AchatError("Une commande déjà réceptionnée ne peut pas être annulée.")

    commande.statut = Statut.ANNULEE
    commande.save(update_fields=["statut"])
    return commande


@transaction.atomic
def receptionner(commande, lignes, utilisateur, notes=""):
    """Réceptionne tout ou partie d'une commande.

    `lignes` : liste de dictionnaires
    {"ligne_achat", "numero_lot", "date_peremption", "quantite"}.
    """
    commande = _verrouiller(commande)
    if commande.statut not in (Statut.COMMANDEE, Statut.PARTIELLE):
        raise AchatError("Seule une commande validée peut être réceptionnée.")
    if not lignes:
        raise AchatError("Aucune ligne à réceptionner.")

    reception = ReceptionAchat.objects.create(
        commande=commande, recu_par=utilisateur, notes=notes
    )

    for item in lignes:
        ligne_achat = item["ligne_achat"]
        quantite = item["quantite"]
        peremption = item["date_peremption"]

        if ligne_achat.commande_id != commande.pk:
            raise AchatError("Cette ligne n'appartient pas à la commande.")
        if quantite <= 0:
            raise AchatError("La quantité reçue doit être positive.")
        if quantite > ligne_achat.quantite_restante:
            raise AchatError(
                f"{ligne_achat.medicament} : {quantite} reçu(s) pour "
                f"{ligne_achat.quantite_restante} restant(s) à recevoir."
            )
        if peremption <= timezone.localdate():
            raise AchatError("Un lot déjà périmé ne peut pas être réceptionné.")

        lot, _ = LotStock.objects.get_or_create(
            medicament=ligne_achat.medicament,
            numero_lot=item["numero_lot"],
            defaults={
                "date_peremption": peremption,
                "quantite_recue": 0,
                "quantite_disponible": 0,
            },
        )
        if lot.date_peremption != peremption:
            raise AchatError(
                f"Le lot {lot.numero_lot} existe déjà avec une autre date de péremption."
            )

        enregistrer_mouvement(
            lot=lot,
            type_mouvement=MouvementStock.Type.RECEPTION,
            quantite=quantite,
            auteur=utilisateur,
            motif=f"{reception.numero} ({commande.numero})",
        )
        LotStock.objects.filter(pk=lot.pk).update(
            quantite_recue=F("quantite_recue") + quantite
        )
        LigneReception.objects.create(
            reception=reception, ligne_achat=ligne_achat, lot=lot, quantite_recue=quantite
        )

    soldee = all(l.quantite_restante == 0 for l in commande.lignes.all())
    commande.statut = Statut.RECUE if soldee else Statut.PARTIELLE
    commande.save(update_fields=["statut"])
    return reception