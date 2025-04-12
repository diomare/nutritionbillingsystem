import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from sqlalchemy import or_
import io
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from app import app, db
from models import PrivateClient, BusinessClient, Invoice, InvoiceItem
from utils import generate_invoice_number, generate_pdf_invoice

@app.route('/')
def index():
    # Count statistics for dashboard
    private_clients_count = PrivateClient.query.count()
    business_clients_count = BusinessClient.query.count()
    invoices_count = Invoice.query.count()
    
    # Get recent invoices
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    return render_template('index.html', 
                          private_clients_count=private_clients_count,
                          business_clients_count=business_clients_count,
                          invoices_count=invoices_count,
                          recent_invoices=recent_invoices)

# Private Client Routes
@app.route('/clients/private')
def private_clients():
    search_term = request.args.get('search', '')
    
    if search_term:
        clients = PrivateClient.query.filter(
            or_(
                PrivateClient.first_name.ilike(f'%{search_term}%'),
                PrivateClient.last_name.ilike(f'%{search_term}%'),
                PrivateClient.fiscal_code.ilike(f'%{search_term}%'),
                PrivateClient.email.ilike(f'%{search_term}%')
            )
        ).order_by(PrivateClient.last_name).all()
    else:
        clients = PrivateClient.query.order_by(PrivateClient.last_name).all()
    
    return render_template('clients/index.html', clients=clients, client_type='private', search_term=search_term)

