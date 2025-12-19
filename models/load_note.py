"""
Load Note Model

Defines the LoadNote model for admin notes on shipments.
"""

from datetime import datetime

from extensions import db


class LoadNote(db.Model):
    """LoadNote model for admin notes on shipments."""
    
    __tablename__ = 'load_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    load_id = db.Column(db.Integer, db.ForeignKey('loads.id'), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    load = db.relationship('Load', backref='admin_notes')
    admin = db.relationship('User', backref='load_notes')
    
    def __repr__(self):
        return f'<LoadNote {self.id} for Load {self.load_id}>'
    
    def to_dict(self):
        """Convert note to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'load_id': self.load_id,
            'admin_id': self.admin_id,
            'admin_name': self.admin.full_name if self.admin else 'Unknown',
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

