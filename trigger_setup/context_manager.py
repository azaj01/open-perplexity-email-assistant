"""
Context window management for conversation history.

Handles smart loading of conversation context to avoid token limits:
- Keeps recent messages in full detail
- Summarizes older messages
- Drops very old messages
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from database import get_conversation_store


class ContextManager:
    """
    Manages conversation context with smart window sizing.

    Strategy:
    1. Keep last N messages in full detail (recent_window_size)
    2. Summarize messages older than X hours (summarize_after_hours)
    3. Drop messages older than Y days (drop_after_days)
    """

    def __init__(
        self,
        recent_window_size: int = 10,
        summarize_after_hours: int = 48,
        drop_after_days: int = 7
    ):
        self.recent_window_size = recent_window_size
        self.summarize_after_hours = summarize_after_hours
        self.drop_after_days = drop_after_days
        self.db = get_conversation_store()

    def load_conversation_context(
        self,
        user_id: str,
        thread_id: str
    ) -> List[BaseMessage]:
        """
        Load conversation context with smart windowing.

        Returns:
            List of LangChain messages ready for the agent
        """
        # Get conversation from database
        conversation = self.db.get_conversation(user_id, thread_id)

        if not conversation:
            # New conversation
            return []

        # Get all message history
        all_messages = conversation['message_history']

        if len(all_messages) <= self.recent_window_size:
            # Short conversation, return everything
            return self._deserialize_messages(all_messages)

        # Apply sliding window: keep last N messages
        recent_messages = all_messages[-self.recent_window_size:]

        # TODO: Add summarization for older messages
        # For now, just use recent window

        return self._deserialize_messages(recent_messages)

    def save_conversation_context(
        self,
        user_id: str,
        thread_id: str,
        sender_email: str,
        messages: List[BaseMessage],
        pending_action: Optional[str] = None
    ):
        """
        Save updated conversation context to database.

        Args:
            user_id: User's email (sender)
            thread_id: Gmail thread ID
            sender_email: Email address of sender
            messages: Updated full message history
            pending_action: Optional state tracking
        """
        # Serialize messages to dict format
        message_dicts = self._serialize_messages(messages)

        # Save to database
        self.db.save_conversation(
            user_id=user_id,
            thread_id=thread_id,
            sender_email=sender_email,
            message_history=message_dicts,
            pending_action=pending_action
        )

    def _serialize_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Convert LangChain messages to dict format for storage."""
        serialized = []
        for msg in messages:
            msg_dict = {
                "type": msg.__class__.__name__,
                "content": msg.content,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Preserve additional fields
            if hasattr(msg, 'additional_kwargs'):
                msg_dict['additional_kwargs'] = msg.additional_kwargs

            serialized.append(msg_dict)

        return serialized

    def _deserialize_messages(self, message_dicts: List[Dict[str, Any]]) -> List[BaseMessage]:
        """Convert dict format back to LangChain messages."""
        messages = []

        for msg_dict in message_dicts:
            msg_type = msg_dict.get('type', 'HumanMessage')
            content = msg_dict.get('content', '')

            if msg_type == 'HumanMessage':
                messages.append(HumanMessage(content=content))
            elif msg_type == 'AIMessage':
                messages.append(AIMessage(content=content))
            elif msg_type == 'SystemMessage':
                messages.append(SystemMessage(content=content))
            else:
                # Fallback to HumanMessage
                messages.append(HumanMessage(content=content))

        return messages

    def get_pending_action(self, user_id: str, thread_id: str) -> Optional[str]:
        """Get pending action for a conversation (e.g., 'awaiting_connection')."""
        conversation = self.db.get_conversation(user_id, thread_id)
        if conversation:
            return conversation.get('pending_action')
        return None

    def clear_pending_action(self, user_id: str, thread_id: str):
        """Clear pending action after it's been resolved."""
        conversation = self.db.get_conversation(user_id, thread_id)
        if conversation:
            self.db.save_conversation(
                user_id=user_id,
                thread_id=thread_id,
                sender_email=conversation['sender_email'],
                message_history=conversation['message_history'],
                pending_action=None
            )


# Global instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get or create the global context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
