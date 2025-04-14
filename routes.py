import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from sqlalchemy import or_
import io
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm
from flask import send_file, jsonify

# Importa le funzioni e gli oggetti necessari dai moduli
from app import app, db
from models import PrivateClient, BusinessClient, Invoice, InvoiceItem, Professionista
from utils import generate_invoice_number, generate_pdf_invoice, genera_xml_ts
# Nota: carica_professionista e salva_professionista da utils non sembrano usate qui
# perché i dati del professionista sono ora nel modello Professionista.
# Potrebbero essere rimosse se non usate altrove.

@app.route("/config/professionista", methods=["GET", "POST"])
def configura_professionista():
    prof = Professionista.query.first() # Prende il primo (e unico) professionista dal DB

    if request.method == "POST":
        if not prof:
            prof = Professionista() # Crea un nuovo oggetto se non esiste

        # Aggiorna i dati dal form
        prof.nome = request.form.get("nome")
        prof.cognome = request.form.get("cognome")
        prof.indirizzo = request.form.get("indirizzo")
        prof.codice_fiscale = request.form.get("codice_fiscale")
        # Assicurati che il nome del campo nel form corrisponda a 'partita_iva'
        prof.piva = request.form.get("partita_iva")
        prof.email = request.form.get("email")
        prof.telefono = request.form.get("telefono")
        # Aggiungi anche il numero fattura corrente se presente nel template
        try:
            # Assicurati che il campo esista e sia un numero valido
             num_fattura = request.form.get("numero_fattura_corrente")
             if num_fattura is not None:
                 prof.numero_fattura_corrente = int(num_fattura)
        except (ValueError, TypeError):
            # Gestisci il caso in cui il numero non sia valido
            flash("Numero fattura corrente non valido.", "warning")
            # Potresti voler mantenere il valore precedente o impostare un default

        # Aggiungi o aggiorna nel database
        if not prof.id: # Se è un nuovo oggetto (non ha ancora un ID)
             db.session.add(prof)
        db.session.commit()

        flash("Dati del professionista salvati con successo.", "success")
        # Redirect alla stessa pagina per mostrare i dati aggiornati
        return redirect(url_for("configura_professionista"))

    # Se è una richiesta GET, mostra il template con i dati attuali (o vuoti se non esiste)
    return render_template("configura_professionista.html", prof=prof)


@app.route('/')
@app.route('/home') # Aggiunto endpoint per coerenza con configura_professionista.html
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

# --- Private Client Routes ---
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
            app.logger.error(f"Errore aggiunta cliente privato: {str(e)}", exc_info=True)
            flash(f'Errore durante l\'aggiunta del cliente: Verificare che il Codice Fiscale non sia già presente.', 'danger')
            # Rirendere il template mantenendo i dati (opzionale)
            return render_template('clients/add.html', client_type='private', form_data=request.form)

    return render_template('clients/add.html', client_type='private')

