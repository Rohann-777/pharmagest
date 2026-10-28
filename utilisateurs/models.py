from django.contrib.auth.models import AbstractUser


class Utilisateur(AbstractUser):
    """Utilisateur de PharmaGest.

    Les rôles (caissier, pharmacien...) sont gérés par les groupes Django.
    """