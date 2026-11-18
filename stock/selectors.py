from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from catalogue.models import Medicament


def annoter_stock(medicaments):
    """Ajoute à chaque médicament son stock délivrable (lots valides, non bloqués)."""
    aujourdhui = timezone.localdate()
    return medicaments.annotate(
        stock=Coalesce(
            Sum(
                "lots__quantite_disponible",
                filter=Q(lots__bloque=False, lots__date_peremption__gte=aujourdhui),
            ),
            0,
        )
    )


def medicaments_avec_stock():
    """Médicaments actifs avec leur stock délivrable (utilisé par la caisse et le tableau de bord)."""
    return annoter_stock(Medicament.objects.filter(statut=Medicament.Statut.ACTIF))