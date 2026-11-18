from django.urls import path

from . import views

urlpatterns = [
    path("", views.tableau_de_bord, name="tableau_de_bord"),
    path("rapports/ventes/", views.rapport_ventes, name="rapport_ventes"),
    path("rapports/ventes.pdf", views.rapport_ventes_pdf, name="rapport_ventes_pdf"),
    path("rapports/stock.pdf", views.rapport_stock_pdf, name="rapport_stock_pdf"),
    path("rapports/peremptions.pdf", views.peremptions_pdf, name="peremptions_pdf"),
    path("rapports/commandes/<int:pk>/bon.pdf", views.bon_commande_pdf, name="bon_commande_pdf"),
]
