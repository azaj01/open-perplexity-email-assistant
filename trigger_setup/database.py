"""
PostgreSQL database layer for conversation persistence.
Stores conversation history per (user_id, thread_id) to survive Railway restarts.
"""
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

Base = declarative_base()


class Conversation(Base):
    """
    Stores email conversation threads with message history.

    Key fields:
    - user_id: Email address of the person sending emails (e.g., "alice@example.com")
    - thread_id: Gmail thread ID for grouping related emails
    - message_history: JSON array of LangChain messages
    - pending_action: Tracks state like "awaiting_gmail_connection"
    """
    __tablename__ = "conversations"

    user_id = Column(String, primary_key=True)
    thread_id = Column(String, primary_key=True)
    sender_email = Column(String, nullable=False)
    message_history = Column(Text, nullable=False)  # JSON array
    pending_action = Column(String, nullable=True)
    context = Column(Text, nullable=False)  # JSON object for additional state
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for fast lookups
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_thread_id', 'thread_id'),
        Index('idx_updated_at', 'updated_at'),
    )


class ConversationStore:
    """
    Manages PostgreSQL connection and conversation CRUD operations.
    """

    def __init__(self, database_url: str = None):
        """
        Initialize database connection.

        Args:
            database_url: PostgreSQL URL. If None, reads from DATABASE_URL env var.
                         Format: postgresql://user:password@host:port/dbname
        """
        if database_url is None:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError(
                    "DATABASE_URL environment variable not set. "
                    "Set it to your PostgreSQL connection string."
                )

        # Handle Railway's postgres:// URLs (need postgresql://)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_conversation(
        self,
        user_id: str,
        thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get conversation by user_id and thread_id.

        Returns:
            Dict with conversation data or None if not found.
        """
        with self.get_session() as session:
            conversation = session.query(Conversation).filter_by(
                user_id=user_id,
                thread_id=thread_id
            ).first()

            if not conversation:
                return None

            return {
                "user_id": conversation.user_id,
                "thread_id": conversation.thread_id,
                "sender_email": conversation.sender_email,
                "message_history": json.loads(conversation.message_history),
                "pending_action": conversation.pending_action,
                "context": json.loads(conversation.context),
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat()
            }

    def save_conversation(
        self,
        user_id: str,
        thread_id: str,
        sender_email: str,
        message_history: List[Dict[str, Any]],
        pending_action: Optional[str] = None,
        context: Dict[str, Any] = None
    ):
        """
        Save or update conversation (upsert).

        Args:
            user_id: User's email address
            thread_id: Gmail thread ID
            sender_email: Email address of sender
            message_history: List of LangChain message dicts
            pending_action: Optional state tracking (e.g., "awaiting_connection")
            context: Additional state dictionary
        """
        if context is None:
            context = {}

        with self.get_session() as session:
            conversation = session.query(Conversation).filter_by(
                user_id=user_id,
                thread_id=thread_id
            ).first()

            if conversation:
                # Update existing
                conversation.sender_email = sender_email
                conversation.message_history = json.dumps(message_history)
                conversation.pending_action = pending_action
                conversation.context = json.dumps(context)
                conversation.updated_at = datetime.utcnow()
            else:
                # Create new
                conversation = Conversation(
                    user_id=user_id,
                    thread_id=thread_id,
                    sender_email=sender_email,
                    message_history=json.dumps(message_history),
                    pending_action=pending_action,
                    context=json.dumps(context)
                )
                session.add(conversation)

    def delete_conversation(self, user_id: str, thread_id: str):
        """Delete a conversation."""
        with self.get_session() as session:
            session.query(Conversation).filter_by(
                user_id=user_id,
                thread_id=thread_id
            ).delete()

    def get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user, ordered by most recent first.
        """
        with self.get_session() as session:
            conversations = session.query(Conversation).filter_by(
                user_id=user_id
            ).order_by(Conversation.updated_at.desc()).all()

            return [
                {
                    "user_id": conv.user_id,
                    "thread_id": conv.thread_id,
                    "sender_email": conv.sender_email,
                    "message_history": json.loads(conv.message_history),
                    "pending_action": conv.pending_action,
                    "context": json.loads(conv.context),
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                }
                for conv in conversations
            ]


# Global store instance (singleton)
_store: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    """
    Get or create the global conversation store.

    Uses DATABASE_URL environment variable for PostgreSQL connection.
    """
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
