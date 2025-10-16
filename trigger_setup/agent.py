import json
import asyncio
import os
from langchain_core.messages import HumanMessage
from constants import initialise_composio_client
from email_handler import get_email_handler
from context_manager import get_context_manager
from session_manager import get_session_manager


async def process_email_trigger(trigger_data: dict):
    """Process incoming email trigger from Composio."""
    try:
        print("\n" + "="*80)
        print("📧 NEW EMAIL TRIGGER RECEIVED")
        print("="*80)
        print(json.dumps(trigger_data, indent=2))

        email_handler = get_email_handler()
        context_manager = get_context_manager()
        session_manager = get_session_manager()

        email_data = email_handler.parse_trigger_payload(trigger_data)
        user_id = email_data['sender_email']
        thread_id = email_data['thread_id']

        print(f"\n📨 From: {email_data['sender_email']}")
        print(f"📋 Subject: {email_data['subject']}")
        print(f"🧵 Thread ID: {thread_id}")
        print(f"📝 Body Preview: {email_data['body'][:200]}...")

        inbox_owner_email = os.getenv('GMAIL_USER_ID', '').lower()
        if inbox_owner_email and user_id.lower() == inbox_owner_email:
            print(f"⚠️ Skipping - email is from assistant itself (avoiding loop)")
            return

        print(f"\n📚 Loading conversation history...")
        message_history = context_manager.load_conversation_context(user_id, thread_id)
        print(f"✅ Loaded {len(message_history)} previous messages")

        print(f"\n🔧 Creating Tool Router session...")
        session_data = await session_manager.create_session_and_graph(user_id)
        graph = session_data['graph']

        full_email_content = f"Subject: {email_data['subject']}\n\nFrom: {email_data['sender_email']}\n\n{email_data['body']}"
        new_message = HumanMessage(content=f"Process this email and execute the instructions:\n\n{full_email_content}")

        print(f"\n🤖 Running agent workflow...")
        current_messages = message_history + [new_message]
        result_messages = []
        agent_response = ""

        async for event in graph.astream({"messages": current_messages}):
            for value in event.values():
                if "messages" in value and value["messages"]:
                    for msg in value["messages"]:
                        result_messages.append(msg)
                        current_messages.append(msg)

                        if hasattr(msg, 'content') and msg.content:
                            print(f"\n💬 Agent: {msg.content[:500]}...")
                            if not hasattr(msg, 'tool_calls') or not msg.tool_calls:
                                agent_response = msg.content

        print(f"\n💾 Saving conversation to database...")
        context_manager.save_conversation_context(
            user_id=user_id,
            thread_id=thread_id,
            sender_email=email_data['sender_email'],
            messages=current_messages
        )

        print(f"\n✅ Email processed successfully!")
        print(f"🔨 Actions taken: {len([m for m in result_messages if hasattr(m, 'tool_calls') and m.tool_calls])}")
        print("="*80 + "\n")

        if thread_id and agent_response:
            print(f"📧 Sending reply...")
            connected_account_id = email_data.get('connected_account_id')

            try:
                email_handler.send_reply(
                    connected_account_id=connected_account_id,
                    thread_id=thread_id,
                    recipient_email=email_data['sender_email'],
                    message_body=agent_response
                )
            except Exception as reply_error:
                print(f"❌ Failed to send reply: {reply_error}")
                print(f"   Continuing without sending reply...")
        else:
            print(f"⚠️ Skipping reply - No thread_id or response")

    except Exception as e:
        print(f"\n❌ Error processing email trigger: {e}")
        import traceback
        traceback.print_exc()


def start_trigger_listener():
    """Start listening to email triggers using Composio's subscription API."""
    composio_client = initialise_composio_client()

    print("="*80)
    print("🚀 Starting Composio Email Trigger Listener")
    print("="*80)
    print("\n📡 Subscribing to email triggers...")
    print("💡 The agent will automatically process any emails sent to the monitored inbox")
    print("⚡ Press Ctrl+C to stop\n")

    listener = composio_client.triggers.subscribe()
    trigger_id = os.getenv('GMAIL_TRIGGER_ID')

    @listener.handle(trigger_id=trigger_id)
    def callback_function(event):
        print(f"🔔 Trigger received: {event.get('trigger_name', 'Unknown')}")
        asyncio.run(process_email_trigger(event))

    print("✅ Listener registered!")
    print("="*80 + "\n")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down trigger listener...")


async def main_interactive():
    """Interactive mode for testing without email triggers."""
    print("Composio Email Assistant (Interactive Mode)")
    user_id = input("Enter your user ID (email): ")

    session_manager = get_session_manager()
    session_data = await session_manager.create_session_and_graph(user_id)
    graph = session_data['graph']

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            async for event in graph.astream({"messages": [HumanMessage(content=user_input)]}):
                for value in event.values():
                    if "messages" in value and value["messages"]:
                        last_message = value["messages"][-1]
                        if hasattr(last_message, 'content') and last_message.content:
                            print("Assistant:", last_message.content)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            break


def main():
    """Main function - choose to run trigger listener or interactive mode."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "listen":
        start_trigger_listener()
    else:
        print("Composio Email Assistant")
        print("Usage:")
        print("  python agent.py listen    - Start listening to email triggers")
        print("  python agent.py           - Interactive mode (for testing)")
        print()
        asyncio.run(main_interactive())


if __name__ == "__main__":
    main()
