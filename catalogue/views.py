from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from stock.selectors import annoter_stock

from .forms import MedicamentForm
from .models import Categorie, Medicament


class AccesRestreint(LoginRequiredMixin, PermissionRequiredMixin):
    """Non connecté : redirection vers la connexion. Connecté sans le droit : erreur 403."""


class MedicamentListe(AccesRestreint, ListView):
    permission_required = "catalogue.view_medicament"
    template_name = "catalogue/medicament_liste.html"
    context_object_name = "medicaments"
    paginate_by = 12

    def get_queryset(self):
        self.q = self.request.GET.get("q", "").strip()
        self.categorie = self.request.GET.get("categorie", "")
        self.archives = self.request.GET.get("archives") == "1"

        statut = Medicament.Statut.ARCHIVE if self.archives else Medicament.Statut.ACTIF
        medicaments = annoter_stock(
            Medicament.objects.filter(statut=statut).select_related("categorie")
        )
        if self.q:
            medicaments = medicaments.filter(
                Q(nom_commercial__icontains=self.q)
                | Q(denomination_generique__icontains=self.q)
                | Q(code_barres=self.q)
            )
        if self.categorie.isdigit():
            medicaments = medicaments.filter(categorie_id=self.categorie)
        return medicaments.order_by("nom_commercial")

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        filtres = self.request.GET.copy()
        filtres.pop("page", None)  # les liens de pagination gardent la recherche et les filtres
        contexte.update(
            q=self.q,
            categorie=self.categorie,
            archives=self.archives,
            categories=Categorie.objects.all(),
            filtres=filtres.urlencode(),
        )
        return contexte


class MedicamentCreation(AccesRestreint, SuccessMessageMixin, CreateView):
    permission_required = "catalogue.add_medicament"
    model = Medicament
    form_class = MedicamentForm
    template_name = "catalogue/medicament_formulaire.html"
    success_url = reverse_lazy("medicament_liste")
    success_message = "%(nom_commercial)s a été ajouté au catalogue."


class MedicamentModification(AccesRestreint, SuccessMessageMixin, UpdateView):
    permission_required = "catalogue.change_medicament"
    model = Medicament
    form_class = MedicamentForm
    template_name = "catalogue/medicament_formulaire.html"
    success_url = reverse_lazy("medicament_liste")
    success_message = "%(nom_commercial)s a été mis à jour."


class MedicamentArchivage(AccesRestreint, View):
    """Archiver au lieu de supprimer : l'historique des lots, achats et ventes est conservé (RG10)."""

    permission_required = "catalogue.change_medicament"

    def get(self, request, pk):
        medicament = get_object_or_404(Medicament, pk=pk)
        return render(request, "catalogue/medicament_archivage.html", {"medicament": medicament})

    def post(self, request, pk):
        medicament = get_object_or_404(Medicament, pk=pk)
        if medicament.statut == Medicament.Statut.ACTIF:
            medicament.statut = Medicament.Statut.ARCHIVE
            messages.success(request, f"{medicament} est archivé : il n'est plus proposé à la caisse.")
        else:
            medicament.statut = Medicament.Statut.ACTIF
            messages.success(request, f"{medicament} est de nouveau proposé à la caisse.")
        medicament.save(update_fields=["statut"])
        return redirect("medicament_liste")