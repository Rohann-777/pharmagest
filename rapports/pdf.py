from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from django.utils.html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from stock.models import LotStock
from stock.selectors import medicaments_avec_stock

STYLES = getSampleStyleSheet()
TEAL = colors.HexColor("#0B6B66")
TEAL_PALE = colors.HexColor("#DDEFED")
ROUGE = colors.HexColor("#B42318")
AMBRE = colors.HexColor("#9A5700")


def formater_ar(montant):
    return f"{montant:,.0f}".replace(",", " ") + " Ar"


def _pied_de_page(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(15 * mm, 10 * mm, f"{settings.PHARMACIE['nom']} - {document.title}")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def _construire(titre, informations, elements):
    """Assemble un document A4 : en-tête de la pharmacie, titre, informations, contenu, pied de page."""
    tampon = BytesIO()
    document = SimpleDocTemplate(
        tampon, pagesize=A4, title=titre,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=18 * mm,
    )
    pharmacie = settings.PHARMACIE
    entete = [
        Paragraph(escape(pharmacie["nom"]), STYLES["Heading3"]),
        Paragraph(f"{escape(pharmacie['adresse'])}<br/>Tél. {escape(pharmacie['telephone'])}", STYLES["Normal"]),
        Spacer(1, 6 * mm),
        Paragraph(escape(titre), STYLES["Title"]),
    ]
    entete += [Paragraph(ligne, STYLES["Normal"]) for ligne in informations]
    entete.append(Spacer(1, 6 * mm))
    document.build(entete + elements, onFirstPage=_pied_de_page, onLaterPages=_pied_de_page)
    return tampon.getvalue()


def _tableau(donnees, largeurs, droite_depuis, ligne_total=False, styles_lignes=()):
    """Tableau aux couleurs de l'application ; les colonnes à partir de `droite_depuis` sont alignées à droite."""
    tableau = Table(donnees, colWidths=largeurs, repeatRows=1)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7F6")]),
        ("ALIGN", (droite_depuis, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if ligne_total:
        style += [
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), TEAL_PALE),
            ("LINEABOVE", (0, -1), (-1, -1), 0.8, TEAL),
            # Le libellé du total occupe les colonnes de texte, pas celles des nombres.
            ("SPAN", (0, -1), (max(droite_depuis - 1, 0), -1)),
            ("ALIGN", (0, -1), (max(droite_depuis - 1, 0), -1), "LEFT"),
        ]
    tableau.setStyle(TableStyle(style + list(styles_lignes)))
    return tableau


def _genere_le(utilisateur):
    auteur = utilisateur.get_full_name() or utilisateur.get_username()
    return f"Généré le {timezone.localtime():%d/%m/%Y à %H:%M} par {escape(auteur)}"


def rapport_stock(utilisateur):
    """Stock délivrable de chaque médicament actif, valorisé au prix d'achat actuel."""
    medicaments = medicaments_avec_stock().select_related("categorie").order_by(
        "categorie__nom", "nom_commercial"
    )
    donnees = [["Médicament", "Catégorie", "État", "Seuil", "Stock", "Prix d'achat", "Valeur"]]
    styles_lignes, valeur_totale = [], Decimal("0")
    for numero, m in enumerate(medicaments, start=1):
        valeur = m.stock * m.prix_achat
        valeur_totale += valeur
        if m.stock == 0:
            etat, couleur = "Rupture", ROUGE
        elif m.stock <= m.seuil_alerte:
            etat, couleur = "Sous le seuil", AMBRE
        else:
            etat, couleur = "Normal", None
        if couleur:
            styles_lignes.append(("TEXTCOLOR", (2, numero), (2, numero), couleur))
        donnees.append([
            str(m), m.categorie.nom, etat, m.seuil_alerte, m.stock,
            formater_ar(m.prix_achat), formater_ar(valeur),
        ])
    donnees.append(["Valeur totale du stock délivrable", "", "", "", "", "", formater_ar(valeur_totale)])

    informations = [
        _genere_le(utilisateur),
        "Stock délivrable : lots non périmés et non bloqués. Valeur calculée au prix d'achat actuel, "
        "ce n'est ni un chiffre d'affaires ni un bénéfice.",
    ]
    largeurs = [48 * mm, 30 * mm, 22 * mm, 13 * mm, 13 * mm, 26 * mm, 28 * mm]
    return _construire(
        "Rapport de stock", informations,
        [_tableau(donnees, largeurs, droite_depuis=3, ligne_total=True, styles_lignes=styles_lignes)],
    )


def liste_peremptions(utilisateur, jours=30):
    """Lots encore en stock déjà périmés ou qui périment dans les `jours` prochains jours."""
    aujourdhui = timezone.localdate()
    lots = (
        LotStock.objects.filter(
            quantite_disponible__gt=0, date_peremption__lte=aujourdhui + timedelta(days=jours)
        )
        .select_related("medicament")
        .order_by("date_peremption")
    )
    donnees = [["Médicament", "Lot", "Péremption", "Échéance", "Bloqué", "Quantité"]]
    styles_lignes = []
    for numero, lot in enumerate(lots, start=1):
        restant = (lot.date_peremption - aujourdhui).days
        if restant < 0:
            echeance = "Périmé"
            styles_lignes.append(("TEXTCOLOR", (3, numero), (3, numero), ROUGE))
        else:
            echeance = f"dans {restant} j"
        donnees.append([
            str(lot.medicament), lot.numero_lot, f"{lot.date_peremption:%d/%m/%Y}",
            echeance, "Oui" if lot.bloque else "", lot.quantite_disponible,
        ])
    if len(donnees) == 1:
        donnees.append(["Aucun lot périmé ni proche de l'échéance.", "", "", "", "", ""])
        styles_lignes.append(("SPAN", (0, 1), (-1, 1)))

    informations = [
        _genere_le(utilisateur),
        f"Lots en stock périmés ou arrivant à échéance d'ici le "
        f"{aujourdhui + timedelta(days=jours):%d/%m/%Y}. Les lots périmés doivent être retirés de la vente.",
    ]
    largeurs = [55 * mm, 30 * mm, 25 * mm, 25 * mm, 18 * mm, 27 * mm]
    return _construire(
        "Produits périmés ou proches de la péremption", informations,
        [_tableau(donnees, largeurs, droite_depuis=5, styles_lignes=styles_lignes)],
    )


def bon_commande(commande, utilisateur):
    """Bon de commande adressé au fournisseur, avec les prix copiés sur les lignes (RG12)."""
    fournisseur = commande.fournisseur
    donnees = [["Désignation", "Quantité", "Prix unitaire", "Total"]]
    for ligne in commande.lignes.select_related("medicament"):
        donnees.append([
            str(ligne.medicament), ligne.quantite_commandee,
            formater_ar(ligne.prix_achat_unitaire), formater_ar(ligne.sous_total),
        ])
    donnees.append(["Total de la commande", "", "", formater_ar(commande.montant_total)])

    date = commande.date_commande or commande.date_creation
    informations = [
        f"<b>Numéro :</b> {commande.numero}",
        f"<b>Date :</b> {timezone.localtime(date):%d/%m/%Y}",
        f"<b>Statut :</b> {escape(commande.get_statut_display())}",
        f"<b>Fournisseur :</b> {escape(fournisseur.nom)}",
    ]
    if fournisseur.adresse:
        informations.append(escape(fournisseur.adresse))
    if fournisseur.telephone:
        informations.append(f"Tél. {escape(fournisseur.telephone)}")

    elements = [_tableau(donnees, [90 * mm, 22 * mm, 34 * mm, 34 * mm], droite_depuis=1, ligne_total=True)]
    if commande.statut == commande.Statut.BROUILLON:
        avertissement = STYLES["Normal"].clone("avertissement", textColor=ROUGE)
        elements = [Paragraph("Brouillon : ce document n'est pas une commande validée.", avertissement),
                    Spacer(1, 4 * mm)] + elements
    elements += [Spacer(1, 10 * mm), Paragraph(_genere_le(utilisateur), STYLES["Normal"])]
    return _construire(f"Bon de commande {commande.numero}", informations, elements)


def rapport_ventes(utilisateur, periode, stats):
    """Rapport des ventes validées d'une période : indicateurs, paiements, produits, détail par jour."""
    titre_section = STYLES["Heading4"]
    informations = [
        f"<b>Période :</b> du {periode.debut:%d/%m/%Y} au {periode.fin:%d/%m/%Y}",
        _genere_le(utilisateur),
        "Chiffre d'affaires des ventes validées, aux prix appliqués le jour de la vente. "
        "Les paiements étant encaissés à la vente, il correspond aux encaissements ; ce n'est pas un bénéfice.",
    ]

    indicateurs = _tableau(
        [
            ["Chiffre d'affaires", "Nombre de ventes", "Panier moyen", "Unités vendues"],
            [formater_ar(stats["ca"]), stats["nb_ventes"], formater_ar(stats["panier_moyen"]), stats["unites"]],
        ],
        [45 * mm] * 4, droite_depuis=0,
    )

    total = stats["ca"]
    paiements = [["Mode de paiement", "Chiffre d'affaires", "Part"]]
    for m in stats["par_mode"]:
        part = f"{m['ca'] / total * 100:.0f} %" if total else "0 %"
        paiements.append([m["nom"], formater_ar(m["ca"]), part])

    produits = [["Rang", "Médicament", "Unités", "Chiffre d'affaires"]]
    for rang, p in enumerate(stats["top_produits"], start=1):
        produits.append([rang, p["nom"], p["unites"], formater_ar(p["ca"])])

    jours = [["Date", "Ventes", "Chiffre d'affaires"]]
    for j in stats["jours"]:
        if j["nb"]:
            jours.append([f"{j['jour']:%d/%m/%Y}", j["nb"], formater_ar(j["ca"])])
    if stats["nb_ventes"]:
        jours.append(["Total de la période", stats["nb_ventes"], formater_ar(stats["ca"])])

    def section(titre, donnees, largeurs, droite_depuis, ligne_total=False):
        if len(donnees) == 1:
            return [Paragraph(titre, titre_section), Paragraph("Aucune vente sur la période.", STYLES["Normal"])]
        return [Paragraph(titre, titre_section),
                _tableau(donnees, largeurs, droite_depuis, ligne_total=ligne_total), Spacer(1, 4 * mm)]

    elements = [indicateurs, Spacer(1, 4 * mm)]
    elements += section("Répartition par mode de paiement", paiements, [80 * mm, 60 * mm, 40 * mm], 1)
    elements += section("Produits les plus vendus", produits, [15 * mm, 95 * mm, 25 * mm, 45 * mm], 2)
    elements += section("Ventes par jour", jours, [80 * mm, 40 * mm, 60 * mm], 1, ligne_total=True)
    return _construire("Rapport des ventes", informations, elements)
