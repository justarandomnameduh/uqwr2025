import datetime
import uuid
import hashlib
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
        # Composite index for efficient duplicate checking
        db.Index('idx_message_deduplication', 'session_id', 'message_type', 'content_hash', 'created_at'),
    )
    
    # Message unique identifier (UUIDv4)
    id = db.Column(db.String(36), primary_key=True, nullable=False, default=lambda: str(uuid.uuid4()))
    # Session ID this message belongs to
    session_id = db.Column(db.String(36), db.ForeignKey('chat_sessions.id'), nullable=False)
    # Message type: 'user' or 'assistant'
    message_type = db.Column(db.String(20), nullable=False)
    # Message content
    content = db.Column(db.Text, nullable=False)
    # Content hash for efficient duplicate detection (SHA256 of content + session_id + message_type)
    content_hash = db.Column(db.String(64), nullable=True, index=True)
    # Image paths used in this message (JSON string)
    images = db.Column(db.Text, nullable=True)  # JSON string of image paths
    # Number of images used
    images_used = db.Column(db.Integer, nullable=False, default=0)
    # User input for assistant messages (to track context)
    user_input = db.Column(db.Text, nullable=True)
    # Created at timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    def generate_content_hash(self):
        """Generate SHA256 hash of content + session_id + message_type for duplicate detection"""
        content_for_hash = f"{self.session_id}:{self.message_type}:{self.content}"
        return hashlib.sha256(content_for_hash.encode('utf-8')).hexdigest()
    
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
    
    @staticmethod
    def get_conversation_history(session_id: str, limit_pairs: int = 5, exclude_latest_user: bool = False):
        """
        Retrieve the latest conversation history for a session.
        Returns a list of message pairs (user, assistant) for context.
        
        Args:
            session_id: The session ID to get history for
            limit_pairs: Number of conversation pairs to retrieve (default: 5)
            exclude_latest_user: Whether to exclude the most recent user message (default: False)
            
        Returns:
            List of tuples (user_message, assistant_message) ordered from oldest to newest
        """
        # Get all messages for this session, ordered by creation time (newest first)
        query = ChatMessage.query.filter_by(session_id=session_id)\
                                 .order_by(ChatMessage.created_at.desc())
        
        # If we want to exclude the latest user message (e.g., when getting context for response generation)
        if exclude_latest_user:
            # Get all messages and skip the first one if it's a user message
            all_messages = query.all()
            if all_messages and all_messages[0].message_type == 'user':
                messages = all_messages[1:]  # Skip the latest user message
            else:
                messages = all_messages
        else:
            # Limit to avoid getting too many messages
            messages = query.limit(limit_pairs * 2 + 2).all()  # +2 for safety buffer
        
        # Reverse to get chronological order (oldest first)
        messages.reverse()
        
        # Group messages into conversation pairs
        conversation_pairs = []
        i = 0
        while i < len(messages) - 1:  # -1 because we need pairs
            current_msg = messages[i]
            next_msg = messages[i + 1] if i + 1 < len(messages) else None
            
            # Look for user-assistant pairs
            if (current_msg.message_type == 'user' and 
                next_msg and next_msg.message_type == 'assistant'):
                conversation_pairs.append((current_msg, next_msg))
                i += 2  # Skip both messages since we paired them
            else:
                i += 1  # Skip this message and try the next one
        
        # Return the most recent pairs up to the limit, but maintain chronological order
        return conversation_pairs[-limit_pairs:] if len(conversation_pairs) > limit_pairs else conversation_pairs