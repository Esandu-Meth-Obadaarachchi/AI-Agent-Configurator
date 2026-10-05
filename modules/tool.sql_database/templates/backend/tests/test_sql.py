from __future__ import annotations

import sqlite3

from app.tools.sql import is_read_only, make_sql_tools


def test_read_only_guard() -> None:
    assert is_read_only("SELECT * FROM users")
    assert is_read_only("with t as (select 1) select * from t")
    assert not is_read_only("DELETE FROM users")
    assert not is_read_only("SELECT 1; DROP TABLE users")


def test_query_against_sqlite(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db = tmp_path / "t.db"
    with sqlite3.connect(db) as conn:
        conn.execute("create table items (id integer, name text)")
        conn.execute("insert into items values (1, 'apple')")
    monkeypatch.setenv("TEST_SQL_URL", f"sqlite:///{db}")
    list_tables, describe, query = make_sql_tools("TEST_SQL_URL")
    assert "items" in list_tables.invoke({})
    assert "name" in describe.invoke({"table": "items"})
    assert "apple" in query.invoke({"query": "select name from items"})
    assert query.invoke({"query": "drop table items"}).startswith("Rejected")
