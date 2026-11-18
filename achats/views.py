from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import CommandeAchat
from .services import AchatError, receptionner


@login_required
@permission_required("achats.add_receptionachat", raise_exception=True)
def reception(request, pk):
    commande = get_object_or_404(CommandeAchat.objects.select_related("fournisseur"), pk=pk)
    lignes = [l for l in commande.lignes.select_related("medicament") if l.quantite_restante > 0]

    # On conserve la saisie si le formulaire est renvoyé avec une erreur.
    for ligne in lignes:
        ligne.val_lot = request.POST.get(f"lot_{ligne.pk}", "")
        ligne.val_peremption = request.POST.get(f"peremption_{ligne.pk}", "")
        ligne.val_quantite = request.POST.get(f"quantite_{ligne.pk}", "")

    if request.method == "POST":
        try:
            elements = []
            for ligne in lignes:
                quantite = int(ligne.val_quantite or 0)
                if quantite == 0:
                    continue  # ligne non livrée
                if not ligne.val_lot.strip():
                    raise AchatError("Indiquez un numéro de lot pour chaque ligne reçue.")
                elements.append({
                    "ligne_achat": ligne,
                    "quantite": quantite,
                    "numero_lot": ligne.val_lot.strip(),
                    "date_peremption": date.fromisoformat(ligne.val_peremption),
                })
            reception_enregistree = receptionner(commande, elements, request.user)
        except AchatError as erreur:
            messages.error(request, str(erreur))
        except ValueError:
            messages.error(request, "Vérifiez les quantités et les dates de péremption saisies.")
        else:
            messages.success(request, f"Réception {reception_enregistree.numero} enregistrée.")
            return redirect("admin:achats_commandeachat_changelist")

    return render(request, "achats/reception.html", {"commande": commande, "lignes": lignes})