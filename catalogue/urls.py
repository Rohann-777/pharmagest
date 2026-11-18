from django.urls import path

from . import views

urlpatterns = [
    path("", views.MedicamentListe.as_view(), name="medicament_liste"),
    path("nouveau/", views.MedicamentCreation.as_view(), name="medicament_creation"),
    path("<int:pk>/modifier/", views.MedicamentModification.as_view(), name="medicament_modification"),
    path("<int:pk>/archivage/", views.MedicamentArchivage.as_view(), name="medicament_archivage"),
]