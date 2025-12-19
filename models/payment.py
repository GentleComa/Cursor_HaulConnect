"""
Payment Model

Defines the Payment model for load payments and transactions.
"""

from datetime import datetime
from enum import Enum

from extensions import db


class PaymentStatus(Enum):
    """Payment status enumeration."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'


class Payment(db.Model):
    """Payment model for load transactions."""
    
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(100), unique=True, index=True)
    
    # Foreign keys
    load_id = db.Column(db.Integer, db.ForeignKey('loads.id'), nullable=False, unique=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Note: driver relationship is defined via backref in User.payments_received
    
    # Amount details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    platform_fee = db.Column(db.Numeric(10, 2), default=0)
    driver_payout = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Status
    status = db.Column(db.String(20), default=PaymentStatus.PENDING.value, index=True)
    
    # Payment method info
    payment_method = db.Column(db.String(50))  # bank_transfer, quick_pay, factoring
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Notes
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Payment {self.transaction_id}>'
    
    @staticmethod
    def generate_transaction_id():
        """Generate a unique transaction ID."""
        import random
        import string
        prefix = 'TXN'
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        return f'{prefix}{suffix}'
    
    def mark_processing(self):
        """Mark payment as processing."""
        self.status = PaymentStatus.PROCESSING.value
        self.processed_at = datetime.utcnow()
    
    def mark_completed(self):
        """Mark payment as completed."""
        self.status = PaymentStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
    
    def mark_failed(self, reason=None):
        """Mark payment as failed."""
        self.status = PaymentStatus.FAILED.value
        if reason:
            self.notes = reason
    
    def refund(self, reason=None):
        """Refund the payment."""
        self.status = PaymentStatus.REFUNDED.value
        if reason:
            self.notes = f'Refund reason: {reason}'

