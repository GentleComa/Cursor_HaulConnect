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
    # For load-based messaging (new system)
    load_id = db.Column(db.Integer, db.ForeignKey('loads.id'), nullable=False, index=True)
    # For conversation-based messaging (legacy, kept for backward compatibility)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)
    
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for system messages
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    
    # Content
    content = db.Column(db.Text, nullable=True)  # Nullable to allow photo-only messages
    photo_url = db.Column(db.String(500))  # Path to uploaded image
    
    # Read status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Timestamps
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Keep for backward compatibility
    
    def __repr__(self):
        return f'<Message {self.id}>'
    
    def mark_as_read(self):
        """Mark message as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert message to dictionary for API responses."""
        # Handle system messages (sender_id is None)
        if self.sender_id is None:
            sender_name = 'System'
        elif self.sender:
            sender_name = self.sender.full_name
        else:
            sender_name = 'Unknown'
        
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'sender_name': sender_name,
            'is_system': self.sender_id is None,
            'content': self.content,
            'photo_url': self.photo_url,
            'is_read': self.is_read,
            'timestamp': self.timestamp.isoformat() if self.timestamp else self.created_at.isoformat()
        }

