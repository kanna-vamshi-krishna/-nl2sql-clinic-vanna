"""
vanna_setup.py
Initializes the Vanna 2.0 Agent with:
  - GeminiLlmService (Google Gemini flash - free via AI Studio)
  - ToolRegistry with RunSqlTool, VisualizeDataTool, and memory tools
  - DemoAgentMemory (in-memory learning system)
  - SqliteRunner pointing at clinic.db
  - A simple DefaultUserResolver that identifies all callers as 'default_user'
"""

import os
from dotenv import load_dotenv

from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
)
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.google import GeminiLlmService

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "clinic.db")

# ---------------------------------------------------------------------------
# User resolver: every request maps to a single default user
# ---------------------------------------------------------------------------

class DefaultUserResolver(UserResolver):
    """Maps every incoming request to a single default user (no auth needed)."""

    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id="default_user",
            username="clinic_user",
            email="user@clinic.local",
            group_memberships=["user", "admin"],
        )


# ---------------------------------------------------------------------------
# Build the agent - call this once and reuse the returned instance
# ---------------------------------------------------------------------------

def build_agent() -> Agent:
    """Construct and return a fully-wired Vanna 2.0 Agent."""

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set. "
            "Get a free key at https://aistudio.google.com/apikey and add it to your .env file."
        )

    # 1. LLM Service - Google Gemini flash (free tier)
    llm_service = GeminiLlmService(
        api_key=api_key,
        model="gemini-2.0-flash",
    )

    # 2. SQL Runner pointing at our SQLite clinic database
    sql_runner = SqliteRunner(database_path=DB_PATH)

    # 3. Agent memory (in-memory; persists for the lifetime of the process)
    agent_memory = DemoAgentMemory(max_items=10_000)

    # 4. Tool Registry
    registry = ToolRegistry()
    registry.register_local_tool(RunSqlTool(sql_runner=sql_runner), access_groups=["user", "admin"])
    registry.register_local_tool(VisualizeDataTool(), access_groups=["user", "admin"])
    registry.register_local_tool(SaveQuestionToolArgsTool(), access_groups=["user", "admin"])
    registry.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=["user", "admin"])

    # 5. User resolver
    user_resolver = DefaultUserResolver()

    # 6. Agent configuration
    config = AgentConfig(
        max_tool_iterations=10,
        stream_responses=False,   # we consume the full stream in FastAPI
        temperature=0.2,          # low temp for deterministic SQL generation
    )

    # 7. Assemble the Agent
    agent = Agent(
        llm_service=llm_service,
        tool_registry=registry,
        user_resolver=user_resolver,
        agent_memory=agent_memory,
        config=config,
    )

    return agent


# Singleton - import this in main.py and seed_memory.py
agent = build_agent()
memory = agent.agent_memory   # expose for seeding