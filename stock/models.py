from django.conf import settings
from django.db import models
from django.utils import timezone

from catalogue.models import Medicament


class LotStock(models.Model):
    medicament = models.ForeignKey(
        Medicament, on_delete=models.PROTECT, related_name="lots"
    )
    numero_lot = models.CharField(max_length=50)
    date_peremption = models.DateField()
    quantite_recue = models.PositiveIntegerField()
    quantite_disponible = models.PositiveIntegerField()
    bloque = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "lot"
        ordering = ["date_peremption"]  # FEFO : le plus proche de la péremption d'abord
        constraints = [
            models.UniqueConstraint(
                fields=["medicament", "numero_lot"],
                name="lot_unique_par_medicament",
            )
        ]

    def __str__(self):
        return f"{self.medicament} - lot {self.numero_lot}"

    @property
    def est_perime(self):
        return self.date_peremption < timezone.localdate()

    @property
    def est_delivrable(self):
        """RG08 : un lot périmé, bloqué ou vide ne peut pas être vendu."""
        return not self.bloque and not self.est_perime and self.quantite_disponible > 0


class MouvementStock(models.Model):
    class Type(models.TextChoices):
        RECEPTION = "reception", "Réception d'achat"
        VENTE = "vente", "Vente"
        RETOUR = "retour", "Retour client"
        CORRECTION = "correction", "Correction d'inventaire"

    lot = models.ForeignKey(
        LotStock, on_delete=models.PROTECT, related_name="mouvements"
    )
    type_mouvement = models.CharField(max_length=20, choices=Type.choices)
    quantite = models.IntegerField(help_text="Positive pour une entrée, négative pour une sortie.")
    motif = models.CharField(max_length=255, blank=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="mouvements_stock",
    )
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "mouvement de stock"
        verbose_name_plural = "mouvements de stock"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_type_mouvement_display()} {self.quantite:+d} - {self.lot}"