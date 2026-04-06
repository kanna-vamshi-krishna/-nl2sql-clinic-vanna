"""
main.py
FastAPI backend for the NL2SQL clinic chatbot.

Endpoints:
  POST /chat    — Ask a question in English, get SQL + results + optional chart
  GET  /health  — Liveness probe with memory stats

Start the server:
    uvicorn main:app --port 8000 --reload
"""

import asyncio
import json
import re
import sqlite3
import time
import logging
import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from vanna.core.user import RequestContext
from vanna import (
    DataFrameComponent,
    ArtifactComponent,
    RichTextComponent,
    SimpleTextComponent,
)

from vanna_setup import agent, memory

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nl2sql")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Clinic NL2SQL API",
    description="Ask questions in plain English and get SQL results from the clinic database.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH", "clinic.db")

# ---------------------------------------------------------------------------
# Simple in-memory query cache
# ---------------------------------------------------------------------------

_cache: dict[str, dict] = {}
_CACHE_MAX = 200

# ---------------------------------------------------------------------------
# SQL Validation
# ---------------------------------------------------------------------------

_BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE|GRANT|REVOKE|SHUTDOWN"
    r"|xp_|sp_|sqlite_master|sqlite_sequence|sqlite_stat)\b",
    re.IGNORECASE,
)

