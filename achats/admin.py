from django.contrib import admin

from .models import CommandeAchat, Fournisseur, LigneAchat


class LigneAchatInline(admin.TabularInline):
    model = LigneAchat
    extra = 1


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "email", "actif")
    list_filter = ("actif",)
    search_fields = ("nom", "telephone")


@admin.register(CommandeAchat)
class CommandeAchatAdmin(admin.ModelAdmin):
    list_display = ("numero", "fournisseur", "statut", "montant_total", "date_creation")
    list_filter = ("statut", "fournisseur")
    exclude = ("cree_par",)
    inlines = [LigneAchatInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.cree_par = request.user  # RG09 : on garde l'auteur de l'opération
        super().save_model(request, obj, form, change)