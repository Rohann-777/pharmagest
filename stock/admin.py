from django.contrib import admin

from .models import LotStock, MouvementStock


@admin.register(LotStock)
class LotStockAdmin(admin.ModelAdmin):
    list_display = ("medicament", "numero_lot", "date_peremption", "quantite_disponible", "bloque")
    list_filter = ("bloque", "date_peremption")
    search_fields = ("numero_lot", "medicament__nom_commercial")


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ("date", "lot", "type_mouvement", "quantite", "auteur")
    list_filter = ("type_mouvement",)