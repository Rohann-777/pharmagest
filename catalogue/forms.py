from django import forms
from django.core.exceptions import ValidationError

from .models import Medicament

TAILLE_MAX_PHOTO = 2 * 1024 * 1024  # 2 Mo
FORMATS_AUTORISES = {"JPEG", "PNG", "WEBP"}


class MedicamentForm(forms.ModelForm):
    class Meta:
        model = Medicament
        fields = [
            "nom_commercial", "denomination_generique", "categorie", "forme", "dosage",
            "laboratoire", "code_barres", "prix_achat", "prix_vente", "seuil_alerte", "photo",
        ]
        widgets = {
            "photo": forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }
        help_texts = {
            "photo": "JPEG, PNG ou WEBP, 2 Mo maximum. Laissez vide pour garder la photo actuelle.",
            "code_barres": "Facultatif, mais unique s'il est renseigné.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.widget.attrs.setdefault("class", "champ")

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        # L'attribut `image` n'existe que sur un fichier qui vient d'être envoyé et lu par Pillow.
        if photo and hasattr(photo, "image"):
            if photo.size > TAILLE_MAX_PHOTO:
                raise ValidationError("La photo dépasse 2 Mo. Choisissez une image plus légère.")
            if photo.image.format not in FORMATS_AUTORISES:
                raise ValidationError("Format non accepté. Utilisez une image JPEG, PNG ou WEBP.")
        return photo