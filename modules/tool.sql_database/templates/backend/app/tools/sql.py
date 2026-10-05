"""SQL tools: list tables, describe a table, run a query.

Read-only mode rejects anything that isn't a SELECT / WITH / EXPLAIN / SHOW query
and, on Postgres, also runs inside a read-only transaction. Still connect with a
database user that only has read permissions.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache

from langchain_core.tools import BaseTool, tool
from sqlalchemy import Engine, create_engine, inspect, text

READ_ONLY_START = re.compile(r"^\s*(select|with|explain|show|pragma|describe)\b", re.IGNORECASE)
WRITE_WORDS = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge|replace)\b", re.IGNORECASE)


def is_read_only(query: str) -> bool:
    body = query.strip().rstrip(";")
    return bool(READ_ONLY_START.match(body)) and ";" not in body and not WRITE_WORDS.search(body)


@lru_cache
def _engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def make_sql_tools(url_env: str, read_only: bool = True, max_rows: int = 50) -> list[BaseTool]:
    def engine() -> Engine:
        url = os.environ.get(url_env)
        if not url:
            raise RuntimeError(f"Set {url_env} in .env to the database connection string.")
        return _engine(url)

    @tool
    def sql_list_tables() -> str:
        """List the tables in the database."""
        try:
            return ", ".join(inspect(engine()).get_table_names()) or "No tables."
        except Exception as exc:
            return f"Error: {exc}"

    @tool
    def sql_describe_table(table: str) -> str:
        """Show the columns and types of one table. Call this before writing a query."""
        try:
            cols = inspect(engine()).get_columns(table)
        except Exception as exc:
            return f"Error: {exc}"
        return "\n".join(f"{c['name']}: {c['type']}" for c in cols)

    @tool
    def sql_query(query: str) -> str:
        """Run one SQL query and return up to the row limit as a table."""
        if read_only and not is_read_only(query):
            return "Rejected: only single read-only queries (SELECT, WITH, EXPLAIN) are allowed."
        try:
            with engine().connect() as conn:
                if read_only and conn.dialect.name == "postgresql":
                    conn.execute(text("SET TRANSACTION READ ONLY"))
                result = conn.execute(text(query))
                if not result.returns_rows:
                    return "Query ran; no rows returned."
                cols = list(result.keys())
                rows = result.fetchmany(max_rows)
        except Exception as exc:
            return f"Error: {exc}"
        lines = [" | ".join(cols)] + [" | ".join(str(v) for v in row) for row in rows]
        suffix = f"\n(first {max_rows} rows)" if len(rows) == max_rows else ""
        return "\n".join(lines) + suffix

    return [sql_list_tables, sql_describe_table, sql_query]
