from django.urls import path

from . import views

urlpatterns = [
    path("", views.caisse, name="caisse"),
    path("ajouter/", views.ajouter, name="caisse_ajouter"),
    path("retirer/<int:medicament_id>/", views.retirer, name="caisse_retirer"),
    path("valider/", views.valider, name="caisse_valider"),
    path("recu/<int:pk>/pdf/", views.recu_pdf, name="recu_pdf"),
]