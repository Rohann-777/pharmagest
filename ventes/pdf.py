from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from django.conf import settings
from django.utils.html import escape


def formater_ar(montant):
    return f"{montant:,.0f}".replace(",", " ") + " Ar"


def generer_recu(vente):
    """Retourne le reçu de vente au format PDF (octets)."""
    tampon = BytesIO()
    document = SimpleDocTemplate(
        tampon, pagesize=A5, title=f"Reçu {vente.numero}",
        leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    caissier = vente.caissier.get_full_name() or vente.caissier.get_username()

    elements = [
        Paragraph(escape(settings.PHARMACIE["nom"]), styles["Title"]),
        Paragraph(
            f"{escape(settings.PHARMACIE['adresse'])} - Tél. {escape(settings.PHARMACIE['telephone'])}",
            styles["Normal"],
        ),
        Paragraph(f"Reçu n° {vente.numero}", styles["Heading2"]),
        Paragraph(f"Date : {timezone.localtime(vente.date):%d/%m/%Y %H:%M}", styles["Normal"]),
        Paragraph(f"Caissier : {caissier}", styles["Normal"]),
        Paragraph(f"Paiement : {vente.get_mode_paiement_display()}", styles["Normal"]),
        Spacer(1, 6 * mm),
    ]

    donnees = [["Désignation", "Lot", "Qté", "P.U.", "Total"]]
    for ligne in vente.lignes.select_related("medicament", "lot"):
        donnees.append([
            str(ligne.medicament), ligne.lot.numero_lot, ligne.quantite,
            formater_ar(ligne.prix_unitaire), formater_ar(ligne.sous_total),
        ])
    donnees.append(["", "", "", "TOTAL", formater_ar(vente.total)])

    tableau = Table(donnees, repeatRows=1, colWidths=[44 * mm, 24 * mm, 10 * mm, 22 * mm, 24 * mm])
    tableau.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.grey),
    ]))
    elements += [tableau, Spacer(1, 8 * mm), Paragraph("Merci de votre visite.", styles["Normal"])]

    document.build(elements)
    return tampon.getvalue()