import os
from typing import Dict, Any
from constants import initialise_composio_client


class EmailHandler:
    """Handles email parsing and reply operations."""

    def __init__(self):
        self.composio_client = initialise_composio_client()

    def parse_trigger_payload(self, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Composio email trigger payload."""
        payload = trigger_data.get("payload", {})

        sender_full = payload.get("sender", "")
        if "<" in sender_full and ">" in sender_full:
            sender_email = sender_full.split("<")[1].split(">")[0]
        else:
            sender_email = sender_full or "unknown@email.com"

        metadata = trigger_data.get("metadata", {})
        connected_account = metadata.get("connected_account", {})
        connected_account_id = connected_account.get("id")

        return {
            "sender_email": sender_email,
            "subject": payload.get("subject", "No Subject"),
            "body": payload.get("message_text", ""),
            "thread_id": payload.get("thread_id"),
            "message_id": payload.get("message_id"),
            "connected_account_id": connected_account_id
        }

    def send_reply(self, connected_account_id: str, thread_id: str, recipient_email: str, message_body: str) -> Dict[str, Any]:
        """Send a reply to an email thread."""
        print(f"📧 Sending reply to {recipient_email}")

        result = self.composio_client.tools.execute(
            "GMAIL_REPLY_TO_THREAD",
            connected_account_id=connected_account_id,
            arguments={
                "thread_id": thread_id,
                "recipient_email": recipient_email,
                "message_body": message_body,
                "is_html": True,
                "user_id": "me"
            }
        )
        print(f"✅ Reply sent successfully!")
        return result


_email_handler = None


def get_email_handler() -> EmailHandler:
    global _email_handler
    if _email_handler is None:
        _email_handler = EmailHandler()
    return _email_handler
