"""TTD-LLM's schema-bound, read-only analytics engine. Models never execute SQL."""
from __future__ import annotations

import csv
import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

MAX_FILE_BYTES = 10_000_000
MAX_IMPORT_ROWS = 10_000
MAX_QUERY_ROWS = 50
OPS = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
FUNCS = {"count": "COUNT", "sum": "SUM", "avg": "AVG", "min": "MIN", "max": "MAX"}
NUMERIC = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


class TTDValidationError(ValueError):
    """Unsupported source, access, or model-generated plan."""


def ident(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128 or "\x00" in value:
        raise TTDValidationError("invalid database identifier")
    return '"' + value.replace('"', '""') + '"'


def number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value if not isinstance(value, float) or math.isfinite(value) else None
    if not isinstance(value, str) or not NUMERIC.fullmatch(value.strip()):
        return None
    text = value.strip()
    if re.match(r"[+-]?0\d", text):
        return None  # preserve postal codes and identifiers
    n = float(text) if any(char in text for char in ".eE") else int(text)
    return n if not isinstance(n, float) or math.isfinite(n) else None


def safe_cell(value: Any) -> Any:
    if isinstance(value, bytes):
        return "<binary omitted>"
    if value is None or isinstance(value, (int, float)):
        return value
    value = str(value)
    return value[:500] + ("...[truncated]" if len(value) > 500 else "")


class DataCatalog:
    """An explicitly selected file and its schema-authorized SQLite tables."""

    def __init__(self, source: str | Path, kind: str = "sqlite", tables: list[str] | None = None):
        if kind not in {"sqlite", "csv", "json"}:
            raise TTDValidationError("kind must be sqlite, csv, or json")
        self.path = Path(source).expanduser().resolve(strict=True)
        if not self.path.is_file():
            raise TTDValidationError("source must be a regular file")
        self.kind = kind
        if kind == "sqlite":
            uri = "file:" + quote(str(self.path), safe="/") + "?mode=ro"
            self.conn = sqlite3.connect(uri, uri=True, timeout=2)
        else:
            if self.path.stat().st_size > MAX_FILE_BYTES:
                raise TTDValidationError("CSV/JSON exceeds the 10 MB import limit")
            self.conn = sqlite3.connect(":memory:")
            self._import_data()
        self.conn.execute("PRAGMA query_only=ON")
        self.conn.execute("PRAGMA trusted_schema=OFF")
        self.conn.row_factory = sqlite3.Row
        self._schema = self._inspect()
        self._allow = set(tables) if tables else set(self._schema)
        if not self._allow or not self._allow.issubset(self._schema):
            self.close()
            raise TTDValidationError("requested tables are not in the source")

    def _import_data(self) -> None:
        if self.kind == "csv":
            with self.path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                columns = reader.fieldnames or []
                rows = []
                for index, row in enumerate(reader):
                    if index >= MAX_IMPORT_ROWS or None in row:
                        raise TTDValidationError("CSV exceeds row limit or has extra fields")
                    rows.append(row)
        else:
            with self.path.open(encoding="utf-8") as handle:
                rows = json.load(handle)
            if not isinstance(rows, list) or len(rows) > MAX_IMPORT_ROWS or any(
                not isinstance(row, dict) for row in rows
            ):
                raise TTDValidationError("JSON must be an array of 10,000 or fewer objects")
            columns = list(dict.fromkeys(c for row in rows for c in row))
        if not columns or len(columns) > 64 or len(set(columns)) != len(columns):
            raise TTDValidationError("source must contain 1-64 unique columns")
        for column in columns:
            ident(column)
        for row in rows:
            if any(value is not None and not isinstance(value, (str, bool, int, float))
                   or isinstance(value, float) and not math.isfinite(value)
                   for value in row.values()):
                raise TTDValidationError("nested or nonfinite data is unsupported")
        kinds = {}
        for col in columns:
            observed = [row.get(col) for row in rows if row.get(col) not in (None, "")]
            numeric = bool(observed) and all(number(v) is not None for v in observed)
            kinds[col] = ("REAL" if numeric and any(isinstance(number(v), float) for v in observed)
                          else "INTEGER" if numeric else "TEXT")
        self.conn.execute("CREATE TABLE data (" + ", ".join(ident(c) + " " + kinds[c] for c in columns) + ")")
        values = [tuple(number(row.get(c)) if kinds[c] != "TEXT" and row.get(c) not in (None, "")
                        else None if row.get(c) in (None, "") else str(row[c])
                        for c in columns) for row in rows]
        self.conn.executemany("INSERT INTO data VALUES (" + ",".join("?" for _ in columns) + ")", values)
        self.conn.commit()

    def _inspect(self) -> dict[str, dict[str, str]]:
        schema = {}
        for (table,) in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            if len(table) > 128:
                continue
            columns = {info[1]: info[2] or "UNKNOWN"
                       for info in self.conn.execute("PRAGMA table_info(" + ident(table) + ")")
                       if len(info[1]) <= 128}
            if columns:
                schema[table] = columns
        return schema

    def schema(self) -> dict[str, Any]:
        return {"source": self.path.name, "kind": self.kind,
                "tables": {table: self._schema[table] for table in sorted(self._allow)}}

    def compile_plan(self, plan: dict[str, Any]) -> tuple[str, list[Any]]:
        allowed_keys = {"table", "select", "aggregate", "group_by", "filters", "order_by", "limit"}
        if not isinstance(plan, dict) or set(plan) - allowed_keys:
            raise TTDValidationError("unsupported query plan fields")
        table = plan.get("table")
        if not isinstance(table, str) or table not in self._allow:
            raise TTDValidationError("table not allowed")
        columns = self._schema[table]
        group = plan.get("group_by", [])
        select = plan.get("select", [])
        if (not isinstance(group, list) or len(group) > 3 or len(set(map(str, group))) != len(group)
                or any(not isinstance(c, str) or c not in columns for c in group)):
            raise TTDValidationError("invalid group_by")
        if (not isinstance(select, list) or len(set(map(str, select))) != len(select)
                or any(not isinstance(c, str) or c not in columns for c in select)):
            raise TTDValidationError("invalid select")
        aggregate = plan.get("aggregate")
        if aggregate is not None:
            if not isinstance(aggregate, dict) or set(aggregate) != {"function", "column"}:
                raise TTDValidationError("aggregate requires function and column")
            fn, col = aggregate["function"], aggregate["column"]
            if (not isinstance(fn, str) or fn not in FUNCS or not isinstance(col, str)
                    or col != "*" and col not in columns or col == "*" and fn != "count"):
                raise TTDValidationError("unsupported aggregate")
            if select and select != group:
                raise TTDValidationError("aggregate select must equal group_by")
            projection = [ident(c) for c in group] + [
                FUNCS[fn] + "(" + ("*" if col == "*" else ident(col)) + ') AS "metric"'
            ]
            sorts = set(group) | {"metric"}
        else:
            if group:
                raise TTDValidationError("group_by requires aggregate")
            projection = [ident(c) for c in (select or list(columns))]
            sorts = set(select or columns)
        sql = "SELECT " + ", ".join(projection) + " FROM " + ident(table)
        filters = plan.get("filters", [])
        if not isinstance(filters, list) or len(filters) > 8:
            raise TTDValidationError("filters must be a list with at most eight conditions")
        predicates, params = [], []
        for condition in filters:
            if not isinstance(condition, dict) or set(condition) != {"column", "op", "value"}:
                raise TTDValidationError("invalid filter")
            col, op, value = condition["column"], condition["op"], condition["value"]
            if not isinstance(col, str) or col not in columns or not isinstance(op, str):
                raise TTDValidationError("unrecognized filter")
            if (value is not None and not isinstance(value, (str, int, float, bool))
                    or isinstance(value, str) and len(value) > 500
                    or isinstance(value, float) and not math.isfinite(value)):
                raise TTDValidationError("filter requires a bounded scalar")
            if op == "contains" and isinstance(value, str):
                escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                predicates.append(ident(col) + " LIKE ? ESCAPE '\\'")
                params.append("%" + escaped + "%")
            elif op in OPS:
                predicates.append(ident(col) + " " + OPS[op] + " ?")
                params.append(value)
            else:
                raise TTDValidationError("unsupported filter operator")
        # Do not let a model combine magnitudes, dollars, populations or citations.
        # The canonical public dataset always names the measure and source.
        if (table == "open_records" and {"source_id", "measure", "metric_unit"}.issubset(columns)
                and aggregate is not None and aggregate["column"] == "metric_value"
                and aggregate["function"] in {"sum", "avg", "min", "max"}
                and not any(condition["column"] == "measure" and condition["op"] == "eq"
                            and isinstance(condition["value"], str)
                            for condition in filters)):
            raise TTDValidationError("filter metric_value aggregates by measure to avoid mixed units")
        if predicates:
            sql += " WHERE " + " AND ".join(predicates)
        if aggregate is not None and group:
            sql += " GROUP BY " + ", ".join(ident(c) for c in group)
        order = plan.get("order_by")
        if order is not None:
            if not isinstance(order, dict) or set(order) != {"column", "direction"}:
                raise TTDValidationError("invalid order_by")
            key, direction = order["column"], order["direction"]
            if not isinstance(key, str) or key not in sorts or direction not in {"asc", "desc"}:
                raise TTDValidationError("invalid sort column or direction")
            sql += " ORDER BY " + ident(key) + (" DESC" if direction == "desc" else " ASC")
        limit = plan.get("limit", 25)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_QUERY_ROWS:
            raise TTDValidationError("limit must be between 1 and 50")
        return sql + " LIMIT ?", params + [limit]

    def execute(self, plan: dict[str, Any]) -> dict[str, Any]:
        sql, params = self.compile_plan(plan)
        counter = 0

        def budget() -> int:
            nonlocal counter
            counter += 1
            return int(counter > 50_000)

        self.conn.set_progress_handler(budget, 1000)
        try:
            raw = self.conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError as exc:
            raise TTDValidationError("query stopped: invalid or resource-heavy plan") from exc
        finally:
            self.conn.set_progress_handler(None, 0)
        rows = [{key: safe_cell(value) for key, value in dict(row).items()} for row in raw]
        return {"rows": rows, "returned_rows": len(rows), "row_limit": params[-1],
                "evidence": {"source": self.path.name, "kind": self.kind,
                             "table": plan["table"], "sql": sql, "params": params}}

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "DataCatalog":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()