_SELECT_PATTERN = re.compile(r"^\s*SELECT\b", re.IGNORECASE)


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Returns (True, "") if the SQL is safe to run.
    Returns (False, reason) otherwise.
    """
    if not sql or not sql.strip():
        return False, "Empty SQL query."

    if not _SELECT_PATTERN.match(sql):
        return False, "Only SELECT statements are allowed."

    match = _BLOCKED_KEYWORDS.search(sql)
    if match:
        return False, f"Blocked keyword detected: '{match.group()}'. Query rejected for safety."

    return True, ""


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, description="Question in plain English")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for multi-turn chats")


class ChatResponse(BaseModel):
    message: str
    sql_query: Optional[str] = None
    columns: Optional[list[str]] = None
    rows: Optional[list[list[Any]]] = None
    row_count: Optional[int] = None
    chart: Optional[dict] = None
    chart_type: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------

def _extract_sql(text: str) -> Optional[str]:
    """Pull the first SQL SELECT from a block of text."""
    # Try ```sql ... ``` blocks first
    block = re.search(r"```(?:sql)?\s*(SELECT.*?)```", text, re.DOTALL | re.IGNORECASE)
    if block:
        return block.group(1).strip()
    # Bare SELECT statement
    sel = re.search(r"(SELECT\b.*?;)", text, re.DOTALL | re.IGNORECASE)
    if sel:
        return sel.group(1).strip()
    return None


def _parse_chart(content: str) -> Optional[dict]:
    """Try to extract a Plotly JSON figure from an artifact/HTML blob."""
    # Look for JSON object that looks like a Plotly spec
    match = re.search(r"(\{[^{}]*\"data\"\s*:\s*\[.*?\})", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


async def _run_agent(question: str, conversation_id: Optional[str]) -> dict:
    """
    Send the question to the Vanna agent and gather all yielded UiComponents.
    Returns a dict with keys: message, sql_query, columns, rows, row_count, chart, chart_type
    """
    ctx = RequestContext()

    result: dict[str, Any] = {
        "message": "",
        "sql_query": None,
        "columns": None,
        "rows": None,
        "row_count": None,
        "chart": None,
        "chart_type": None,
    }

    text_parts: list[str] = []
    df_component: Optional[DataFrameComponent] = None
    artifact_content: Optional[str] = None

    logger.info("Sending question to agent: %s", question)
    start = time.perf_counter()

    async for component in agent.send_message(
        request_context=ctx,
        message=question,
        conversation_id=conversation_id,
    ):
        rich = getattr(component, "rich_component", None)
        simple = getattr(component, "simple_component", None)

        # Collect rich text / code
        if isinstance(rich, RichTextComponent):
            text_parts.append(rich.content)
            # Try to pull SQL from code blocks
            if rich.code_language and rich.code_language.lower() in ("sql", ""):
                if not result["sql_query"]:
                    sql = _extract_sql(rich.content)
                    if sql:
                        result["sql_query"] = sql

        # DataFrame → tabular results
        if isinstance(rich, DataFrameComponent):
            df_component = rich

        # Artifact → chart HTML
        if isinstance(rich, ArtifactComponent):
            artifact_content = rich.content

        # Simple text fallback
        if isinstance(simple, SimpleTextComponent):
            text_parts.append(simple.text)

    elapsed = time.perf_counter() - start
    logger.info("Agent finished in %.2fs", elapsed)

    # Assemble message
    result["message"] = " ".join(text_parts).strip() or "Query processed successfully."

    # Pull SQL from message text if not already found
    if not result["sql_query"]:
        result["sql_query"] = _extract_sql(result["message"])

    # Fill tabular data from DataFrame component
    if df_component is not None:
        result["columns"] = df_component.columns
        result["rows"] = [
            [row.get(col) for col in df_component.columns]
            for row in df_component.rows
        ]
        result["row_count"] = len(df_component.rows)

    # Fall back: if we have SQL but no rows, run it ourselves
    if result["sql_query"] and result["rows"] is None:
        ok, reason = validate_sql(result["sql_query"])
        if ok:
            try:
                con = sqlite3.connect(DB_PATH)
                cur = con.execute(result["sql_query"])
                cols = [d[0] for d in cur.description] if cur.description else []
                raw_rows = cur.fetchall()
                con.close()
                result["columns"] = cols
                result["rows"] = [list(r) for r in raw_rows]
                result["row_count"] = len(raw_rows)
            except Exception as exc:
                logger.warning("Fallback SQL execution failed: %s", exc)

    # Chart from artifact
    if artifact_content:
        chart = _parse_chart(artifact_content)
        if chart:
            result["chart"] = chart
            data = chart.get("data", [])
            if data:
                result["chart_type"] = data[0].get("type", "chart")

    return result


# ---------------------------------------------------------------------------
# Rate limiting (simple in-memory token bucket per IP)
# ---------------------------------------------------------------------------

_rate_buckets: dict[str, tuple[float, int]] = {}
_RATE_LIMIT = 20       # requests
_RATE_WINDOW = 60.0    # seconds


def _check_rate_limit(ip: str) -> bool:
    now = time.monotonic()
    if ip in _rate_buckets:
        window_start, count = _rate_buckets[ip]
        if now - window_start < _RATE_WINDOW:
            if count >= _RATE_LIMIT:
                return False
            _rate_buckets[ip] = (window_start, count + 1)
        else:
            _rate_buckets[ip] = (now, 1)
    else:
        _rate_buckets[ip] = (now, 1)
    return True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    """
    Ask a question in plain English.
    The agent generates SQL, executes it against clinic.db, and returns
    the results along with an optional Plotly chart.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait a moment before sending another request.",
        )

    # Input validation
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    logger.info("[%s] /chat question=%r", client_ip, question)

    # Cache lookup
    cache_key = question.lower()
    if cache_key in _cache:
        logger.info("Cache hit for: %s", question)
        return ChatResponse(**_cache[cache_key])

    # Run the agent
    try:
        result = await _run_agent(question, body.conversation_id)
    except Exception as exc:
        logger.exception("Unexpected error in /chat")
        return ChatResponse(
            message="An unexpected error occurred while processing your question.",
            error=str(exc),
        )

    # Validate generated SQL before surfacing
    if result.get("sql_query"):
        ok, reason = validate_sql(result["sql_query"])
        if not ok:
            logger.warning("SQL validation failed: %s | SQL: %s", reason, result["sql_query"])
            return ChatResponse(
                message="The system generated an unsafe SQL query and it was blocked.",
                error=reason,
            )

    # Handle no results
    if result.get("rows") is not None and len(result["rows"]) == 0:
        result["message"] = result["message"] or "No data found for your query."

    response = ChatResponse(**result)

    # Cache successful responses
    if result.get("rows") is not None:
        if len(_cache) >= _CACHE_MAX:
            oldest = next(iter(_cache))
            del _cache[oldest]
        _cache[cache_key] = response.model_dump()

    return response


@app.get("/health")
async def health():
    """Liveness probe — checks DB connectivity and reports memory stats."""
    # DB check
    db_status = "connected"
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("SELECT 1")
        con.close()
    except Exception as exc:
        db_status = f"error: {exc}"

    # Memory stats
    ctx = RequestContext()
    try:
        recent = await memory.get_recent_memories(context=ctx, limit=10_000)
        memory_items = len(recent)
    except Exception:
        memory_items = -1

    return {
        "status": "ok",
        "database": db_status,
        "agent_memory_items": memory_items,
        "cache_entries": len(_cache),
    }


@app.get("/")
async def root():
    return {
        "message": "Clinic NL2SQL API is running.",
        "endpoints": {
            "POST /chat": "Ask a question in plain English",
            "GET /health": "Liveness probe",
            "GET /docs": "Interactive API docs (Swagger UI)",
        },
    }
