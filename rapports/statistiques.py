import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from ventes.models import LigneVente, Vente

DUREE_MAX = 92  # jours : au-delà, une colonne par jour devient illisible
PRESETS = [("7", "7 jours"), ("30", "30 jours"), ("90", "90 jours"), ("mois", "Ce mois-ci")]

MONTANT = ExpressionWrapper(
    F("quantite") * F("prix_unitaire"), output_field=DecimalField(max_digits=14, decimal_places=2)
)


def formater_ar(montant):
    return f"{montant:,.0f}".replace(",", " ") + " Ar"


@dataclass
class Periode:
    debut: date
    fin: date
    cle: str
    erreur: str = ""

    @property
    def nb_jours(self):
        return (self.fin - self.debut).days + 1


def lire_periode(parametres):
    """Transforme les paramètres GET (?periode=30, ou ?periode=perso&du=...&au=...) en période."""
    aujourdhui = timezone.localdate()
    par_defaut = Periode(aujourdhui - timedelta(days=29), aujourdhui, "30")
    cle = parametres.get("periode", "30")

    if cle == "mois":
        return Periode(aujourdhui.replace(day=1), aujourdhui, cle)
    if cle in ("7", "30", "90"):
        return Periode(aujourdhui - timedelta(days=int(cle) - 1), aujourdhui, cle)
    if cle != "perso":
        return par_defaut

    try:
        debut = date.fromisoformat(parametres.get("du", ""))
        fin = date.fromisoformat(parametres.get("au", ""))
    except ValueError:
        par_defaut.erreur = "Dates invalides : indiquez une date de début et une date de fin."
        return par_defaut
    if debut > fin:
        par_defaut.erreur = "La date de début doit précéder la date de fin."
    elif (fin - debut).days + 1 > DUREE_MAX:
        par_defaut.erreur = f"La période choisie ne peut pas dépasser {DUREE_MAX} jours."
    else:
        return Periode(debut, fin, cle)
    return par_defaut


def statistiques_ventes(periode):
    """Indicateurs des ventes validées de la période, calculés à partir des lignes (prix figés)."""
    ventes = Vente.objects.filter(
        statut=Vente.Statut.VALIDEE, date__date__gte=periode.debut, date__date__lte=periode.fin
    )
    lignes = LigneVente.objects.filter(vente__in=ventes)
    totaux = lignes.aggregate(ca=Sum(MONTANT), unites=Sum("quantite"))
    ca = totaux["ca"] or Decimal("0")
    nb_ventes = ventes.count()

    # Une ligne par jour, y compris les jours sans vente (sinon le graphique serait trompeur).
    bruts = {
        ligne["jour"]: ligne
        for ligne in lignes.annotate(jour=TruncDate("vente__date"))
        .values("jour")
        .annotate(ca=Sum(MONTANT), nb=Count("vente", distinct=True))
        .order_by("jour")
    }
    jours = []
    for decalage in range(periode.nb_jours):
        jour = periode.debut + timedelta(days=decalage)
        brut = bruts.get(jour, {})
        jours.append({"jour": jour, "ca": brut.get("ca") or Decimal("0"), "nb": brut.get("nb", 0)})

    top_produits = [
        {
            "nom": f"{p['medicament__nom_commercial']} {p['medicament__dosage']}".strip(),
            "ca": p["ca"],
            "unites": p["unites"],
        }
        for p in lignes.values("medicament_id", "medicament__nom_commercial", "medicament__dosage")
        .annotate(ca=Sum(MONTANT), unites=Sum("quantite"))
        .order_by("-ca")[:10]
    ]
    par_mode = [
        {"nom": Vente.ModePaiement(m["vente__mode_paiement"]).label, "ca": m["ca"]}
        for m in lignes.values("vente__mode_paiement").annotate(ca=Sum(MONTANT)).order_by("-ca")
    ]

    return {
        "ca": ca,
        "nb_ventes": nb_ventes,
        "unites": totaux["unites"] or 0,
        "panier_moyen": ca / nb_ventes if nb_ventes else Decimal("0"),
        "jours": jours,
        "top_produits": top_produits,
        "par_mode": par_mode,
    }