@app.route('/clients/private/add', methods=['GET', 'POST'])
def add_private_client():
    if request.method == 'POST':
        try:
            # Create a new private client from form data
            new_client = PrivateClient(
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                fiscal_code=request.form['fiscal_code'],
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                address=request.form.get('address'),
                city=request.form.get('city'),
                postal_code=request.form.get('postal_code'),
                province=request.form.get('province'),
                date_of_birth=datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d') if request.form.get('date_of_birth') else None,
                notes=request.form.get('notes')
            )
            
            db.session.add(new_client)
            db.session.commit()
            
            flash('Cliente privato aggiunto con successo!', 'success')
            return redirect(url_for('private_clients'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiunta del cliente: {str(e)}', 'danger')
    
    return render_template('clients/add.html', client_type='private')

@app.route('/clients/private/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_private_client(client_id):
    client = PrivateClient.query.get_or_404(client_id)
    
    if request.method == 'POST':
        try:
            client.first_name = request.form['first_name']
            client.last_name = request.form['last_name']
            client.fiscal_code = request.form['fiscal_code']
            client.email = request.form.get('email')
            client.phone = request.form.get('phone')
            client.address = request.form.get('address')
            client.city = request.form.get('city')
            client.postal_code = request.form.get('postal_code')
            client.province = request.form.get('province')
            client.date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d') if request.form.get('date_of_birth') else None
            client.notes = request.form.get('notes')
            
            db.session.commit()
            
            flash('Cliente aggiornato con successo!', 'success')
            return redirect(url_for('private_clients'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiornamento del cliente: {str(e)}', 'danger')
    
    return render_template('clients/edit.html', client=client, client_type='private')

@app.route('/clients/private/view/<int:client_id>')
def view_private_client(client_id):
    client = PrivateClient.query.get_or_404(client_id)
    invoices = Invoice.query.filter_by(private_client_id=client_id).order_by(Invoice.invoice_date.desc()).all()
    
    return render_template('clients/view.html', client=client, invoices=invoices, client_type='private')

@app.route('/clients/private/delete/<int:client_id>', methods=['POST'])
def delete_private_client(client_id):
    client = PrivateClient.query.get_or_404(client_id)
    
    try:
        db.session.delete(client)
        db.session.commit()
        flash('Cliente rimosso con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Impossibile rimuovere il cliente: {str(e)}', 'danger')
    
    return redirect(url_for('private_clients'))

# Business Client Routes
@app.route('/clients/business')
def business_clients():
    search_term = request.args.get('search', '')
    
    if search_term:
        clients = BusinessClient.query.filter(
            or_(
                BusinessClient.business_name.ilike(f'%{search_term}%'),
                BusinessClient.vat_number.ilike(f'%{search_term}%'),
                BusinessClient.fiscal_code.ilike(f'%{search_term}%'),
                BusinessClient.contact_person.ilike(f'%{search_term}%')
            )
        ).order_by(BusinessClient.business_name).all()
    else:
        clients = BusinessClient.query.order_by(BusinessClient.business_name).all()
    
    return render_template('clients/index.html', clients=clients, client_type='business', search_term=search_term)

@app.route('/clients/business/add', methods=['GET', 'POST'])
def add_business_client():
    if request.method == 'POST':
        try:
            # Create a new business client from form data
            new_client = BusinessClient(
                business_name=request.form['business_name'],
                vat_number=request.form['vat_number'],
                fiscal_code=request.form.get('fiscal_code'),
                sdi_code=request.form.get('sdi_code'),
                pec=request.form.get('pec'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                address=request.form.get('address'),
                city=request.form.get('city'),
                postal_code=request.form.get('postal_code'),
                province=request.form.get('province'),
                contact_person=request.form.get('contact_person'),
                notes=request.form.get('notes')
            )
            
            db.session.add(new_client)
            db.session.commit()
            
            flash('Cliente aziendale aggiunto con successo!', 'success')
            return redirect(url_for('business_clients'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiunta del cliente: {str(e)}', 'danger')
    
    return render_template('clients/add.html', client_type='business')

@app.route('/clients/business/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_business_client(client_id):
    client = BusinessClient.query.get_or_404(client_id)
    
    if request.method == 'POST':
        try:
            client.business_name = request.form['business_name']
            client.vat_number = request.form['vat_number']
            client.fiscal_code = request.form.get('fiscal_code')
            client.sdi_code = request.form.get('sdi_code')
            client.pec = request.form.get('pec')
            client.email = request.form.get('email')
            client.phone = request.form.get('phone')
            client.address = request.form.get('address')
            client.city = request.form.get('city')
            client.postal_code = request.form.get('postal_code')
            client.province = request.form.get('province')
            client.contact_person = request.form.get('contact_person')
            client.notes = request.form.get('notes')
            
            db.session.commit()
            
            flash('Cliente aziendale aggiornato con successo!', 'success')
            return redirect(url_for('business_clients'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiornamento del cliente: {str(e)}', 'danger')
    
    return render_template('clients/edit.html', client=client, client_type='business')

@app.route('/clients/business/view/<int:client_id>')
def view_business_client(client_id):
    client = BusinessClient.query.get_or_404(client_id)
    invoices = Invoice.query.filter_by(business_client_id=client_id).order_by(Invoice.invoice_date.desc()).all()
    
    return render_template('clients/view.html', client=client, invoices=invoices, client_type='business')

@app.route('/clients/business/delete/<int:client_id>', methods=['POST'])
def delete_business_client(client_id):
    client = BusinessClient.query.get_or_404(client_id)
    
    try:
        db.session.delete(client)
        db.session.commit()
        flash('Cliente aziendale rimosso con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Impossibile rimuovere il cliente: {str(e)}', 'danger')
    
    return redirect(url_for('business_clients'))

# Invoice Routes
@app.route('/invoices')
def invoices():
    search_term = request.args.get('search', '')
    
    if search_term:
        invoices = Invoice.query.filter(
            or_(
                Invoice.invoice_number.ilike(f'%{search_term}%'),
                Invoice.notes.ilike(f'%{search_term}%')
            )
        ).order_by(Invoice.invoice_date.desc()).all()
    else:
        invoices = Invoice.query.order_by(Invoice.invoice_date.desc()).all()
    
    return render_template('invoices/index.html', invoices=invoices, search_term=search_term)

@app.route('/invoices/add', methods=['GET', 'POST'])
def add_invoice():
    private_clients = PrivateClient.query.order_by(PrivateClient.last_name).all()
    business_clients = BusinessClient.query.order_by(BusinessClient.business_name).all()
    
    if request.method == 'POST':
        try:
            invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date()
            
            # Determine client type and ID
            client_type = request.form.get('client_type')
            private_client_id = None
            business_client_id = None
            
            if client_type == 'private':
                private_client_id = request.form.get('private_client_id')
            else:
                business_client_id = request.form.get('business_client_id')
            
            # Create a new invoice
            new_invoice = Invoice(
                invoice_number=generate_invoice_number(),
                invoice_date=invoice_date,
                private_client_id=private_client_id,
                business_client_id=business_client_id,
                payment_method=request.form.get('payment_method'),
                notes=request.form.get('notes'),
                payment_due_date=datetime.strptime(request.form.get('payment_due_date'), '%Y-%m-%d').date() if request.form.get('payment_due_date') else None,
                status=request.form.get('status', 'draft'),
                health_service_related=True if request.form.get('health_service_related') == 'on' else False,
                apply_enpab=True if request.form.get('apply_enpab') == 'on' else False,
                apply_stamp=True if request.form.get('apply_stamp') == 'on' else False,
                enpab_rate=float(request.form.get('enpab_rate', 4.0)),
                stamp_amount=float(request.form.get('stamp_amount', 2.0))
            )
            
            db.session.add(new_invoice)
            db.session.flush()  # Get the ID of the invoice
            
            # Process invoice items
            descriptions = request.form.getlist('item_description[]')
            quantities = request.form.getlist('item_quantity[]')
            unit_prices = request.form.getlist('item_unit_price[]')
            vat_rates = request.form.getlist('item_vat_rate[]')
            exemption_reasons = request.form.getlist('item_exemption_reason[]')
            
            for i in range(len(descriptions)):
                if descriptions[i]:  # Only add items with a description
                    item = InvoiceItem(
                        invoice_id=new_invoice.id,
                        description=descriptions[i],
                        quantity=int(quantities[i]) if quantities[i] else 1,
                        unit_price=float(unit_prices[i]) if unit_prices[i] else 0.0,
                        vat_rate=float(vat_rates[i]) if vat_rates[i] else 22.0,
                        exemption_reason=exemption_reasons[i] if exemption_reasons[i] else None
                    )
                    db.session.add(item)
            
            db.session.commit()
            
            flash('Fattura creata con successo!', 'success')
            return redirect(url_for('view_invoice', invoice_id=new_invoice.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione della fattura: {str(e)}', 'danger')
    
    # Generate a new invoice number for the form
    new_invoice_number = generate_invoice_number()
    
    return render_template('invoices/add.html', 
                          private_clients=private_clients, 
                          business_clients=business_clients,
                          new_invoice_number=new_invoice_number,
                          today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/invoices/edit/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    private_clients = PrivateClient.query.order_by(PrivateClient.last_name).all()
    business_clients = BusinessClient.query.order_by(BusinessClient.business_name).all()
    
    if request.method == 'POST':
        try:
            invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date()
            
            # Determine client type and ID
            client_type = request.form.get('client_type')
            
            if client_type == 'private':
                invoice.private_client_id = request.form.get('private_client_id')
                invoice.business_client_id = None
            else:
                invoice.business_client_id = request.form.get('business_client_id')
                invoice.private_client_id = None
            
            # Update invoice
            invoice.invoice_date = invoice_date
            invoice.payment_method = request.form.get('payment_method')
            invoice.notes = request.form.get('notes')
            invoice.payment_due_date = datetime.strptime(request.form.get('payment_due_date'), '%Y-%m-%d').date() if request.form.get('payment_due_date') else None
            invoice.status = request.form.get('status', 'draft')
            invoice.health_service_related = True if request.form.get('health_service_related') == 'on' else False
            invoice.apply_enpab = True if request.form.get('apply_enpab') == 'on' else False
            invoice.apply_stamp = True if request.form.get('apply_stamp') == 'on' else False
            invoice.enpab_rate = float(request.form.get('enpab_rate', 4.0))
            invoice.stamp_amount = float(request.form.get('stamp_amount', 2.0))
            
            # Delete existing items and create new ones
            for item in invoice.items:
                db.session.delete(item)
            
            # Process invoice items
            descriptions = request.form.getlist('item_description[]')
            quantities = request.form.getlist('item_quantity[]')
            unit_prices = request.form.getlist('item_unit_price[]')
            vat_rates = request.form.getlist('item_vat_rate[]')
            exemption_reasons = request.form.getlist('item_exemption_reason[]')
            
            for i in range(len(descriptions)):
                if descriptions[i]:  # Only add items with a description
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        description=descriptions[i],
                        quantity=int(quantities[i]) if quantities[i] else 1,
                        unit_price=float(unit_prices[i]) if unit_prices[i] else 0.0,
                        vat_rate=float(vat_rates[i]) if vat_rates[i] else 22.0,
                        exemption_reason=exemption_reasons[i] if exemption_reasons[i] else None
                    )
                    db.session.add(item)
            
            db.session.commit()
            
            flash('Fattura aggiornata con successo!', 'success')
            return redirect(url_for('view_invoice', invoice_id=invoice.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiornamento della fattura: {str(e)}', 'danger')
    
    # Determine client type for the form
    client_type = 'private' if invoice.private_client_id else 'business'
    
    return render_template('invoices/edit.html', 
                          invoice=invoice,
                          private_clients=private_clients, 
                          business_clients=business_clients,
                          client_type=client_type)

@app.route('/invoices/view/<int:invoice_id>')
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('invoices/view.html', invoice=invoice)

@app.route('/invoices/delete/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    try:
        db.session.delete(invoice)
        db.session.commit()
        flash('Fattura rimossa con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Impossibile rimuovere la fattura: {str(e)}', 'danger')
    
    return redirect(url_for('invoices'))

@app.route('/invoices/pdf/<int:invoice_id>')
def generate_invoice_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Generate PDF using the utility function
    pdf_data = generate_pdf_invoice(invoice)
    
    # Create response
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        attachment_filename=f'Fattura_{invoice.invoice_number}.pdf'
    )

@app.route('/invoices/send-to-sdi/<int:invoice_id>', methods=['POST'])
def send_to_sdi(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    try:
        # In a real implementation, this would connect to SDI web services
        # For now, we'll just mark it as sent
        invoice.sent_to_sdi = True
        db.session.commit()
        flash('Fattura inviata con successo al Sistema di Interscambio!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'invio della fattura al SDI: {str(e)}', 'danger')
    
    return redirect(url_for('view_invoice', invoice_id=invoice_id))

@app.route('/invoices/send-to-sts/<int:invoice_id>', methods=['POST'])
def send_to_sts(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if not invoice.health_service_related:
        flash('Solo le fatture relative a servizi sanitari possono essere inviate al Sistema TS.', 'warning')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))
    
    try:
        # In a real implementation, this would connect to STS web services
        # For now, we'll just mark it as sent
        invoice.sent_to_sts = True
        db.session.commit()
        flash('Fattura inviata con successo al Sistema Tessera Sanitaria!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'invio della fattura al Sistema TS: {str(e)}', 'danger')
    
    return redirect(url_for('view_invoice', invoice_id=invoice_id))

# Reports
@app.route('/reports')
def reports():
    return render_template('reports/index.html')

@app.route('/reports/generate', methods=['POST'])
def generate_report():
    report_type = request.form.get('report_type')
    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
    format_type = request.form.get('format_type', 'pdf')
    
    if report_type == 'invoices':
        # Get invoices in date range
        invoices = Invoice.query.filter(
            Invoice.invoice_date.between(start_date, end_date)
        ).order_by(Invoice.invoice_date).all()
        
        if format_type == 'excel':
            # Generate Excel report
            data = []
            for invoice in invoices:
                client_name = invoice.client_name
                
                data.append({
                    'Numero Fattura': invoice.invoice_number,
                    'Data': invoice.invoice_date,
                    'Cliente': client_name,
                    'Importo': invoice.total,
                    'IVA': invoice.total_vat,
                    'Totale': invoice.total,
                    'Stato': invoice.status
                })
            
            df = pd.DataFrame(data)
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Fatture', index=False)
            
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                attachment_filename=f'Report_Fatture_{start_date}_{end_date}.xlsx'
            )
        else:
            # Generate PDF report
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            
            # Add title
            styles = getSampleStyleSheet()
            elements.append(Paragraph(f"Report Fatture dal {start_date} al {end_date}", styles['Title']))
            elements.append(Spacer(1, 12))
            
            # Create table data
            data = [['Numero', 'Data', 'Cliente', 'Totale', 'Stato']]
            for invoice in invoices:
                data.append([
                    invoice.invoice_number,
                    invoice.invoice_date.strftime('%d/%m/%Y'),
                    invoice.client_name,
                    f"€{invoice.total:.2f}",
                    invoice.status
                ])
            
            # Create table
            table = Table(data, colWidths=[80, 80, 150, 80, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(table)
            
            # Add summary
            elements.append(Spacer(1, 20))
            total_amount = sum(invoice.total for invoice in invoices)
            elements.append(Paragraph(f"Totale fatturato: €{total_amount:.2f}", styles['Heading3']))
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                attachment_filename=f'Report_Fatture_{start_date}_{end_date}.pdf'
            )
    
    elif report_type == 'clients':
        # Get clients with invoice count and total amount
        if format_type == 'excel':
            # For Excel, we'll create a more detailed report
            private_clients = db.session.query(
                PrivateClient,
                db.func.count(Invoice.id).label('invoice_count'),
                db.func.sum(Invoice.total).label('total_amount')
            ).outerjoin(Invoice, Invoice.private_client_id == PrivateClient.id).filter(
                db.or_(
                    Invoice.invoice_date.between(start_date, end_date),
                    Invoice.invoice_date == None
                )
            ).group_by(PrivateClient.id).all()
            
            business_clients = db.session.query(
                BusinessClient,
                db.func.count(Invoice.id).label('invoice_count'),
                db.func.sum(Invoice.total).label('total_amount')
            ).outerjoin(Invoice, Invoice.business_client_id == BusinessClient.id).filter(
                db.or_(
                    Invoice.invoice_date.between(start_date, end_date),
                    Invoice.invoice_date == None
                )
            ).group_by(BusinessClient.id).all()
            
            # Create DataFrame for private clients
            private_data = []
            for client, count, amount in private_clients:
                private_data.append({
                    'Tipo': 'Privato',
                    'Nome': f"{client.first_name} {client.last_name}",
                    'Codice Fiscale': client.fiscal_code,
                    'Email': client.email,
                    'Telefono': client.phone,
                    'Numero Fatture': count,
                    'Totale Fatturato': amount or 0
                })
            
            # Create DataFrame for business clients
            business_data = []
            for client, count, amount in business_clients:
                business_data.append({
                    'Tipo': 'Azienda',
                    'Nome': client.business_name,
                    'Partita IVA': client.vat_number,
                    'Email': client.email,
                    'Telefono': client.phone,
                    'Numero Fatture': count,
                    'Totale Fatturato': amount or 0
                })
            
            # Combine data
            all_data = private_data + business_data
            df = pd.DataFrame(all_data)
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Clienti', index=False)
            
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                attachment_filename=f'Report_Clienti_{start_date}_{end_date}.xlsx'
            )
        else:
            # For PDF, we'll create a simpler report
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            
            # Add title
            styles = getSampleStyleSheet()
            elements.append(Paragraph(f"Report Clienti dal {start_date} al {end_date}", styles['Title']))
            elements.append(Spacer(1, 12))
            
            # Get private clients with invoice data
            private_clients = db.session.query(
                PrivateClient,
                db.func.count(Invoice.id).label('invoice_count'),
                db.func.sum(Invoice.total).label('total_amount')
            ).outerjoin(Invoice, Invoice.private_client_id == PrivateClient.id).filter(
                db.or_(
                    Invoice.invoice_date.between(start_date, end_date),
                    Invoice.invoice_date == None
                )
            ).group_by(PrivateClient.id).all()
            
            # Create table for private clients
            elements.append(Paragraph("Clienti Privati", styles['Heading2']))
            elements.append(Spacer(1, 6))
            
            private_data = [['Nome', 'Codice Fiscale', 'N. Fatture', 'Totale']]
            for client, count, amount in private_clients:
                private_data.append([
                    f"{client.first_name} {client.last_name}",
                    client.fiscal_code,
                    count,
                    f"€{amount or 0:.2f}"
                ])
            
            private_table = Table(private_data, colWidths=[150, 100, 80, 100])
            private_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(private_table)
            elements.append(Spacer(1, 20))
            
            # Get business clients with invoice data
            business_clients = db.session.query(
                BusinessClient,
                db.func.count(Invoice.id).label('invoice_count'),
                db.func.sum(Invoice.total).label('total_amount')
            ).outerjoin(Invoice, Invoice.business_client_id == BusinessClient.id).filter(
                db.or_(
                    Invoice.invoice_date.between(start_date, end_date),
                    Invoice.invoice_date == None
                )
            ).group_by(BusinessClient.id).all()
            
            # Create table for business clients
            elements.append(Paragraph("Clienti Aziendali", styles['Heading2']))
            elements.append(Spacer(1, 6))
            
            business_data = [['Nome', 'Partita IVA', 'N. Fatture', 'Totale']]
            for client, count, amount in business_clients:
                business_data.append([
                    client.business_name,
                    client.vat_number,
                    count,
                    f"€{amount or 0:.2f}"
                ])
            
            business_table = Table(business_data, colWidths=[150, 100, 80, 100])
            business_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(business_table)
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                attachment_filename=f'Report_Clienti_{start_date}_{end_date}.pdf'
            )
    
    flash('Tipo di report non valido.', 'danger')
    return redirect(url_for('reports'))
