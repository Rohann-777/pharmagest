from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from achats.models import CommandeAchat
from catalogue.models import Medicament
from stock.models import LotStock
from stock.selectors import medicaments_avec_stock
from ventes.models import LigneVente, Vente

from . import pdf
from .statistiques import (
    PRESETS, barres_classees, formater_ar, graphique_par_jour, lire_periode, statistiques_ventes,
)


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


@login_required
@permission_required("ventes.voir_statistiques", raise_exception=True)
def rapport_ventes(request):
    periode = lire_periode(request.GET)
    stats = statistiques_ventes(periode)
    contexte = {
        "periode": periode,
        "presets": PRESETS,
        "stats": stats,
        "ca": formater_ar(stats["ca"]),
        "panier_moyen": formater_ar(stats["panier_moyen"]),
        "graphique": graphique_par_jour(stats["jours"]),
        "top_produits": barres_classees(stats["top_produits"]),
        "par_mode": barres_classees(stats["par_mode"]),
        # Le PDF reprend exactement la période affichée, même après un raccourci.
        "requete_pdf": urlencode(
            {"periode": "perso", "du": periode.debut.isoformat(), "au": periode.fin.isoformat()}
        ),
    }
    return render(request, "rapports/ventes.html", contexte)


def reponse_pdf(contenu, nom_fichier):
    reponse = HttpResponse(contenu, content_type="application/pdf")
    reponse["Content-Disposition"] = f'inline; filename="{nom_fichier}"'
    return reponse


@login_required
@permission_required("ventes.voir_statistiques", raise_exception=True)
def rapport_ventes_pdf(request):
    periode = lire_periode(request.GET)
    contenu = pdf.rapport_ventes(request.user, periode, statistiques_ventes(periode))
    return reponse_pdf(contenu, f"rapport-ventes-{periode.debut:%Y%m%d}-{periode.fin:%Y%m%d}.pdf")


@login_required
@permission_required("stock.view_lotstock", raise_exception=True)
def rapport_stock_pdf(request):
    return reponse_pdf(
        pdf.rapport_stock(request.user), f"rapport-stock-{timezone.localdate():%Y%m%d}.pdf"
    )


@login_required
@permission_required("stock.view_lotstock", raise_exception=True)
def peremptions_pdf(request):
    return reponse_pdf(
        pdf.liste_peremptions(request.user), f"peremptions-{timezone.localdate():%Y%m%d}.pdf"
    )


@login_required
@permission_required("achats.view_commandeachat", raise_exception=True)
def bon_commande_pdf(request, pk):
    commande = get_object_or_404(CommandeAchat.objects.select_related("fournisseur"), pk=pk)
    return reponse_pdf(pdf.bon_commande(commande, request.user), f"bon-commande-{commande.numero}.pdf")
