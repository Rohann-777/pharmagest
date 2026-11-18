from django.urls import path

from . import views

urlpatterns = [
    path("commandes/<int:pk>/reception/", views.reception, name="reception"),
]