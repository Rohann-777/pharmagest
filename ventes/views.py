import uuid
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse

from catalogue.models import Medicament
from stock.selectors import medicaments_avec_stock

from .models import Vente
from .pdf import generer_recu
from .services import VenteError, valider_vente

CLE_PANIER = "caisse_panier"
CLE_JETON = "caisse_jeton"


def caissier_requis(vue):
    """Connexion + permission d'enregistrer une vente."""
    return login_required(permission_required("ventes.add_vente", raise_exception=True)(vue))

def retour_caisse(request):
    """Revient à la caisse en conservant la recherche en cours."""
    q = request.POST.get("q", "").strip()
    if q:
        return redirect(f"{reverse('caisse')}?{urlencode({'q': q})}")
    return redirect("caisse")

@caissier_requis
def caisse(request):
    q = request.GET.get("q", "").strip()
    resultats = []
    if q:
        resultats = medicaments_avec_stock().filter(
            Q(nom_commercial__icontains=q)
            | Q(denomination_generique__icontains=q)
            | Q(code_barres=q)
        )[:10]

    panier = request.session.get(CLE_PANIER, {})
    medicaments = Medicament.objects.in_bulk([int(pk) for pk in panier])
    lignes, total = [], Decimal("0")
    for pk, quantite in panier.items():
        medicament = medicaments.get(int(pk))
        if medicament is None:
            continue
        sous_total = medicament.prix_vente * quantite
        total += sous_total
        lignes.append({"medicament": medicament, "quantite": quantite, "sous_total": sous_total})

    if CLE_JETON not in request.session:
        request.session[CLE_JETON] = str(uuid.uuid4())

    return render(request, "ventes/caisse.html", {
        "q": q,
        "resultats": resultats,
        "lignes": lignes,
        "total": total,
        "jeton": request.session[CLE_JETON],
        "modes_paiement": Vente.ModePaiement.choices,
        "derniere_vente": Vente.objects.filter(pk=request.session.get("derniere_vente")).first(),
    })


@caissier_requis
@require_POST
def ajouter(request):
    medicament = get_object_or_404(
        Medicament, pk=request.POST.get("medicament"), statut=Medicament.Statut.ACTIF
    )
    try:
        quantite = int(request.POST.get("quantite", "1"))
    except ValueError:
        quantite = 0
    if quantite <= 0:
        messages.error(request, "La quantité doit être un nombre positif.")
        return retour_caisse(request)

    panier = request.session.get(CLE_PANIER, {})
    cle = str(medicament.pk)
    panier[cle] = panier.get(cle, 0) + quantite
    request.session[CLE_PANIER] = panier
    return retour_caisse(request)


@caissier_requis
@require_POST
def retirer(request, medicament_id):
    panier = request.session.get(CLE_PANIER, {})
    panier.pop(str(medicament_id), None)
    request.session[CLE_PANIER] = panier
    return retour_caisse(request)


@caissier_requis
@require_POST
def valider(request):
    panier = request.session.get(CLE_PANIER, {})
    medicaments = Medicament.objects.in_bulk([int(pk) for pk in panier])
    lignes = [
        {"medicament": medicaments[int(pk)], "quantite": quantite}
        for pk, quantite in panier.items()
        if int(pk) in medicaments
    ]
    try:
        vente = valider_vente(
            caissier=request.user,
            panier=lignes,
            mode_paiement=request.POST.get("mode_paiement", ""),
            jeton=uuid.UUID(request.POST.get("jeton", "")),
        )
    except (VenteError, ValueError) as erreur:
        messages.error(request, str(erreur))
        return redirect("caisse")

    request.session.pop(CLE_PANIER, None)
    request.session.pop(CLE_JETON, None)
    request.session["derniere_vente"] = vente.pk
    messages.success(request, f"Vente {vente.numero} enregistrée.")
    return redirect("caisse")


@login_required
@permission_required("ventes.view_vente", raise_exception=True)
def recu_pdf(request, pk):
    vente = get_object_or_404(Vente.objects.select_related("caissier", "client"), pk=pk)
    reponse = HttpResponse(generer_recu(vente), content_type="application/pdf")
    reponse["Content-Disposition"] = f'inline; filename="recu-{vente.numero}.pdf"'
    return reponse