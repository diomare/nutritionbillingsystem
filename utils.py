import os
import io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
import xml.etree.ElementTree as ET
import zipfile
import os
import json 

def carica_professionista(percorso="config/professionista.json"):
    with open(percorso, "r", encoding="utf-8") as f:
        return json.load(f)

def salva_professionista(dati, percorso="config/professionista.json"):
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=4)

def generate_invoice_number():
    prof = carica_professionista()
    numero = prof.get("numero_fattura_corrente", 0)
    prof["numero_fattura_corrente"] = numero + 1
    salva_professionista(prof)
    return numero


def generate_pdf_invoice(invoice):
    """Generate a PDF for the given invoice."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading2_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Add title
    elements.append(Paragraph(f"FATTURA n. {invoice.invoice_number}", title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Add date
    elements.append(Paragraph(f"Data: {invoice.invoice_date.strftime('%d/%m/%Y')}", normal_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Add client information
    if invoice.private_client_id:
        client = invoice.private_client
        elements.append(Paragraph("Cliente:", heading2_style))
        elements.append(Paragraph(f"Nome: {client.first_name} {client.last_name}", normal_style))
        elements.append(Paragraph(f"Codice Fiscale: {client.fiscal_code}", normal_style))
        if client.address:
            elements.append(Paragraph(f"Indirizzo: {client.address}, {client.postal_code} {client.city} ({client.province})", normal_style))
        if client.email:
            elements.append(Paragraph(f"Email: {client.email}", normal_style))
        if client.phone:
            elements.append(Paragraph(f"Telefono: {client.phone}", normal_style))
    else:
        client = invoice.business_client
        elements.append(Paragraph("Cliente:", heading2_style))
        elements.append(Paragraph(f"Azienda: {client.business_name}", normal_style))
        elements.append(Paragraph(f"Partita IVA: {client.vat_number}", normal_style))
        if client.fiscal_code:
            elements.append(Paragraph(f"Codice Fiscale: {client.fiscal_code}", normal_style))
        if client.address:
            elements.append(Paragraph(f"Indirizzo: {client.address}, {client.postal_code} {client.city} ({client.province})", normal_style))
        if client.email:
            elements.append(Paragraph(f"Email: {client.email}", normal_style))
        if client.phone:
            elements.append(Paragraph(f"Telefono: {client.phone}", normal_style))
    
    elements.append(Spacer(1, 1*cm))
    
    # Add invoice items
    elements.append(Paragraph("Dettaglio:", heading2_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Create table for invoice items
    data = [['Descrizione', 'Quantità', 'Prezzo Unitario', 'IVA %', 'Totale']]
    for item in invoice.items:
        data.append([
            item.description,
            str(item.quantity),
            f"€{item.unit_price:.2f}",
            f"{item.vat_rate}%",
            f"€{item.total_price:.2f}"
        ])
    
    # Add totals row
    data.append(['', '', '', 'Imponibile:', f"€{invoice.subtotal:.2f}"])
    
    if invoice.apply_stamp:
        data.append(['', '', '', 'Imposta di bollo:', f"€{invoice.stamp_duty:.2f}"])
    
    if invoice.apply_enpab:
        # Include note that ENPAB is calculated on subtotal + stamp
        enpab_label = f'Contributo ENPAB {invoice.enpab_rate}%'
        if invoice.apply_stamp:
            enpab_label += ' (su imponibile + bollo)'
        data.append(['', '', '', enpab_label + ':', f"€{invoice.enpab_amount:.2f}"])
        
        # Aggiungi nota esplicativa
        if invoice.apply_stamp:
            data.append(['', '', '', 'Nota: IVA calcolata solo sull\'ENPAB relativo all\'imponibile', ''])
    
    data.append(['', '', '', 'IVA:', f"€{invoice.total_vat:.2f}"])
    
    data.append(['', '', '', 'TOTALE:', f"€{invoice.total:.2f}"])
    
    # Create table
    table = Table(data, colWidths=[220, 60, 80, 60, 80])
    # Calculate the number of rows dedicated to the product items (excluding header and totals)
    item_rows = len(invoice.items)
    
    # Calculate row index where totals begin
    totals_start = item_rows + 1  # +1 for the header row
    
    table.setStyle(TableStyle([
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Items rows styling (all rows between header and totals)
        ('BACKGROUND', (0, 1), (-1, totals_start), colors.beige),
        ('GRID', (0, 0), (-1, totals_start), 1, colors.black),
        
        # General text styling
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Align right for numeric columns
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, totals_start), 'LEFT'),
        
        # Styling for the totals section
        ('LINEBELOW', (3, -1), (-1, -1), 2, colors.black),  # Double line under final total
        ('FONTNAME', (3, -1), (4, -1), 'Helvetica-Bold'),  # Bold for final total
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 1*cm))
    
    # Payment information
    if invoice.payment_method:
        elements.append(Paragraph(f"Metodo di pagamento: {invoice.payment_method}", normal_style))
    
    if invoice.payment_due_date:
        elements.append(Paragraph(f"Scadenza pagamento: {invoice.payment_due_date.strftime('%d/%m/%Y')}", normal_style))
    
    # Notes
    if invoice.notes:
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Note:", heading2_style))
        elements.append(Paragraph(invoice.notes, normal_style))
    
    # Footer
    elements.append(Spacer(1, 2*cm))
    footer_text = """
    Fattura emessa ai sensi dell'art. 21 del DPR 633/72 e successive modifiche.
    """
    
    if invoice.apply_enpab:
        footer_text += """
        Contributo previdenziale ENPAB applicato ai sensi della Legge 335/95.
        """
    
    if invoice.apply_stamp:
        footer_text += """
        Imposta di bollo assolta sull'originale ai sensi del D.M. 17 Giugno 2014.
        """
    
    if invoice.health_service_related:
        footer_text += """
        Prestazione sanitaria da comunicare al Sistema Tessera Sanitaria ai sensi del D.M. 31/07/2015.
        """
    
    elements.append(Paragraph(footer_text, normal_style))
    
def genera_xml_ts(fattura, output_path="fattura_ts.xml"):
    root = ET.Element("SpeseSanitarie")
    spesa = ET.SubElement(root, "Spesa")

    ET.SubElement(spesa, "Identificativo").text = str(fattura.get("id", ""))
    ET.SubElement(spesa, "CodiceFiscale").text = fattura.get("codice_fiscale", "")
    ET.SubElement(spesa, "DataSpesa").text = fattura.get("data", datetime.today().strftime("%Y-%m-%d"))
    ET.SubElement(spesa, "TipoSpesa").text = fattura.get("tipo_spesa", "SR")
    ET.SubElement(spesa, "Importo").text = str(fattura.get("importo", "0.00"))
    ET.SubElement(spesa, "TipoPagamento").text = fattura.get("tipo_pagamento", "MP")
    ET.SubElement(spesa, "FlagOpposizione").text = fattura.get("flag_opposizione", "N")

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path


def crea_zip_fatture(percorso_zip, lista_file):
    with zipfile.ZipFile(percorso_zip, 'w') as zipf:
        for file in lista_file:
            zipf.write(file, arcname=os.path.basename(file))
    return percorso_zip
    
    # Build the PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data
