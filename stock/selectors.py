from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from catalogue.models import Medicament


def medicaments_avec_stock():
    """Médicaments actifs, annotés de leur stock délivrable (lots valides, non bloqués)."""
    aujourdhui = timezone.localdate()
    return Medicament.objects.filter(statut=Medicament.Statut.ACTIF).annotate(
        stock=Coalesce(
            Sum(
                "lots__quantite_disponible",
                filter=Q(lots__bloque=False, lots__date_peremption__gte=aujourdhui),
            ),
            0,
        )
    )