# --- Préparation des graphiques -------------------------------------------------------
# Toutes les valeurs numériques sont converties en texte ici : le template n'affiche que des
# chaînes, ce qui évite qu'un nombre soit écrit « 12,5 » (format français) dans le SVG ou le CSS.


def barres_classees(elements):
    """Barres horizontales : la plus longue vaut 1, les autres sont proportionnelles."""
    maximum = max((e["ca"] for e in elements), default=0)
    total = sum((e["ca"] for e in elements), Decimal("0"))
    for e in elements:
        proportion = float(e["ca"]) / float(maximum) if maximum else 0
        e["proportion"] = f"{max(proportion, 0.01):.3f}"
        e["ca_texte"] = formater_ar(e["ca"])
        e["part"] = f"{float(e['ca']) / float(total) * 100:.0f} %" if total else "0 %"
    return elements


def _pas_arrondi(valeur):
    """Pas de graduation « rond » (1, 2, 2,5 ou 5 × une puissance de 10)."""
    exposant = 10 ** math.floor(math.log10(valeur))
    for multiple in (1, 2, 2.5, 5, 10):
        if valeur <= multiple * exposant:
            return multiple * exposant
    return 10 * exposant


def _etiquette_axe(valeur, compacte):
    if valeur == 0:
        return "0"
    if compacte:
        if valeur >= 1_000_000:
            return f"{valeur / 1_000_000:g} M"
        return f"{valeur / 1000:g} k"
    return f"{valeur:,.0f}".replace(",", " ")


def _chemin_colonne(x, y, largeur, hauteur, base):
    """Colonne aux coins supérieurs arrondis (4 px), base carrée."""
    r = min(4, hauteur, largeur / 2)
    return (
        f"M{x:.1f},{base:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
        f"H{x + largeur - r:.1f} Q{x + largeur:.1f},{y:.1f} {x + largeur:.1f},{y + r:.1f} V{base:.1f} Z"
    )


def graphique_par_jour(jours, largeur=720, hauteur_trace=200):
    """Géométrie SVG d'un histogramme : une colonne par jour, axe des montants arrondi."""
    haut, gauche, droite, bas = 10, 56, 8, 26
    base = haut + hauteur_trace
    largeur_trace = largeur - gauche - droite
    maximum = float(max((j["ca"] for j in jours), default=0))
    pas = _pas_arrondi(maximum / 4) if maximum else 1000
    plafond = pas * max(1, math.ceil(maximum / pas))
    compacte = plafond >= 10_000

    graduations = []
    valeur = 0
    while valeur <= plafond + 1e-9:
        y = base - valeur / plafond * hauteur_trace
        graduations.append({"y": f"{y:.1f}", "libelle": _etiquette_axe(valeur, compacte)})
        valeur += pas

    nb = len(jours)
    case = largeur_trace / nb
    epaisseur = min(24, case * 0.7)
    tous_les = math.ceil(nb / 8)
    colonnes = []
    for i, j in enumerate(jours):
        x_case = gauche + i * case
        hauteur = float(j["ca"]) / plafond * hauteur_trace
        x = x_case + (case - epaisseur) / 2
        colonnes.append({
            "jour": j["jour"],
            "ca_texte": formater_ar(j["ca"]),
            "nb": j["nb"],
            "case_x": f"{x_case:.1f}",
            "case_largeur": f"{case:.1f}",
            "chemin": _chemin_colonne(x, base - hauteur, epaisseur, hauteur, base) if hauteur > 0 else "",
            "etiquette": f"{j['jour']:%d/%m}" if i % tous_les == 0 else "",
            "etiquette_x": f"{x_case + case / 2:.1f}",
        })

    return {
        "largeur": largeur,
        "hauteur": base + bas,
        "haut": haut,
        "base": f"{base:.1f}",
        "gauche": gauche,
        "gauche_texte": gauche - 8,
        "droite": largeur - droite,
        "hauteur_trace": hauteur_trace,
        "etiquette_y": f"{base + 18:.1f}",
        "graduations": graduations,
        "colonnes": colonnes,
    }
