from django.contrib import admin

from .models import Client, LigneVente, Vente


class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 0
    can_delete = False
    readonly_fields = ("medicament", "lot", "quantite", "prix_unitaire")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "actif")
    search_fields = ("nom", "telephone")


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ("numero", "date", "caissier", "mode_paiement", "total", "statut")
    list_filter = ("statut", "mode_paiement")
    inlines = [LigneVenteInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # RG10 : une vente validée ne se supprime pas