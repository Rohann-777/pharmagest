from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from catalogue.models import Medicament
from stock.models import LotStock


class Client(models.Model):
    nom = models.CharField(max_length=150)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Vente(models.Model):
    class ModePaiement(models.TextChoices):
        ESPECES = "especes", "Espèces"
        MOBILE_MONEY = "mobile_money", "Mobile money"
        AUTRE = "autre", "Autre"

    class Statut(models.TextChoices):
        VALIDEE = "validee", "Validée"
        ANNULEE = "annulee", "Annulée"

    # Jeton généré à l'affichage de la caisse : empêche la double validation.
    jeton = models.UUIDField(unique=True, editable=False)
    client = models.ForeignKey(
        Client, null=True, blank=True, on_delete=models.PROTECT, related_name="ventes"
    )
    caissier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ventes"
    )
    mode_paiement = models.CharField(max_length=20, choices=ModePaiement.choices)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.VALIDEE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return self.numero

    @property
    def numero(self):
        return f"V-{self.pk:06d}"

    @property
    def total(self):
        return sum((ligne.sous_total for ligne in self.lignes.all()), Decimal("0"))


class LigneVente(models.Model):
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name="lignes")
    medicament = models.ForeignKey(
        Medicament, on_delete=models.PROTECT, related_name="lignes_vente"
    )
    lot = models.ForeignKey(LotStock, on_delete=models.PROTECT, related_name="lignes_vente")
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # RG12 : le prix est copié au moment de la vente.
    prix_unitaire = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )

    def __str__(self):
        return f"{self.medicament} x {self.quantite}"

    @property
    def sous_total(self):
        return self.quantite * self.prix_unitaire