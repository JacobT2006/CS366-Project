"""Read the documented query catalog from queries.sql."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QUERY_HEADER = re.compile(
    r"^-- Query: (Q\d+) \| Level: (Level [23]) \| Title: ([^\r\n]+)\r?\n"
    r"-- Description: ([^\r\n]+)\r?\n"
    r"-- Useful for: ([^\r\n]+)\r?\n",
    re.MULTILINE,
)
QUERY_MARKER = re.compile(r"(?m)^-- Query: Q\d+ \| Level: Level [23] \| Title: ")


@dataclass(frozen=True)
class QueryDefinition:
    query_id: str
    level: str
    title: str
    description: str
    usefulness: str
    sql: str


def load_queries(path: Path | None = None) -> tuple[QueryDefinition, ...]:
    source_path = path or ROOT / "queries.sql"
    source = source_path.read_text(encoding="utf-8")
    definitions: list[QueryDefinition] = []
    for match in QUERY_HEADER.finditer(source):
        following_marker = QUERY_MARKER.search(source, match.end())
        end = following_marker.start() if following_marker else len(source)
        statement = source[match.end():end].strip()
        if not statement.endswith(";"):
            raise ValueError(f"SQL statement for {match.group(1)} is missing its semicolon")
        definitions.append(
            QueryDefinition(
                query_id=match.group(1),
                level=match.group(2),
                title=match.group(3).strip(),
                description=match.group(4).strip(),
                usefulness=match.group(5).strip(),
                sql=statement.rstrip()[:-1].strip(),
            )
        )
    definitions = tuple(definitions)
    if len(definitions) != 10:
        raise ValueError(f"Expected 10 documented queries in {source_path}; found {len(definitions)}")
    return definitions
