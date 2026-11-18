from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "connexion/",
        auth_views.LoginView.as_view(template_name="connexion.html"),
        name="login",
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("caisse/", include("ventes.urls")),
    path("achats/", include("achats.urls")),
    path("medicaments/", include("catalogue.urls")),
    path("", include("rapports.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)