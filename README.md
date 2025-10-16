# Open Perplexity Email Assistant

An Open Source version of Perplexity Email Assistant powered by Composio's Tool Router, LangGraph, and MCP (Model Context Protocol).

## Features

- **Real-time email trigger listening** - Continuously monitors for new emails
- **Automatic tool discovery** - Finds and authenticates tools across 500+ apps with Composio's Tool Router
- **LangGraph-based agentic workflow** - Smart agent loop for complex tasks
- **MCP integration** - Standardized tool access via Model Context Protocol

## Setup

1. **Install dependencies:**
```bash
uv sync
```

2. **Configure environment variables:**
Create a `.env` file with:
```
OPENAI_API_KEY=your_openai_key
COMPOSIO_API_KEY=your_composio_key
```

3. **Set up email trigger in Composio Dashboard:**
   - Go to your Composio dashboard
   - Connect your Gmail/email account
   - Enable the `gmail_new_gmail_message` trigger
   - Note: The trigger setup is done via the dashboard, not programmatically

## Usage

### Production Mode (Trigger Listener)

Start the email trigger listener that continuously monitors for new emails:

```bash
cd trigger_setup
python agent.py listen
```

This will:
- Subscribe to email triggers from Composio
- Automatically process any emails sent to the monitored inbox
- Execute instructions found in email content
- Run continuously until stopped (Ctrl+C)

**How it works:**
1. User sends an email to your monitored inbox
2. Composio trigger fires and sends event to the listener
3. Agent reads the email content
4. Agent executes the instructions using tool router
5. Agent can optionally reply back to sender

### Interactive Mode (Testing)

For testing the agent without email triggers:

```bash
cd trigger_setup
python agent.py
```

Enter your user ID when prompted, then chat with the agent directly.

## Architecture

```
Email → Composio Trigger → Subscription Listener → Tool Router Session → MCP Client → LangGraph Agent
                                                                                        ↓
                                                                                   Tool Discovery
                                                                                        ↓
                                                                                   Authentication
                                                                                        ↓
                                                                                   Tool Execution
```

## How the Email Assistant Works

1. **Trigger Setup**: Configure Gmail trigger in Composio dashboard to monitor an inbox
2. **Subscription**: Agent subscribes to trigger events using Composio SDK
3. **Email Received**: When someone sends email to monitored inbox, trigger fires
4. **Processing**:
   - Creates tool router session for the user
   - Builds LangGraph workflow with MCP tools
   - Agent analyzes email and determines required actions
   - Uses meta tools (COMPOSIO_SEARCH_TOOLS, COMPOSIO_MANAGE_CONNECTIONS, COMPOSIO_MULTI_EXECUTE_TOOL)
   - Executes the requested tasks
5. **Response**: Optionally sends reply email back to sender

## Example Use Cases

- "Create a GitHub issue titled 'Bug in login' with description 'Users cannot log in'"
- "Schedule a meeting with john@example.com tomorrow at 2pm"
- "Search Slack for messages about 'project deadline' and summarize them"
- "Add a task to my Notion board: 'Review PR #123'"

The agent automatically figures out which apps to use and executes the tasks!

## References

- [Tool Router Docs](https://docs.composio.dev/docs/tool-router/quick-start)
- [Langgraph Docs](https://langchain-ai.github.io/langgraph/agents/mcp/)
- [Perplexity Email Assistant](https://www.perplexity.ai/hub/blog/a-personal-assistant-for-your-inbox)
