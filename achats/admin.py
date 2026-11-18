from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .models import CommandeAchat, Fournisseur, LigneAchat, LigneReception, ReceptionAchat
from .services import AchatError, annuler_commande, valider_commande

Statut = CommandeAchat.Statut


class LigneAchatInline(admin.TabularInline):
    model = LigneAchat
    extra = 1

    def _modifiable(self, commande):
        # Les lignes ne changent plus une fois la commande validée.
        return commande is None or commande.statut == Statut.BROUILLON

    def has_add_permission(self, request, obj=None):
        return self._modifiable(obj)

    def has_change_permission(self, request, obj=None):
        return self._modifiable(obj)

    def has_delete_permission(self, request, obj=None):
        return self._modifiable(obj)


class LigneReceptionInline(admin.TabularInline):
    model = LigneReception
    extra = 0
    can_delete = False
    readonly_fields = ("ligne_achat", "lot", "quantite_recue")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "email", "actif")
    list_filter = ("actif",)
    search_fields = ("nom", "telephone")


@admin.register(CommandeAchat)
class CommandeAchatAdmin(admin.ModelAdmin):
    list_display = ("numero", "fournisseur", "statut", "montant_total", "date_creation", "lien_reception", "lien_bon")
    list_filter = ("statut", "fournisseur")
    exclude = ("cree_par",)
    readonly_fields = ("statut", "date_commande")
    inlines = [LigneAchatInline]
    actions = ["valider", "annuler"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.cree_par = request.user  # RG09
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        # RG10 : seul un brouillon peut être supprimé (et jamais en suppression groupée).
        return obj is not None and obj.statut == Statut.BROUILLON

    @admin.display(description="Réception")
    def lien_reception(self, obj):
        if obj.statut in (Statut.COMMANDEE, Statut.PARTIELLE):
            return format_html('<a href="{}">Réceptionner</a>', reverse("reception", args=[obj.pk]))
        return "-"

    @admin.display(description="Bon de commande")
    def lien_bon(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">PDF</a>', reverse("bon_commande_pdf", args=[obj.pk])
        )

    @admin.action(description="Valider les commandes sélectionnées", permissions=["change"])
    def valider(self, request, queryset):
        for commande in queryset:
            try:
                valider_commande(commande)
            except AchatError as erreur:
                self.message_user(request, f"{commande.numero} : {erreur}", level=messages.ERROR)
            else:
                self.message_user(request, f"{commande.numero} validée.")

    @admin.action(description="Annuler les commandes sélectionnées", permissions=["change"])
    def annuler(self, request, queryset):
        for commande in queryset:
            try:
                annuler_commande(commande)
            except AchatError as erreur:
                self.message_user(request, f"{commande.numero} : {erreur}", level=messages.ERROR)
            else:
                self.message_user(request, f"{commande.numero} annulée.")


@admin.register(ReceptionAchat)
class ReceptionAchatAdmin(admin.ModelAdmin):
    list_display = ("numero", "commande", "recu_par", "date")
    inlines = [LigneReceptionInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False