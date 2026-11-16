from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from catalogue.models import Medicament


class Fournisseur(models.Model):
    nom = models.CharField("nom ou raison sociale", max_length=150)
    adresse = models.CharField(max_length=255, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField(blank=True)
    numero_fiscal = models.CharField(
        "numéro fiscal", max_length=50, blank=True, help_text="NIF ou STAT, si applicable."
    )
    contact_principal = models.CharField(max_length=150, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class CommandeAchat(models.Model):
    class Statut(models.TextChoices):
        BROUILLON = "brouillon", "Brouillon"
        COMMANDEE = "commandee", "Commandée"
        PARTIELLE = "partielle", "Partiellement réceptionnée"
        RECUE = "recue", "Entièrement réceptionnée"
        ANNULEE = "annulee", "Annulée"

    fournisseur = models.ForeignKey(
        Fournisseur, on_delete=models.PROTECT, related_name="commandes"
    )
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="commandes_creees"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_commande = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "commande d'achat"
        verbose_name_plural = "commandes d'achat"
        ordering = ["-date_creation"]

    def __str__(self):
        return self.numero

    @property
    def numero(self):
        return f"CA-{self.pk:06d}"

    @property
    def montant_total(self):
        return sum((ligne.sous_total for ligne in self.lignes.all()), Decimal("0"))


class LigneAchat(models.Model):
    commande = models.ForeignKey(
        CommandeAchat, on_delete=models.CASCADE, related_name="lignes"
    )
    medicament = models.ForeignKey(
        Medicament, on_delete=models.PROTECT, related_name="lignes_achat"
    )
    quantite_commandee = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prix_achat_unitaire = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = "ligne d'achat"
        constraints = [
            models.UniqueConstraint(
                fields=["commande", "medicament"],
                name="un_medicament_par_commande",
            )
        ]

    def __str__(self):
        return f"{self.medicament} x {self.quantite_commandee}"

    @property
    def sous_total(self):
        return self.quantite_commandee * self.prix_achat_unitaire