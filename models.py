from datetime import datetime
from app import db

class PrivateClient(db.Model):
    __tablename__ = 'private_clients'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    fiscal_code = db.Column(db.String(16), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(10), nullable=True)
    province = db.Column(db.String(2), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with invoices
    invoices = db.relationship('Invoice', backref='private_client', lazy=True, 
                               foreign_keys='Invoice.private_client_id')
    
    def __repr__(self):
        return f'<PrivateClient {self.first_name} {self.last_name}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class BusinessClient(db.Model):
    __tablename__ = 'business_clients'
    
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(200), nullable=False)
    vat_number = db.Column(db.String(20), nullable=False, unique=True)
    fiscal_code = db.Column(db.String(16), nullable=True)
    sdi_code = db.Column(db.String(7), nullable=True)  # Codice destinatario SDI
    pec = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(10), nullable=True)
    province = db.Column(db.String(2), nullable=True)
    contact_person = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with invoices
    invoices = db.relationship('Invoice', backref='business_client', lazy=True,
                               foreign_keys='Invoice.business_client_id')
    
    def __repr__(self):
        return f'<BusinessClient {self.business_name}>'


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    vat_rate = db.Column(db.Float, nullable=False, default=22.0)  # Default 22% VAT in Italy
    exemption_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<InvoiceItem {self.description}>'
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price


class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=False, unique=True)
    invoice_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    private_client_id = db.Column(db.Integer, db.ForeignKey('private_clients.id'), nullable=True)
    business_client_id = db.Column(db.Integer, db.ForeignKey('business_clients.id'), nullable=True)
    payment_method = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    payment_due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, sent, paid, cancelled
    sent_to_sdi = db.Column(db.Boolean, default=False)  # Sent to Sistema di Interscambio
    sent_to_sts = db.Column(db.Boolean, default=False)  # Sent to Sistema Tessera Sanitaria
    health_service_related = db.Column(db.Boolean, default=False)  # If related to health services
    apply_enpab = db.Column(db.Boolean, default=True)  # Apply ENPAB contribution (4%)
    apply_stamp = db.Column(db.Boolean, default=True)  # Apply revenue stamp (€2.00)
    stamp_amount = db.Column(db.Float, default=2.00)  # Revenue stamp amount, default €2.00
    enpab_rate = db.Column(db.Float, default=4.00)  # ENPAB rate, default 4%
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with invoice items
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'
    
    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items)
    
    @property
    def enpab_amount(self):
        if not self.apply_enpab:
            return 0
        stamp_amount = self.stamp_amount if self.apply_stamp else 0
        return (self.subtotal + stamp_amount) * (self.enpab_rate / 100)
    
    @property
    def taxable_amount(self):
        # Subtotal + ENPAB contribution
        return self.subtotal + self.enpab_amount
    
    @property
    def total_vat(self):
        # Calcola l'IVA sugli elementi della fattura e sul contributo ENPAB (22%)
        # Il bollo non è soggetto a IVA
        enpab_without_stamp = self.subtotal * (self.enpab_rate / 100) if self.apply_enpab else 0
        return sum(item.total_price * (item.vat_rate / 100) for item in self.items) + (enpab_without_stamp * 0.22)
    
    @property
    def stamp_duty(self):
        if not self.apply_stamp:
            return 0
        return self.stamp_amount
    
    @property
    def total(self):
        # Subtotal + ENPAB + VAT + Stamp
        return self.taxable_amount + self.total_vat + self.stamp_duty
    
    @property
    def client_name(self):
        if self.private_client_id:
            return self.private_client.full_name
        elif self.business_client_id:
            return self.business_client.business_name
        return "Unknown Client"
