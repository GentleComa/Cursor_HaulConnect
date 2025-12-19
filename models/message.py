"""
Message Model

Defines the Message and Conversation models for internal messaging.
"""

from datetime import datetime

from extensions import db


# Association table for conversation participants
conversation_participants = db.Table(
    'conversation_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('conversation_id', db.Integer, db.ForeignKey('conversations.id'), primary_key=True)
)


class Conversation(db.Model):
    """Conversation model for message threads."""
    
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255))
    
    # Optional link to a load
    load_id = db.Column(db.Integer, db.ForeignKey('loads.id'), nullable=True)
    load = db.relationship('Load', backref='conversations')
    
    # Participants
    participants = db.relationship(
        'User',
        secondary=conversation_participants,
        backref=db.backref('conversations', lazy='dynamic')
    )
    
    # Messages
    messages = db.relationship('Message', backref='conversation', lazy='dynamic', order_by='Message.created_at')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Conversation {self.id}>'
    
    @property
    def last_message(self):
        """Get the most recent message."""
        return self.messages.order_by(Message.created_at.desc()).first()
    
    def add_participant(self, user):
        """Add a participant to the conversation."""
        if user not in self.participants:
            self.participants.append(user)
    
    def remove_participant(self, user):
        """Remove a participant from the conversation."""
        if user in self.participants:
            self.participants.remove(user)


class Message(db.Model):
    """Message model for individual messages."""
    
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationships
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender = db.relationship('User', backref='sent_messages')
    
    # Content
    content = db.Column(db.Text, nullable=False)
    
    # Read status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id}>'
    
    def mark_as_read(self):
        """Mark message as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

