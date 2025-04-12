import io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm


def generate_invoice_number():
    """Generate a unique invoice number based on the current date and time."""
    now = datetime.now()
    return f"FT{now.strftime('%Y%m%d%H%M%S')}"


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
    data.append(['', '', '', 'IVA:', f"€{invoice.total_vat:.2f}"])
    data.append(['', '', '', 'TOTALE:', f"€{invoice.total:.2f}"])
    
    # Create table
    table = Table(data, colWidths=[220, 60, 80, 60, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -4), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('LINEBELOW', (3, -3), (-1, -3), 1, colors.black),
        ('LINEBELOW', (3, -2), (-1, -2), 1, colors.black),
        ('LINEBELOW', (3, -1), (-1, -1), 2, colors.black),
        ('FONTNAME', (3, -1), (4, -1), 'Helvetica-Bold'),
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
    elements.append(Paragraph(footer_text, normal_style))
    
    # Build the PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data
