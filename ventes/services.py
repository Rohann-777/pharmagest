from django.db import transaction
from django.utils import timezone

from catalogue.models import Medicament
from stock.models import LotStock, MouvementStock
from stock.services import enregistrer_mouvement

from .models import LigneVente, Vente


class VenteError(Exception):
    """Règle métier de vente non respectée (message affichable)."""


@transaction.atomic
def valider_vente(*, caissier, panier, mode_paiement, jeton, client=None):
    """Valide une vente et sort le stock en FEFO.

    `panier` : liste de {"medicament": Medicament, "quantite": int}.
    """
    if not panier:
        raise VenteError("Le panier est vide.")
    if mode_paiement not in Vente.ModePaiement.values:
        raise VenteError("Mode de paiement invalide.")
    if Vente.objects.filter(jeton=jeton).exists():
        raise VenteError("Cette vente a déjà été enregistrée.")

    vente = Vente.objects.create(
        jeton=jeton, client=client, caissier=caissier, mode_paiement=mode_paiement
    )
    aujourdhui = timezone.localdate()

    for item in panier:
        quantite = item["quantite"]
        if quantite <= 0:
            raise VenteError("La quantité doit être positive.")

        # On relit le médicament : le prix de référence est celui de la base.
        medicament = Medicament.objects.get(pk=item["medicament"].pk)
        if medicament.statut != Medicament.Statut.ACTIF:
            raise VenteError(f"{medicament} n'est plus en vente.")

        # FEFO : lots valides, non bloqués, du plus proche de la péremption au plus lointain.
        lots = (
            LotStock.objects.select_for_update()
            .filter(
                medicament=medicament,
                bloque=False,
                quantite_disponible__gt=0,
                date_peremption__gte=aujourdhui,
            )
            .order_by("date_peremption")
        )

        reste = quantite
        for lot in lots:
            if reste == 0:
                break
            prise = min(lot.quantite_disponible, reste)
            enregistrer_mouvement(
                lot=lot,
                type_mouvement=MouvementStock.Type.VENTE,
                quantite=-prise,
                auteur=caissier,
                motif=f"Vente {vente.numero}",
            )
            LigneVente.objects.create(
                vente=vente,
                medicament=medicament,
                lot=lot,
                quantite=prise,
                prix_unitaire=medicament.prix_vente,
            )
            reste -= prise

        if reste > 0:
            raise VenteError(
                f"Stock insuffisant pour {medicament} : il manque {reste} unité(s)."
            )

    return vente