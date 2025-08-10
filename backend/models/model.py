import datetime
import uuid
from . import db

class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    
    __table_args__ = (
        db.Index('idx_session_created_at', 'created_at'),
        db.Index('idx_session_model_id', 'model_id'),
    )
    
    # Session unique identifier (UUIDv4)
    id = db.Column(db.String(36), primary_key=True, nullable=False, default=lambda: str(uuid.uuid4()))
    # Session name provided by user
    name = db.Column(db.String(255), nullable=False)
    # Model ID used for this session
    model_id = db.Column(db.String(100), nullable=False)
    # Created at timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    # Updated at timestamp (updates when new messages are added)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationship to messages
    messages = db.relationship('ChatMessage', backref='session', cascade='all, delete-orphan', lazy=True)
    
    def to_dict(self):
        created_iso = self.created_at.isoformat(timespec='seconds') + 'Z' if self.created_at else None
        updated_iso = self.updated_at.isoformat(timespec='seconds') + 'Z' if self.updated_at else None
        return {
            'id': self.id,
            'name': self.name,
            'model_id': self.model_id,
            'created_at': created_iso,
            'updated_at': updated_iso,
            'message_count': len(self.messages) if self.messages else 0
        }
    
    def __repr__(self):
        return f'<ChatSession {self.id} {self.name} {self.model_id}>'

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    __table_args__ = (
        db.Index('idx_message_session_id', 'session_id'),
        db.Index('idx_message_created_at', 'created_at'),
        db.Index('idx_message_type', 'message_type'),
    )
    
    # Message unique identifier (UUIDv4)
    id = db.Column(db.String(36), primary_key=True, nullable=False, default=lambda: str(uuid.uuid4()))
    # Session ID this message belongs to
    session_id = db.Column(db.String(36), db.ForeignKey('chat_sessions.id'), nullable=False)
    # Message type: 'user' or 'assistant'
    message_type = db.Column(db.String(20), nullable=False)
    # Message content
    content = db.Column(db.Text, nullable=False)
    # Image paths used in this message (JSON string)
    images = db.Column(db.Text, nullable=True)  # JSON string of image paths
    # Number of images used
    images_used = db.Column(db.Integer, nullable=False, default=0)
    # User input for assistant messages (to track context)
    user_input = db.Column(db.Text, nullable=True)
    # Created at timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        created_iso = self.created_at.isoformat(timespec='seconds') + 'Z' if self.created_at else None
        return {
            'id': self.id,
            'session_id': self.session_id,
            'message_type': self.message_type,
            'content': self.content,
            'images': self.images,
            'images_used': self.images_used,
            'user_input': self.user_input,
            'created_at': created_iso
        }
    
    def __repr__(self):
        return f'<ChatMessage {self.id} {self.session_id} {self.message_type}>'
