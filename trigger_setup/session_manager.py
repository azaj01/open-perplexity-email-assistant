import os
from typing import Dict, Any
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from constants import initialise_composio_client, initialise_chatmodel


class SessionManager:
    """Manages Composio Tool Router sessions and LangGraph agent."""

    def __init__(self):
        self.composio_client = initialise_composio_client()
        self.llm = initialise_chatmodel()

    async def create_session_and_graph(self, user_id: str) -> Dict[str, Any]:
        """Create Tool Router session and agent for user."""
        print(f"🔧 Creating Tool Router session for: {user_id}")

        session = self.composio_client.experimental.tool_router.create_session(
            user_id=user_id,
            toolkits=[
                {'toolkit': 'gmail', 'auth_config': os.getenv("GMAIL_AUTH_CONFIG")},
            ],
            manually_manage_connections=True
        )

        mcp_url = session['url']
        print(f"✅ Session URL: {mcp_url[:60]}...")

        graph = await self._build_graph(mcp_url)

        return {'session': session, 'mcp_url': mcp_url, 'graph': graph}

    async def _build_graph(self, mcp_url: str):
        """Build LangGraph agent with MCP tools."""
        mcp_client = MultiServerMCPClient({
            "composio": {"url": mcp_url, "transport": "streamable_http"}
        })

        tools = await mcp_client.get_tools()
        print(f"🔨 Loaded {len(tools)} tools from Tool Router")

        system_prompt = """You are an intelligent email assistant. You receive emails and execute instructions.

**INSTRUCTIONS:**
1. Analyze each email content carefully
2. Determine what action the sender wants you to take
3. Use the available Composio tools to complete the task
4. Execute the instructions in the email
5. DO NOT send a reply email on your own under ANY circumstances
6. After completing the task, return your response explaining what you did, if there are any links, include them as plaintext.

**RESPONSE FORMAT:**
- Format your response in HTML (not markdown)
- Use proper HTML tags: <h2>, <p>, <ul>, <li>, <a>, <strong>, etc.
- If no connections are found, initiate a connection and obtain the connection link.
- If you receive a connection link (redirect_url) from COMPOSIO_MANAGE_CONNECTIONS, include it as a clickable HTML link
- Example: <p>Please connect your account: <a href="https://link">Click here to connect</a></p>

**IMPORTANT:**
- Never use any email sending or replying tools. Your response will be automatically sent as a reply.
- You have access to the full conversation history, so you can reference previous emails and context.

The tool router will automatically discover, authenticate, and execute the right tools across 500+ apps.
Be helpful, efficient, and professional."""

        agent = create_react_agent(self.llm, tools, prompt=system_prompt)
        return agent


_session_manager = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
