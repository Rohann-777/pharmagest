from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.shortcuts import render
from django.utils import timezone

from catalogue.models import Medicament
from stock.models import LotStock
from stock.selectors import medicaments_avec_stock
from ventes.models import LigneVente, Vente


@login_required
def tableau_de_bord(request):
    aujourdhui = timezone.localdate()
    ventes_du_jour = Vente.objects.filter(
        date__date=aujourdhui, statut=Vente.Statut.VALIDEE
    )
    chiffre_affaires = LigneVente.objects.filter(vente__in=ventes_du_jour).aggregate(
        total=Sum(
            ExpressionWrapper(
                F("quantite") * F("prix_unitaire"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
    )["total"] or 0

    contexte = {
        "nb_medicaments": Medicament.objects.filter(statut=Medicament.Statut.ACTIF).count(),
        "nb_ventes": ventes_du_jour.count(),
        "chiffre_affaires": chiffre_affaires,
        "stocks_faibles": medicaments_avec_stock()
        .filter(stock__lte=F("seuil_alerte"))
        .order_by("stock"),
        "lots_proches": LotStock.objects.filter(
            quantite_disponible__gt=0,
            date_peremption__gte=aujourdhui,
            date_peremption__lte=aujourdhui + timedelta(days=30),
        )
        .select_related("medicament")
        .order_by("date_peremption"),
        "lots_perimes": LotStock.objects.filter(
            quantite_disponible__gt=0, date_peremption__lt=aujourdhui
        ).select_related("medicament"),
    }
    return render(request, "rapports/tableau_de_bord.html", contexte)