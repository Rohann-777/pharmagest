from django.db import transaction

from .models import LotStock, MouvementStock


class StockError(Exception):
    """Règle métier de stock non respectée (message affichable à l'utilisateur)."""


@transaction.atomic
def enregistrer_mouvement(*, lot, type_mouvement, quantite, auteur, motif=""):
    """Modifie le stock d'un lot et écrit le mouvement correspondant.

    `quantite` est signée : positive pour une entrée, négative pour une sortie.
    """
    Type = MouvementStock.Type

    if quantite == 0:
        raise StockError("La quantité ne peut pas être nulle.")
    if type_mouvement in (Type.RECEPTION, Type.RETOUR) and quantite < 0:
        raise StockError("Une entrée de stock doit avoir une quantité positive.")
    if type_mouvement == Type.VENTE and quantite > 0:
        raise StockError("Une vente doit avoir une quantité négative.")

    # On verrouille la ligne du lot et on relit son état réel dans la base.
    lot = LotStock.objects.select_for_update().get(pk=lot.pk)

    # RG08 : un lot périmé ou bloqué ne se vend pas.
    if type_mouvement == Type.VENTE and not lot.est_delivrable:
        raise StockError(
            f"Le lot {lot.numero_lot} n'est pas délivrable (périmé, bloqué ou vide)."
        )

    # RG07 : le stock ne peut pas devenir négatif.
    nouvelle_quantite = lot.quantite_disponible + quantite
    if nouvelle_quantite < 0:
        raise StockError(
            f"Stock insuffisant : {lot.quantite_disponible} disponible(s), "
            f"{-quantite} demandé(s)."
        )

    lot.quantite_disponible = nouvelle_quantite
    lot.save(update_fields=["quantite_disponible"])

    return MouvementStock.objects.create(
        lot=lot,
        type_mouvement=type_mouvement,
        quantite=quantite,
        motif=motif,
        auteur=auteur,
    )