@app.route('/clients/private/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_private_client(client_id):
    client = PrivateClient.query.get_or_404(client_id)

    if request.method == 'POST':
        try:
            client.first_name = request.form['first_name']
            client.last_name = request.form['last_name']
            client.fiscal_code = request.form['fiscal_code'] # Assicurati che non vada in conflitto se modificato
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
            return redirect(url_for('view_private_client', client_id=client.id)) # Redirect alla vista del cliente
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Errore modifica cliente privato {client_id}: {str(e)}", exc_info=True)
            flash(f'Errore durante l\'aggiornamento del cliente: Verificare che il Codice Fiscale non sia già in uso da un altro cliente.', 'danger')
            # Rirendere il template di modifica con i dati attuali e l'errore
            return render_template('clients/edit.html', client=client, client_type='private')

    return render_template('clients/edit.html', client=client, client_type='private')

@app.route('/clients/private/view/<int:client_id>')
def view_private_client(client_id):
    client = PrivateClient.query.get_or_404(client_id)
    invoices = Invoice.query.filter_by(private_client_id=client_id).order_by(Invoice.invoice_date.desc()).all()

    return render_template('clients/view.html', client=client, invoices=invoices, client_type='private')

@app.route('/clients/private/delete/<int:client_id>', methods=['POST'])
def delete_private_client(client_id):
    client = PrivateClient.query.get_or_404(client_id)

    # Verifica se ci sono fatture associate prima di eliminare
    if client.invoices:
         flash(f'Impossibile rimuovere il cliente "{client.full_name}" perché ha fatture associate. Elimina prima le fatture.', 'danger')
         return redirect(url_for('view_private_client', client_id=client_id))

    try:
        db.session.delete(client)
        db.session.commit()
        flash('Cliente rimosso con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Errore eliminazione cliente privato {client_id}: {str(e)}", exc_info=True)
        flash(f'Impossibile rimuovere il cliente: {str(e)}', 'danger')
        return redirect(url_for('view_private_client', client_id=client_id)) # Torna alla vista se c'è errore

    return redirect(url_for('private_clients'))

# --- Business Client Routes ---
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
            app.logger.error(f"Errore aggiunta cliente aziendale: {str(e)}", exc_info=True)
            flash(f'Errore durante l\'aggiunta del cliente: Verificare che la Partita IVA non sia già presente.', 'danger')
            return render_template('clients/add.html', client_type='business', form_data=request.form)

    return render_template('clients/add.html', client_type='business')

@app.route('/clients/business/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_business_client(client_id):
    client = BusinessClient.query.get_or_404(client_id)

    if request.method == 'POST':
        try:
            client.business_name = request.form['business_name']
            client.vat_number = request.form['vat_number'] # Assicurati che non vada in conflitto
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
            return redirect(url_for('view_business_client', client_id=client.id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Errore modifica cliente aziendale {client_id}: {str(e)}", exc_info=True)
            flash(f'Errore durante l\'aggiornamento del cliente: Verificare che la Partita IVA non sia già in uso.', 'danger')
            return render_template('clients/edit.html', client=client, client_type='business')

    return render_template('clients/edit.html', client=client, client_type='business')

@app.route('/clients/business/view/<int:client_id>')
def view_business_client(client_id):
    client = BusinessClient.query.get_or_404(client_id)
    invoices = Invoice.query.filter_by(business_client_id=client_id).order_by(Invoice.invoice_date.desc()).all()

    return render_template('clients/view.html', client=client, invoices=invoices, client_type='business')

@app.route('/clients/business/delete/<int:client_id>', methods=['POST'])
def delete_business_client(client_id):
    client = BusinessClient.query.get_or_404(client_id)

    # Verifica se ci sono fatture associate
    if client.invoices:
        flash(f'Impossibile rimuovere il cliente "{client.business_name}" perché ha fatture associate. Elimina prima le fatture.', 'danger')
        return redirect(url_for('view_business_client', client_id=client_id))

    try:
        db.session.delete(client)
        db.session.commit()
        flash('Cliente aziendale rimosso con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Errore eliminazione cliente aziendale {client_id}: {str(e)}", exc_info=True)
        flash(f'Impossibile rimuovere il cliente: {str(e)}', 'danger')
        return redirect(url_for('view_business_client', client_id=client_id)) # Torna alla vista se c'è errore

    return redirect(url_for('business_clients'))

# --- Invoice Routes ---
@app.route('/invoices')
def invoices():
    search_term = request.args.get('search', '')

    query = Invoice.query

    if search_term:
        # Cerca per numero fattura o nome cliente (sia privato che business)
        query = query.outerjoin(PrivateClient, Invoice.private_client_id == PrivateClient.id)\
                     .outerjoin(BusinessClient, Invoice.business_client_id == BusinessClient.id)\
                     .filter(
                         or_(
                             Invoice.invoice_number.ilike(f'%{search_term}%'),
                             PrivateClient.first_name.ilike(f'%{search_term}%'),
                             PrivateClient.last_name.ilike(f'%{search_term}%'),
                             BusinessClient.business_name.ilike(f'%{search_term}%'),
                             Invoice.notes.ilike(f'%{search_term}%') # Cerca anche nelle note
                         )
                     )

    invoices_list = query.order_by(Invoice.invoice_date.desc(), Invoice.invoice_number.desc()).all()

    return render_template('invoices/index.html', invoices=invoices_list, search_term=search_term)


# Funzione helper per ricaricare il contesto del template add_invoice
def _render_add_invoice_template_with_error(error_message, form_data=None):
    """Carica i dati necessari e renderizza il template add_invoice con un messaggio di errore."""
    private_clients = PrivateClient.query.order_by(PrivateClient.last_name).all()
    business_clients = BusinessClient.query.order_by(BusinessClient.business_name).all()
    # Ottieni il prossimo numero fattura senza incrementarlo subito
    professionista = Professionista.query.first()
    # Gestisci il caso in cui professionista sia None o non abbia numero_fattura_corrente
    next_invoice_num = 1
    if professionista and professionista.numero_fattura_corrente is not None:
         # Il *prossimo* numero è quello corrente + 1
         next_invoice_num = professionista.numero_fattura_corrente + 1

    flash(error_message, 'danger')
    return render_template('invoices/add.html',
                          private_clients=private_clients,
                          business_clients=business_clients,
                          new_invoice_number=next_invoice_num, # Mostra il prossimo numero previsto
                          today=datetime.now().strftime('%Y-%m-%d'),
                          professionista=professionista,
                          form_data=form_data or request.form # Mantiene i dati inseriti
                         )

@app.route('/invoices/add', methods=['GET', 'POST'])
def add_invoice():
    if request.method == 'POST':
        app.logger.info("Inizio elaborazione POST /invoices/add")
        app.logger.debug("Dati Form ricevuti: %s", request.form)

        # Recupera i dati di base della fattura
        try:
            invoice_date_str = request.form.get('invoice_date')
            if not invoice_date_str:
                return _render_add_invoice_template_with_error("Data fattura mancante.")
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()

            payment_due_date_str = request.form.get('payment_due_date')
            payment_due_date = datetime.strptime(payment_due_date_str, '%Y-%m-%d').date() if payment_due_date_str else None

            payment_method = request.form.get('payment_method')
            notes = request.form.get('notes')
            status = request.form.get('status', 'draft')
            health_service_related = request.form.get('health_service_related') == 'on'
            apply_enpab = request.form.get('apply_enpab') == 'on'
            apply_stamp = request.form.get('apply_stamp') == 'on'

            # Gestione tassi/importi con valori di default
            try:
                enpab_rate_str = request.form.get('enpab_rate', '4.0')
                enpab_rate = float(enpab_rate_str) if enpab_rate_str else 4.0
            except ValueError:
                enpab_rate = 4.0 # Default se il valore non è un numero valido
                flash("Tasso ENPAB non valido, impostato al default (4%).", "warning")

            try:
                stamp_amount_str = request.form.get('stamp_amount', '2.0')
                stamp_amount = float(stamp_amount_str) if stamp_amount_str else 2.0
            except ValueError:
                stamp_amount = 2.0 # Default se il valore non è un numero valido
                flash("Importo bollo non valido, impostato al default (€2.00).", "warning")

        except Exception as e:
             app.logger.error("Errore nel parsing dei dati base della fattura: %s", str(e), exc_info=True)
             return _render_add_invoice_template_with_error(f"Errore nei dati della fattura: {str(e)}")


        # --- Gestione Cliente ---
        client_type = request.form.get('client_type')
        private_client_id = None
        business_client_id = None

        app.logger.debug(f"Tipo Cliente Selezionato: {client_type}")

        if client_type == 'private':
            private_client_id_str = request.form.get('private_client_id')
            app.logger.debug(f"ID Cliente Privato (str): {private_client_id_str}")
            if private_client_id_str:
                try:
                    private_client_id = int(private_client_id_str)
                except ValueError:
                    app.logger.error("ID cliente privato non valido ricevuto: %s", private_client_id_str)
                    return _render_add_invoice_template_with_error("ID cliente privato non valido.")
            else:
                return _render_add_invoice_template_with_error("Devi selezionare un cliente privato.")

        elif client_type == 'business':
            business_client_id_str = request.form.get('business_client_id')
            app.logger.debug(f"ID Cliente Aziendale (str): {business_client_id_str}")
            if business_client_id_str:
                try:
                    business_client_id = int(business_client_id_str)
                except ValueError:
                    app.logger.error("ID cliente aziendale non valido ricevuto: %s", business_client_id_str)
                    return _render_add_invoice_template_with_error("ID cliente aziendale non valido.")
            else:
                return _render_add_invoice_template_with_error("Devi selezionare un cliente aziendale.")
        else:
             return _render_add_invoice_template_with_error("Tipo di cliente non specificato correttamente.")

        app.logger.debug(f"ID Cliente Privato: {private_client_id}, ID Cliente Aziendale: {business_client_id}")


        # --- Gestione Righe Fattura ---
        descriptions = request.form.getlist('item_description[]')
        quantities_str = request.form.getlist('item_quantity[]')
        unit_prices_str = request.form.getlist('item_unit_price[]')
        vat_rates_str = request.form.getlist('item_vat_rate[]')
        exemption_reasons = request.form.getlist('item_exemption_reason[]')

        invoice_items_data = [] # Lista temporanea per validare prima del DB
        if not descriptions or not any(descriptions):
             return _render_add_invoice_template_with_error("La fattura deve contenere almeno una riga con descrizione.")

        for i in range(len(descriptions)):
            desc = descriptions[i].strip()
            if not desc:
                # Salta righe vuote o continua se vuoi permettere righe senza descrizione (sconsigliato)
                # Qui decidiamo di ignorarle silenziosamente, ma potresti voler avvisare
                continue

            try:
                qty_str = quantities_str[i] if i < len(quantities_str) else '1'
                qty = int(qty_str) if qty_str else 1
                if qty <= 0: qty = 1 # Assicura quantità positiva

                price_str = unit_prices_str[i] if i < len(unit_prices_str) else '0.0'
                price = float(price_str) if price_str else 0.0

                vat_str = vat_rates_str[i] if i < len(vat_rates_str) else '22.0'
                vat = float(vat_str) if vat_str is not None and vat_str != '' else 22.0 # Default 22 se vuoto/mancante
                if vat < 0: vat = 0 # Assicura IVA non negativa

                exemption = exemption_reasons[i].strip() if i < len(exemption_reasons) and exemption_reasons[i] else None

                invoice_items_data.append({
                    'description': desc,
                    'quantity': qty,
                    'unit_price': price,
                    'vat_rate': vat,
                    'exemption_reason': exemption
                })
            except (ValueError, IndexError) as item_err:
                 app.logger.error(f"Errore nel parsing della riga {i+1} della fattura: {item_err}", exc_info=True)
                 return _render_add_invoice_template_with_error(f"Errore nei dati della riga {i+1}: controllare quantità, prezzo e IVA.")

        if not invoice_items_data:
             return _render_add_invoice_template_with_error("La fattura deve contenere almeno una riga valida.")


        # --- Creazione Fattura e Righe nel DB (dopo validazione) ---
        try:
            # Ottieni e incrementa il numero fattura DAL PROFESSIONISTA
            professionista = Professionista.query.first()
            if not professionista or professionista.numero_fattura_corrente is None:
                 # Gestione errore: Dati professionista mancanti
                 app.logger.error("Dati professionista o numero fattura corrente mancanti nel database.")
                 return _render_add_invoice_template_with_error("Errore: Configurare i dati del professionista e il numero fattura iniziale.")

            current_invoice_number = professionista.numero_fattura_corrente + 1
            professionista.numero_fattura_corrente = current_invoice_number # Aggiorna il numero per la prossima fattura

            # Crea l'oggetto Invoice
            new_invoice = Invoice(
                invoice_number=str(current_invoice_number), # Usa il numero incrementato
                invoice_date=invoice_date,
                private_client_id=private_client_id,
                business_client_id=business_client_id,
                payment_method=payment_method,
                notes=notes,
                payment_due_date=payment_due_date,
                status=status,
                health_service_related=health_service_related,
                apply_enpab=apply_enpab,
                apply_stamp=apply_stamp,
                enpab_rate=enpab_rate,
                stamp_amount=stamp_amount
            )

            db.session.add(new_invoice)
            db.session.flush() # Ottieni l'ID della fattura prima di aggiungere le righe

            app.logger.info(f"Fattura ID {new_invoice.id} creata (ancora non committata).")

            # Crea gli oggetti InvoiceItem
            for item_data in invoice_items_data:
                item = InvoiceItem(
                    invoice_id=new_invoice.id,
                    **item_data # Espande il dizionario negli argomenti del costruttore
                )
                db.session.add(item)

            # Committa tutte le modifiche (Fattura, Righe, Numero Fattura Professionista)
            db.session.commit()
            app.logger.info(f"Fattura {new_invoice.invoice_number} (ID: {new_invoice.id}) e righe salvate con successo.")

            flash(f'Fattura {new_invoice.invoice_number} creata con successo!', 'success')
            return redirect(url_for('view_invoice', invoice_id=new_invoice.id))

        except Exception as db_err:
            db.session.rollback() # Annulla tutte le modifiche in caso di errore
            app.logger.error(f"Errore durante il salvataggio nel database: {db_err}", exc_info=True)
            return _render_add_invoice_template_with_error(f"Errore interno durante il salvataggio: {str(db_err)}")

    # --- Metodo GET ---
    else:
        # Carica i dati necessari per popolare i menu a discesa nel form
        private_clients = PrivateClient.query.order_by(PrivateClient.last_name).all()
        business_clients = BusinessClient.query.order_by(BusinessClient.business_name).all()
        professionista = Professionista.query.first()

        # Calcola il prossimo numero fattura da mostrare nel form
        next_invoice_num = 1
        if professionista and professionista.numero_fattura_corrente is not None:
             next_invoice_num = professionista.numero_fattura_corrente + 1
        elif not professionista:
             flash("Attenzione: Dati professionista non configurati. Il numero fattura partirà da 1.", "warning")


        return render_template('invoices/add.html',
                              private_clients=private_clients,
                              business_clients=business_clients,
                              new_invoice_number=next_invoice_num, # Mostra il prossimo numero
                              today=datetime.now().strftime('%Y-%m-%d'),
                              professionista=professionista)


@app.route('/invoices/edit/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    private_clients = PrivateClient.query.order_by(PrivateClient.last_name).all()
    business_clients = BusinessClient.query.order_by(BusinessClient.business_name).all()

    if request.method == 'POST':
        app.logger.info(f"Inizio elaborazione POST /invoices/edit/{invoice_id}")
        app.logger.debug("Dati Form ricevuti: %s", request.form)

        # --- Validazione Dati Base Fattura ---
        try:
            invoice_date_str = request.form.get('invoice_date')
            if not invoice_date_str:
                flash("Data fattura mancante.", 'danger')
                # Ricarica template edit con dati attuali
                return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='private' if invoice.private_client_id else 'business')

            invoice.invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()

            payment_due_date_str = request.form.get('payment_due_date')
            invoice.payment_due_date = datetime.strptime(payment_due_date_str, '%Y-%m-%d').date() if payment_due_date_str else None

            invoice.payment_method = request.form.get('payment_method')
            invoice.notes = request.form.get('notes')
            invoice.status = request.form.get('status', 'draft')
            invoice.health_service_related = request.form.get('health_service_related') == 'on'
            invoice.apply_enpab = request.form.get('apply_enpab') == 'on'
            invoice.apply_stamp = request.form.get('apply_stamp') == 'on'

            try:
                enpab_rate_str = request.form.get('enpab_rate', '4.0')
                invoice.enpab_rate = float(enpab_rate_str) if enpab_rate_str else 4.0
            except ValueError:
                 invoice.enpab_rate = 4.0
                 flash("Tasso ENPAB non valido, mantenuto valore precedente o default.", "warning")

            try:
                stamp_amount_str = request.form.get('stamp_amount', '2.0')
                invoice.stamp_amount = float(stamp_amount_str) if stamp_amount_str else 2.0
            except ValueError:
                invoice.stamp_amount = 2.0
                flash("Importo bollo non valido, mantenuto valore precedente o default.", "warning")

        except Exception as e:
             app.logger.error(f"Errore nel parsing dei dati base modifica fattura {invoice_id}: {e}", exc_info=True)
             flash(f"Errore nei dati della fattura: {str(e)}", 'danger')
             return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='private' if invoice.private_client_id else 'business')

        # --- Gestione Cliente ---
        client_type = request.form.get('client_type')
        original_private_client_id = invoice.private_client_id
        original_business_client_id = invoice.business_client_id

        app.logger.debug(f"Modifica Fattura {invoice_id}: Tipo Cliente Selezionato: {client_type}")

        if client_type == 'private':
            private_client_id_str = request.form.get('private_client_id')
            app.logger.debug(f"ID Cliente Privato (str): {private_client_id_str}")
            if private_client_id_str:
                try:
                    invoice.private_client_id = int(private_client_id_str)
                    invoice.business_client_id = None # Assicura che l'altro sia None
                except ValueError:
                    flash("ID cliente privato non valido.", 'danger')
                    return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='private') # Mostra errore
            else:
                flash("Devi selezionare un cliente privato.", 'danger')
                return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='private') # Mostra errore

        elif client_type == 'business':
            business_client_id_str = request.form.get('business_client_id')
            app.logger.debug(f"ID Cliente Aziendale (str): {business_client_id_str}")
            if business_client_id_str:
                try:
                    invoice.business_client_id = int(business_client_id_str)
                    invoice.private_client_id = None # Assicura che l'altro sia None
                except ValueError:
                    flash("ID cliente aziendale non valido.", 'danger')
                    return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='business') # Mostra errore
            else:
                flash("Devi selezionare un cliente aziendale.", 'danger')
                return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='business') # Mostra errore
        else:
             flash("Tipo di cliente non specificato correttamente.", 'danger')
             return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='private' if original_private_client_id else 'business') # Mostra errore


        # --- Gestione Righe Fattura ---
        descriptions = request.form.getlist('item_description[]')
        quantities_str = request.form.getlist('item_quantity[]')
        unit_prices_str = request.form.getlist('item_unit_price[]')
        vat_rates_str = request.form.getlist('item_vat_rate[]')
        exemption_reasons = request.form.getlist('item_exemption_reason[]')

        new_invoice_items_data = []
        if not descriptions or not any(descriptions):
            flash("La fattura deve contenere almeno una riga con descrizione.", 'danger')
            return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='private' if invoice.private_client_id else 'business')


        for i in range(len(descriptions)):
            desc = descriptions[i].strip()
            if not desc:
                continue # Ignora righe vuote

            try:
                qty_str = quantities_str[i] if i < len(quantities_str) else '1'
                qty = int(qty_str) if qty_str else 1
                if qty <= 0: qty = 1

                price_str = unit_prices_str[i] if i < len(unit_prices_str) else '0.0'
                price = float(price_str) if price_str else 0.0

                vat_str = vat_rates_str[i] if i < len(vat_rates_str) else '22.0'
                vat = float(vat_str) if vat_str is not None and vat_str != '' else 22.0
                if vat < 0: vat = 0

                exemption = exemption_reasons[i].strip() if i < len(exemption_reasons) and exemption_reasons[i] else None

                new_invoice_items_data.append({
                    'description': desc,
                    'quantity': qty,
                    'unit_price': price,
                    'vat_rate': vat,
                    'exemption_reason': exemption
                })
            except (ValueError, IndexError) as item_err:
                 flash(f"Errore nei dati della riga {i+1}: controllare quantità, prezzo e IVA.", 'danger')
                 return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='private' if invoice.private_client_id else 'business')

        if not new_invoice_items_data:
             flash("La fattura deve contenere almeno una riga valida.", 'danger')
             return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type='private' if invoice.private_client_id else 'business')


        # --- Aggiornamento DB ---
        try:
            # 1. Rimuovi le vecchie righe
            # Usare delete-orphan nella relazione è più efficiente, ma questo approccio manuale funziona
            InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
            # Alternativa se cascade="all, delete-orphan" è impostato nella relazione Invoice.items:
            # invoice.items.clear() # Questo dovrebbe rimuovere gli item orfani al commit

            # 2. Aggiungi le nuove righe
            for item_data in new_invoice_items_data:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    **item_data
                )
                db.session.add(item)

            # 3. Committa le modifiche alla fattura e alle righe
            db.session.commit()
            app.logger.info(f"Fattura {invoice.invoice_number} (ID: {invoice.id}) aggiornata con successo.")

            flash('Fattura aggiornata con successo!', 'success')
            return redirect(url_for('view_invoice', invoice_id=invoice.id))

        except Exception as db_err:
            db.session.rollback()
            app.logger.error(f"Errore durante l'aggiornamento DB fattura {invoice_id}: {db_err}", exc_info=True)
            flash(f'Errore interno durante l\'aggiornamento: {str(db_err)}', 'danger')
            # Ricarica i dati originali della fattura per mostrare lo stato pre-errore
            invoice = Invoice.query.get_or_404(invoice_id)
            client_type_original = 'private' if invoice.private_client_id else 'business'
            return render_template('invoices/edit.html', invoice=invoice, private_clients=private_clients, business_clients=business_clients, client_type=client_type_original)

    # --- Metodo GET ---
    else:
        # Determina il tipo di cliente per preselezionare il radio button corretto
        client_type = 'private' if invoice.private_client_id else 'business'
        return render_template('invoices/edit.html',
                              invoice=invoice,
                              private_clients=private_clients,
                              business_clients=business_clients,
                              client_type=client_type)


@app.route('/invoices/view/<int:invoice_id>')
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    professionista = Professionista.query.first() # Recupera i dati del professionista
    # Potrebbe essere utile passare anche i dati del cliente direttamente se non già presenti in invoice
    return render_template('invoices/view.html', invoice=invoice, professionista=professionista)

@app.route('/invoices/delete/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)

    try:
        # Le righe dovrebbero essere eliminate automaticamente grazie a cascade="all, delete-orphan"
        invoice_number = invoice.invoice_number # Salva il numero per il messaggio flash
        db.session.delete(invoice)
        db.session.commit()
        flash(f'Fattura {invoice_number} rimossa con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Errore eliminazione fattura {invoice_id}: {str(e)}", exc_info=True)
        flash(f'Impossibile rimuovere la fattura: {str(e)}', 'danger')

    return redirect(url_for('invoices'))

@app.route('/invoices/pdf/<int:invoice_id>')
def generate_invoice_pdf(invoice_id): 
    invoice = Invoice.query.get_or_404(invoice_id)

    try:
        # Generate PDF using the utility function
        pdf_data = generate_pdf_invoice(invoice) # Assumendo che questa funzione esista in utils.py

        # Create response
        buffer = io.BytesIO(pdf_data)
        buffer.seek(0)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True, # Forza il download
            download_name=f'Fattura_{invoice.invoice_number}.pdf'
        )
    except Exception as e:
        app.logger.error(f"Errore generazione PDF per fattura {invoice_id}: {e}", exc_info=True)
        flash("Errore durante la generazione del PDF.", "danger")
        return redirect(url_for('view_invoice', invoice_id=invoice_id))


# --- Sistema Tessera Sanitaria (Simulazione) ---

# Simulazione database locale (o puoi collegarlo al tuo vero database)
# Rimosso FATTURE, useremo il DB reale
# FATTURE = { ... }

@app.route("/genera-ts/<int:invoice_id>")
def genera_ts(invoice_id):
    fattura_db = Invoice.query.get_or_404(invoice_id)

    # Verifica che sia una fattura sanitaria e per cliente privato
    if not fattura_db.health_service_related or not fattura_db.private_client_id:
        flash("Questa fattura non è idonea per l'invio al Sistema TS (non sanitaria o non per cliente privato).", "warning")
        return redirect(url_for('view_invoice', invoice_id=invoice_id))

    # Prepara i dati per la funzione XML (adatta i nomi dei campi se necessario)
    fattura_data_ts = {
        "id": fattura_db.id, # Potrebbe servire un identificativo univoco del documento
        "codice_fiscale": fattura_db.private_client.fiscal_code,
        "data": fattura_db.invoice_date.strftime("%Y-%m-%d"),
        "tipo_spesa": "SR", # O altro codice rilevante
        "importo": fattura_db.total, # Usa il totale calcolato dalla property
        "tipo_pagamento": "MP" if fattura_db.payment_method else "NC", # Mappa metodi di pagamento
        "flag_opposizione": "N" # Da gestire se si implementa l'opposizione
    }

    try:
        # Crea un percorso temporaneo o usa BytesIO se la funzione lo supporta
        # Qui usiamo un file temporaneo per semplicità
        output_filename = f"fattura_ts_{fattura_db.invoice_number}_{fattura_db.id}.xml"
        # Assicurati che la directory 'temp' esista o scegli un'altra locazione
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        output_path = os.path.join(temp_dir, output_filename)

        genera_xml_ts(fattura_data_ts, output_path) # Funzione da utils.py
        app.logger.info(f"File XML per TS generato: {output_path}")

        # Invia il file come allegato
        return send_file(output_path, as_attachment=True, download_name=output_filename)

    except Exception as e:
        app.logger.error(f"Errore generazione XML TS per fattura {invoice_id}: {e}", exc_info=True)
        flash("Errore durante la generazione del file XML per il Sistema TS.", "danger")
        return redirect(url_for('view_invoice', invoice_id=invoice_id))


@app.route('/invoices/send-to-sdi/<int:invoice_id>', methods=['POST'])
def send_to_sdi(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)

    # Verifica se è per cliente business (o PA se la implementerai)
    if not invoice.business_client_id:
         flash("Invio SDI possibile solo per fatture a clienti aziendali.", "warning")
         return redirect(url_for('view_invoice', invoice_id=invoice_id))

    if invoice.sent_to_sdi:
         flash("Fattura già contrassegnata come inviata al SDI.", "info")
         return redirect(url_for('view_invoice', invoice_id=invoice_id))

    try:
        # QUI: Logica di generazione XML FatturaPA e invio tramite WS SDI
        # Esempio: generate_and_send_xml_pa(invoice)
        # Per ora, simuliamo solo l'aggiornamento dello stato
        app.logger.info(f"Simulazione invio SDI per fattura {invoice_id}")
        # -------------------------------------------------------------

        invoice.sent_to_sdi = True
        db.session.commit()
        flash('Fattura contrassegnata come inviata al Sistema di Interscambio!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Errore (simulato) invio SDI per fattura {invoice_id}: {e}", exc_info=True)
        flash(f'Errore durante l\'invio (simulato) della fattura al SDI: {str(e)}', 'danger')

    return redirect(url_for('view_invoice', invoice_id=invoice_id))

@app.route('/invoices/send-to-sts/<int:invoice_id>', methods=['POST'])
def send_to_sts(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)

    if not invoice.health_service_related:
        flash('Solo le fatture relative a prestazioni sanitarie possono essere inviate al Sistema TS.', 'warning')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))

    if not invoice.private_client_id:
        flash('Invio Sistema TS possibile solo per fatture a clienti privati.', 'warning')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))

    if invoice.sent_to_sts:
         flash("Fattura già contrassegnata come inviata al Sistema TS.", "info")
         return redirect(url_for('view_invoice', invoice_id=invoice_id))

    try:
        # QUI: Logica di generazione XML TS (se non già fatto) e invio tramite WS STS
        # Esempio: generate_and_send_xml_ts(invoice)
        # Per ora, simuliamo solo l'aggiornamento dello stato
        app.logger.info(f"Simulazione invio STS per fattura {invoice_id}")
        # -------------------------------------------------------------

        invoice.sent_to_sts = True
        db.session.commit()
        flash('Fattura contrassegnata come inviata al Sistema Tessera Sanitaria!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Errore (simulato) invio STS per fattura {invoice_id}: {e}", exc_info=True)
        flash(f'Errore durante l\'invio (simulato) della fattura al Sistema TS: {str(e)}', 'danger')

    return redirect(url_for('view_invoice', invoice_id=invoice_id))

# --- Reports ---
@app.route('/reports')
def reports():
    return render_template('reports/index.html')


@app.route('/reports/generate', methods=['POST'])
def generate_report():
    report_type = request.form.get('report_type')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    format_type = request.form.get('format_type', 'pdf')

    # Validazione date
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        if not start_date or not end_date:
             raise ValueError("Date di inizio e fine sono obbligatorie.")
        if start_date > end_date:
             raise ValueError("La data di inizio non può essere successiva alla data di fine.")
    except ValueError as date_err:
        flash(f"Errore nelle date del report: {date_err}", "danger")
        return redirect(url_for('reports'))

    app.logger.info(f"Generazione report: Tipo={report_type}, Start={start_date}, End={end_date}, Formato={format_type}")

    if report_type == 'invoices':
        # Get invoices in date range
        invoices_report = Invoice.query.filter(
            Invoice.invoice_date.between(start_date, end_date)
        ).order_by(Invoice.invoice_date, Invoice.invoice_number).all()

        if not invoices_report:
            flash("Nessuna fattura trovata nel periodo selezionato.", "info")
            return redirect(url_for('reports'))

        if format_type == 'excel':
            try:
                data = []
                for invoice in invoices_report:
                    data.append({
                        'Numero Fattura': invoice.invoice_number,
                        'Data': invoice.invoice_date.strftime('%d/%m/%Y'),
                        'Cliente': invoice.client_name, # Usa la property
                        'Imponibile': invoice.subtotal,
                        'Bollo': invoice.stamp_duty,
                        'ENPAB': invoice.enpab_amount,
                        'IVA': invoice.total_vat,
                        'Totale': invoice.total,
                        'Stato': invoice.status.capitalize(),
                        'Tipo Cliente': 'Privato' if invoice.private_client_id else 'Aziendale',
                        'Inviata SDI': 'Sì' if invoice.sent_to_sdi else 'No',
                        'Inviata STS': 'Sì' if invoice.sent_to_sts else ('No' if invoice.health_service_related else 'N/A')
                    })

                df = pd.DataFrame(data)

                # Create Excel file in memory
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Fatture', index=False)
                    # Optional: Aggiusta larghezza colonne
                    worksheet = writer.sheets['Fatture']
                    for idx, col in enumerate(df):
                        series = df[col]
                        max_len = max((
                            series.astype(str).map(len).max(),
                            len(str(series.name))
                        )) + 1
                        worksheet.set_column(idx, idx, max_len)

                output.seek(0)
                app.logger.info("Report fatture Excel generato.")
                return send_file(
                    output,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=f'Report_Fatture_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx'
                )
            except Exception as excel_err:
                 app.logger.error(f"Errore generazione Excel fatture: {excel_err}", exc_info=True)
                 flash("Errore durante la generazione del report Excel.", "danger")
                 return redirect(url_for('reports'))

        else: # PDF Report
            try:
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=cm, bottomMargin=cm, leftMargin=cm, rightMargin=cm)
                elements = []
                styles = getSampleStyleSheet()

                elements.append(Paragraph(f"Report Fatture dal {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}", styles['Title']))
                elements.append(Spacer(1, 0.5*cm))

                # Create table data
                data_pdf = [['Num.', 'Data', 'Cliente', 'Totale', 'Stato']]
                for invoice in invoices_report:
                    data_pdf.append([
                        invoice.invoice_number,
                        invoice.invoice_date.strftime('%d/%m/%Y'),
                        Paragraph(invoice.client_name, styles['Normal']), # Usa Paragraph per wrap testo lungo
                        f"€{invoice.total:.2f}",
                        invoice.status.capitalize()
                    ])

                # Create table
                # Larghezze colonne da aggiustare
                table = Table(data_pdf, colWidths=[1.5*cm, 2*cm, 8.5*cm, 2.5*cm, 2.5*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    #('BACKGROUND', (0, 1), (-1, -1), colors.beige), # Sfondo alternato opzionale
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('ALIGN', (0, 1), (1, -1), 'LEFT'), # Allinea a sinistra Num e Data
                    ('ALIGN', (3, 1), (4, -1), 'RIGHT'), # Allinea a destra Totale e Stato
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ]))

                elements.append(table)
                elements.append(Spacer(1, 0.5*cm))

                # Add summary
                total_amount_period = sum(inv.total for inv in invoices_report)
                elements.append(Paragraph(f"<b>Totale fatturato nel periodo: €{total_amount_period:.2f}</b>", styles['Normal']))

                doc.build(elements)
                buffer.seek(0)
                app.logger.info("Report fatture PDF generato.")
                return send_file(
                    buffer,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f'Report_Fatture_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf'
                )
            except Exception as pdf_err:
                 app.logger.error(f"Errore generazione PDF fatture: {pdf_err}", exc_info=True)
                 flash("Errore durante la generazione del report PDF.", "danger")
                 return redirect(url_for('reports'))

    elif report_type == 'clients':
        # Report Clienti (con fatturato nel periodo)
        try:
             # Clienti Privati
             private_clients_data = []
             all_private_clients = PrivateClient.query.order_by(PrivateClient.last_name, PrivateClient.first_name).all()
             for client in all_private_clients:
                 invoices_period = Invoice.query.filter_by(private_client_id=client.id).filter(
                     Invoice.invoice_date.between(start_date, end_date)
                 ).all()
                 invoice_count = len(invoices_period)
                 total_amount = sum(inv.total for inv in invoices_period)
                 private_clients_data.append({
                     'Tipo': 'Privato',
                     'Nome': client.full_name,
                     'Codice Fiscale': client.fiscal_code,
                     'Email': client.email or '-',
                     'Telefono': client.phone or '-',
                     'N. Fatture Periodo': invoice_count,
                     'Totale Fatturato Periodo': total_amount
                 })

             # Clienti Aziendali
             business_clients_data = []
             all_business_clients = BusinessClient.query.order_by(BusinessClient.business_name).all()
             for client in all_business_clients:
                 invoices_period = Invoice.query.filter_by(business_client_id=client.id).filter(
                     Invoice.invoice_date.between(start_date, end_date)
                 ).all()
                 invoice_count = len(invoices_period)
                 total_amount = sum(inv.total for inv in invoices_period)
                 business_clients_data.append({
                     'Tipo': 'Azienda',
                     'Nome': client.business_name,
                     'Partita IVA': client.vat_number,
                     'Email': client.email or '-',
                     'Telefono': client.phone or '-',
                     'N. Fatture Periodo': invoice_count,
                     'Totale Fatturato Periodo': total_amount
                 })

             all_clients_data = private_clients_data + business_clients_data

             if not all_clients_data:
                 flash("Nessun cliente trovato o nessun cliente con fatture nel periodo.", "info")
                 return redirect(url_for('reports'))

             df_clients = pd.DataFrame(all_clients_data)

             if format_type == 'excel':
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_clients.to_excel(writer, sheet_name='Clienti', index=False)
                    # Optional: Aggiusta larghezza colonne
                    worksheet = writer.sheets['Clienti']
                    for idx, col in enumerate(df_clients):
                        series = df_clients[col]
                        max_len = max((
                            series.astype(str).map(len).max(),
                            len(str(series.name))
                        )) + 1
                        worksheet.set_column(idx, idx, max_len)

                output.seek(0)
                app.logger.info("Report clienti Excel generato.")
                return send_file(
                    output,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=f'Report_Clienti_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx'
                )
             else: # PDF Clienti
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=cm, bottomMargin=cm, leftMargin=cm, rightMargin=cm)
                elements = []
                styles = getSampleStyleSheet()

                elements.append(Paragraph(f"Report Clienti (Fatturato periodo {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})", styles['Title']))
                elements.append(Spacer(1, 0.5*cm))

                # Tabella Clienti Privati
                elements.append(Paragraph("Clienti Privati", styles['Heading2']))
                elements.append(Spacer(1, 0.2*cm))
                data_pdf_priv = [['Nome', 'C.F.', 'N. Fatt.', 'Tot. Fatt. (€)']]
                for client_data in private_clients_data:
                     data_pdf_priv.append([
                         Paragraph(client_data['Nome'], styles['Normal']),
                         client_data['Codice Fiscale'],
                         client_data['N. Fatture Periodo'],
                         f"{client_data['Totale Fatturato Periodo']:.2f}"
                     ])
                table_priv = Table(data_pdf_priv, colWidths=[7*cm, 3.5*cm, 2*cm, 3.5*cm])
                table_priv.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'), # Allinea CF, N. Fatt, Totale
                    ('ALIGN', (3, 1), (-1, -1), 'RIGHT'), # Allinea Totale a destra
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ]))
                elements.append(table_priv)
                elements.append(Spacer(1, 0.5*cm))

                 # Tabella Clienti Aziendali
                elements.append(Paragraph("Clienti Aziendali", styles['Heading2']))
                elements.append(Spacer(1, 0.2*cm))
                data_pdf_biz = [['Ragione Sociale', 'P.IVA', 'N. Fatt.', 'Tot. Fatt. (€)']]
                for client_data in business_clients_data:
                     data_pdf_biz.append([
                         Paragraph(client_data['Nome'], styles['Normal']),
                         client_data['Partita IVA'],
                         client_data['N. Fatture Periodo'],
                         f"{client_data['Totale Fatturato Periodo']:.2f}"
                     ])
                table_biz = Table(data_pdf_biz, colWidths=[7*cm, 3.5*cm, 2*cm, 3.5*cm]) # Stesse larghezze
                table_biz.setStyle(TableStyle([ # Stesso stile della tabella privati
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ]))
                elements.append(table_biz)

                doc.build(elements)
                buffer.seek(0)
                app.logger.info("Report clienti PDF generato.")
                return send_file(
                    buffer,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f'Report_Clienti_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf'
                )

        except Exception as client_rep_err:
             app.logger.error(f"Errore generazione report clienti: {client_rep_err}", exc_info=True)
             flash("Errore durante la generazione del report clienti.", "danger")
             return redirect(url_for('reports'))

    # Aggiungere qui altri tipi di report ('fiscal', etc.) se necessario

    else:
        flash(f'Tipo di report "{report_type}" non riconosciuto.', 'warning')
        return redirect(url_for('reports'))


# Se hai definito un endpoint 'home' da qualche parte (es. in index), assicurati che non vada in conflitto.
# L'endpoint per '/' è implicitamente 'index' se non specificato diversamente.
# Ho aggiunto un endpoint 'home' a '/' per coerenza con il link in configura_professionista.html
# @app.route("/", methods=["GET"], endpoint="home") # Rimosso perché è gestito da @app.route('/')
